"""Held-out business-month snapshots ranked by predicted next-month cash-flow-stress risk."""

from fastapi import APIRouter, HTTPException, Query, Request

from app.analysis import cashflow
from app.api.deps import CASHFLOW_MODEL, CASHFLOW_TRAIN_COMMAND, require_model
from app.config import CASHFLOW_FILE
from app.models import cashflow as cf

router = APIRouter(prefix="/api/risk", tags=["risk"])


@router.get(
    "/cashflow/records",
    summary="Held-out small-business snapshots ranked by predicted cash-flow-stress risk next month",
)
def cashflow_records(request: Request, limit: int = Query(50, ge=1, le=500)):
    if request.app.state.cashflow is None:
        raise HTTPException(503, f"Dataset not present: put {CASHFLOW_FILE} in the datasets folder.")
    model, metadata = require_model(request, CASHFLOW_MODEL, CASHFLOW_TRAIN_COMMAND)
    if not cf.beats_baseline(metadata["evaluation"]):
        raise HTTPException(
            503,
            f"'{CASHFLOW_MODEL}' held-out ROC AUC is below {cf.MIN_ROC_AUC}, too close to chance to rank records."
            " See /api/risk/cashflow/summary for its evaluation.",
        )
    return {
        "model_version": metadata["model_version"],
        "prediction_time": metadata["prediction_time"],
        "scored_months": {"start": metadata["split_date"], "end_exclusive": metadata["test_end"]},
        "records": cashflow.score_records(
            request.app.state.cashflow, model, limit, metadata["split_date"], metadata["test_end"]
        ),
    }
