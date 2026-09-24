from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.models import Membership, User
from app.security.deps import OWNER_ONLY, AuthContext, get_context, require_roles
from app.services.analysis_service import get_analysis

router = APIRouter(prefix="/business", tags=["business"])


@router.get("")
def business_profile(ctx: AuthContext = Depends(get_context)) -> dict[str, Any]:
    b = ctx.business
    a = get_analysis(ctx.db, b)
    return {"id": str(b.id), "name": b.name, "sector": b.sector, "currency": b.currency,
            "opening_cash": float(b.opening_cash), "opening_date": str(b.opening_date),
            "data_label": b.data_label, "data_as_of": str(a.as_of.date()),
            "transactions": int(len(a.ledger.tx)), "invoices": int(len(a.ledger.invoices))}


@router.get("/members")
def members(ctx: AuthContext = Depends(require_roles(*OWNER_ONLY))) -> list[dict[str, Any]]:
    rows = ctx.db.execute(select(User, Membership).join(Membership, Membership.user_id == User.id)
                          .where(Membership.business_id == ctx.business_id)).all()
    return [{"name": u.full_name, "email": u.email, "role": m.role.value,
             "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None} for u, m in rows]
