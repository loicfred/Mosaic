"""Open orders ranked by late-delivery risk."""

from fastapi import APIRouter, Query, Request

from app.analysis import delivery
from app.api.deps import LATE_MODEL, RISK_TRAIN_COMMAND, require_model

router = APIRouter(prefix="/api/risk", tags=["risk"])


@router.get("/delivery/open-orders")
def delivery_open_orders(request: Request, limit: int = Query(50, ge=1, le=500)):
    model, metadata = require_model(request, LATE_MODEL, RISK_TRAIN_COMMAND)
    return {
        "model_version": metadata["model_version"],
        "prediction_time": metadata["prediction_time"],
        "orders": delivery.score_open_orders(request.app.state.orders.frame, model, limit),
    }
