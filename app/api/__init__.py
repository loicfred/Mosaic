"""Register one route per get_* module in a single application router."""

from fastapi import APIRouter

from app.api import (
    get_cashflow_risk,
    get_cashflow_summary,
    get_category_detail,
    get_datasets,
    get_delivery_open_orders,
    get_delivery_sellers,
    get_delivery_summary,
    get_health,
    get_review_summary,
    get_unreviewed_orders,
    get_sales_categories,
    get_sales_forecast,
    get_sales_history,
    get_sales_impact,
    get_sales_opportunities,
    get_sales_caveats,
)

router = APIRouter()
for endpoint in (
    get_health,
    get_datasets,
    get_sales_history,
    get_sales_forecast,
    get_sales_categories,
    get_category_detail,
    get_delivery_summary,
    get_delivery_open_orders,
    get_delivery_sellers,
    get_review_summary,
    get_unreviewed_orders,
    get_sales_impact,
    get_sales_opportunities,
    get_sales_caveats,
    get_cashflow_summary,
    get_cashflow_risk,
):
    router.include_router(endpoint.router)
