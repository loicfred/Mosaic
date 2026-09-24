"""Every check from the sales and trend pages as one ranked list, with the orders behind the record-backed ones.

A finding is ``<page>:<check id>``. Its numbers come from the same functions as the page it belongs to; only the
selection (periods, category, customer state, thresholds) can change them, and only for the current request.
"""
import hashlib
import json

import pandas as pd

from app.analysis import business_profile, caveats, delivery_speed, satisfaction, seller_base, trends
from app.analysis.selection import select_windows
from app.data.records import records

RANKING_RULE = ("Triggered checks first, then by the gross item sales of the orders they touch in the recent window "
                "(largest first); checks with no order subset to measure come last.")
EXPOSURE_NOTE = "Sales exposed: gross item value of the orders involved, not money lost and not profit."
RECORD_FIELDS = ["order_id", "month", "order_status", "customer_state", "category", "seller_id", "total_price",
                 "late", "days_late", "review_score", "low_review", "installments", "cancelled"]
TREND_MEASURES = {"delivery": delivery_speed, "reviews": satisfaction, "sellers": seller_base}
GROUP_COLUMNS = {"customer state": "customer_state", "category": "category"}


def _placed(frame):
    return business_profile.placed_orders(frame, with_items=False)


def _paid(frame):
    sold = business_profile.placed_orders(frame)
    paid = sold[(sold["cancelled"] == 0) & sold["installments"].notna()]
    return paid.assign(multi_instalment=(paid["installments"] > 1).astype(float))


def _delivered(frame):
    delivered = trends.eligible(frame, "late")
    return delivered.assign(unreviewed=delivered["review_score"].isna().astype(float))


# finding id -> (orders that form the rate's denominator, the 0/1 column that is its numerator, what a row means)
RECORD_RULES = {
    "sales:late_rate_rising": (lambda f: trends.eligible(f, "late"), "late", "Delivered orders with a delivery date; late = after the promised date"),
    "sales:low_reviews_rising": (lambda f: trends.eligible(f, "low_review"), "low_review", "Reviewed orders; low = latest review of 1 or 2 stars"),
    "sales:cancellations_rising": (_placed, "cancelled", "Every order placed; cancelled = canceled or unavailable"),
    "sales:instalments_rising": (_paid, "multi_instalment", "Sold orders with a payment; more than one instalment"),
    "reviews:unreviewed_share_rising": (_delivered, "unreviewed", "Delivered orders; no review yet"),
}


def dataset_version(hashes: dict) -> str:
    return hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()[:12]


def all_checks(frame: pd.DataFrame, categories: list[dict], thresholds: dict) -> list[dict]:
    sold = trends.sold(frame)
    recent = select_windows(sold["month"])[0]
    found = [_finding("sales", c) for c in caveats.sales_checks(frame, categories)]
    for path, measure in TREND_MEASURES.items():
        found += [_finding(path, c) for c in measure.caveats(frame)]
    found = [apply_threshold(f, thresholds) for f in found]
    for finding in found:
        finding["exposure"] = _exposure(finding, frame, sold, recent)
        finding["records_available"] = finding["finding_id"] in RECORD_RULES
    found.sort(key=lambda f: (not f["triggered"], f["exposure"] is None, -(f["exposure"] or {}).get("sales", 0)))
    return found


def records_page(frame: pd.DataFrame, finding_id: str, population: str, page: int | None, page_size: int) -> dict | None:
    """The finding's orders in the recent window; `page=None` returns every row (for the export)."""
    rule = RECORD_RULES.get(finding_id)
    if rule is None:
        return None
    build, flag, meaning = rule
    orders = build(frame)
    recent, previous = select_windows(orders["month"])
    window = orders[orders["month"].isin(recent)].sort_values(["month", "order_id"])
    count, total = int(window[flag].sum()), int(len(window))
    shown = window[window[flag] == 1] if population == "numerator" else window
    rows = shown if page is None else shown.iloc[(page - 1) * page_size: page * page_size]
    before = orders[orders["month"].isin(previous)]
    return {"finding_id": finding_id, "population": population, "total": int(len(shown)), "page": page,
            "page_size": page_size, "numerator_column": flag,
            "summary": {"rule": meaning, "recent_months": list(recent), "previous_months": list(previous),
                        "numerator_orders": count, "denominator_orders": total, "value": count / total if total else None,
                        "previous_value": float(before[flag].mean()) if len(before) else None,
                        "sales": float(window["total_price"].sum())},
            "records": records(rows[[c for c in dict.fromkeys([*RECORD_FIELDS, flag]) if c in rows]])}


def _finding(page: str, check: dict) -> dict:
    return {**check, "finding_id": f"{page}:{check['id']}", "page": page}


