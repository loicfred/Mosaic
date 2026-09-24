"""Category health summaries with optional flag filtering."""

from typing import Literal

from fastapi import APIRouter, Query, Request

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
        categories = [category for category in categories if category["flags"][flag]]
    return {
        "recent_months": RECENT_MONTHS,
        "total_change_pct": categories[0]["total_change_pct"] if categories else None,
        "count": len(categories),
        "categories": [{key: value for key, value in category.items() if key != "series"} for category in categories[:limit]],
    }
