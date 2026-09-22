"""Late-delivery and low-review risk routes."""
from fastapi import APIRouter, Query, Request

from app.analysis import delivery, reviews
from app.api.deps import require_model

router = APIRouter(prefix="/api/risk", tags=["risk"])

TRAIN_COMMAND = "python -m app.models.train_risk"
LATE_MODEL = "late_delivery"
REVIEW_MODEL = "low_review"


@router.get("/delivery/summary")
def delivery_summary(request: Request):
    frame = request.app.state.orders.frame
    return {
        "monthly": delivery.monthly_late_rate(frame),
        "exclusions": request.app.state.orders.exclusions,
        "model": _model_summary(request, LATE_MODEL),
    }


@router.get("/delivery/open-orders")
def delivery_open_orders(request: Request, limit: int = Query(50, ge=1, le=500)):
    model, metadata = require_model(request, LATE_MODEL, TRAIN_COMMAND)
    return {
        "model_version": metadata["model_version"],
        "prediction_time": metadata["prediction_time"],
        "orders": delivery.score_open_orders(request.app.state.orders.frame, model, limit),
    }


@router.get("/delivery/sellers")
def delivery_sellers(
    request: Request, min_orders: int = Query(30, ge=1), limit: int = Query(50, ge=1, le=500)
):
    return {
        "min_orders": min_orders,
        "sellers": delivery.seller_table(request.app.state.orders.frame, min_orders, limit),
    }


@router.get("/reviews/summary")
def reviews_summary(request: Request):
    frame = request.app.state.orders.frame
    return {
        "monthly": reviews.monthly_low_review_rate(frame),
        "by_lateness": reviews.low_review_by_lateness(frame),
        "exclusions": request.app.state.orders.exclusions,
        "model": _model_summary(request, REVIEW_MODEL),
    }


@router.get("/reviews/unreviewed")
def reviews_unreviewed(request: Request, limit: int = Query(50, ge=1, le=500)):
    model, metadata = require_model(request, REVIEW_MODEL, TRAIN_COMMAND)
    return {
        "model_version": metadata["model_version"],
        "prediction_time": metadata["prediction_time"],
        "orders": reviews.score_unreviewed(request.app.state.orders.frame, model, limit),
    }


def _model_summary(request: Request, name: str) -> dict | None:
    """Evaluation block for the summary pages; None when the model is not trained."""
    _, metadata = request.app.state.models.get(name, (None, None))
    if metadata is None:
        return None
    keys = ("model_version", "trained_at", "prediction_time", "split_date", "test_end",
            "evaluation", "importances", "limitations")
    return {key: metadata[key] for key in keys}
