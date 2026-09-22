"""Category health routes (deterministic analysis computed at startup)."""
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request

from app.analysis.categories import RECENT_MONTHS

router = APIRouter(prefix="/api/sales/categories", tags=["categories"])

Flag = Literal["underperforming_total", "latest_month_anomaly"]


@router.get("")
def list_categories(
    request: Request,
    limit: int = Query(20, ge=1, le=200),
    flag: Flag | None = None,
):
    categories = request.app.state.categories
    if flag is not None:
        categories = [c for c in categories if c["flags"][flag]]
    total_change = categories[0]["total_change_pct"] if categories else None
    return {
        "recent_months": RECENT_MONTHS,
        "total_change_pct": total_change,
        "count": len(categories),
        "categories": [_without_series(c) for c in categories[:limit]],
    }


@router.get("/{category}")
def category_detail(request: Request, category: str):
    for entry in request.app.state.categories:
        if entry["category"] == category:
            return {"recent_months": RECENT_MONTHS, **entry}
    raise HTTPException(404, f"Unknown category '{category}'")


def _without_series(entry: dict) -> dict:
    return {k: v for k, v in entry.items() if k != "series"}
