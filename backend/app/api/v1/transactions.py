from __future__ import annotations

import uuid
from datetime import date
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import cast, select
from sqlalchemy.dialects.postgresql import JSONB

from app.core.errors import AppError
from app.models import Opportunity, ProposedChange, Transaction
from app.repositories import ledger_repo
from app.schemas.finance import TransactionDetail, TransactionOut, TransactionPage
from app.security.deps import AuthContext, get_context
from app.services import audit_service

router = APIRouter(prefix="/transactions", tags=["transactions"])


def _out(t: Transaction) -> TransactionOut:
    return TransactionOut(id=t.id, date=t.txn_date, direction=t.direction, amount=float(t.amount),
                          category=t.category, subcategory=t.subcategory, description=t.description,
                          counterparty=t.counterparty, reference=t.reference, source=t.source,
                          is_anomaly=t.is_anomaly, anomaly_reason=t.anomaly_reason,
                          duplicate_group=t.duplicate_group, excluded=t.excluded)


@router.get("", response_model=TransactionPage)
def list_transactions(
    ctx: AuthContext = Depends(get_context),
    q: str | None = Query(None, max_length=80),
    category: str | None = Query(None, max_length=60),
    direction: Literal["inflow", "outflow"] | None = None,
    counterparty: str | None = Query(None, max_length=160),
    date_from: date | None = None,
    date_to: date | None = None,
    min_amount: float | None = Query(None, ge=0),
    max_amount: float | None = Query(None, ge=0),
    flag: Literal["anomaly", "duplicate", "uncategorised", "excluded"] | None = None,
    sort: Literal["date_desc", "date_asc", "amount_desc", "amount_asc"] = "date_desc",
    page: int = Query(1, ge=1, le=10_000),
    page_size: int = Query(50, ge=1, le=200),
) -> TransactionPage:
    f = {"q": q, "category": category, "direction": direction, "counterparty": counterparty,
         "date_from": date_from, "date_to": date_to, "min_amount": min_amount, "max_amount": max_amount,
         "flag": flag}
    rows, total = ledger_repo.list_transactions(ctx.db, ctx.business_id, f, page, page_size, sort)
    return TransactionPage(items=[_out(t) for t in rows], total=total, page=page, page_size=page_size)


@router.get("/facets")
def facets(ctx: AuthContext = Depends(get_context)) -> dict[str, Any]:
    return ledger_repo.facets(ctx.db, ctx.business_id)


@router.get("/{txn_id}", response_model=TransactionDetail)
def transaction_detail(txn_id: uuid.UUID, request: Request, ctx: AuthContext = Depends(get_context)) -> TransactionDetail:
    t = ledger_repo.get_transaction(ctx.db, ctx.business_id, txn_id)
    if t is None:
        raise AppError(404, "not_found", "Transaction not found.")
    db = ctx.db
    related = db.scalars(select(Opportunity).where(
        Opportunity.business_id == ctx.business_id,
        Opportunity.supporting_records["transaction_ids"].op("@>")(cast([str(t.id)], JSONB)))).all()
    history = None
    if t.counterparty:
        hist = db.scalars(select(Transaction).where(Transaction.business_id == ctx.business_id,
                                                    Transaction.counterparty == t.counterparty,
                                                    Transaction.direction == t.direction,
                                                    Transaction.excluded.is_(False))
                          .order_by(Transaction.txn_date.desc())).all()
        amounts = sorted(float(h.amount) for h in hist)
        history = {"count": len(hist), "median": amounts[len(amounts) // 2] if amounts else None,
                   "total": round(sum(amounts), 2),
                   "recent": [{"id": str(h.id), "date": str(h.txn_date), "amount": float(h.amount)} for h in hist[:6]]}
    dups = []
    if t.duplicate_group:
        dups = [{"id": str(d.id), "date": str(d.txn_date), "amount": float(d.amount), "excluded": d.excluded}
                for d in db.scalars(select(Transaction).where(Transaction.business_id == ctx.business_id,
                                                              Transaction.duplicate_group == t.duplicate_group))]
    pending = [{"id": str(p.id), "change_type": p.change_type, "new_value": p.new_value, "reason": p.reason,
                "status": p.status} for p in db.scalars(select(ProposedChange).where(
                    ProposedChange.business_id == ctx.business_id, ProposedChange.target_id == t.id))]
    audit_service.record("data.transaction_viewed", "access", request=request, user_id=ctx.user.id,
                         actor=ctx.user.email, business_id=ctx.business_id, resource_type="transaction",
                         resource_id=str(t.id))
    base = _out(t).model_dump()
    return TransactionDetail(**base, counterparty_type=t.counterparty_type, payment_method=t.payment_method,
                             anomaly_score=t.anomaly_score, import_batch_id=t.import_batch_id,
                             created_at=t.created_at,
                             related_opportunities=[{"id": str(o.id), "title": o.title, "status": o.status}
                                                    for o in related],
                             counterparty_history=history, duplicates=dups, pending_changes=pending)


@router.post("/lookup")
def lookup(ids: list[str], ctx: AuthContext = Depends(get_context)) -> list[TransactionOut]:
    """Resolve evidence record ids (max 50) to transactions of THIS business only."""
    if len(ids) > 50:
        raise AppError(422, "too_many", "At most 50 ids.")
    return [_out(t) for t in ledger_repo.get_transactions(ctx.db, ctx.business_id, ids)]
