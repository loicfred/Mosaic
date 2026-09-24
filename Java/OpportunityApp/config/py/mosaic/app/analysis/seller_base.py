"""Seller base: how many sellers sell each month, where new sellers find customers, and what could hide behind growth.

A seller counts in a month when it sold the priciest item of at least one order that month, as everywhere else in
this API; a seller of a cheaper item in a multi-seller order is not counted for that order.
"""
import pandas as pd

from app.analysis import trends
from app.analysis.opportunities import group_rates
from app.data.records import records

MEASURE = {"measure": "sellers", "label": "Active sellers a month", "unit": "count", "good_direction": "up",
           "group_label": "category"}
ORDERS_PER_SELLER_FALL_PCT = 5.0
ORDERS_FALL_PCT = 5.0
NEW_SELLER_LATE_RATIO = 1.5
CATEGORY_CROWDING_PCT = 10.0
RULES = {
    "window": "the last 3 months against the 3 before; active sellers are averaged over the months of each window",
    "population": "orders counted as sales (with items, not cancelled or unavailable), by purchase month",
    "seller": "the seller of each order's priciest item; a seller who only sold cheaper items in multi-seller orders "
              "that month is not counted (about 1% of sellers a month)",
    "suggestion": "categories whose active sellers grew at least as fast as the business while their orders grew too, "
                  "with enough orders in both windows",
    "min_group_orders": trends.MIN_RATE_ORDERS,
    "checks_against_business": "late-delivery and low-review rates in the last 3 months",
    "new_seller": "a seller whose first order in the data is in the last 3 months",
    "thresholds": {"orders_per_seller_fall_pct": ORDERS_PER_SELLER_FALL_PCT, "orders_fall_pct": ORDERS_FALL_PCT,
                   "new_seller_late_ratio": NEW_SELLER_LATE_RATIO, "category_crowding_pct": CATEGORY_CROWDING_PCT},
}
LIMITATIONS = [
    "An order's seller and category are those of its priciest item.",
    "More sellers is not more sales: each seller's orders can fall while the seller count grows.",
]


def monthly(frame: pd.DataFrame) -> list[dict]:
    rows = _sold(frame).groupby("month").agg(orders=("order_id", "size"), value=("seller_id", "nunique")).reset_index()
    rows["orders_per_seller"] = rows["orders"] / rows["value"]
    return records(rows)


def trend(frame: pd.DataFrame) -> dict:
    rows = monthly(frame)
    recent, previous = trends.windows([row["month"] for row in rows])
    return trends.trend(trends.monthly_mean(rows, "value", recent), trends.monthly_mean(rows, "value", previous),
                        "count", "up", recent, previous)


def opportunities(frame: pd.DataFrame, limit: int) -> dict:
    sold = _sold(frame)
    business = trend(frame)
    recent = business["recent_months"]
    groups = _category_windows(sold, recent, business["previous_months"])
    rates = {"late_rate": group_rates(trends.eligible(frame, "late"), "late", "category", recent),
             "low_review_rate": group_rates(trends.eligible(frame, "low_review"), "low_review", "category", recent)}
    series = _category_series(sold, [g["name"] for g in groups])
    orders_growing = lambda g: g["orders"]["change_pct"] is not None and g["orders"]["change_pct"] > 0
    found = trends.candidates(groups, business, "count", "up", rates, series, limit, orders_growing) if business["improving"] else []
    return {"trend": business, "candidates": found,
            "business_rates": {name: rate["business"] for name, rate in rates.items()}}


