from __future__ import annotations

import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from sqlalchemy import select

from app.core.config import get_settings
from app.core.errors import AppError
from app.models import ImportBatch, User
from app.schemas.finance import BulkDecisionIn, DecisionIn
from app.security.deps import EDITORS, AuthContext, get_context, require_roles
from app.services import import_service, opportunity_service
from app.services.analysis_service import get_analysis

router = APIRouter(prefix="/data-quality", tags=["data-quality"])


def _batch_out(b: ImportBatch, uploader: str | None = None) -> dict[str, Any]:
    return {"id": str(b.id), "filename": b.filename, "status": b.status, "row_count": b.row_count,
            "valid_count": b.valid_count, "warning_count": b.warning_count, "error_count": b.error_count,
            "duplicate_count": b.duplicate_count, "committed_rows": b.committed_rows, "health": b.health,
            "created_at": b.created_at.isoformat(), "uploaded_by": uploader,
            "committed_at": b.committed_at.isoformat() if b.committed_at else None,
            "file_sha256": b.file_sha256[:12]}


@router.get("/health")
def ledger_health(ctx: AuthContext = Depends(get_context)) -> dict[str, Any]:
    a = get_analysis(ctx.db, ctx.business)
    pending = import_service.list_proposals(ctx.db, ctx.business_id, "pending", None)
    return {**a.health, "pending_changes": len(pending), "as_of": str(a.as_of.date())}


@router.get("/proposals")
def proposals(ctx: AuthContext = Depends(get_context),
              status: Literal["pending", "approved", "rejected", "expired"] | None = None,
              batch_id: uuid.UUID | None = None) -> list[dict[str, Any]]:
    return import_service.list_proposals(ctx.db, ctx.business_id, status, batch_id)


@router.post("/proposals/{change_id}/decision")
def decide(change_id: uuid.UUID, body: DecisionIn, request: Request,
           ctx: AuthContext = Depends(require_roles(*EDITORS))) -> dict[str, Any]:
    p = import_service.decide(ctx.db, ctx.business, ctx.user, change_id, body.decision, body.new_value, request)
    if p.target_type == "transaction":
        opportunity_service.refresh(ctx.db, ctx.business, ctx.user)
    return {"id": str(p.id), "status": p.status, "new_value": p.new_value}


@router.post("/proposals/bulk-decision")
def bulk_decide(body: BulkDecisionIn, request: Request,
                ctx: AuthContext = Depends(require_roles(*EDITORS))) -> dict[str, Any]:
    done, ledger_touched = 0, False
    for cid in body.ids:
        try:
            p = import_service.decide(ctx.db, ctx.business, ctx.user, cid, body.decision, None, request)
            done += 1
            ledger_touched |= p.target_type == "transaction"
        except AppError:
            ctx.db.rollback()
    if ledger_touched:
        opportunity_service.refresh(ctx.db, ctx.business, ctx.user)
    return {"decided": done}


@router.post("/imports")
async def upload(request: Request, file: UploadFile = File(...),
                 ctx: AuthContext = Depends(require_roles(*EDITORS))) -> dict[str, Any]:
    limit = get_settings().max_upload_bytes
    chunks, size = [], 0
    while chunk := await file.read(64 * 1024):
        size += len(chunk)
        if size > limit:
            raise AppError(413, "file_too_large", f"File exceeds {limit // (1024 * 1024)} MB.")
        chunks.append(chunk)
    batch = import_service.create_batch(ctx.db, ctx.business, ctx.user, file.filename or "upload.csv",
                                        b"".join(chunks), request)
    return _batch_out(batch, ctx.user.full_name)


@router.get("/imports")
def list_imports(ctx: AuthContext = Depends(get_context)) -> list[dict[str, Any]]:
    rows = ctx.db.execute(select(ImportBatch, User.full_name).join(User, User.id == ImportBatch.uploaded_by)
                          .where(ImportBatch.business_id == ctx.business_id)
                          .order_by(ImportBatch.created_at.desc()).limit(50)).all()
    return [_batch_out(b, n) for b, n in rows]


@router.get("/imports/{batch_id}")
def import_detail(batch_id: uuid.UUID, ctx: AuthContext = Depends(get_context),
                  status: Literal["valid", "warning", "error", "duplicate"] | None = Query(None)) -> dict[str, Any]:
    b = import_service.get_batch(ctx.db, ctx.business_id, batch_id)
    uploader = ctx.db.scalar(select(User.full_name).where(User.id == b.uploaded_by))
    rows = import_service.batch_rows(ctx.db, ctx.business_id, batch_id)
    if status:
        rows = [r for r in rows if r.status == status]
    return {**_batch_out(b, uploader), "pending_duplicates": import_service.pending_count(ctx.db, ctx.business_id, b.id,
                                                                                "exclude_duplicate"),
            "pending_changes": import_service.pending_count(ctx.db, ctx.business_id, b.id),
            "rows": [{"id": str(r.id), "row_number": r.row_number, "raw": r.raw, "parsed": r.parsed,
                      "status": r.status, "issues": r.issues, "include": r.include} for r in rows],
            "proposals": import_service.list_proposals(ctx.db, ctx.business_id, None, b.id)}


@router.post("/imports/{batch_id}/commit")
def commit(batch_id: uuid.UUID, request: Request, ctx: AuthContext = Depends(require_roles(*EDITORS))) -> dict[str, Any]:
    b = import_service.commit_batch(ctx.db, ctx.business, ctx.user, batch_id, request)
    a = get_analysis(ctx.db, ctx.business)
    import_service.sync_ledger_proposals(ctx.db, ctx.business, a)
    ctx.db.commit()
    result = opportunity_service.refresh(ctx.db, ctx.business, ctx.user)
    return {**_batch_out(b), "refresh": result}


@router.post("/imports/{batch_id}/discard")
def discard(batch_id: uuid.UUID, request: Request, ctx: AuthContext = Depends(require_roles(*EDITORS))) -> dict[str, Any]:
    return _batch_out(import_service.discard_batch(ctx.db, ctx.business, ctx.user, batch_id, request))
