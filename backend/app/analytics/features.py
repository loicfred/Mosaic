"""Feature pipeline for the 30-day cash-pressure model.

This module is imported by BOTH the training script (ml/train_cash_pressure.py)
and the live API (app/services/ml_service.py). Sharing one implementation
removes train/serve skew: the model sees exactly the same feature definitions in
production as it saw during evaluation.

All features are scale-free (ratios, days, growth rates) so a model can be
applied to businesses of different sizes.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.analytics.ledger import Ledger

HORIZON_DAYS = 30
BUFFER_DAYS_THRESHOLD = 14  # pressure = cash falls below 14 days of typical outflows

FEATURE_NAMES: list[str] = [
    "buffer_days",
    "net_margin_90d",
    "revenue_growth_30d",
    "expense_growth_30d",
    "supplier_cost_growth_30d",
    "recurring_share",
    "collection_days",
    "collection_days_trend",
    "overdue_receivables_ratio",
    "top_customer_share",
    "top_supplier_share",
    "cashflow_volatility",
    "cash_trend_30d",
    "scheduled_obligations_ratio",
    "seasonal_index_next_30d",
    "txn_frequency_change",
]

FEATURE_LABELS: dict[str, str] = {
    "buffer_days": "Cash buffer (days of outflows)",
    "net_margin_90d": "Net cash margin, last 90 days",
    "revenue_growth_30d": "Revenue growth, last 30 days vs prior run-rate",
    "expense_growth_30d": "Expense growth, last 30 days vs prior run-rate",
    "supplier_cost_growth_30d": "Supplier cost growth, last 30 days vs prior run-rate",
    "recurring_share": "Recurring expenses as share of outflows",
    "collection_days": "Average days to collect invoices",
    "collection_days_trend": "Change in collection days (recent vs earlier)",
    "overdue_receivables_ratio": "Overdue receivables vs monthly revenue",
    "top_customer_share": "Largest customer's share of revenue",
    "top_supplier_share": "Largest supplier's share of purchases",
    "cashflow_volatility": "Weekly cash-flow volatility",
    "cash_trend_30d": "Cash change over last 30 days vs monthly outflows",
    "scheduled_obligations_ratio": "Known obligations due in next 30 days vs monthly outflows",
    "seasonal_index_next_30d": "Seasonal revenue index for the next 30 days",
    "txn_frequency_change": "Change in transaction frequency",
}

VAT_MONTHS = (1, 4, 7, 10)


@dataclass
class FeatureRow:
    as_of: pd.Timestamp
    values: dict[str, float]
    support: dict[str, float]  # raw numbers used, for evidence display


def _safe_div(a: float, b: float, default: float = 0.0) -> float:
    return float(a / b) if b and np.isfinite(b) and abs(b) > 1e-9 else default


def _growth(recent_30: float, prior_90: float) -> float:
    base = prior_90 / 3.0
    if base <= 0:
        return 0.0
    return float(np.clip(recent_30 / base - 1.0, -1.0, 3.0))


def _collection_days(inv: pd.DataFrame, lo: pd.Timestamp, hi: pd.Timestamp) -> tuple[float, int]:
    if inv.empty:
        return 0.0, 0
    paid = inv[(inv["paid_date"] > lo) & (inv["paid_date"] <= hi)]
    if paid.empty:
        return 0.0, 0
    days = (paid["paid_date"] - paid["issue_date"]).dt.days.astype(float)
    w = paid["amount"].astype(float)
    return float(np.average(days, weights=w)), int(len(paid))


def _slicer(ledger: Ledger):
    dates = ledger.tx["date"].to_numpy(dtype="datetime64[ns]")

    def between(lo: pd.Timestamp, hi: pd.Timestamp) -> pd.DataFrame:
        """Rows with lo < date <= hi, using binary search on the sorted ledger."""
        i = int(np.searchsorted(dates, np.datetime64(lo, "ns"), side="right"))
        j = int(np.searchsorted(dates, np.datetime64(hi, "ns"), side="right"))
        return ledger.tx.iloc[i:j]

    return between


def compute_features(ledger: Ledger, as_of: pd.Timestamp) -> FeatureRow:
    as_of = pd.Timestamp(as_of).normalize()
    between = _slicer(ledger)
    day = pd.Timedelta(days=1)
    tx = between(pd.Timestamp("1900-01-01"), as_of)
    w90 = between(as_of - 90 * day, as_of)
    w30 = between(as_of - 30 * day, as_of)
    p90 = between(as_of - 120 * day, as_of - 30 * day)
    w180 = between(as_of - 180 * day, as_of)

    out = lambda df: float(df.loc[df["is_obligation"], "amount"].sum())  # noqa: E731
    rev = lambda df: float(df.loc[df["group"] == "revenue", "amount"].sum())  # noqa: E731
    opx = lambda df: float(df.loc[df["group"].isin(["cogs", "operating"]), "amount"].sum())  # noqa: E731
    cogs = lambda df: float(df.loc[df["group"] == "cogs", "amount"].sum())  # noqa: E731

    out90 = out(w90)
    daily_out = out90 / 90.0
    cash = ledger.cash_at(as_of)
    rev90 = rev(w90)
    ops_in90 = float(w90.loc[(w90["direction"] == "inflow") & (w90["group"] != "financing"), "amount"].sum())
    monthly_rev = rev90 / 3.0
    monthly_out = out90 / 3.0

    # collections
    inv = ledger.invoices
    inv = inv[inv["issue_date"] <= as_of] if not inv.empty else inv
    cd_recent, n_recent = _collection_days(inv, as_of - pd.Timedelta(days=60), as_of)
    cd_prior, n_prior = _collection_days(inv, as_of - pd.Timedelta(days=180), as_of - pd.Timedelta(days=60))
    cd_90, n_90 = _collection_days(inv, as_of - pd.Timedelta(days=90), as_of)
    if not inv.empty:
        open_mask = inv["paid_date"].isna() | (inv["paid_date"] > as_of)
        overdue = float(inv.loc[open_mask & (inv["due_date"] < as_of), "amount"].sum())
        open_recv = float(inv.loc[open_mask, "amount"].sum())
    else:
        overdue = open_recv = 0.0

    # concentration (180d)
    rev180 = w180[w180["group"] == "revenue"]
    total_rev180 = float(rev180["amount"].sum())
    by_cust = rev180.dropna(subset=["counterparty"]).groupby("counterparty")["amount"].sum()
    top_cust = _safe_div(float(by_cust.max()) if len(by_cust) else 0.0, total_rev180)
    sup180 = w180[w180["group"] == "cogs"]
    by_sup = sup180.dropna(subset=["counterparty"]).groupby("counterparty")["amount"].sum()
    top_sup = _safe_div(float(by_sup.max()) if len(by_sup) else 0.0, float(sup180["amount"].sum()))

    # volatility of weekly net flow over 13 weeks
    wk = w90.set_index("date")["signed"].resample("W").sum()
    weekly_out = monthly_out * 12 / 52
    vol = _safe_div(float(wk.std(ddof=0)) if len(wk) > 2 else 0.0, weekly_out)

    cash_30_ago = ledger.cash_at(as_of - pd.Timedelta(days=30))

    # known obligations in the next 30 days: recurring run-rate + VAT + 13th-month bonus
    recurring_monthly = float(w90.loc[(w90["direction"] == "outflow") & w90["is_recurring_cat"], "amount"].sum()) / 3.0
    obligations = recurring_monthly
    horizon_end = as_of + pd.Timedelta(days=HORIZON_DAYS)
    vat_rows = tx[tx["category"] == "Taxes (VAT)"]
    last_vat = float(vat_rows["amount"].iloc[-1]) if len(vat_rows) else 0.0
    for m_off in range(0, 2):
        cand = (as_of + pd.DateOffset(months=m_off)).replace(day=20)
        if cand.month in VAT_MONTHS and as_of < cand <= horizon_end:
            obligations += last_vat
    dec20 = pd.Timestamp(year=as_of.year, month=12, day=20)
    if as_of < dec20 <= horizon_end:
        payroll_monthly = float(w90.loc[w90["category"] == "Payroll", "amount"].sum()) / 3.0
        obligations += payroll_monthly * 0.9

    # seasonality: same 30-day window last year vs last year's average 30 days
    ly_lo, ly_hi = as_of - pd.Timedelta(days=365), as_of - pd.Timedelta(days=335)
    ly_win = between(ly_lo, ly_hi)
    ly_year = between(as_of - 365 * day, as_of)
    has_year = (as_of - ledger.start).days >= 365
    seasonal = _safe_div(rev(ly_win), rev(ly_year) / 12.17, 1.0) if has_year else 1.0

    n30 = len(w30)
    nprior = len(p90) / 3.0

    values = {
        "buffer_days": float(np.clip(_safe_div(cash, daily_out, 0.0), -60, 365)),
        "net_margin_90d": float(np.clip(_safe_div(ops_in90 - out90, ops_in90, -1.0), -1.5, 1.0)),
        "revenue_growth_30d": _growth(rev(w30), rev(p90)),
        "expense_growth_30d": _growth(opx(w30), opx(p90)),
        "supplier_cost_growth_30d": _growth(cogs(w30), cogs(p90)),
        "recurring_share": _safe_div(recurring_monthly * 3, out90),
        "collection_days": cd_90,
        "collection_days_trend": (cd_recent - cd_prior) if (n_recent and n_prior) else 0.0,
        "overdue_receivables_ratio": float(np.clip(_safe_div(overdue, monthly_rev), 0, 5)),
        "top_customer_share": top_cust,
        "top_supplier_share": top_sup,
        "cashflow_volatility": float(np.clip(vol, 0, 10)),
        "cash_trend_30d": float(np.clip(_safe_div(cash - cash_30_ago, monthly_out), -3, 3)),
        "scheduled_obligations_ratio": float(np.clip(_safe_div(obligations, monthly_out), 0, 5)),
        "seasonal_index_next_30d": float(np.clip(seasonal, 0.3, 3.0)),
        "txn_frequency_change": float(np.clip(_safe_div(n30, nprior, 1.0) - 1.0, -1, 3)),
    }
    support = {
        "cash": cash,
        "cash_30_days_ago": cash_30_ago,
        "avg_daily_outflow_90d": daily_out,
        "monthly_revenue_90d": monthly_rev,
        "monthly_outflow_90d": monthly_out,
        "revenue_30d": rev(w30),
        "supplier_cost_30d": cogs(w30),
        "recurring_monthly": recurring_monthly,
        "overdue_receivables": overdue,
        "open_receivables": open_recv,
        "known_obligations_30d": obligations,
        "invoices_paid_90d": float(n_90),
        "transactions_90d": float(len(w90)),
    }
    return FeatureRow(as_of=as_of, values=values, support=support)


def pressure_label(ledger: Ledger, as_of: pd.Timestamp, horizon: int = HORIZON_DAYS) -> int | None:
    """Ground truth: did cash fall below BUFFER_DAYS_THRESHOLD days of outflows
    at any point in the next `horizon` days? Returns None when the future window
    is not fully observed."""
    as_of = pd.Timestamp(as_of).normalize()
    if as_of + pd.Timedelta(days=horizon) > ledger.end:
        return None
    w90 = ledger.window(as_of, 90)
    daily_out = float(w90.loc[w90["is_obligation"], "amount"].sum()) / 90.0
    future = ledger.daily_cash.loc[as_of + pd.Timedelta(days=1): as_of + pd.Timedelta(days=horizon)]
    if future.empty:
        return None
    return int(float(future.min()) < BUFFER_DAYS_THRESHOLD * daily_out)
