"""Hidden problems behind a good sales result: deterministic checks, each with the figures that triggered it.

A caveat says where to look, not why it happened.
"""
from app.analysis import business_profile, delivery, reviews
from app.analysis.business_profile import TOP_SELLERS
from app.analysis.categories import RECENT_MONTHS
from app.analysis.selection import row_windows
from app.config import DATA_RANGE

MIN_RATE_RISE_PP = 1.0
LATE_REVIEW_RATIO = 2.0
TOP_CATEGORIES = 3
# Cancellations are rare, so a quarter of a point (one more in every 400 orders) is already worth a look.
MIN_CANCEL_RISE_PP = 0.25
MIN_INSTALMENT_RISE_PP = 2.0
MIN_FREIGHT_RISE_PP = 1.0
MIN_BASKET_FALL_PCT = -2.0
# Growth that rests on new customers: under one order in ten comes from someone who bought before.
MIN_RETURNING_RATE = 0.10
MAX_TOP_SELLERS_SHARE = 0.25
MAX_TOP_STATE_SHARE = 0.50


def window_rate(monthly: list[dict], count: str, total: str, months: int = RECENT_MONTHS) -> dict:
    """Pooled rate over the last `months` months against the `months` before (sum of counts, not a mean of rates)."""
    recent, previous = row_windows(monthly, months)

    def pooled(rows):
        denominator = sum(r[total] for r in rows)
        return {"count": sum(r[count] for r in rows), "total": denominator,
                "rate": sum(r[count] for r in rows) / denominator if denominator else None}

    now, before = pooled(recent), pooled(previous)
    change_pp = (now["rate"] - before["rate"]) * 100 if now["rate"] is not None and before["rate"] is not None else None
    return {"recent": now, "previous": before, "change_pp": change_pp,
            "recent_months": [r["month"] for r in recent], "previous_months": [r["month"] for r in previous],
            "monthly": monthly}


def falling_behind(categories: list[dict]) -> dict:
    flagged = [c for c in categories if c["flags"]["underperforming_total"]]
    worst = sorted(flagged, key=lambda c: c["change_abs"])[:TOP_CATEGORIES]
    return {
        "id": "categories_falling_behind",
        "triggered": bool(flagged),
        "title": "Some categories are falling well behind the business",
        "evidence": {
            "flagged": len(flagged), "categories": len(categories),
            "total_change_pct": categories[0]["total_change_pct"] if categories else None,
            "sales_lost_by_flagged": sum(c["change_abs"] for c in flagged),
            "worst": [{"category": c["category"], "change_pct": c["change_pct"], "change_abs": c["change_abs"],
                       "series": [{"month": m["month"], "sales": m["sales"]} for m in c["series"]]} for c in worst],
        },
    }


def rate_rising(caveat_id: str, title: str, window: dict, threshold_pp: float = MIN_RATE_RISE_PP) -> dict:
    change = window["change_pp"]
    return {"id": caveat_id, "triggered": change is not None and change >= threshold_pp,
            "title": title, "evidence": {**window, "threshold_pp": threshold_pp}}


def late_orders_hurt_reviews(by_lateness: dict) -> dict:
    late, on_time = by_lateness["late"]["low_rate"], by_lateness["on_time"]["low_rate"]
    ratio = late / on_time if late is not None and on_time else None
    # no low reviews at all on time leaves the ratio undefined, yet any on late orders is the starkest gap
    never_on_time = on_time == 0 and late is not None and late > 0
    return {
        "id": "late_orders_get_low_reviews",
        "triggered": never_on_time or (ratio is not None and ratio >= LATE_REVIEW_RATIO),
        "title": "Late orders are far more likely to get a 1 or 2 star review",
        "evidence": {"late": by_lateness["late"], "on_time": by_lateness["on_time"], "ratio": ratio,
                     "threshold_ratio": LATE_REVIEW_RATIO, "period": {"start": DATA_RANGE[0], "end": DATA_RANGE[1]}},
    }


