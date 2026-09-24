from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query, Request

from app.models import Opportunity
from app.opportunities.targets import TARGETS
from app.schemas.opportunity import NoteIn, OpportunityOut, Status, StatusIn
from app.security.deps import EDITORS, AuthContext, get_context, require_roles
from app.services import audit_service, opportunity_service
from app.services.analysis_service import get_analysis

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


def out(o: Opportunity) -> OpportunityOut:
    target = {"key": o.target_metric, "params": o.target_params or {}, **TARGETS[o.target_metric]} \
        if o.target_metric else None
    return OpportunityOut(
        id=o.id, detector=o.detector, kind=o.kind, category=o.category, title=o.title, summary=o.summary,
        why_it_matters=o.why_it_matters, explanation=o.explanation, severity=o.severity,
        priority_score=o.priority_score, confidence=o.confidence, confidence_basis=o.confidence_basis,
        impact_low=o.impact_low, impact_high=o.impact_high, impact_kind=o.impact_kind, impact_basis=o.impact_basis,
        evidence=o.evidence, supporting_records=o.supporting_records, actions=o.actions,
        scenario_preset=o.scenario_preset, provenance=o.provenance, target=target, baseline_value=o.baseline_value,
        expected_change=o.expected_change, status=o.status, is_active=o.is_active == "yes",
        action_started_at=str(o.action_started_at) if o.action_started_at else None,
        completed_at=str(o.completed_at) if o.completed_at else None, outcome=o.outcome,
        data_as_of=str(o.data_as_of), detected_at=o.detected_at.isoformat(), updated_at=o.updated_at.isoformat())


@router.get("", response_model=list[OpportunityOut])
def list_opportunities(ctx: AuthContext = Depends(get_context), status: Status | None = None,
                       include_inactive: bool = Query(False)) -> list[OpportunityOut]:
    return [out(o) for o in opportunity_service.list_opportunities(ctx.db, ctx.business_id, status, include_inactive)]


@router.post("/refresh")
def refresh(request: Request, ctx: AuthContext = Depends(require_roles(*EDITORS))) -> dict[str, Any]:
    r = opportunity_service.refresh(ctx.db, ctx.business, ctx.user)
    audit_service.record("opportunity.engine_run", "opportunity", request=request, user_id=ctx.user.id,
                         actor=ctx.user.email, business_id=ctx.business_id, details=r)
    return r


@router.get("/{opp_id}")
def detail(opp_id: uuid.UUID, ctx: AuthContext = Depends(get_context)) -> dict[str, Any]:
    o = opportunity_service.get(ctx.db, ctx.business_id, opp_id)
    if o.status in ("in_progress", "completed"):
        o.outcome = opportunity_service.outcome_for(get_analysis(ctx.db, ctx.business), o)
        ctx.db.commit()
    evs = [{"id": str(e.id), "type": e.event_type, "from": e.from_status, "to": e.to_status, "note": e.note,
            "by": name, "at": e.created_at.isoformat()}
           for e, name in opportunity_service.events(ctx.db, ctx.business_id, o.id)]
    return {**out(o).model_dump(mode="json"), "events": evs}


@router.patch("/{opp_id}/status", response_model=OpportunityOut)
def change_status(opp_id: uuid.UUID, body: StatusIn, request: Request,
                  ctx: AuthContext = Depends(require_roles(*EDITORS))) -> OpportunityOut:
    before = opportunity_service.get(ctx.db, ctx.business_id, opp_id).status
    o = opportunity_service.change_status(ctx.db, ctx.business, ctx.user, opp_id, body.status, body.note)
    audit_service.record("opportunity.status_changed", "opportunity", request=request, user_id=ctx.user.id,
                         actor=ctx.user.email, business_id=ctx.business_id, resource_type="opportunity",
                         resource_id=str(o.id), details={"from": before, "to": o.status, "title": o.title})
    return out(o)


@router.post("/{opp_id}/notes", status_code=204)
def add_note(opp_id: uuid.UUID, body: NoteIn, ctx: AuthContext = Depends(require_roles(*EDITORS))) -> None:
    opportunity_service.add_note(ctx.db, ctx.business, ctx.user, opp_id, body.note)
