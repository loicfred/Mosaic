"""Recurring expenses, concentration and collection behaviour (deterministic)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.analytics.ledger import Ledger

# ------------------------------------------------------------------ recurring streams

FUNCTION_KEYWORDS = {
    "accounting": ("accounting", "books", "ledger", "invoice"),
    "point of sale": ("pos",),
    "inventory": ("inventory", "stock"),
    "security": ("cctv", "security", "alarm"),
    "payroll software": ("payroll app", "hr software"),
}


def _stream_key(row: pd.Series) -> str:
    """Identify a recurring stream by payee + category (payroll has no payee)."""
    if isinstance(row["counterparty"], str) and row["counterparty"]:
        return f"{row['counterparty']}::{row['category']}"
    return f"::{row['category']}"


def recurring_streams(ledger: Ledger, as_of: pd.Timestamp, months: int = 6) -> list[dict[str, Any]]:
    """Outflow streams that appear in >= 3 distinct months with stable amounts.

    Supplier stock purchases are excluded: they scale with sales and are
    analysed separately as supplier costs.
    """
    as_of = pd.Timestamp(as_of)
    lo = as_of - pd.DateOffset(months=months)
    t = ledger.tx
    t = t[(t["date"] > lo) & (t["date"] <= as_of) & (t["direction"] == "outflow")
          & (~t["group"].isin(["cogs", "financing"])) | ((t["category"] == "Loan repayment")
          & (t["date"] > lo) & (t["date"] <= as_of))].copy()
    if t.empty:
        return []
    t["key"] = t.apply(_stream_key, axis=1)
    t["month"] = t["date"].dt.to_period("M")
    hist = ledger.tx[(ledger.tx["direction"] == "outflow") & (ledger.tx["date"] <= as_of)]
    first_seen = hist.assign(key=hist.apply(_stream_key, axis=1)).groupby("key")["date"].min()
    out = []
    for key, g in t.groupby("key"):
        monthly = g.groupby("month")["amount"].sum()
        n_months = monthly.index.nunique()
        if n_months < 2:
            continue
        # stability of the individual payment amounts (robust to two payments landing in one month)
        amounts = g["amount"].astype(float)
        cv = float(amounts.std(ddof=0) / amounts.mean()) if amounts.mean() else 1.0
        if n_months < 3 and not g["is_recurring_cat"].all():
            continue
        if cv > 0.45 and not g["is_recurring_cat"].all():
            continue
        first_seen_all = first_seen.get(key, g["date"].min())
        span_start = max(pd.Timestamp(first_seen_all), lo)
        span_months = max(1.0, (as_of - span_start).days / 30.44)
        recent = float(g["amount"].iloc[-1])  # latest payment (run-rate for monthly items)
        earliest = float(g["amount"].iloc[0])
        gaps = g["date"].diff().dt.days.dropna()
        med_gap = float(gaps.median()) if len(gaps) else 30.0
        if 24 <= med_gap <= 38:
            cadence, run_rate = "monthly", recent
        elif 75 <= med_gap <= 105:
            cadence, run_rate = "quarterly", recent / 3.0
        else:
            cadence, run_rate = "irregular", float(g["amount"].sum()) / span_months
        active = g["date"].max() >= as_of - pd.Timedelta(days=max(45.0, med_gap * 1.5))
        if not active:
            run_rate = 0.0
        cat = g["category"].mode().iat[0]
        name = g["counterparty"].dropna().iloc[0] if g["counterparty"].notna().any() else cat
        func = None
        low = f"{name} {' '.join(g['description'].astype(str).str.lower().head(3))}".lower()
        for f, kws in FUNCTION_KEYWORDS.items():
            if any(k in low for k in kws):
                func = f
                break
        out.append({
            "key": key, "name": name, "category": cat,
            "months_active": int(n_months),
            "monthly_average": round(float(g["amount"].sum()) / span_months, 2),
            "cadence": cadence,
            "monthly_run_rate": round(run_rate, 2),
            "active": bool(active),
            "latest_payment": round(recent, 2),
            "payments": int(len(g)),
            "first_seen": str(pd.Timestamp(first_seen_all).date()),
            "last_seen": str(g["date"].max().date()),
            "is_new": bool(pd.Timestamp(first_seen_all) > as_of - pd.Timedelta(days=120)),
            "change_pct": round(float((recent - earliest) / earliest * 100), 2) if earliest else None,
            "stability_cv": round(cv, 3),
            "function": func,
            "transaction_ids": g["id"].astype(str).tolist()[-6:],
        })
    return sorted(out, key=lambda r: -r["monthly_run_rate"])


# ------------------------------------------------------------------ concentration


def concentration(ledger: Ledger, as_of: pd.Timestamp, side: str, days: int = 180) -> dict[str, Any]:
    """side='customer' uses revenue; side='supplier' uses cost of goods."""
    w = ledger.window(as_of, days)
    grp = "revenue" if side == "customer" else "cogs"
    w = w[w["group"] == grp]
    total = float(w["amount"].sum())
    ident = w.dropna(subset=["counterparty"])
    by = ident.groupby("counterparty")["amount"].agg(["sum", "count"]).sort_values("sum", ascending=False)
    unidentified = total - float(by["sum"].sum())
    shares = (by["sum"] / total) if total else by["sum"] * 0
    hhi = float(((by["sum"] / by["sum"].sum()) ** 2).sum() * 10_000) if len(by) else 0.0
    top = [{"name": n, "amount": round(float(r["sum"]), 2), "share_pct": round(float(shares[n]) * 100, 2),
            "transactions": int(r["count"])} for n, r in by.head(6).iterrows()]
    return {
        "side": side, "days": days, "total": round(total, 2),
        "identified_counterparties": int(len(by)),
        "unidentified_amount": round(unidentified, 2),
        "unidentified_label": "Walk-in / POS sales" if side == "customer" else "Unattributed purchases",
        "top": top,
        "top_share_pct": round(float(shares.iloc[0]) * 100, 2) if len(by) else 0.0,
        "top3_share_pct": round(float(shares.head(3).sum()) * 100, 2) if len(by) else 0.0,
        "hhi_identified": round(hhi, 1),
    }


# ------------------------------------------------------------------ collections


def collections(ledger: Ledger, as_of: pd.Timestamp) -> dict[str, Any]:
    inv = ledger.invoices
    as_of = pd.Timestamp(as_of)
    if inv.empty:
        return {"has_invoices": False}
    inv = inv[inv["issue_date"] <= as_of].copy()
    paid = inv[inv["paid_date"].notna() & (inv["paid_date"] <= as_of)].copy()
    paid["days_to_pay"] = (paid["paid_date"] - paid["issue_date"]).dt.days
    paid["days_late"] = (paid["paid_date"] - paid["due_date"]).dt.days

    def dso(lo_days: int, hi_days: int) -> tuple[float | None, int]:
        s = paid[(paid["paid_date"] > as_of - pd.Timedelta(days=hi_days))
                 & (paid["paid_date"] <= as_of - pd.Timedelta(days=lo_days))]
        if s.empty:
            return None, 0
        return float(np.average(s["days_to_pay"], weights=s["amount"])), int(len(s))

    recent, n_recent = dso(0, 90)
    prior, n_prior = dso(90, 270)
    open_ = inv[inv["paid_date"].isna() | (inv["paid_date"] > as_of)].copy()
    open_["days_overdue"] = (as_of - open_["due_date"]).dt.days
    buckets = {
        "not_due": float(open_.loc[open_["days_overdue"] <= 0, "amount"].sum()),
        "1_30": float(open_.loc[open_["days_overdue"].between(1, 30), "amount"].sum()),
        "31_60": float(open_.loc[open_["days_overdue"].between(31, 60), "amount"].sum()),
        "over_60": float(open_.loc[open_["days_overdue"] > 60, "amount"].sum()),
    }
    by_customer = []
    for cust, g in inv.groupby("customer"):
        gp = paid[paid["customer"] == cust]
        r = gp[gp["paid_date"] > as_of - pd.Timedelta(days=90)]
        p = gp[(gp["paid_date"] <= as_of - pd.Timedelta(days=90)) & (gp["paid_date"] > as_of - pd.Timedelta(days=270))]
        go = open_[open_["customer"] == cust]
        by_customer.append({
            "customer": cust,
            "invoiced_180d": round(float(g.loc[g["issue_date"] > as_of - pd.Timedelta(days=180), "amount"].sum()), 2),
            "avg_days_to_pay_recent": round(float(np.average(r["days_to_pay"], weights=r["amount"])), 1) if len(r) else None,
            "avg_days_to_pay_prior": round(float(np.average(p["days_to_pay"], weights=p["amount"])), 1) if len(p) else None,
            "open_amount": round(float(go["amount"].sum()), 2),
            "overdue_amount": round(float(go.loc[go["days_overdue"] > 0, "amount"].sum()), 2),
            "open_invoices": go["invoice_no"].tolist(),
        })
    by_customer.sort(key=lambda r: -(r["invoiced_180d"]))
    return {
        "has_invoices": True,
        "collection_days_recent": round(recent, 1) if recent is not None else None,
        "collection_days_prior": round(prior, 1) if prior is not None else None,
        "invoices_paid_recent": n_recent,
        "invoices_paid_prior": n_prior,
        "open_receivables": round(float(open_["amount"].sum()), 2),
        "overdue_receivables": round(float(open_.loc[open_["days_overdue"] > 0, "amount"].sum()), 2),
        "aging": {k: round(v, 2) for k, v in buckets.items()},
        "by_customer": by_customer,
        "standard_terms_days": int((inv["due_date"] - inv["issue_date"]).dt.days.median()),
    }
