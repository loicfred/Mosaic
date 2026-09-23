"""Observed delivery reliability by seller."""

from fastapi import APIRouter, Query, Request

from app.analysis import delivery

router = APIRouter(prefix="/api/risk", tags=["risk"])


@router.get("/delivery/sellers")
def delivery_sellers(
    request: Request, min_orders: int = Query(30, ge=1), limit: int = Query(50, ge=1, le=500)
):
    return {
        "min_orders": min_orders,
        "sellers": delivery.seller_table(request.app.state.orders.frame, min_orders, limit),
    }
