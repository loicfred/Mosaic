"""Deterministic 90-day cash projection and scenario simulation.

The projection is a transparent driver model, not a black box:

  inflows  = walk-in/POS sales run-rate (by weekday, seasonally adjusted)
           + open invoices collected at each customer's recent payment speed
           + future invoices at each customer's recent invoicing run-rate
  outflows = supplier purchases at the last-60-day run-rate
           + recurring commitments on their usual day of month
           + VAT due on the 20th after each quarter
           + other variable spending at the 90-day run-rate
           + 13th-month bonus if 20 December falls inside the horizon

Scenario levers only change these drivers. They never touch stored
transactions: a scenario is a pure function of (drivers, assumptions).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from app.analytics.features import BUFFER_DAYS_THRESHOLD
from app.analytics.ledger import Ledger
from app.analytics.patterns import recurring_streams

VAT_RATE = 0.15
VAT_MONTHS = (1, 4, 7, 10)


@dataclass
class Assumptions:
    """All values are percentages except collection_days_change (days)."""

    supplier_cost_pct: float = 0.0
    price_pct: float = 0.0
    sales_volume_pct: float = 0.0
    recurring_expense_pct: float = 0.0
    collection_days_change: float = 0.0
    marketing_spend_pct: float = 0.0
    staffing_cost_pct: float = 0.0
    inventory_spend_pct: float = 0.0

    def is_baseline(self) -> bool:
        return all(v == 0 for v in asdict(self).values())


LEVER_LABELS = {
    "supplier_cost_pct": "Supplier prices",
    "price_pct": "Selling prices",
    "sales_volume_pct": "Sales volume",
    "recurring_expense_pct": "Recurring expenses (excl. payroll, loans)",
    "collection_days_change": "Invoice collection time (days)",
    "marketing_spend_pct": "Marketing spend",
    "staffing_cost_pct": "Staffing cost",
    "inventory_spend_pct": "Inventory purchasing volume",
}


@dataclass
class Drivers:
    as_of: pd.Timestamp
    opening_cash: float
    b2c_weekday: list[float]  # average walk-in sales per weekday (Mon..Sun)
    seasonal: dict[int, float]  # month -> factor
    open_invoices: list[dict[str, Any]]  # customer, amount, expected_date
    customer_rates: list[dict[str, Any]]  # customer, daily_invoiced, lag_days
    cogs_daily: float
    recurring: list[dict[str, Any]]  # name, category, amount, day, cadence, next_date
    variable_daily: float
    marketing_monthly: float
    marketing_day: int
    payroll_monthly: float
    vat_to_date: dict[str, float] = field(default_factory=dict)  # quarter sales/purchases so far
    buffer_threshold: float = 0.0
    notes: list[str] = field(default_factory=list)


def _weekday_avg(df: pd.DataFrame, days: int) -> list[float]:
    idx = pd.date_range(df["date"].min() if len(df) else pd.Timestamp.today(), periods=days, freq="D")
    daily = df.groupby("date")["amount"].sum()
    out = []
    for wd in range(7):
        n = max(1, sum(1 for d in idx if d.weekday() == wd))
        out.append(float(daily[daily.index.weekday == wd].sum()) / n)
    return out


def build_drivers(ledger: Ledger, as_of: pd.Timestamp | None = None) -> Drivers:
    as_of = pd.Timestamp(as_of or ledger.end).normalize()
    t = ledger.tx[ledger.tx["date"] <= as_of]
    w90 = t[t["date"] > as_of - pd.Timedelta(days=90)]
    w60 = t[t["date"] > as_of - pd.Timedelta(days=60)]
    notes: list[str] = []

    walk_in = w90[(w90["group"] == "revenue") & w90["counterparty"].isna()]
    b2c = _weekday_avg(walk_in.assign(date=walk_in["date"]), 90) if len(walk_in) else [0.0] * 7

    # Seasonality: compare each calendar month last year with the same 90-day window
    # last year that our run-rate is based on. Needs >= 15 months of history.
    seasonal = {m: 1.0 for m in range(1, 13)}
    if (as_of - ledger.start).days >= 455:
        rev_all = t[t["group"] == "revenue"]
        ly_end = as_of - pd.Timedelta(days=365)
        ly_win = rev_all[(rev_all["date"] > ly_end - pd.Timedelta(days=90)) & (rev_all["date"] <= ly_end)]
        base_daily = float(ly_win["amount"].sum()) / 90.0
        ly_year = rev_all[(rev_all["date"] > ly_end) & (rev_all["date"] <= ly_end + pd.Timedelta(days=120))]
        if base_daily > 0 and len(ly_year):
            by_m = ly_year.groupby(ly_year["date"].dt.month)["amount"].sum()
            covered = pd.date_range(ly_end + pd.Timedelta(days=1), ly_end + pd.Timedelta(days=120), freq="D")
            days_m = pd.Series(1, index=covered).groupby(covered.month).sum()
            for m in by_m.index:
                if days_m.get(m, 0) >= 7:
                    seasonal[int(m)] = float(np.clip(by_m[m] / days_m[m] / base_daily, 0.6, 1.6))
        notes.append("Seasonal adjustment uses the same months last year relative to the same 90-day window.")
    else:
        notes.append("Less than 15 months of history: no seasonal adjustment applied.")

    # receivables
    inv = ledger.invoices
    open_invoices: list[dict[str, Any]] = []
    customer_rates: list[dict[str, Any]] = []
    if not inv.empty:
        inv = inv[inv["issue_date"] <= as_of]
        paid = inv[inv["paid_date"].notna() & (inv["paid_date"] <= as_of)]
        for cust, g in inv.groupby("customer"):
            gp = paid[paid["customer"] == cust]
            recent = gp[gp["paid_date"] > as_of - pd.Timedelta(days=120)]
            ref = recent if len(recent) else gp
            lag = float(((ref["paid_date"] - ref["issue_date"]).dt.days).mean()) if len(ref) else 30.0
            late = float(((ref["paid_date"] - ref["due_date"]).dt.days).mean()) if len(ref) else 0.0
            issued90 = g[g["issue_date"] > as_of - pd.Timedelta(days=90)]
            customer_rates.append({"customer": cust, "daily_invoiced": float(issued90["amount"].sum()) / 90.0,
                                   "lag_days": lag})
            open_g = g[g["paid_date"].isna() | (g["paid_date"] > as_of)]
            for _, r in open_g.iterrows():
                exp = (r["due_date"] + pd.Timedelta(days=round(max(0.0, late)))).normalize()
                if exp <= as_of:
                    exp = as_of + pd.Timedelta(days=7)  # overdue: assume collected within a week
                open_invoices.append({"customer": cust, "invoice_no": r["invoice_no"],
                                      "amount": float(r["amount"]), "expected_date": exp,
                                      "due_date": r["due_date"]})

    cogs_daily = float(w60.loc[w60["group"] == "cogs", "amount"].sum()) / 60.0

    streams = [s for s in recurring_streams(ledger, as_of) if s["active"]]
    recurring = []
    rec_ids: set[str] = set()
    payroll_monthly = 0.0
    marketing_monthly, marketing_day = 0.0, 8
    for s in streams:
        g = t[t["id"].astype(str).isin(s["transaction_ids"])]
        day = int(g["date"].dt.day.median()) if len(g) else 1
        last = g["date"].max() if len(g) else as_of
        rec_ids.update(s["transaction_ids"])
        if s["category"] == "Marketing":
            marketing_monthly, marketing_day = s["monthly_run_rate"], day
            continue
        if s["category"] == "Payroll":
            payroll_monthly += s["monthly_run_rate"]
        step = 91 if s["cadence"] == "quarterly" else 30
        amount = s["latest_payment"] if s["cadence"] in ("monthly", "quarterly") else s["monthly_run_rate"]
        recurring.append({"name": s["name"], "category": s["category"], "amount": float(amount), "day": day,
                          "cadence": s["cadence"], "last": last, "step": step})

    # everything else that is operating spend, excluding recurring streams, one-off equipment,
    # confirmed anomalies and marketing (handled above)
    rec_keys = {(s["name"], s["category"]) for s in streams}
    other = w90[(w90["direction"] == "outflow") & (w90["group"] == "operating")
                & (w90["category"] != "Equipment") & (w90["category"] != "Marketing")]
    if "is_anomaly" in other.columns:
        other = other[~other["is_anomaly"].fillna(False).astype(bool)]
    other = other[[(cp, cat) not in rec_keys for cp, cat in
                   zip(other["counterparty"].fillna(other["category"]), other["category"], strict=False)]]
    variable_daily = float(other["amount"].sum()) / 90.0
    if marketing_monthly == 0.0:
        mk = w90[w90["category"] == "Marketing"]
        marketing_monthly = float(mk["amount"].sum()) / 3.0

    # VAT: quarter-to-date sales and purchases for the quarter currently open
    q_start = pd.Timestamp(year=as_of.year, month=((as_of.month - 1) // 3) * 3 + 1, day=1)
    qtd = t[t["date"] >= q_start]
    vat_to_date = {
        "quarter_start": str(q_start.date()),
        "sales": float(qtd.loc[qtd["group"] == "revenue", "amount"].sum()),
        "purchases": float(qtd.loc[qtd["group"] == "cogs", "amount"].sum()),
        "registered": float(bool((t["category"] == "Taxes (VAT)").any())),
    }

    obligations = t[t["is_obligation"] & (t["date"] > as_of - pd.Timedelta(days=90))]
    buffer_threshold = BUFFER_DAYS_THRESHOLD * float(obligations["amount"].sum()) / 90.0

    notes.append("Supplier purchases follow the last 60 days' run-rate, so recent price changes are included.")
    notes.append("No owner drawings or capital injections are assumed.")
    return Drivers(
        as_of=as_of, opening_cash=ledger.cash_at(as_of), b2c_weekday=b2c, seasonal=seasonal,
        open_invoices=open_invoices, customer_rates=customer_rates, cogs_daily=cogs_daily,
        recurring=recurring, variable_daily=variable_daily, marketing_monthly=marketing_monthly,
        marketing_day=marketing_day, payroll_monthly=payroll_monthly, vat_to_date=vat_to_date,
        buffer_threshold=buffer_threshold, notes=notes,
    )


def project(drv: Drivers, a: Assumptions | None = None, horizon: int = 90) -> pd.DataFrame:
    """Daily projection. Returns columns: date, inflow, outflow, cash and a breakdown."""
    a = a or Assumptions()
    price = 1 + a.price_pct / 100
    vol = 1 + a.sales_volume_pct / 100
    days = pd.date_range(drv.as_of + pd.Timedelta(days=1), periods=horizon, freq="D")
    n = len(days)
    cols = {k: np.zeros(n) for k in ("sales_walk_in", "collections", "suppliers", "recurring", "payroll",
                                    "marketing", "variable", "vat")}
    pos = {d: i for i, d in enumerate(days)}

    for i, d in enumerate(days):
        cols["sales_walk_in"][i] = drv.b2c_weekday[d.weekday()] * drv.seasonal.get(d.month, 1.0) * price * vol
        cols["suppliers"][i] = drv.cogs_daily * drv.seasonal.get(d.month, 1.0) * vol \
            * (1 + a.supplier_cost_pct / 100) * (1 + a.inventory_spend_pct / 100)
        cols["variable"][i] = drv.variable_daily

    for inv in drv.open_invoices:
        exp = max((inv["expected_date"] + pd.Timedelta(days=round(a.collection_days_change))).normalize(),
                  drv.as_of + pd.Timedelta(days=1))
        if exp in pos:
            cols["collections"][pos[exp]] += inv["amount"]
    for c in drv.customer_rates:
        lag = max(0.0, c["lag_days"] + a.collection_days_change)
        for d in days:
            pay = d + pd.Timedelta(days=round(lag))
            if pay in pos:
                cols["collections"][pos[pay]] += c["daily_invoiced"] * price * vol * drv.seasonal.get(d.month, 1.0)

    for r in drv.recurring:
        is_payroll = r["category"] == "Payroll"
        is_fixed_financing = r["category"] in ("Loan repayment",)
        if is_payroll:
            factor = 1 + a.staffing_cost_pct / 100
        elif is_fixed_financing:
            factor = 1.0
        else:
            factor = 1 + a.recurring_expense_pct / 100
        amount = r["amount"] * factor
        target = "payroll" if is_payroll else "recurring"
        if r["cadence"] == "quarterly":
            nxt = r["last"] + pd.Timedelta(days=r["step"])
            while nxt <= days[-1]:
                if nxt in pos:
                    cols[target][pos[nxt]] += amount
                nxt += pd.Timedelta(days=r["step"])
        elif r["cadence"] == "monthly":
            for d in days:
                last_dom = d.days_in_month
                if d.day == min(r["day"], last_dom):
                    cols[target][pos[d]] += amount
        else:
            for i in range(n):
                cols[target][i] += amount / 30.44

    mk = drv.marketing_monthly * (1 + a.marketing_spend_pct / 100)
    for d in days:
        if d.day == min(drv.marketing_day, d.days_in_month):
            cols["marketing"][pos[d]] += mk
        if d.month == 12 and d.day == 20:
            cols["payroll"][pos[d]] += drv.payroll_monthly * 0.92 * (1 + a.staffing_cost_pct / 100)

    # VAT on the 20th of Jan/Apr/Jul/Oct: 15/115 of (sales - purchases) of the quarter just closed.
    if drv.vat_to_date.get("registered"):
        q_sales = drv.vat_to_date["sales"]
        q_purch = drv.vat_to_date["purchases"]
        pending = 0.0
        for i, d in enumerate(days):
            if d.day == 1 and d.month in VAT_MONTHS:  # a new quarter starts: close the previous one
                pending = max(0.0, VAT_RATE / (1 + VAT_RATE) * (q_sales - q_purch))
                q_sales = q_purch = 0.0
            if d.day == 20 and d.month in VAT_MONTHS and pending:
                cols["vat"][i] += pending
                pending = 0.0
            q_sales += cols["sales_walk_in"][i] + cols["collections"][i]
            q_purch += cols["suppliers"][i]

    df = pd.DataFrame({"date": days, **cols})
    df["inflow"] = df["sales_walk_in"] + df["collections"]
    df["outflow"] = df[["suppliers", "recurring", "payroll", "marketing", "variable", "vat"]].sum(axis=1)
    df["cash"] = drv.opening_cash + (df["inflow"] - df["outflow"]).cumsum()
    return df


def summarise_projection(df: pd.DataFrame, drv: Drivers) -> dict[str, Any]:
    def at(day: int) -> float:
        return float(df["cash"].iloc[min(day, len(df)) - 1])

    i_min = int(df["cash"].idxmin())
    below = df["cash"] < drv.buffer_threshold
    first_below = df.loc[below, "date"].min() if below.any() else None
    return {
        "starting_cash": round(drv.opening_cash, 2),
        "cash_day_30": round(at(30), 2),
        "cash_day_60": round(at(60), 2),
        "cash_day_90": round(at(90), 2),
        "lowest_cash": round(float(df["cash"].iloc[i_min]), 2),
        "lowest_cash_date": str(df["date"].iloc[i_min].date()),
        "buffer_threshold": round(drv.buffer_threshold, 2),
        "days_below_buffer": int(below.sum()),
        "first_date_below_buffer": str(first_below.date()) if first_below is not None else None,
        "total_inflow": round(float(df["inflow"].sum()), 2),
        "total_outflow": round(float(df["outflow"].sum()), 2),
    }


def simulate(drv: Drivers, a: Assumptions, horizon: int = 90) -> dict[str, Any]:
    base = project(drv, Assumptions(), horizon)
    scen = project(drv, a, horizon)
    bs, ss = summarise_projection(base, drv), summarise_projection(scen, drv)
    diff = {k: round(ss[k] - bs[k], 2) for k in ("cash_day_30", "cash_day_60", "cash_day_90", "lowest_cash",
                                                  "total_inflow", "total_outflow")}
    diff["days_below_buffer"] = ss["days_below_buffer"] - bs["days_below_buffer"]
    series = [{"date": str(d.date()), "baseline": round(float(b), 2), "scenario": round(float(s), 2)}
              for d, b, s in zip(base["date"], base["cash"], scen["cash"], strict=True)]
    parts = ["sales_walk_in", "collections", "suppliers", "recurring", "payroll", "marketing", "variable", "vat"]
    breakdown = [{"driver": p, "baseline": round(float(base[p].sum()), 2), "scenario": round(float(scen[p].sum()), 2),
                  "difference": round(float(scen[p].sum() - base[p].sum()), 2)} for p in parts]
    return {
        "as_of": str(drv.as_of.date()),
        "horizon_days": horizon,
        "assumptions": asdict(a),
        "baseline": bs,
        "scenario": ss,
        "difference": diff,
        "series": series,
        "breakdown": breakdown,
        "method_notes": drv.notes,
        "label": "SIMULATED - projection only; historical transactions are not modified",
    }


def backtest(ledger: Ledger, horizon: int = 30, step_days: int = 28, n: int = 8) -> dict[str, Any]:
    """Project from past dates and compare with what actually happened."""
    rows = []
    end = ledger.end - pd.Timedelta(days=horizon)
    for k in range(n):
        cut = end - pd.Timedelta(days=step_days * k)
        if (cut - ledger.start).days < 150:
            break
        drv = build_drivers(ledger, cut)
        proj = project(drv, Assumptions(), horizon)
        predicted = float(proj["cash"].iloc[-1])
        actual = ledger.cash_at(cut + pd.Timedelta(days=horizon))
        # owner drawings/injections are not forecastable; remove them from actuals for a fair test
        fin = ledger.tx[(ledger.tx["date"] > cut) & (ledger.tx["date"] <= cut + pd.Timedelta(days=horizon))
                        & ledger.tx["category"].isin(["Owner drawings", "Owner contribution"])]
        actual_adj = actual + float(fin.loc[fin["direction"] == "outflow", "amount"].sum()) \
            - float(fin.loc[fin["direction"] == "inflow", "amount"].sum())
        monthly_out = drv.buffer_threshold / BUFFER_DAYS_THRESHOLD * 30.44
        rows.append({"cut": str(cut.date()), "predicted": round(predicted, 2), "actual": round(actual_adj, 2),
                     "error_pct_of_monthly_outflow": round(abs(predicted - actual_adj) / monthly_out * 100, 2)})
    errs = [r["error_pct_of_monthly_outflow"] for r in rows]
    return {"horizon_days": horizon, "points": rows,
            "median_abs_error_pct_of_monthly_outflow": round(float(np.median(errs)), 2) if errs else None}
