"""Hidden problems behind a good sales result: deterministic checks, each with the figures that triggered it.

A caveat says where to look, not why it happened.
"""
from app.analysis.categories import RECENT_MONTHS

MIN_RATE_RISE_PP = 1.0
LATE_REVIEW_RATIO = 2.0
TOP_CATEGORIES = 3


def window_rate(monthly: list[dict], count: str, total: str, months: int = RECENT_MONTHS) -> dict:
    """Pooled rate over the last `months` months against the `months` before (sum of counts, not a mean of rates)."""
    recent, previous = monthly[-months:], monthly[-2 * months:-months]

    def pooled(rows):
        denominator = sum(r[total] for r in rows)
        return {"count": sum(r[count] for r in rows), "total": denominator,
                "rate": sum(r[count] for r in rows) / denominator if denominator else None}

    now, before = pooled(recent), pooled(previous)
    change_pp = (now["rate"] - before["rate"]) * 100 if now["rate"] is not None and before["rate"] is not None else None
    return {"recent": now, "previous": before, "change_pp": change_pp,
            "recent_months": [r["month"] for r in recent], "previous_months": [r["month"] for r in previous]}


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
            "worst": [{"category": c["category"], "change_pct": c["change_pct"], "change_abs": c["change_abs"]} for c in worst],
        },
    }


def rate_rising(caveat_id: str, title: str, window: dict) -> dict:
    change = window["change_pp"]
    return {"id": caveat_id, "triggered": change is not None and change >= MIN_RATE_RISE_PP,
            "title": title, "evidence": {**window, "threshold_pp": MIN_RATE_RISE_PP}}


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
                     "threshold_ratio": LATE_REVIEW_RATIO},
    }
