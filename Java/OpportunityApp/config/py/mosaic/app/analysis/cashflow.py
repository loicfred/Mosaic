"""Observed cash-flow-stress rates and risk scoring of business-month snapshots."""
import pandas as pd

from app.data.records import records
from app.models import cashflow as cf

RECORD_FIELDS = [
    "record_id", "sector", "month", "employees", "revenue_usd", "opex_usd", "operating_margin",
    "accounts_receivable_days", "inventory_days", "loan_balance_usd", "owner_injections_usd",
]


def stress_rate_by_sector(frame: pd.DataFrame) -> list[dict]:
    return records(_stress_rate(frame, "sector").sort_values("stress_rate", ascending=False))


def stress_rate_by_month(frame: pd.DataFrame) -> list[dict]:
    return records(_stress_rate(frame, "month").sort_values("month"))


def _stress_rate(frame: pd.DataFrame, by: str) -> pd.DataFrame:
    grouped = frame.groupby(by).agg(records=(cf.LABEL, "size"), stressed=(cf.LABEL, "sum")).reset_index()
    grouped["stressed"] = grouped["stressed"].astype(int)
    grouped["stress_rate"] = grouped["stressed"] / grouped["records"]
    return grouped


def score_records(frame: pd.DataFrame, model, limit: int, start: str, end_exclusive: str) -> list[dict]:
    """Held-out snapshots only, ranked by predicted next-month stress; training rows would flatter the model."""
    _, held_out = cf.temporal_split(frame, start, end_exclusive)
    if held_out.empty:
        return []
    scored = held_out.copy()
    scored["risk"] = cf.predict_risk(model, scored)
    ranked = scored.sort_values("risk", ascending=False).head(limit)
    return records(ranked[RECORD_FIELDS + ["risk"]])
