"""Analytics API and model availability."""

from fastapi import APIRouter, Request

from app.api.deps import SALES_MODEL

router = APIRouter()


@router.get("/api/health")
def health(request: Request):
    models = request.app.state.models
    return {
        "status": "ok",
        "model_loaded": models[SALES_MODEL][0] is not None,
        "models": {name: model is not None for name, (model, _) in models.items()},
    }
