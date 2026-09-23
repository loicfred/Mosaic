"""Delivered orders ranked by low-review risk."""

from fastapi import APIRouter, Query, Request

from app.analysis import reviews
from app.api.deps import REVIEW_MODEL, RISK_TRAIN_COMMAND, require_model

router = APIRouter(prefix="/api/risk", tags=["risk"])


@router.get("/reviews/unreviewed")
def reviews_unreviewed(request: Request, limit: int = Query(50, ge=1, le=500)):
    model, metadata = require_model(request, REVIEW_MODEL, RISK_TRAIN_COMMAND)
    return {
        "model_version": metadata["model_version"],
        "prediction_time": metadata["prediction_time"],
        "orders": reviews.score_unreviewed(request.app.state.orders.frame, model, limit),
    }
