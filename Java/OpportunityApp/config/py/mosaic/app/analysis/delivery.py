"""Observed late-delivery statistics and risk scoring of in-flight orders."""
import pandas as pd

from app.analysis.populations import labelled_orders_in_range, monthly_rate
from app.config import DATA_RANGE, OPEN_STATUSES
from app.data.records import records
from app.models import risk

ORDER_ID_FIELDS = [
    "order_id",
    "order_status",
    "purchase_ts",
    "order_estimated_delivery_date",
    "seller_id",
    "seller_state",
    "customer_state",
    "category",
    "total_price",
]


def monthly_late_rate(frame: pd.DataFrame, data_range: tuple[str, str] = DATA_RANGE) -> list[dict]:
    return monthly_rate(frame, "late", "delivered", "late", data_range)


def seller_table(
    frame: pd.DataFrame,
    min_orders: int,
    limit: int,
    recent_months: int = 3,
    data_range: tuple[str, str] = DATA_RANGE,
) -> list[dict]:
    """Observed rates per seller (seller of the priciest item), recent window versus earlier."""
    labelled = labelled_orders_in_range(frame, "late", data_range)
    labelled = labelled[labelled["seller_id"].notna()]
    months = sorted(labelled["month"].unique())
    recent = set(months[-recent_months:])
    labelled = labelled.assign(is_recent=labelled["month"].isin(recent))

    grouped = labelled.groupby("seller_id")
    table = grouped.agg(
        orders=("late", "size"),
        late=("late", "sum"),
        handover_known=("handover_late", "count"),
        handover_late=("handover_late", "sum"),
    )
    table["late_rate"] = table["late"] / table["orders"]
    table["handover_late_rate"] = table["handover_late"] / table["handover_known"].replace(0, pd.NA)
    table["recent_late_rate"] = labelled[labelled["is_recent"]].groupby("seller_id")["late"].mean()
    table["earlier_late_rate"] = labelled[~labelled["is_recent"]].groupby("seller_id")["late"].mean()
    table = table[table["orders"] >= min_orders].sort_values(["late_rate", "orders"], ascending=[False, False])
    table[["late", "handover_late", "handover_known"]] = table[["late", "handover_late", "handover_known"]].astype(int)
    return records(table.head(limit).reset_index())


def score_open_orders(frame: pd.DataFrame, model, limit: int) -> list[dict]:
    """In-flight orders ranked by predicted late-delivery probability."""
    open_orders = frame[frame["order_status"].isin(OPEN_STATUSES)]
    if open_orders.empty:
        return []
    ranked = risk.rank(model, "late_delivery", open_orders, limit)
    ranked = ranked.assign(days_since_purchase=(frame["purchase_ts"].max().normalize() - ranked["purchase_ts"].dt.normalize()).dt.days)
    return records(ranked[ORDER_ID_FIELDS + ["days_since_purchase", "risk"]])
