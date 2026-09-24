from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.security.deps import AuthContext, get_context
from app.services import insights_service
from app.services.analysis_service import get_analysis

router = APIRouter(tags=["analytics"])


@router.get("/analytics/overview")
def overview(ctx: AuthContext = Depends(get_context)) -> dict[str, Any]:
    return insights_service.overview(get_analysis(ctx.db, ctx.business))


@router.get("/insights")
def insights(ctx: AuthContext = Depends(get_context)) -> dict[str, Any]:
    return insights_service.insights(get_analysis(ctx.db, ctx.business))
