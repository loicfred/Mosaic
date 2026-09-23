"""Business-month snapshots ranked by predicted next-month cash-flow-stress risk."""

from fastapi import APIRouter, Query, Request

from app.analysis import cashflow
from app.api.deps import CASHFLOW_MODEL, CASHFLOW_TRAIN_COMMAND, require_model

router = APIRouter(prefix="/api/risk", tags=["risk"])


@router.get(
    "/cashflow/records",
    summary="Small-business snapshots ranked by predicted cash-flow-stress risk next month",
)
def cashflow_records(request: Request, limit: int = Query(50, ge=1, le=500)):
    model, metadata = require_model(request, CASHFLOW_MODEL, CASHFLOW_TRAIN_COMMAND)
    return {
        "model_version": metadata["model_version"],
        "prediction_time": metadata["prediction_time"],
        "records": cashflow.score_records(request.app.state.cashflow, model, limit),
    }
