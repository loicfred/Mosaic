"""Target metrics used to MEASURE whether an action worked.

Each opportunity names one target metric. At detection we store its baseline;
after the user starts the action we recompute the same metric on data recorded
after the start date and compare. Same code, same definition, before and after.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.analytics.ledger import Ledger
from app.analytics.patterns import concentration, recurring_streams

TARGETS: dict[str, dict[str, Any]] = {
    "buffer_days": {"label": "Cash buffer", "unit": "days", "better": "higher", "kind": "point"},
    "cogs_to_revenue_pct": {"label": "Supplier cost per MUR 100 of sales", "unit": "%", "better": "lower",
                            "kind": "flow"},
    "collection_days": {"label": "Average days to collect", "unit": "days", "better": "lower", "kind": "flow"},
    "recurring_monthly": {"label": "Fixed monthly commitments (rent, subscriptions, telecom, insurance, fees)",
                          "unit": "MUR",
                          "better": "lower", "kind": "point"},
    "function_subscriptions_monthly": {"label": "Monthly cost of overlapping tools", "unit": "MUR",
                                       "better": "lower", "kind": "point"},
    "top_customer_share": {"label": "Largest customer's share of revenue", "unit": "%", "better": "lower",
                           "kind": "point"},
    "top_supplier_share": {"label": "Largest supplier's share of purchases", "unit": "%", "better": "lower",
                           "kind": "point"},
    "product_line_monthly_revenue": {"label": "Monthly revenue of product line", "unit": "MUR",
                                     "better": "higher", "kind": "flow"},
}


def compute_target(ledger: Ledger, key: str, params: dict[str, Any], start: pd.Timestamp,
                   end: pd.Timestamp) -> float | None:
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    t = ledger.tx
    w = t[(t["date"] >= start) & (t["date"] <= end)]
    months = max(1.0, (end - start).days / 30.44)
    if key == "buffer_days":
        w90 = ledger.window(end, 90)
        daily = float(w90.loc[w90["is_obligation"], "amount"].sum()) / 90.0
        return float(ledger.cash_at(end) / daily) if daily else None
    if key == "cogs_to_revenue_pct":
        rev = float(w.loc[w["group"] == "revenue", "amount"].sum())
        cogs = float(w.loc[w["group"] == "cogs", "amount"].sum())
        return cogs / rev * 100 if rev else None
    if key == "collection_days":
        inv = ledger.invoices
        if inv.empty:
            return None
        paid = inv[inv["paid_date"].notna() & (inv["paid_date"] >= start) & (inv["paid_date"] <= end)]
        if params.get("customer"):
            paid = paid[paid["customer"] == params["customer"]]
        if paid.empty:
            return None
        return float(np.average((paid["paid_date"] - paid["issue_date"]).dt.days, weights=paid["amount"]))
    if key in ("recurring_monthly", "function_subscriptions_monthly"):
        streams = [s for s in recurring_streams(ledger, end) if s["active"]]
        if key == "recurring_monthly":
            from app.opportunities.engine import FIXED_COMMITMENT_CATEGORIES
            streams = [s for s in streams if s["category"] in FIXED_COMMITMENT_CATEGORIES
                       and s["stability_cv"] <= 0.2]
        else:
            streams = [s for s in streams if s["function"] == params.get("function")
                       and s["category"] == "Software & subscriptions"]
        return float(sum(s["monthly_run_rate"] for s in streams))
    if key == "top_customer_share":
        return float(concentration(ledger, end, "customer")["top_share_pct"])
    if key == "top_supplier_share":
        return float(concentration(ledger, end, "supplier")["top_share_pct"])
    if key == "product_line_monthly_revenue":
        s = w[(w["group"] == "revenue") & (w["subcategory"] == params.get("line"))]
        return float(s["amount"].sum()) / months
    return None


def measure_outcome(ledger: Ledger, key: str | None, params: dict[str, Any], baseline: float | None,
                    expected_change: float | None, action_started: pd.Timestamp | None,
                    as_of: pd.Timestamp) -> dict[str, Any]:
    """Compare the target metric after the action started with its baseline."""
    as_of = pd.Timestamp(as_of)
    if key is None:
        return {"status": "manual", "message": "This finding is resolved by confirming the review manually."}
    meta = TARGETS[key]
    if action_started is None:
        return {"status": "not_started", "message": "Start the action to begin measuring its effect."}
    started = pd.Timestamp(action_started)
    days_since = int((as_of - started).days)
    if days_since < 30:
        return {"status": "too_early", "days_observed": max(days_since, 0),
                "message": f"Only {max(days_since, 0)} days of data since the action started; "
                           "at least 30 are needed for a fair comparison."}
    window_start = max(started, as_of - pd.Timedelta(days=120))
    current = compute_target(ledger, key, params, window_start, as_of)
    if current is None or baseline is None:
        return {"status": "insufficient_data", "message": "Not enough matching records to measure yet."}
    change = current - baseline
    good_sign = -1 if meta["better"] == "lower" else 1
    if expected_change:
        progress = change / expected_change
    else:
        progress = (change * good_sign) / (abs(baseline) or 1.0)
    if expected_change and progress >= 0.8:
        verdict, msg = "achieved", "The measured change meets or exceeds the expected effect."
    elif progress >= 0.3:
        verdict, msg = "partial", "Some improvement is visible but less than expected."
    elif change * good_sign < 0 and abs(change) > 0.05 * abs(baseline):
        verdict, msg = "worsened", "The metric moved in the wrong direction after the action."
    else:
        verdict, msg = "no_change", "No meaningful change yet."
    return {
        "status": verdict,
        "message": msg,
        "metric": key,
        "metric_label": meta["label"],
        "unit": meta["unit"],
        "baseline": round(float(baseline), 2),
        "current": round(float(current), 2),
        "change": round(float(change), 2),
        "expected_change": round(float(expected_change), 2) if expected_change is not None else None,
        "progress_pct": round(float(progress) * 100, 1),
        "window": [str(window_start.date()), str(as_of.date())],
        "days_observed": days_since,
        "caveat": "Before/after comparison on your own ledger; other events in the same period can "
                  "also move this metric, so treat it as evidence, not proof of cause.",
    }
