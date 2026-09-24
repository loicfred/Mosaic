"""Assembles the Overview and Financial Insights payloads from the analysis bundle.
Every figure here comes from app.analytics - nothing is computed in the frontend."""

from __future__ import annotations

from typing import Any

import pandas as pd

from app.analytics import metrics
from app.analytics.patterns import collections, concentration, recurring_streams
from app.services.analysis_service import Analysis

# Only drivers that move the log-odds meaningfully are presented as "why".
DRIVER_MIN = 0.25


def overview(a: Analysis) -> dict[str, Any]:
    L, as_of = a.ledger, a.as_of
    cmp90 = metrics.month_comparison(L, as_of, 3)
    cur, prev = cmp90["current"], cmp90["previous"]
    p = a.prediction
    return {
        "as_of": str(as_of.date()),
        "data_window": [str(L.start.date()), str(as_of.date())],
        "cash": {
            "balance": round(L.cash_at(as_of), 2),
            "balance_30d_ago": round(L.cash_at(as_of - pd.Timedelta(days=30)), 2),
            "buffer_days": round(p.get("features", {}).get("buffer_days", 0) or 0, 1),
            "buffer_threshold": a.projection.get("buffer_threshold"),
        },
        "kpis_90d": {
            "period": cmp90["current_period"], "previous_period": cmp90["previous_period"],
            "revenue": round(cur["revenue"], 2), "revenue_change_pct": cmp90["change_pct"]["revenue"],
            "expenses": round(cur["expenses"], 2), "expenses_change_pct": cmp90["change_pct"]["expenses"],
            "gross_margin_pct": round(cur["gross_margin_pct"], 2),
            "gross_margin_change_pp": round(cmp90["change_pct"]["gross_margin_pct"], 2),
            "operating_cash_flow": round(cur["operating_cash_flow"], 2),
            "operating_cash_flow_prev": round(prev["operating_cash_flow"], 2),
        },
        "cash_series": metrics.cash_series(L, 180),
        "projection_series": a.projection_series,
        "projection": a.projection,
        "monthly": metrics.monthly_series(L, 12),
        "prediction": {k: p.get(k) for k in ("mode", "band", "probability", "model_version", "reason", "thresholds")}
        | {"top_drivers": [c for c in p.get("contributions", []) if c["contribution"] >= DRIVER_MIN][:3]},
        "data_health": {"score": a.health.get("score"),
                        "issues": sum(c.get("count", 0) for c in a.health.get("checks", [])
                                      if c["status"] == "warning")},
    }


def insights(a: Analysis) -> dict[str, Any]:
    L, as_of = a.ledger, a.as_of
    return {
        "as_of": str(as_of.date()),
        "monthly": metrics.monthly_series(L, 12),
        "comparison_90d": metrics.month_comparison(L, as_of, 3),
        "expense_categories": metrics.category_breakdown_months(L, as_of, 3, "outflow"),
        "product_lines": metrics.product_line_performance(L, as_of),
        "customer_concentration": concentration(L, as_of, "customer"),
        "supplier_concentration": concentration(L, as_of, "supplier"),
        "recurring": [r for r in recurring_streams(L, as_of) if r["active"]],
        "collections": collections(L, as_of),
        "cash_series": metrics.cash_series(L, 365),
    }
