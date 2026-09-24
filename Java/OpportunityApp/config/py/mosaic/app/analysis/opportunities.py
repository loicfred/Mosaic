"""Where to invest when sales are forecast to rise: growing categories checked against delivery and reviews.

Deterministic rules with their inputs exposed as evidence. Growth comes from item sales; the checks and risks use
the rest of the data: deliveries, reviews, cancellations, freight, payments, repeat customers and the seller base.
A suggestion says where the data points, not that investing there would pay off.
"""
import pandas as pd

from app.analysis.categories import MIN_RECENT_SALES
from app.analysis.populations import labelled_orders_in_range
from app.config import DATA_RANGE

MIN_RATE_ORDERS = 30
RATE_TOLERANCE_PP = 2.0
# Growth is judged against the business, size by share of recent sales; each label names its threshold in the API.
GROWTH_LEVELS_PP = {"strong": 20.0, "moderate": 5.0}
SIZE_LEVELS_SHARE = {"large": 0.05, "medium": 0.01}
# Rates a category must keep no worse than the business to count as ready.
RATE_CHECKS = ("late_rate", "low_review_rate", "cancel_rate")
# Risks from the category's profile: sales resting on one seller, freight far above the business, a shrinking basket.
SINGLE_SELLER_SHARE = 0.5
FREIGHT_GAP_PP = 5.0
BASKET_FALL_PCT = -5.0
READINESS_ORDER = {"ready": 0, "watch": 1, "unknown": 2, "fix_first": 3}


def sales_trend(history: list[float], forecast: list[float], recent_months: int) -> dict:
    """Average forecast month against the average of the last observed months."""
    recent = history[-recent_months:]
    recent_mean = sum(recent) / len(recent) if recent else 0.0
    forecast_mean = sum(forecast) / len(forecast) if forecast else 0.0
    change_pct = (forecast_mean - recent_mean) / recent_mean * 100 if recent_mean > 0 else None
    return {
        "recent_months": len(recent),
        "recent_monthly_mean": recent_mean,
        "forecast_months": len(forecast),
        "forecast_monthly_mean": forecast_mean,
        "change_pct": change_pct,
        "increasing": change_pct is not None and change_pct > 0,
    }


def category_rates(frame: pd.DataFrame, months: list[str], data_range: tuple[str, str] = DATA_RANGE) -> dict:
    """Late-delivery, low-review and cancellation rates per category (of the priciest item) over the given purchase months."""
    return {rate: group_rates(labelled_orders_in_range(frame, label, data_range), label, "category", months)
            for label, rate in (("late", "late_rate"), ("low_review", "low_review_rate"), ("cancelled", "cancel_rate"))}


def group_rates(orders: pd.DataFrame, label: str, group: str, months: list[str]) -> dict:
    """A rate for the business and each group over the given months, to judge a candidate against the business."""
    window = orders[orders["month"].isin(months)]
    grouped = window.groupby(group)[label].agg(["size", "mean"])
    return {
        "business": {"orders": int(len(window)), "rate": float(window[label].mean()) if len(window) else None},
        "by_group": {name: {"orders": int(row["size"]), "rate": float(row["mean"])} for name, row in grouped.iterrows()},
    }


def compare_with_business(rates: dict, name: str) -> dict:
    """A group's rate against the business rate; too few orders means no verdict rather than a guess."""
    business = rates["business"]["rate"]
    own = rates["by_group"].get(name, {"orders": 0, "rate": None})
    enough = own["orders"] >= MIN_RATE_ORDERS and own["rate"] is not None and business is not None
    gap_pp = (own["rate"] - business) * 100 if enough else None
    return {
        "orders": own["orders"],
        "rate": own["rate"] if enough else None,
        "business_rate": business,
        "gap_pp": gap_pp,
        "tolerance_pp": RATE_TOLERANCE_PP,
        "min_orders": MIN_RATE_ORDERS,
        "within_business": None if gap_pp is None else gap_pp <= RATE_TOLERANCE_PP,
        "level": rate_level(gap_pp),
    }


