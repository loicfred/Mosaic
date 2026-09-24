from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select

from app.models import Opportunity
from app.security.deps import AuthContext, get_context
from app.services import audit_service, insights_service
from app.services.analysis_service import get_analysis

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/decision-brief")
def decision_brief(request: Request, ctx: AuthContext = Depends(get_context)) -> dict[str, Any]:
    """A printable one-page brief: position, prediction, top opportunities and tracked actions."""
    a = get_analysis(ctx.db, ctx.business)
    ov = insights_service.overview(a)
    opps = ctx.db.scalars(select(Opportunity).where(Opportunity.business_id == ctx.business_id)
                          .order_by(Opportunity.priority_score.desc())).all()
    audit_service.record("data.report_generated", "access", request=request, user_id=ctx.user.id,
                         actor=ctx.user.email, business_id=ctx.business_id, details={"report": "decision-brief"})
    return {
        "business": {"name": ctx.business.name, "sector": ctx.business.sector, "currency": ctx.business.currency,
                     "data_label": ctx.business.data_label},
        "as_of": ov["as_of"], "cash": ov["cash"], "kpis_90d": ov["kpis_90d"], "prediction": ov["prediction"],
        "projection": ov["projection"], "data_health": ov["data_health"],
        "open_opportunities": [{"title": o.title, "severity": o.severity, "confidence": o.confidence,
                                "impact_low": o.impact_low, "impact_high": o.impact_high,
                                "impact_kind": o.impact_kind, "status": o.status,
                                "top_action": (o.actions or [{}])[0].get("title")}
                               for o in opps if o.status not in ("completed", "dismissed") and o.is_active == "yes"],
        "tracked_actions": [{"title": o.title, "status": o.status, "action_started_at": str(o.action_started_at)
                             if o.action_started_at else None, "outcome": o.outcome}
                            for o in opps if o.status in ("in_progress", "completed")],
        "generated_by": ctx.user.full_name,
    }
