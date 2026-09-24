"""Sales impact scenario route. Figures only: the plain-language summary is written by the Spring app."""
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field

from app.analysis.impact import compute_sales_impact

router = APIRouter(tags=["scenarios"])

MIN_HORIZON, MAX_HORIZON = 1, 6
MIN_CHANGE_PCT, MAX_CHANGE_PCT = -50.0, 100.0


class SalesImpactRequest(BaseModel):
    category: str | None = Field(None, max_length=100)
    horizon: int = Field(3, ge=MIN_HORIZON, le=MAX_HORIZON)
    sales_change_pct: float = Field(20.0, ge=MIN_CHANGE_PCT, le=MAX_CHANGE_PCT)


@router.post("/api/scenarios/sales-impact", summary="Explore a hypothetical sales change")
def sales_impact(request: Request, body: SalesImpactRequest):
    categories = request.app.state.orders.frame.get("category")
    if body.category is not None and (categories is None or body.category not in categories.values):
        raise HTTPException(422, "Choose an available category or the whole business.")
    return compute_sales_impact(
        request.app.state.monthly,
        request.app.state.orders.frame,
        category=body.category,
        horizon=body.horizon,
        sales_change_pct=body.sales_change_pct,
    )
