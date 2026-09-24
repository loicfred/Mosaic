"""One category's metrics, evidence and monthly series."""

from fastapi import APIRouter, HTTPException, Request

from app.analysis.categories import RECENT_MONTHS

router = APIRouter(prefix="/api/sales/categories", tags=["categories"])


@router.get("/{category}")
def category_detail(request: Request, category: str):
    for entry in request.app.state.categories:
        if entry["category"] == category:
            return {"recent_months": RECENT_MONTHS, **entry}
    raise HTTPException(404, f"Unknown category '{category}'")
