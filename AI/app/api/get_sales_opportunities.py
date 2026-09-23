"""Where to invest when the sales forecast rises: growing categories with their delivery and review checks."""

from fastapi import APIRouter, Query, Request

from app.analysis import opportunities
from app.analysis.categories import RECENT_MONTHS
from app.api.deps import SALES_MODEL, SALES_TRAIN_COMMAND, require_model
from app.forecast import sales as sales_forecasting

router = APIRouter(prefix="/api/sales", tags=["sales"])


@router.get("/opportunities", summary="If the sales forecast rises, the growing categories worth a closer look for investment")
def sales_opportunities(
    request: Request,
    horizon: int = Query(3, ge=1, le=6),
    limit: int = Query(5, ge=1, le=20),
):
    model, _ = require_model(request, SALES_MODEL, SALES_TRAIN_COMMAND)
    months = request.app.state.monthly.months
    history = months["sales"].tolist()
    forecast = sales_forecasting.recursive_forecast(model, history, horizon)
    trend = opportunities.sales_trend(history, forecast, RECENT_MONTHS)
    body = {
        "unit": "BRL",
        "measure": "gross_item_sales",
        "trend": trend,
        "rules": {
            "growth": "category sales up over the last 3 months against the 3 before, at least as fast as the business",
            "min_support_sales": opportunities.MIN_RECENT_SALES,
            "rate_window_months": RECENT_MONTHS,
            "rate_tolerance_pp": opportunities.RATE_TOLERANCE_PP,
            "min_rate_orders": opportunities.MIN_RATE_ORDERS,
            "growth_levels_pp_above_business": opportunities.GROWTH_LEVELS_PP,
            "size_levels_share_of_sales": opportunities.SIZE_LEVELS_SHARE,
            "rate_levels": "worse or better when more than rate_tolerance_pp from the business, otherwise in_line",
        },
        "limitations": [
            "Sales are gross item sales, not profit; costs and margins are not in the data.",
            "Growth in the past does not prove more investment would add sales.",
            "Delivery and review rates use the category of each order's priciest item.",
        ],
        "candidates": [],
    }
    if not trend["increasing"]:
        return {**body, "reason": "sales_not_increasing"}
    rate_months = months["month"].tolist()[-RECENT_MONTHS:]
    rates = opportunities.category_rates(request.app.state.orders.frame, rate_months)
    body["candidates"] = opportunities.investment_candidates(request.app.state.categories, rates, limit)
    body["business_rates"] = {name: rate["business"] for name, rate in rates.items()}
    return {**body, "reason": None if body["candidates"] else "no_growing_categories"}
