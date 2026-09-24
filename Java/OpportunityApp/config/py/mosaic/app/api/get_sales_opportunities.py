"""Where the data points for investment: the categories doing best, whether or not the forecast rises."""

from fastapi import APIRouter, Query, Request

from app.analysis import business_profile, opportunities
from app.analysis.categories import RECENT_MONTHS
from app.api.deps import SALES_MODEL, SALES_TRAIN_COMMAND, require_model
from app.forecast import sales as sales_forecasting

router = APIRouter(prefix="/api/sales", tags=["sales"])


@router.get("/opportunities", summary="The categories worth a closer look for investment, with the forecast as context")
def sales_opportunities(
    request: Request,
    horizon: int = Query(3, ge=1, le=6),
    limit: int = Query(5, ge=1, le=20),
):
    model, metadata = require_model(request, SALES_MODEL, SALES_TRAIN_COMMAND)
    months = request.app.state.monthly.months
    history = months["sales"].tolist()
    method = sales_forecasting.preferred_method(metadata["evaluation"])
    forecast = sales_forecasting.forecast_by_method(method, model, history, horizon)
    frame = request.app.state.orders.frame
    all_months = months["month"].tolist()
    rate_months, previous_months = all_months[-RECENT_MONTHS:], all_months[-2 * RECENT_MONTHS:-RECENT_MONTHS]
    rates = opportunities.category_rates(frame, rate_months)
    profiles = business_profile.windows(frame, rate_months, previous_months)
    candidates = opportunities.investment_candidates(
        request.app.state.categories, rates, limit, profiles["categories"], profiles["business"]["recent"]
    )
    return {
        "unit": "BRL",
        "measure": "gross_item_sales",
        "forecast_method": method,
        "trend": opportunities.sales_trend(history, forecast, RECENT_MONTHS),
        "rules": {
            "growth": "category sales up over the last 3 months against the 3 before, at least as fast as the business",
            "basis": "growing when any category meets the growth rule; otherwise beats_business (falling less than the "
                     "business); otherwise best_available (the smallest falls)",
            "min_support_sales": opportunities.MIN_RECENT_SALES,
            "rate_window_months": RECENT_MONTHS,
            "rate_tolerance_pp": opportunities.RATE_TOLERANCE_PP,
            "min_rate_orders": opportunities.MIN_RATE_ORDERS,
            "growth_levels_pp_above_business": opportunities.GROWTH_LEVELS_PP,
            "size_levels_share_of_sales": opportunities.SIZE_LEVELS_SHARE,
            "rate_levels": "worse or better when more than rate_tolerance_pp from the business, otherwise in_line",
            "rate_checks": list(opportunities.RATE_CHECKS),
            "readiness": "fix_first: a rate check is worse than the business; unknown: a rate cannot be judged; "
                         "watch: a profile risk is triggered; ready: none of these",
            "single_seller_share": opportunities.SINGLE_SELLER_SHARE,
            "freight_gap_pp": opportunities.FREIGHT_GAP_PP,
            "basket_fall_pct": opportunities.BASKET_FALL_PCT,
        },
        "limitations": [
            "Sales are gross item sales, not profit; costs and margins are not in the data.",
            "Growth in the past does not prove more investment would add sales.",
            "When the forecast does not rise, a suggestion is about where to hold or shift effort, not a promise of growth.",
            "Delivery, review, cancellation, freight, payment, customer and seller figures use the category of each "
            "order's priciest item; category sales growth uses every item.",
            "Payments are what customers paid and in how many instalments, not when the seller was paid.",
            "A returning customer placed an earlier order in the data; purchases elsewhere are not visible.",
        ],
        "candidates": candidates,
        "business_rates": {name: rate["business"] for name, rate in rates.items()},
        "business_profile": profiles["business"],
        "business_series": months[["month", "sales"]].to_dict(orient="records"),
        "reason": None if candidates else "no_categories_with_enough_sales",
    }
