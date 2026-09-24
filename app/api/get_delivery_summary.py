"""Observed monthly late-delivery rates and optional model evaluation."""

from fastapi import APIRouter, Request

from app.analysis import delivery
from app.api.deps import LATE_MODEL, model_summary

router = APIRouter(prefix="/api/risk", tags=["risk"])


@router.get("/delivery/summary")
def delivery_summary(request: Request):
    frame = request.app.state.orders.frame
    return {
        "monthly": delivery.monthly_late_rate(frame),
        "exclusions": request.app.state.orders.exclusions,
        "model": model_summary(request, LATE_MODEL),
    }
