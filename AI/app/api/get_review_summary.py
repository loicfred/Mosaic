"""Observed low-review rates and optional model evaluation."""

from fastapi import APIRouter, Request

from app.analysis import reviews
from app.api.deps import REVIEW_MODEL, model_summary

router = APIRouter(prefix="/api/risk", tags=["risk"])


@router.get("/reviews/summary")
def reviews_summary(request: Request):
    frame = request.app.state.orders.frame
    return {
        "monthly": reviews.monthly_low_review_rate(frame),
        "by_lateness": reviews.low_review_by_lateness(frame),
        "exclusions": request.app.state.orders.exclusions,
        "model": model_summary(request, REVIEW_MODEL),
    }