def window_ratio(monthly: list[dict], numerator: str, denominator: str, months: int = RECENT_MONTHS) -> dict:
    """Pooled ratio of two sums (such as freight over sales, or sales over orders), last months against the months before."""
    recent, previous = row_windows(monthly, months)

    def pooled(rows):
        bottom = sum(r[denominator] for r in rows)
        return {numerator: sum(r[numerator] for r in rows), denominator: bottom,
                "value": sum(r[numerator] for r in rows) / bottom if bottom else None}

    now, before = pooled(recent), pooled(previous)
    known = now["value"] is not None and before["value"] is not None
    return {"recent": now, "previous": before,
            "change": now["value"] - before["value"] if known else None,
            "change_pct": (now["value"] - before["value"]) / before["value"] * 100 if known and before["value"] else None,
            "recent_months": [r["month"] for r in recent], "previous_months": [r["month"] for r in previous]}


def freight_share_rising(monthly: list[dict]) -> dict:
    window = window_ratio(monthly, "freight", "sales")
    change_pp = window["change"] * 100 if window["change"] is not None else None
    return {"id": "freight_share_rising", "triggered": change_pp is not None and change_pp >= MIN_FREIGHT_RISE_PP,
            "title": "Freight is taking a bigger share of what customers pay",
            "evidence": {**window, "change_pp": change_pp, "threshold_pp": MIN_FREIGHT_RISE_PP, "monthly": monthly}}


def basket_shrinking(monthly: list[dict]) -> dict:
    window = window_ratio(monthly, "sales", "orders")
    change = window["change_pct"]
    return {"id": "basket_shrinking", "triggered": change is not None and change <= MIN_BASKET_FALL_PCT,
            "title": "The average order is getting smaller",
            "evidence": {**window, "threshold_pct": MIN_BASKET_FALL_PCT, "monthly": monthly}}


def few_returning_customers(monthly: list[dict], months: int = RECENT_MONTHS) -> dict:
    recent, _ = row_windows(monthly, months)
    customers, returning = sum(r["customers"] for r in recent), sum(r["returning"] for r in recent)
    rate = returning / customers if customers else None
    return {"id": "few_returning_customers", "triggered": rate is not None and rate < MIN_RETURNING_RATE,
            "title": "Almost every order comes from a new customer",
            "evidence": {"returning": returning, "customers": customers, "rate": rate, "threshold": MIN_RETURNING_RATE,
                         "recent_months": [r["month"] for r in recent], "monthly": monthly}}


def sales_concentrated(recent_profile: dict) -> list[dict]:
    """Two checks on the recent sales: resting on a few sellers, or on one customer state."""
    top_sellers, top_state = recent_profile["top_sellers_share"], recent_profile["top_state"]
    return [
        {"id": "sales_rest_on_few_sellers",
         "triggered": top_sellers is not None and top_sellers >= MAX_TOP_SELLERS_SHARE,
         "title": "A few sellers make a large part of the sales",
         "evidence": {"top_sellers": TOP_SELLERS, "share": top_sellers, "sellers": recent_profile["sellers"],
                      "threshold": MAX_TOP_SELLERS_SHARE}},
        {"id": "sales_rest_on_one_state",
         "triggered": top_state is not None and top_state["share"] >= MAX_TOP_STATE_SHARE,
         "title": "One state buys a large part of the sales",
         "evidence": {"state": top_state and top_state["state"], "share": top_state and top_state["share"],
                      "states": recent_profile["customer_states"], "threshold": MAX_TOP_STATE_SHARE}},
    ]


def sales_checks(frame, categories: list[dict]) -> list[dict]:
    """Every check behind the sales result, over the active windows (the last 3 months against the 3 before by default)."""
    late = window_rate(delivery.monthly_late_rate(frame), "late", "delivered")
    low = window_rate(reviews.monthly_low_review_rate(frame), "low", "reviewed")
    monthly = business_profile.monthly(frame)
    recent_months = [row["month"] for row in row_windows(monthly)[0]]
    recent = business_profile.profile(business_profile.placed_orders(frame, recent_months))
    return [
        falling_behind(categories),
        rate_rising("late_rate_rising", "Late deliveries are becoming more common", late),
        rate_rising("low_reviews_rising", "Low reviews are becoming more common", low),
        late_orders_hurt_reviews(reviews.low_review_by_lateness(frame)),
        rate_rising("cancellations_rising", "More orders are being cancelled",
                    window_rate(monthly, "cancelled", "placed"), MIN_CANCEL_RISE_PP),
        basket_shrinking(monthly),
        freight_share_rising(monthly),
        rate_rising("instalments_rising", "More customers are spreading payments over instalments",
                    window_rate(monthly, "multi_instalment", "paid"), MIN_INSTALMENT_RISE_PP),
        few_returning_customers(monthly),
        *sales_concentrated(recent),
    ]