def _exposure(finding: dict, frame: pd.DataFrame, sold: pd.DataFrame, recent: list[str]) -> dict | None:
    rule = RECORD_RULES.get(finding["finding_id"])
    if rule:
        orders = rule[0](frame)
        touched = orders[orders["month"].isin(select_windows(orders["month"])[0]) & (orders[rule[1]] == 1)]
        basis = "orders in the numerator"
    elif finding.get("kind") == "groups" and finding["groups"]["flagged"]:
        g = finding["groups"]
        flagged = [x["name"] for x in g["all"] if trends._past(trends.measured(x, g["unit"]), g["worse_when"], g["threshold"])]
        column = GROUP_COLUMNS[g["group_label"]]
        touched = sold[sold["month"].isin(recent) & sold[column].isin(flagged)]
        basis = f"orders in the flagged {g['group_label']} groups"
    else:
        return None
    return {"sales": float(touched["total_price"].sum()), "orders": int(len(touched)), "basis": basis, "note": EXPOSURE_NOTE}


def apply_threshold(finding: dict, thresholds: dict) -> dict:
    """The check re-judged against an owner-chosen threshold, in the unit its `threshold` states; others are unchanged."""
    value = thresholds.get(finding["finding_id"], thresholds.get(finding["id"]))
    if value is not None:
        finding = {**finding, **_rejudge(finding, value)}
    return {**finding, "threshold": _threshold(finding), "size": _size(finding)}


def _size(f: dict) -> dict | None:
    """How far the check's figure moved or stands, in its own unit, for ranking and display."""
    e = f.get("evidence", {})
    if f.get("comparison"):
        return {"value": f["comparison"]["change"], "unit": f["comparison"]["change_unit"]}
    if f.get("groups"):
        return {"value": f["groups"]["flagged"], "unit": f"of {f['groups']['of']} groups"}
    if f.get("gap") or "ratio" in e:
        return {"value": (f.get("gap") or e)["ratio"], "unit": "times"}
    for key, unit in (("change_pp", "pp"), ("change_pct", "%")):
        if key in e:
            return {"value": e[key], "unit": unit}
    share = e.get("share", e.get("rate"))
    if share is not None or "threshold" in e:
        return {"value": share * 100 if share is not None else None, "unit": "% share"}
    if "flagged" in e:
        return {"value": e["flagged"], "unit": f"of {e['categories']} categories"}
    return None


def _rejudge(f: dict, value: float) -> dict:
    kind, e = f.get("kind"), f.get("evidence", {})
    if kind == "change":
        c = f["comparison"]
        return trends.change_check(f["id"], f["title"], c["label"], c["unit"], c["recent"], c["previous"],
                                   c["worse_when"], value, f["monthly"])
    if kind == "groups":
        g = f["groups"]
        return trends.groups_check(f["id"], f["title"], g["label"], g["group_label"], g["unit"], g["all"],
                                   g["worse_when"], value)
    if kind == "gap":
        g = f["gap"]
        return trends.gap_check(f["id"], f["title"], g["label"], g["unit"], g["worse"], g["better"], value, g["min_orders"])
    if "threshold_pp" in e:
        return caveats.rate_rising(f["id"], f["title"], e, value)
    if "threshold_pct" in e:
        return {"triggered": e["change_pct"] is not None and e["change_pct"] <= -value, "evidence": {**e, "threshold_pct": -value}}
    if "threshold_ratio" in e:
        stark = e["on_time"]["low_rate"] == 0 and (e["late"]["low_rate"] or 0) > 0
        return {"triggered": stark or (e["ratio"] is not None and e["ratio"] >= value), "evidence": {**e, "threshold_ratio": value}}
    if "threshold" in e:
        share, limit = e.get("share", e.get("rate")), value / 100
        below = f["id"] == "few_returning_customers"
        return {"triggered": share is not None and (share < limit if below else share >= limit),
                "evidence": {**e, "threshold": limit}}
    return {}


def _threshold(f: dict) -> dict | None:
    """The check's threshold as the owner edits it: pp, % change, ratio or % share."""
    e = f.get("evidence", {})
    section = f.get("comparison") or f.get("groups")
    if section:
        return {"value": section["threshold"], "unit": section["threshold_unit"]}
    if f.get("kind") == "gap" or "threshold_ratio" in e:
        return {"value": (f.get("gap") or e)["threshold_ratio"], "unit": "ratio"}
    if "threshold_pp" in e:
        return {"value": e["threshold_pp"], "unit": "pp"}
    if "threshold_pct" in e:
        return {"value": -e["threshold_pct"], "unit": "% fall"}
    if "threshold" in e:
        return {"value": e["threshold"] * 100, "unit": "% share"}
    return None