def caveats(frame: pd.DataFrame) -> list[dict]:
    sold = _sold(frame)
    rows = monthly(frame)
    recent, previous = trends.windows([row["month"] for row in rows])
    groups = _category_windows(sold, recent, previous)
    crowding = [{**g["orders_per_seller"], "name": g["name"]} for g in groups]
    return [
        trends.change_check(
            "orders_per_seller_falling", "Each seller gets fewer orders", "Orders per active seller a month", "count",
            _per_seller(rows, recent), _per_seller(rows, previous), "down", ORDERS_PER_SELLER_FALL_PCT,
            [{"month": row["month"], "value": row["orders_per_seller"]} for row in rows]),
        trends.change_check(
            "orders_falling", "There are fewer orders to share between sellers", "Orders a month", "count",
            trends.monthly_mean(rows, "orders", recent), trends.monthly_mean(rows, "orders", previous), "down",
            ORDERS_FALL_PCT, [{"month": row["month"], "value": row["orders"]} for row in rows]),
        _new_sellers_late(frame, recent),
        trends.groups_check(
            "categories_crowding", "In some categories each seller gets far fewer orders", "Orders per active seller a month",
            "category", "count", crowding, "down", CATEGORY_CROWDING_PCT),
    ]


def _sold(frame: pd.DataFrame) -> pd.DataFrame:
    sold = trends.sold(frame)
    return sold[sold["seller_id"].notna()]


def _per_seller(rows: list[dict], months: list[str]) -> dict:
    window = [row for row in rows if row["month"] in months]
    sellers = sum(row["value"] for row in window)
    orders = sum(row["orders"] for row in window)
    return {"value": orders / sellers if sellers else None, "orders": orders}


def _category_windows(sold: pd.DataFrame, recent: list[str], previous: list[str]) -> list[dict]:
    """Per category: active sellers a month (a month without orders has none), orders and orders per seller."""
    known = sold[sold["category"].notna()]
    per_month = known.groupby(["category", "month"]).agg(orders=("order_id", "size"), sellers=("seller_id", "nunique"))
    result = []
    for name, rows in per_month.groupby(level=0):
        rows = rows.droplevel(0)
        window = {label: rows.reindex(months, fill_value=0) for label, months in (("recent", recent), ("previous", previous))}
        orders = {label: int(w["orders"].sum()) for label, w in window.items()}
        if not recent or not previous or min(orders.values()) < trends.MIN_RATE_ORDERS:
            continue
        sellers = {label: float(w["sellers"].mean()) for label, w in window.items()}
        per_seller = {label: orders[label] / window[label]["sellers"].sum() for label in window}
        result.append({
            **trends.group_row(name, {"value": sellers["recent"], "orders": orders["recent"]},
                               {"value": sellers["previous"], "orders": orders["previous"]}, "count"),
            "orders": {"recent": orders["recent"], "previous": orders["previous"],
                       **trends.change(float(orders["recent"]), float(orders["previous"]), "count")},
            "orders_per_seller": trends.group_row(name, {"value": per_seller["recent"], "orders": orders["recent"]},
                                                  {"value": per_seller["previous"], "orders": orders["previous"]}, "count"),
        })
    return result


def _category_series(sold: pd.DataFrame, names: list[str]) -> dict[str, list[dict]]:
    counts = sold[sold["category"].isin(names)].groupby(["category", "month"])["seller_id"].nunique()
    return {name: [{"month": month, "value": int(value)} for (_, month), value in rows.items()]
            for name, rows in counts.groupby(level=0)}


def _new_sellers_late(frame: pd.DataFrame, recent: list[str]) -> dict:
    """Late-delivery rate of orders from sellers new in the recent window against sellers seen before it."""
    first_month = frame[frame["seller_id"].notna()].groupby("seller_id")["purchase_ts"].min().dt.strftime("%Y-%m")
    delivered = trends.eligible(frame, "late")
    window = delivered[delivered["month"].isin(recent) & delivered["seller_id"].notna()]
    new = window["seller_id"].map(first_month).isin(recent)
    return trends.gap_check(
        "new_sellers_late_more_often", "Orders from new sellers are delivered late more often", "Late-delivery rate",
        "rate", trends.group_value(window[new], "late", "orders from new sellers"),
        trends.group_value(window[~new], "late", "orders from established sellers"),
        NEW_SELLER_LATE_RATIO)
