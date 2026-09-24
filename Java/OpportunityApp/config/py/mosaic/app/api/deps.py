"""The 503/409 guards shared by every model-backed route."""
from fastapi import HTTPException, Request

from app.models import CASHFLOW_MODEL, LATE_MODEL, MODEL_NAMES, REVIEW_MODEL, SALES_MODEL

SALES_TRAIN_COMMAND = "python -m app.forecast.train"
RISK_TRAIN_COMMAND = "python -m app.models.train_risk"
CASHFLOW_TRAIN_COMMAND = "python -m app.models.train_cashflow"


def require_model(request: Request, name: str, train_command: str) -> tuple[object, dict]:
    """Return (model, metadata) or raise 503 (not trained) / 409 (data changed since training)."""
    model, metadata = request.app.state.models.get(name, (None, None))
    if model is None:
        raise HTTPException(503, f"No trained '{name}' model found. Run: {train_command}")
    current = request.app.state.dataset_hashes
    trained_on = metadata["dataset_hashes"]
    if any(current.get(file) != digest for file, digest in trained_on.items()):
        raise HTTPException(
            409,
            f"Dataset files changed since '{name}' was trained; retrain first: {train_command}",
        )
    return model, metadata


def model_summary(request: Request, name: str) -> dict | None:
    """Evaluation block for summary pages; None when the model is not trained."""
    _, metadata = request.app.state.models.get(name, (None, None))
    if metadata is None:
        return None
    keys = (
        "model_version",
        "trained_at",
        "prediction_time",
        "split_date",
        "test_end",
        "evaluation",
        "importances",
        "limitations",
    )
    return {key: metadata[key] for key in keys}
