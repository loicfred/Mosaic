"""Observed cash-flow-stress rates by sector and month, and optional model evaluation."""

from fastapi import APIRouter, Request

from app.analysis import cashflow
from app.api.deps import CASHFLOW_MODEL, model_summary

router = APIRouter(prefix="/api/risk", tags=["risk"])


@router.get(
    "/cashflow/summary",
    summary="Observed cash-flow-stress rate by sector and month, from the small-business practice dataset",
)
def cashflow_summary(request: Request):
    frame = request.app.state.cashflow
    if frame is None:
        return {
            "unit": "usd",
            "available": False,
            "reason": "dataset_not_present",
            "by_sector": [],
            "monthly": [],
            "model": None,
        }
    return {
        "unit": "usd",
        "available": True,
        "by_sector": cashflow.stress_rate_by_sector(frame),
        "monthly": cashflow.stress_rate_by_month(frame),
        "model": model_summary(request, CASHFLOW_MODEL),
    }
