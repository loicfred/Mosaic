"""Shared rules for the trend pages: the last months against the ones before, with every figure's inputs kept.

A window value is pooled (the sum over the count of known values), so a rate is late orders over delivered orders,
never a mean of monthly rates. Unknown stays None and is never read as zero. A caveat says where to look, not why.
"""
from types import ModuleType

import pandas as pd

from app.analysis.categories import RECENT_MONTHS
from app.analysis.opportunities import MIN_RATE_ORDERS, compare_with_business
from app.analysis.populations import labelled_orders_in_range
from app.analysis.selection import select_windows
from app.config import DATA_RANGE, EXCLUDED_STATUSES

TOP_GROUPS = 3
LIMITATIONS = [
    "The figures show what changed, not why; things that move together are not proof that one causes the other.",
    "The most recent months can still have orders on their way or not yet reviewed, so their figures may change.",
]


def eligible(frame: pd.DataFrame, column: str, data_range: tuple[str, str] = DATA_RANGE) -> pd.DataFrame:
    """Orders whose `column` is known, purchased inside the analysed range, with their purchase month."""
    return labelled_orders_in_range(frame, column, data_range)


def sold(frame: pd.DataFrame, data_range: tuple[str, str] = DATA_RANGE) -> pd.DataFrame:
    """Orders counted as sales: with items, and not cancelled or unavailable."""
    orders = eligible(frame, "total_price", data_range)
    return orders[~orders["order_status"].isin(EXCLUDED_STATUSES)]


def windows(months, n: int = RECENT_MONTHS) -> tuple[list[str], list[str]]:
    """The last `n` months and the `n` before them; either can be short or empty when history is short."""
    return select_windows(months, n)


def pooled_mean(orders: pd.DataFrame, column: str, months: list[str]) -> dict:
    values = orders.loc[orders["month"].isin(months), column].dropna()
    return {"value": float(values.mean()) if len(values) else None, "orders": int(len(values))}


def pooled_ratio(orders: pd.DataFrame, numerator: str, denominator: str, months: list[str]) -> dict:
    window = orders[orders["month"].isin(months)]
    total = float(window[denominator].sum())
    return {"value": float(window[numerator].sum()) / total if total > 0 else None, "orders": int(len(window))}


def group_value(orders: pd.DataFrame, column: str, label: str) -> dict:
    """The mean of `column` over one named set of orders, such as the late orders or the new sellers' orders."""
    return {"label": label, "orders": int(len(orders)), "value": float(orders[column].mean()) if len(orders) else None}


def monthly_mean(monthly: list[dict], key: str, months: list[str]) -> dict:
    """Average of a monthly figure over the window, such as active sellers a month."""
    rows = [row for row in monthly if row["month"] in months]
    return {"value": sum(row[key] for row in rows) / len(rows) if rows else None,
            "orders": sum(row["orders"] for row in rows)}


def change(recent: float | None, previous: float | None, unit: str) -> dict:
    """Rates move in percentage points, other units in their own terms; the relative change needs a non-zero base."""
    change_unit = "pp" if unit == "rate" else unit
    if recent is None or previous is None:
        return {"change": None, "change_unit": change_unit, "change_pct": None}
    diff = recent - previous
    return {"change": diff * 100 if unit == "rate" else diff, "change_unit": change_unit,
            "change_pct": diff / previous * 100 if previous else None}


def measured(moved: dict, unit: str) -> float | None:
    """The figure thresholds are read against: the relative change for counts, the plain change otherwise."""
    return moved["change_pct"] if unit == "count" else moved["change"]


def trend(recent: dict, previous: dict, unit: str, good_direction: str,
          recent_months: list[str], previous_months: list[str]) -> dict:
    moved = change(recent["value"], previous["value"], unit)
    return {"recent": recent, "previous": previous, **moved, "improving": _better(measured(moved, unit), good_direction),
            "recent_months": recent_months, "previous_months": previous_months}


def measure_trend(orders: pd.DataFrame, column: str, unit: str, good_direction: str) -> dict:
    recent, previous = windows(orders["month"])
    return trend(pooled_mean(orders, column, recent), pooled_mean(orders, column, previous), unit, good_direction,
                 recent, previous)


def group_windows(orders: pd.DataFrame, column: str, group: str, recent: list[str], previous: list[str], unit: str,
                  min_orders: int = MIN_RATE_ORDERS) -> list[dict]:
    """Each group's pooled value in both windows; a group short of `min_orders` in either window gets no verdict."""
    known = orders[orders[column].notna() & orders[group].notna()]
    stats = {name: known[known["month"].isin(months)].groupby(group)[column].agg(["size", "mean"])
             for name, months in (("recent", recent), ("previous", previous))}
    result = []
    for name in stats["recent"].index.intersection(stats["previous"].index):
        now, before = stats["recent"].loc[name], stats["previous"].loc[name]
        if now["size"] < min_orders or before["size"] < min_orders:
            continue
        result.append(group_row(name, {"value": float(now["mean"]), "orders": int(now["size"])},
                                {"value": float(before["mean"]), "orders": int(before["size"])}, unit))
    return result


def group_row(name: str, recent: dict, previous: dict, unit: str) -> dict:
    return {"name": name, "recent": recent, "previous": previous, **change(recent["value"], previous["value"], unit)}


