"""Where to invest when sales are forecast to rise: growing categories checked against delivery and reviews.

Deterministic rules with their inputs exposed as evidence. A suggestion says where the data points,
not that investing there would pay off.
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
    """Late-delivery and low-review rates per category (of the priciest item) over the given purchase months."""
    rates = {}
    for label, rate in (("late", "late_rate"), ("low_review", "low_review_rate")):
        labelled = labelled_orders_in_range(frame, label, data_range)
        labelled = labelled[labelled["month"].isin(months)]
        overall = {"orders": int(len(labelled)), "rate": float(labelled[label].mean()) if len(labelled) else None}
        grouped = labelled.groupby("category")[label].agg(["size", "mean"])
        rates[rate] = {
            "business": overall,
            "by_category": {c: {"orders": int(r["size"]), "rate": float(r["mean"])} for c, r in grouped.iterrows()},
        }
    return rates


def investment_candidates(categories: list[dict], rates: dict, limit: int) -> list[dict]:
    """Categories growing faster than the business, ranked by sales added, with their reliability checks."""
    candidates = []
    for category in categories:
        change = category["change_pct"]
        support = category["recent"] + category["previous"]
        if change is None or change <= 0 or support < MIN_RECENT_SALES:
            continue
        if category["total_change_pct"] is not None and change < category["total_change_pct"]:
            continue
        checks = {name: _check(rates[name], category["category"]) for name in ("late_rate", "low_review_rate")}
        verdicts = [check["within_business"] for check in checks.values()]
        readiness = "ready" if all(v is True for v in verdicts) else "fix_first" if False in verdicts else "unknown"
        candidates.append({
            "category": category["category"],
            "recent": category["recent"],
            "previous": category["previous"],
            "change_abs": category["change_abs"],
            "change_pct": change,
            "total_change_pct": category["total_change_pct"],
            "share_recent": category["share_recent"],
            "growth_level": growth_level(change, category["total_change_pct"]),
            "size_level": size_level(category["share_recent"]),
            "checks": checks,
            "readiness": readiness,
        })
    order = {"ready": 0, "unknown": 1, "fix_first": 2}
    candidates.sort(key=lambda c: (order[c["readiness"]], -c["change_abs"]))
    return candidates[:limit]


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


def _check(rate: dict, category: str) -> dict:
    """Category rate against the business rate; too few orders means no verdict rather than a guess."""
    business = rate["business"]["rate"]
    own = rate["by_category"].get(category, {"orders": 0, "rate": None})
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
