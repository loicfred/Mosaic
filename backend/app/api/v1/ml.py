from __future__ import annotations

import copy
from typing import Any

from fastapi import APIRouter, Depends, Query

from app.ml.inference import suggest_category
from app.ml.registry import anomaly_model, benchmark_report, cash_pressure_model, categoriser_model
from app.security.deps import EDITORS, AuthContext, get_context, require_roles
from app.services.analysis_service import get_analysis

router = APIRouter(prefix="/ml", tags=["ml"])


@router.get("/cash-pressure")
def cash_pressure(ctx: AuthContext = Depends(get_context)) -> dict[str, Any]:
    a = get_analysis(ctx.db, ctx.business)
    return {"prediction": a.prediction, "projection": a.projection, "backtest": a.backtest}


@router.get("/models")
def models(ctx: AuthContext = Depends(get_context)) -> dict[str, Any]:
    def card(m: Any) -> dict[str, Any]:
        meta = copy.deepcopy(m.meta)  # never mutate the cached model metadata
        meta.get("explainability", {}).pop("means", None)
        meta.get("explainability", {}).pop("scales", None)
        return {"status": m.status, "detail": m.detail, "metadata": meta}

    a = get_analysis(ctx.db, ctx.business)
    return {"cash_pressure": card(cash_pressure_model()), "anomaly": card(anomaly_model()),
            "categoriser": card(categoriser_model()), "provided_dataset_benchmark": benchmark_report(),
            "projection_backtest": a.backtest}


@router.get("/categorise")
def categorise(description: str = Query(..., min_length=2, max_length=300),
               direction: str = Query("outflow", pattern="^(inflow|outflow)$"),
               ctx: AuthContext = Depends(require_roles(*EDITORS))) -> dict[str, Any] | None:
    return suggest_category(description, direction)