def group_series(orders: pd.DataFrame, column: str, group: str, names: list[str]) -> dict[str, list[dict]]:
    subset = orders[orders[group].isin(names) & orders[column].notna()]
    means = subset.groupby([group, "month"])[column].mean()
    return {name: [{"month": month, "value": float(value)} for (_, month), value in rows.items()]
            for name, rows in means.groupby(level=0)}


def candidates(groups: list[dict], business: dict, unit: str, good_direction: str, rates: dict,
               series: dict[str, list[dict]], limit: int, require=lambda group: True) -> list[dict]:
    """Groups that improved at least as much as the business, ready ones first, then the largest."""
    target = measured(business, unit)
    total = business["recent"]["orders"]
    result = []
    for group in groups:
        own = measured(group, unit)
        if not _better(own, good_direction) or target is None or not require(group):
            continue
        if (own > target) if good_direction == "down" else (own < target):
            continue
        checks = {name: compare_with_business(rate, group["name"]) for name, rate in rates.items()}
        verdicts = [check["within_business"] for check in checks.values()]
        readiness = "ready" if all(v is True for v in verdicts) else "fix_first" if False in verdicts else "unknown"
        result.append({**group, "share_recent": group["recent"]["orders"] / total if total else None,
                       "checks": checks, "readiness": readiness, "series": series.get(group["name"], [])})
    order = {"ready": 0, "unknown": 1, "fix_first": 2}
    result.sort(key=lambda c: (order[c["readiness"]], -c["recent"]["orders"]))
    return result[:limit]


def change_check(check_id: str, title: str, label: str, unit: str, recent: dict, previous: dict, worse_when: str,
                 threshold: float, monthly: list[dict] | None = None) -> dict:
    """One figure, recent against previous; `threshold` is a magnitude in the change's own unit (% for counts)."""
    moved = change(recent["value"], previous["value"], unit)
    return {"id": check_id, "kind": "change", "triggered": _past(measured(moved, unit), worse_when, threshold), "title": title,
            "comparison": {"label": label, "unit": unit, "recent": recent, "previous": previous, **moved,
                           "worse_when": worse_when, "threshold": threshold,
                           "threshold_unit": _threshold_unit(unit)},
            "monthly": monthly or []}


def groups_check(check_id: str, title: str, label: str, group_label: str, unit: str, groups: list[dict],
                 worse_when: str, threshold: float) -> dict:
    """How many groups moved the wrong way by at least `threshold`, with the worst few named."""
    flagged = [g for g in groups if _past(measured(g, unit), worse_when, threshold)]
    worst = sorted(flagged, key=lambda g: measured(g, unit), reverse=worse_when == "up")[:TOP_GROUPS]
    return {"id": check_id, "kind": "groups", "triggered": bool(flagged), "title": title,
            "groups": {"label": label, "group_label": group_label, "unit": unit, "flagged": len(flagged),
                       "of": len(groups), "worst": worst, "all": groups, "worse_when": worse_when, "threshold": threshold,
                       "threshold_unit": _threshold_unit(unit)}}


def gap_check(check_id: str, title: str, label: str, unit: str, worse: dict, better: dict, threshold_ratio: float,
              min_orders: int = MIN_RATE_ORDERS) -> dict:
    """One group's value against another's; both need `min_orders` for a verdict."""
    enough = worse["orders"] >= min_orders and better["orders"] >= min_orders
    known = enough and worse["value"] is not None and better["value"] is not None
    ratio = worse["value"] / better["value"] if known and better["value"] > 0 else None
    # none at all on the better side leaves the ratio undefined, yet any on the worse side is the starkest gap
    starkest = known and better["value"] == 0 and worse["value"] > 0
    return {"id": check_id, "kind": "gap", "triggered": bool(starkest or (ratio is not None and ratio >= threshold_ratio)),
            "title": title, "gap": {"label": label, "unit": unit, "worse": worse, "better": better, "ratio": ratio,
                                    "threshold_ratio": threshold_ratio, "min_orders": min_orders}}


def trend_body(measure: ModuleType, frame: pd.DataFrame) -> dict:
    return {**measure.MEASURE, "trend": measure.trend(frame), "monthly": measure.monthly(frame),
            "rules": measure.RULES, "limitations": measure.LIMITATIONS + LIMITATIONS}


def opportunities_body(measure: ModuleType, frame: pd.DataFrame, limit: int) -> dict:
    found = measure.opportunities(frame, limit)
    return {**measure.MEASURE, **found, "rules": measure.RULES, "limitations": measure.LIMITATIONS + LIMITATIONS,
            "reason": "not_improving" if not found["trend"]["improving"]
            else None if found["candidates"] else "no_improving_groups"}


def caveats_body(measure: ModuleType, frame: pd.DataFrame) -> dict:
    checks = measure.caveats(frame)
    return {**measure.MEASURE, "trend": measure.trend(frame), "checks": checks,
            "triggered": sum(check["triggered"] for check in checks), "limitations": measure.LIMITATIONS + LIMITATIONS}


def _threshold_unit(unit: str) -> str:
    return "pct" if unit == "count" else "pp" if unit == "rate" else unit


def _better(value: float | None, good_direction: str) -> bool:
    return value is not None and (value < 0 if good_direction == "down" else value > 0)


def _past(value: float | None, worse_when: str, threshold: float) -> bool:
    if value is None:
        return False
    value = round(value, 9)  # 21% - 20% is 0.999... pp in floating point; exactly at the threshold must count
    return value >= threshold if worse_when == "up" else value <= -threshold
