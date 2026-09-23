"""Observed low-review statistics and risk scoring of delivered-but-unreviewed orders."""
import pandas as pd

from app.analysis.populations import labelled_orders_in_range
from app.config import DATA_RANGE
from app.data.records import records
from app.models import risk

ORDER_ID_FIELDS = [
    "order_id",
    "purchase_ts",
    "order_delivered_customer_date",
    "seller_id",
    "seller_state",
    "customer_state",
    "category",
    "total_price",
    "delivery_days",
    "days_late",
]


def monthly_low_review_rate(frame: pd.DataFrame, data_range: tuple[str, str] = DATA_RANGE) -> list[dict]:
    reviewed = labelled_orders_in_range(frame, "low_review", data_range)
    monthly = (
        reviewed.groupby("month")
        .agg(reviewed=("low_review", "size"), low=("low_review", "sum"))
        .reset_index()
    )
    monthly["low"] = monthly["low"].astype(int)
    monthly["low_rate"] = monthly["low"] / monthly["reviewed"]
    return records(monthly)


def low_review_by_lateness(frame: pd.DataFrame, data_range: tuple[str, str] = DATA_RANGE) -> dict:
    """Low-review rate for late versus on-time delivered orders (association, not cause)."""
    reviewed = labelled_orders_in_range(frame, "low_review", data_range)
    reviewed = reviewed[reviewed["late"].notna()]
    result = {}
    for name, mask in (("late", reviewed["late"] == 1), ("on_time", reviewed["late"] == 0)):
        subset = reviewed[mask]
        low = int(subset["low_review"].sum())
        result[name] = {
            "reviewed": int(len(subset)),
            "low": low,
            "low_rate": low / len(subset) if len(subset) else None,
        }
    return result


def score_unreviewed(frame: pd.DataFrame, model, limit: int) -> list[dict]:
    """Delivered orders with no review yet, ranked by predicted low-review probability."""
    spec = risk.MODEL_SPECS["low_review"]
    candidates = frame[(frame["delivered"] == 1) & frame["late"].notna() & frame["review_score"].isna()].copy()
    if candidates.empty:
        return []
    candidates["risk"] = risk.predict_risk(model, spec, candidates)
    ranked = candidates.sort_values("risk", ascending=False).head(limit)
    return records(ranked[ORDER_ID_FIELDS + ["risk"]])
