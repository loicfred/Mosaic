"""Observed monthly sales history."""

from fastapi import APIRouter, Request

from app.data.olist import MonthlySales

router = APIRouter(prefix="/api/sales", tags=["sales"])


@router.get("/history")
def sales_history(request: Request):
    return serialise_history(request.app.state.monthly)


def serialise_history(monthly: MonthlySales) -> dict:
    months = monthly.months
    data_range = None
    if not months.empty:
        data_range = {"start": months["month"].iloc[0], "end": months["month"].iloc[-1]}
    return {
        "unit": "BRL",
        "measure": "gross_item_sales",
        "range": data_range,
        "months": months.to_dict(orient="records"),
        "exclusions": monthly.exclusions,
    }
