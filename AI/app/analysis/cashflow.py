"""Observed cash-flow-stress rates and risk scoring of business-month snapshots."""
import pandas as pd

from app.data.records import records
from app.models import cashflow as cf

RECORD_FIELDS = [
    "record_id", "sector", "month", "employees", "revenue_usd", "opex_usd", "operating_margin",
    "accounts_receivable_days", "inventory_days", "loan_balance_usd", "owner_injections_usd",
]


def stress_rate_by_sector(frame: pd.DataFrame) -> list[dict]:
    grouped = frame.groupby("sector").agg(
        records=(cf.LABEL, "size"), stressed=(cf.LABEL, "sum"),
    ).reset_index()
    grouped["stressed"] = grouped["stressed"].astype(int)
    grouped["stress_rate"] = grouped["stressed"] / grouped["records"]
    return records(grouped.sort_values("stress_rate", ascending=False))


def stress_rate_by_month(frame: pd.DataFrame) -> list[dict]:
    grouped = frame.groupby("month").agg(
        records=(cf.LABEL, "size"), stressed=(cf.LABEL, "sum"),
    ).reset_index()
    grouped["stressed"] = grouped["stressed"].astype(int)
    grouped["stress_rate"] = grouped["stressed"] / grouped["records"]
    return records(grouped.sort_values("month"))


def score_records(frame: pd.DataFrame, model, limit: int) -> list[dict]:
    """Every loaded snapshot ranked by predicted next-month stress probability."""
    if frame.empty:
        return []
    scored = frame.copy()
    scored["risk"] = cf.predict_risk(model, scored)
    ranked = scored.sort_values("risk", ascending=False).head(limit)
    return records(ranked[RECORD_FIELDS + ["risk"]])