def investment_candidates(categories: list[dict], rates: dict, limit: int, profiles: dict | None = None,
                          business: dict | None = None) -> list[dict]:
    """The categories worth a closer look, ranked by readiness then sales added, with their checks.

    There is always something to suggest while any category has enough sales. Each candidate's ``basis`` says which
    rule found it, strictest first: ``growing`` (sales up, at least as fast as the business); when none is,
    ``beats_business`` (falling less than the business); when none is, ``best_available`` (the smallest falls).
    ``profiles`` maps a category to its ``{"recent", "previous"}`` business profiles and ``business`` is the whole
    business's recent profile; without them the candidate carries no profile and no risks.
    """
    supported = [c for c in categories if c["change_pct"] is not None and c["recent"] + c["previous"] >= MIN_RECENT_SALES]
    total = next((c["total_change_pct"] for c in supported if c["total_change_pct"] is not None), None)
    growing = [c for c in supported if c["change_pct"] > 0 and (total is None or c["change_pct"] >= total)]
    beating = [c for c in supported if total is not None and c["change_pct"] >= total]
    if growing:
        basis, chosen = "growing", growing
    elif beating:
        basis, chosen = "beats_business", beating
    else:
        basis, chosen = "best_available", sorted(supported, key=lambda c: -c["change_pct"])[:limit]
    candidates = []
    for category in chosen:
        change = category["change_pct"]
        checks = {name: compare_with_business(rates[name], category["category"]) for name in RATE_CHECKS if name in rates}
        own = (profiles or {}).get(category["category"])
        risks = profile_risks(own["recent"], own["previous"], business) if own and business else []
        readiness = _readiness([check["within_business"] for check in checks.values()], risks)
        candidates.append({
            "category": category["category"],
            "basis": basis,
            "recent": category["recent"],
            "previous": category["previous"],
            "change_abs": category["change_abs"],
            "change_pct": change,
            "total_change_pct": category["total_change_pct"],
            "share_recent": category["share_recent"],
            "growth_level": growth_level(change, category["total_change_pct"]),
            "size_level": size_level(category["share_recent"]),
            "checks": checks,
            "risks": risks,
            "profile": own,
            "readiness": readiness,
            "series": [{"month": m["month"], "sales": m["sales"]} for m in category["series"]],
        })
    candidates.sort(key=lambda c: (READINESS_ORDER[c["readiness"]], -c["change_abs"]))
    return candidates[:limit]


def profile_risks(recent: dict, previous: dict, business: dict) -> list[dict]:
    """Risks the growth figures alone do not show, each with the values and the threshold that decided it."""
    top = recent["top_seller_share"]
    gap = _pp(recent["freight_share"], business["freight_share"])
    basket = _pct(recent["average_order_value"], previous["average_order_value"])
    return [
        {"id": "depends_on_one_seller", "triggered": top is not None and top >= SINGLE_SELLER_SHARE,
         "value": top, "sellers": recent["sellers"], "threshold": SINGLE_SELLER_SHARE},
        {"id": "freight_heavy", "triggered": gap is not None and gap >= FREIGHT_GAP_PP,
         "value": recent["freight_share"], "business": business["freight_share"], "gap_pp": gap, "threshold_pp": FREIGHT_GAP_PP},
        {"id": "basket_shrinking", "triggered": basket is not None and basket <= BASKET_FALL_PCT,
         "value": recent["average_order_value"], "previous": previous["average_order_value"], "change_pct": basket,
         "threshold_pct": BASKET_FALL_PCT},
    ]


def growth_level(change_pct: float | None, total_change_pct: float | None) -> str:
    """How far a category's growth beats the business: strong, moderate or weak; unknown without both figures."""
    if change_pct is None or total_change_pct is None:
        return "unknown"
    gap = change_pct - total_change_pct
    return next((name for name, floor in GROWTH_LEVELS_PP.items() if gap >= floor), "weak")


def size_level(share: float | None) -> str:
    """A category's share of recent business sales: large, medium or small; unknown when there were no sales."""
    if share is None:
        return "unknown"
    return next((name for name, floor in SIZE_LEVELS_SHARE.items() if share >= floor), "small")


def rate_level(gap_pp: float | None) -> str:
    """A category rate against the business: better, in_line or worse, within the tolerance either side."""
    if gap_pp is None:
        return "unknown"
    return "worse" if gap_pp > RATE_TOLERANCE_PP else "better" if gap_pp < -RATE_TOLERANCE_PP else "in_line"


def _readiness(verdicts: list, risks: list[dict]) -> str:
    """fix_first when a rate is worse than the business; unknown when one cannot be judged; watch for a profile risk."""
    if False in verdicts:
        return "fix_first"
    if not verdicts or None in verdicts:
        return "unknown"
    return "watch" if any(risk["triggered"] for risk in risks) else "ready"


def _pp(value: float | None, reference: float | None) -> float | None:
    return (value - reference) * 100 if value is not None and reference is not None else None


def _pct(value: float | None, reference: float | None) -> float | None:
    return (value - reference) / reference * 100 if value is not None and reference else None
