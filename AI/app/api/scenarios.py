"""Sales impact scenario and local-LLM health routes."""
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.ai import client as ai_client
from app.ai.explain import LlmSettings, explain
from app.analysis.impact import compute_sales_impact
from app.config import LLM_BASE_URL, LLM_ENABLED, LLM_MODEL, LLM_TIMEOUT_SECONDS

router = APIRouter(tags=["scenarios"])

MIN_HORIZON, MAX_HORIZON = 1, 6
MIN_CHANGE_PCT, MAX_CHANGE_PCT = -50.0, 100.0


class SalesImpactRequest(BaseModel):
    horizon: int = Field(3, ge=MIN_HORIZON, le=MAX_HORIZON)
    sales_change_pct: float = Field(20.0, ge=MIN_CHANGE_PCT, le=MAX_CHANGE_PCT)
    explain: bool = True


@router.post("/api/scenarios/sales-impact")
def sales_impact(request: Request, body: SalesImpactRequest):
    result = compute_sales_impact(
        request.app.state.monthly, request.app.state.orders.frame,
        horizon=body.horizon, sales_change_pct=body.sales_change_pct,
    )
    settings = _llm_settings(enabled=LLM_ENABLED and body.explain)
    return {**result, "narrative": explain(result, settings=settings)}


@router.get("/api/ai/health")
def ai_health():
    models = ai_client.list_models(LLM_BASE_URL, timeout=LLM_TIMEOUT_SECONDS)
    return {
        "enabled": LLM_ENABLED,
        "base_url": LLM_BASE_URL,
        "configured_model": LLM_MODEL or None,
        "reachable": bool(models),
        "models": models,
    }


def _llm_settings(enabled: bool) -> LlmSettings:
    return LlmSettings(
        enabled=enabled, base_url=LLM_BASE_URL, model=LLM_MODEL, timeout=LLM_TIMEOUT_SECONDS
    )
