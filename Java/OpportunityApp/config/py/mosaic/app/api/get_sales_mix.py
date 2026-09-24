"""How recent sales split by category, payment type or state."""

from typing import Literal

from fastapi import APIRouter, Query, Request

from app.analysis import business_profile
from app.analysis.categories import RECENT_MONTHS

router = APIRouter(prefix="/api/sales", tags=["sales"])


@router.get("/mix", summary="Share of the last months' sales by category, payment type, customer state or seller state")
def sales_mix(
    request: Request,
    by: Literal["category", "payment_type", "customer_state", "seller_state"] = "category",
    months: int = Query(RECENT_MONTHS, ge=1, le=12),
):
    all_months = request.app.state.monthly.months["month"].tolist()
    window = all_months[-months:]
    body = business_profile.mix(business_profile.placed_orders(request.app.state.orders.frame, window), by)
    return {
        **body,
        "months": window,
        "unit": "BRL",
        "measure": "gross_item_sales",
        "limitations": [
            "Sales are gross item sales of orders not cancelled, not profit.",
            "Category and seller state are those of each order's priciest item.",
            "Payment type is the type that paid the most of each order.",
        ],
    }
