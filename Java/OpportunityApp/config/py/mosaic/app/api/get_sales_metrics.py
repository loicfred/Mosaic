"""The business's own measures by purchase month: basket size, freight share, cancellations, instalments, repeat buyers."""

from fastapi import APIRouter, Request

from app.analysis import business_profile

router = APIRouter(prefix="/api/sales", tags=["sales"])

METRICS = {
    "average_order_value": ("Average order value", "brl"),
    "freight_share": ("Freight as a share of item prices", "rate"),
    "cancel_rate": ("Cancelled or unavailable orders", "rate"),
    "multi_instalment_rate": ("Orders paid in more than one instalment", "rate"),
    "returning_rate": ("Orders from returning customers", "rate"),
}


@router.get("/metrics", summary="Average order value, freight share, cancellations, instalments and returning customers by month")
def sales_metrics(request: Request):
    return {
        "metrics": {key: {"label": label, "unit": unit} for key, (label, unit) in METRICS.items()},
        "monthly": business_profile.monthly(request.app.state.orders.frame),
        "limitations": [
            "Observed figures of this business; recent months can still have orders on their way.",
            "Cancellations count every order placed; the other measures use orders with items that were not cancelled.",
        ],
    }
