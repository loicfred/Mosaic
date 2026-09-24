"""Customer satisfaction: the share of 1 or 2 star reviews, where it improved, and what could hide behind it."""
import pandas as pd

from app.analysis import trends
from app.analysis.opportunities import group_rates
from app.data.records import records

MEASURE = {"measure": "reviews", "label": "Low-review rate", "unit": "rate", "good_direction": "down",
           "group_label": "category"}
LATE_REVIEW_RATIO = 2.0
CATEGORY_RISE_PP = 2.0
UNREVIEWED_RISE_PP = 1.0
RULES = {
    "window": "the last 3 months against the 3 before, pooled over orders",
    "population": "reviewed orders by purchase month, the latest review of each order; low means 1 or 2 stars",
    "suggestion": "categories whose low-review rate fell at least as much as the business while their sales grew, "
                  "with enough reviewed orders in both windows",
    "min_group_orders": trends.MIN_RATE_ORDERS,
    "checks_against_business": "late-delivery rate in the last 3 months",
    "thresholds": {"late_review_ratio": LATE_REVIEW_RATIO, "category_rise_pp": CATEGORY_RISE_PP,
                   "unreviewed_rise_pp": UNREVIEWED_RISE_PP},
}
LIMITATIONS = [
    "An order's category is the category of its priciest item.",
    "Better reviews in the past do not prove that more sales in a category would keep them.",
]


def monthly(frame: pd.DataFrame) -> list[dict]:
    reviewed = trends.eligible(frame, "low_review")
    rows = reviewed.groupby("month").agg(
        orders=("low_review", "size"), low=("low_review", "sum"), value=("low_review", "mean"),
        score=("review_score", "mean"),
    ).reset_index()
    rows["low"] = rows["low"].astype(int)
    return records(rows)


def trend(frame: pd.DataFrame) -> dict:
    return trends.measure_trend(trends.eligible(frame, "low_review"), "low_review", "rate", "down")


def opportunities(frame: pd.DataFrame, limit: int) -> dict:
    reviewed = trends.eligible(frame, "low_review")
    business = trends.measure_trend(reviewed, "low_review", "rate", "down")
    recent, previous = business["recent_months"], business["previous_months"]
    sales = _category_sales(trends.sold(frame), recent, previous)
    groups = [{**g, "sales": sales.get(g["name"])}
              for g in trends.group_windows(reviewed, "low_review", "category", recent, previous, "rate")]
    rates = {"late_rate": group_rates(trends.eligible(frame, "late"), "late", "category", recent)}
    series = trends.group_series(reviewed, "low_review", "category", [g["name"] for g in groups])
    growing = lambda g: g["sales"] is not None and g["sales"]["change_pct"] is not None and g["sales"]["change_pct"] > 0
    found = trends.candidates(groups, business, "rate", "down", rates, series, limit, growing) if business["improving"] else []
    return {"trend": business, "candidates": found,
            "business_rates": {name: rate["business"] for name, rate in rates.items()}}


def caveats(frame: pd.DataFrame) -> list[dict]:
    reviewed = trends.eligible(frame, "low_review")
    recent, previous = trends.windows(reviewed["month"])
    judged = reviewed[reviewed["month"].isin(recent) & reviewed["late"].notna()]
    delivered = trends.eligible(frame, "late").assign(unreviewed=lambda d: d["review_score"].isna().astype(float))
    unreviewed = delivered.groupby("month")["unreviewed"].mean()
    groups = trends.group_windows(reviewed, "low_review", "category", recent, previous, "rate")
    return [
        trends.gap_check(
            "late_orders_get_low_reviews", "Late orders still get far more 1 or 2 star reviews", "Low-review rate",
            "rate", trends.group_value(judged[judged["late"] == 1], "low_review", "late orders"),
            trends.group_value(judged[judged["late"] == 0], "low_review", "on-time orders"),
            LATE_REVIEW_RATIO),
        trends.groups_check(
            "categories_getting_worse", "Some categories are getting more low reviews", "Low-review rate", "category",
            "rate", groups, "up", CATEGORY_RISE_PP),
        trends.change_check(
            "unreviewed_share_rising", "More delivered orders have no review yet", "Delivered orders without a review",
            "rate", trends.pooled_mean(delivered, "unreviewed", recent), trends.pooled_mean(delivered, "unreviewed", previous),
            "up", UNREVIEWED_RISE_PP, [{"month": m, "value": float(v)} for m, v in unreviewed.items()]),
    ]


def _category_sales(sold: pd.DataFrame, recent: list[str], previous: list[str]) -> dict[str, dict]:
    """Item sales per category in each window, so a suggestion can require growing sales."""
    totals = {name: sold[sold["month"].isin(months)].groupby("category")["total_price"].sum()
              for name, months in (("recent", recent), ("previous", previous))}
    return {c: {"unit": "brl", "recent": float(totals["recent"].get(c, 0.0)), "previous": float(totals["previous"].get(c, 0.0)),
                **trends.change(float(totals["recent"].get(c, 0.0)), float(totals["previous"].get(c, 0.0)), "brl")}
            for c in totals["recent"].index.union(totals["previous"].index)}
