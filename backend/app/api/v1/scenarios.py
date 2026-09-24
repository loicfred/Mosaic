from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request

from app.schemas.scenario import SaveScenarioIn, SimulateIn
from app.security.deps import EDITORS, AuthContext, get_context, require_roles
from app.services import audit_service, scenario_service

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.get("/levers")
def levers(ctx: AuthContext = Depends(get_context)) -> list[dict[str, Any]]:
    return scenario_service.levers()


@router.post("/simulate")
def simulate(body: SimulateIn, ctx: AuthContext = Depends(get_context)) -> dict[str, Any]:
    """Pure computation on a projection. Nothing is stored; actual records are untouched."""
    return scenario_service.run(ctx.db, ctx.business, body.assumptions.model_dump(), body.horizon_days)


@router.get("")
def list_saved(ctx: AuthContext = Depends(get_context)) -> list[dict[str, Any]]:
    return [{"id": str(s.id), "name": s.name, "assumptions": s.assumptions, "result_summary": s.result_summary,
             "opportunity_id": str(s.opportunity_id) if s.opportunity_id else None, "created_by": n,
             "data_as_of": str(s.data_as_of), "created_at": s.created_at.isoformat()}
            for s, n in scenario_service.list_saved(ctx.db, ctx.business_id)]


@router.post("", status_code=201)
def save(body: SaveScenarioIn, request: Request, ctx: AuthContext = Depends(require_roles(*EDITORS))) -> dict[str, Any]:
    s = scenario_service.save(ctx.db, ctx.business, ctx.user, body.name, body.assumptions.model_dump(),
                              body.opportunity_id)
    audit_service.record("scenario.saved", "opportunity", request=request, user_id=ctx.user.id,
                         actor=ctx.user.email, business_id=ctx.business_id, resource_type="scenario",
                         resource_id=str(s.id), details={"name": s.name})
    return {"id": str(s.id)}


@router.delete("/{scenario_id}", status_code=204)
def delete(scenario_id: uuid.UUID, ctx: AuthContext = Depends(require_roles(*EDITORS))) -> None:
    scenario_service.delete(ctx.db, ctx.business_id, scenario_id)
