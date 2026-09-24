"""Delivery speed: the late-delivery rate, where it improved, and what could hide behind the improvement."""
import pandas as pd

from app.analysis import trends
from app.analysis.opportunities import group_rates
from app.data.records import records

MEASURE = {"measure": "delivery", "label": "Late-delivery rate", "unit": "rate", "good_direction": "down",
           "group_label": "customer state"}
FREIGHT_SHARE_RISE_PP = 1.0
ORDERS_FALL_PCT = 5.0
PROMISED_DAYS_RISE = 1.0
STATE_RISE_PP = 2.0
RULES = {
    "window": "the last 3 months against the 3 before, pooled over orders",
    "population": "delivered orders with a delivery date, by purchase month; late means delivered after the promised date",
    "suggestion": "customer states whose late rate fell at least as much as the business, with enough orders in both windows",
    "min_group_orders": trends.MIN_RATE_ORDERS,
    "checks_against_business": "low-review rate in the last 3 months",
    "thresholds": {"freight_share_rise_pp": FREIGHT_SHARE_RISE_PP, "orders_fall_pct": ORDERS_FALL_PCT,
                   "promised_days_rise": PROMISED_DAYS_RISE, "state_rise_pp": STATE_RISE_PP},
}
LIMITATIONS = [
    "A state is the customer's state; the seller may be elsewhere.",
    "Faster delivery in the past does not prove that promoting it would bring more orders.",
]


def monthly(frame: pd.DataFrame) -> list[dict]:
    delivered = trends.eligible(frame, "late")
    rows = delivered.groupby("month").agg(
        orders=("late", "size"), late=("late", "sum"), value=("late", "mean"),
        delivery_days=("delivery_days", "mean"), promised_days=("promised_days", "mean"),
    ).reset_index()
    rows["late"] = rows["late"].astype(int)
    return records(rows)


def trend(frame: pd.DataFrame) -> dict:
    return trends.measure_trend(trends.eligible(frame, "late"), "late", "rate", "down")


def opportunities(frame: pd.DataFrame, limit: int) -> dict:
    delivered = trends.eligible(frame, "late")
    business = trends.measure_trend(delivered, "late", "rate", "down")
    recent, previous = business["recent_months"], business["previous_months"]
    groups = trends.group_windows(delivered, "late", "customer_state", recent, previous, "rate")
    rates = {"low_review_rate": group_rates(trends.eligible(frame, "low_review"), "low_review", "customer_state", recent)}
    series = trends.group_series(delivered, "late", "customer_state", [g["name"] for g in groups])
    found = trends.candidates(groups, business, "rate", "down", rates, series, limit) if business["improving"] else []
    return {"trend": business, "candidates": found,
            "business_rates": {name: rate["business"] for name, rate in rates.items()}}


def caveats(frame: pd.DataFrame) -> list[dict]:
    delivered = trends.eligible(frame, "late")
    sold = trends.sold(frame)
    recent, previous = trends.windows(delivered["month"])
    orders = sold.groupby("month").agg(orders=("order_id", "size")).reset_index().to_dict(orient="records")
    freight = sold.groupby("month")[["total_freight", "total_price"]].sum()
    freight_monthly = [{"month": m, "value": float(r["total_freight"] / r["total_price"])} for m, r in freight.iterrows() if r["total_price"] > 0]
    promised = delivered.groupby("month")["promised_days"].mean()
    groups = trends.group_windows(delivered, "late", "customer_state", recent, previous, "rate")
    return [
        trends.change_check(
            "freight_share_rising", "Freight takes a bigger share of what customers pay", "Freight as a share of item value",
            "rate", trends.pooled_ratio(sold, "total_freight", "total_price", recent),
            trends.pooled_ratio(sold, "total_freight", "total_price", previous), "up", FREIGHT_SHARE_RISE_PP, freight_monthly),
        trends.change_check(
            "orders_falling", "There are fewer orders to deliver", "Orders a month", "count",
            trends.monthly_mean(orders, "orders", recent), trends.monthly_mean(orders, "orders", previous), "down",
            ORDERS_FALL_PCT, [{"month": row["month"], "value": row["orders"]} for row in orders]),
        trends.change_check(
            "promised_days_rising", "Customers are promised longer delivery times", "Promised delivery time",
            "days", trends.pooled_mean(delivered, "promised_days", recent), trends.pooled_mean(delivered, "promised_days", previous),
            "up", PROMISED_DAYS_RISE, [{"month": m, "value": float(v)} for m, v in promised.items()]),
        trends.groups_check(
            "states_getting_later", "Some customer states are getting more late deliveries", "Late-delivery rate",
            "customer state", "rate", groups, "up", STATE_RISE_PP),
    ]
