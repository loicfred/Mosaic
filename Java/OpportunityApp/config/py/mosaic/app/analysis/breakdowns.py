"""Observed breakdowns the other analyses do not show: when customers buy, how each customer state is served, and
how orders are rated. One row per order (``app.state.orders.frame``), orders with items and not cancelled, in the
analysed range; every group carries its counts, and a group without a denominator gives ``None``, never 0.
"""
import pandas as pd

from app.analysis import trends

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def buying_times(frame: pd.DataFrame, by: str) -> list[dict]:
    """Orders and sales by weekday (Monday first) or by hour of the day (0-23), in the customers' local purchase time."""
    sold = trends.sold(frame)
    key = sold["purchase_ts"].dt.weekday if by == "weekday" else sold["purchase_ts"].dt.hour
    grouped = sold.groupby(key).agg(orders=("order_id", "size"), sales=("total_price", "sum"))
    slots = range(7) if by == "weekday" else range(24)
    total = int(grouped["orders"].sum())
    return [{"slot": WEEKDAYS[i] if by == "weekday" else f"{i:02d}:00",
             "orders": int(grouped["orders"].get(i, 0)), "sales": float(grouped["sales"].get(i, 0.0)),
             "share_of_orders": int(grouped["orders"].get(i, 0)) / total if total else None} for i in slots]


def by_customer_state(frame: pd.DataFrame, min_orders: int = 30) -> list[dict]:
    """Per customer state: orders, sales, late-delivery rate, average delivery days and low-review rate."""
    sold = trends.sold(frame)
    rows = []
    for state, group in sold.groupby("customer_state"):
        late, low, days = group["late"].dropna(), group["low_review"].dropna(), group["delivery_days"].dropna()
        rows.append({
            "state": state, "orders": int(len(group)), "sales": float(group["total_price"].sum()),
            "delivered": int(len(late)), "late_rate": float(late.mean()) if len(late) >= min_orders else None,
            "average_delivery_days": float(days.mean()) if len(days) >= min_orders else None,
            "reviewed": int(len(low)), "low_review_rate": float(low.mean()) if len(low) >= min_orders else None,
        })
    return sorted(rows, key=lambda r: -r["orders"])


def review_scores(frame: pd.DataFrame) -> list[dict]:
    """How many orders got each review score, 1 to 5 stars (the latest review per order)."""
    scores = trends.sold(frame)["review_score"].dropna().astype(int)
    total = int(len(scores))
    counts = scores.value_counts()
    return [{"score": s, "orders": int(counts.get(s, 0)), "share": int(counts.get(s, 0)) / total if total else None} for s in range(1, 6)]
