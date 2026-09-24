"""Import pipeline and approval-based data changes.

Flow: upload -> validate & stage -> proposals (category suggestions, duplicate
exclusions, payee matches) -> user approves/rejects -> commit.
Nothing is written to `transactions` before commit, and no existing record is
ever deleted: a confirmed duplicate is *excluded* from analytics, with an
audit event recording who approved it and the before/after values.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics.quality import PAYEE_EXPECTED, health_score
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.taxonomy import UNCATEGORISED, is_valid_category
from app.ml.inference import suggest_category
from app.models import Business, ImportBatch, ImportRow, ProposedChange, Transaction, User
from app.services import audit_service
from app.services.analysis_service import Analysis, invalidate
from app.services.csv_import import CsvRejected, parse_csv, row_key

UTC = timezone.utc  # datetime.UTC needs Python 3.11+

SUGGESTION_REVIEW_THRESHOLD = 0.45


def _existing_keys(db: Session, business_id: uuid.UUID) -> tuple[set[str], list[str], float | None]:
    rows = db.execute(select(Transaction.txn_date, Transaction.direction, Transaction.amount,
                             Transaction.counterparty, Transaction.description)
                      .where(Transaction.business_id == business_id)).all()
    keys = {row_key(d, di, Decimal(a), cp or desc) for d, di, a, cp, desc in rows}
    cps = sorted({cp for *_, cp, _ in rows if cp})
    outs = sorted(float(a) for _, di, a, *_ in rows if di == "outflow")
    typical = outs[len(outs) // 2] if outs else None
    return keys, cps, typical


def batch_health(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    errors = sum(r["status"] == "error" for r in rows)
    dups = sum(r["status"] == "duplicate" for r in rows)
    usable = [r for r in rows if r["status"] != "error"]
    uncategorised = sum(1 for r in usable if r["parsed"].get("category") == UNCATEGORISED)
    needs_payee = [r for r in usable if r["parsed"].get("direction") == "outflow"
                   and r["parsed"].get("category") in PAYEE_EXPECTED]
    missing_payee = sum(1 for r in needs_payee if not r["parsed"].get("counterparty"))
    h = health_score((n - errors) / n if n else 1, dups / n if n else 0,
                     1 - (uncategorised / len(usable) if usable else 0),
                     1 - (missing_payee / len(needs_payee) if needs_payee else 0))
    codes: dict[str, int] = {}
    for r in rows:
        for i in r["issues"]:
            codes[i["code"]] = codes.get(i["code"], 0) + 1
    return {**h, "rows": n, "errors": errors, "duplicates": dups, "uncategorised": uncategorised,
            "missing_payee": missing_payee, "issue_counts": codes,
            "valid_dates_pct": round(100 * (1 - codes.get("invalid_date", 0) / n), 1) if n else 100.0}


def create_batch(db: Session, business: Business, user: User, filename: str, data: bytes,
                 request: Request | None) -> ImportBatch:
    s = get_settings()
    if len(data) > s.max_upload_bytes:
        raise AppError(413, "file_too_large", f"File exceeds {s.max_upload_bytes // (1024 * 1024)} MB.")
    if not filename.lower().endswith((".csv", ".txt")):
        raise AppError(415, "unsupported_file", "Only .csv files are accepted.")
    keys, cps, typical = _existing_keys(db, business.id)
    try:
        parsed = parse_csv(data, max_rows=s.max_import_rows, today=date.today(), opening_date=business.opening_date,
                           existing_keys=keys, known_counterparties=cps, typical_outflow=typical)
    except CsvRejected as exc:
        audit_service.record("data.import_rejected", "data", "failure", request=request, user_id=user.id,
                             actor=user.email, business_id=business.id,
                             details={"filename": filename[:120], "reason": str(exc)})
        raise AppError(400, "csv_rejected", str(exc)) from None

    rows = parsed["rows"]
    health = batch_health(rows)
    batch = ImportBatch(business_id=business.id, filename=filename[:200],
                        file_sha256=hashlib.sha256(data).hexdigest(), uploaded_by=user.id,
                        row_count=len(rows), valid_count=sum(r["status"] == "valid" for r in rows),
                        warning_count=sum(r["status"] == "warning" for r in rows),
                        error_count=health["errors"], duplicate_count=health["duplicates"],
                        health={**health, "column_mapping": parsed["mapping"]})
    db.add(batch)
    db.flush()
    for r in rows:
        ir = ImportRow(business_id=business.id, batch_id=batch.id, row_number=r["row_number"], raw=r["raw"],
                       parsed=r["parsed"], status=r["status"], issues=r["issues"],
                       include=r["status"] != "error")
        db.add(ir)
        db.flush()
        _proposals_for_row(db, business.id, batch.id, ir)
    db.commit()
    audit_service.record("data.import_staged", "data", request=request, user_id=user.id, actor=user.email,
                         business_id=business.id, resource_type="import_batch", resource_id=str(batch.id),
                         details={"filename": filename[:120], "rows": len(rows), "errors": health["errors"],
                                  "duplicates": health["duplicates"], "health": health["score"]})
    return batch


def _proposals_for_row(db: Session, business_id: uuid.UUID, batch_id: uuid.UUID, ir: ImportRow) -> None:
    p = ir.parsed
    if ir.status == "error" or not p:
        return
    if ir.status == "duplicate":
        what = "an existing transaction" if p.get("duplicate_of") == "ledger" else p.get("duplicate_of")
        db.add(ProposedChange(business_id=business_id, batch_id=batch_id, target_type="import_row",
                              target_id=ir.id, change_type="exclude_duplicate", field="include", old_value="true",
                              new_value="false", confidence=0.95, source="rule:exact_duplicate",
                              reason=f"Same date, amount and payee as {what}."))
        ir.include = False  # held back until the user decides; commit is blocked while pending
    if p.get("category") == UNCATEGORISED:
        sug = suggest_category(p.get("description", ""), p.get("direction", ""))
        if sug:
            db.add(ProposedChange(business_id=business_id, batch_id=batch_id, target_type="import_row",
                                  target_id=ir.id, change_type="set_category", field="category",
                                  old_value=UNCATEGORISED, new_value=sug["category"], confidence=sug["confidence"],
                                  source=f"model:{sug['model_version']}",
                                  reason=_category_reason(sug)))
    if p.get("suggested_counterparty") and not p.get("counterparty"):
        db.add(ProposedChange(business_id=business_id, batch_id=batch_id, target_type="import_row",
                              target_id=ir.id, change_type="set_counterparty", field="counterparty",
                              old_value=None, new_value=p["suggested_counterparty"], confidence=0.8,
                              source="rule:known_payee_in_description",
                              reason=f"The description mentions a payee you already use: {p['suggested_counterparty']}."))


def _category_reason(sug: dict[str, Any]) -> str:
    alt = ", ".join(f"{a['category']} {a['confidence'] * 100:.0f}%" for a in sug["alternatives"])
    note = "" if sug["confidence"] >= SUGGESTION_REVIEW_THRESHOLD else " Low confidence - please check."
    return f"Suggested from the description by the category model ({sug['confidence'] * 100:.0f}%). " \
           f"Alternatives: {alt}.{note}"


def sync_ledger_proposals(db: Session, business: Business, a: Analysis) -> int:
    """Create pending proposals for issues found in already-recorded transactions."""
    existing = {(p.target_id, p.change_type) for p in db.scalars(
        select(ProposedChange).where(ProposedChange.business_id == business.id,
                                     ProposedChange.target_type == "transaction")).all()}
    created = 0
    for t in db.scalars(select(Transaction).where(Transaction.business_id == business.id,
                                                  Transaction.category == UNCATEGORISED,
                                                  Transaction.excluded.is_(False))).all():
        if (t.id, "set_category") in existing:
            continue
        sug = suggest_category(t.description, t.direction)
        if sug:
            db.add(ProposedChange(business_id=business.id, target_type="transaction", target_id=t.id,
                                  change_type="set_category", field="category", old_value=UNCATEGORISED,
                                  new_value=sug["category"], confidence=sug["confidence"],
                                  source=f"model:{sug['model_version']}", reason=_category_reason(sug)))
            created += 1
    for g in a.duplicates:
        for tid in g["transaction_ids"][1:]:
            u = uuid.UUID(tid)
            if (u, "exclude_duplicate") in existing:
                continue
            db.add(ProposedChange(business_id=business.id, target_type="transaction", target_id=u,
                                  change_type="exclude_duplicate", field="excluded", old_value="false",
                                  new_value="true", confidence=0.95, source="rule:exact_duplicate",
                                  reason=f"{g['count']} payments of the same amount to {g['counterparty']} on "
                                         f"{g['date']}. Excluding keeps the record but removes it from analytics."))
            created += 1
    db.flush()
    return created


def list_proposals(db: Session, business_id: uuid.UUID, status: str | None, batch_id: uuid.UUID | None) -> list[dict[str, Any]]:
    q = select(ProposedChange, User.full_name).outerjoin(User, User.id == ProposedChange.decided_by).where(
        ProposedChange.business_id == business_id)
    if status:
        q = q.where(ProposedChange.status == status)
    if batch_id:
        q = q.where(ProposedChange.batch_id == batch_id)
    else:
        q = q.where(ProposedChange.target_type == "transaction")
    out = []
    for p, decider in db.execute(q.order_by(ProposedChange.created_at)).all():
        target: dict[str, Any] = {}
        if p.target_type == "transaction":
            t = db.scalar(select(Transaction).where(Transaction.business_id == business_id,
                                                    Transaction.id == p.target_id))
            if t:
                target = {"date": str(t.txn_date), "description": t.description, "amount": float(t.amount),
                          "direction": t.direction, "counterparty": t.counterparty}
        else:
            r = db.scalar(select(ImportRow).where(ImportRow.business_id == business_id, ImportRow.id == p.target_id))
            if r:
                target = {"row_number": r.row_number, **{k: r.parsed.get(k) for k in
                                                         ("date", "description", "amount", "direction", "counterparty")}}
        out.append({"id": str(p.id), "target_type": p.target_type, "target_id": str(p.target_id),
                    "change_type": p.change_type, "field": p.field, "old_value": p.old_value,
                    "new_value": p.new_value, "reason": p.reason, "confidence": p.confidence, "source": p.source,
                    "status": p.status, "decided_by": decider,
                    "decided_at": p.decided_at.isoformat() if p.decided_at else None, "target": target,
                    "batch_id": str(p.batch_id) if p.batch_id else None})
    return out


def decide(db: Session, business: Business, user: User, change_id: uuid.UUID, decision: str,
           new_value: str | None, request: Request | None) -> ProposedChange:
    p = db.scalar(select(ProposedChange).where(ProposedChange.business_id == business.id,
                                               ProposedChange.id == change_id))
    if p is None:
        raise AppError(404, "not_found", "Proposed change not found.")
    if p.status != "pending":
        raise AppError(409, "already_decided", "This change has already been decided.")
    if p.batch_id:
        batch = db.scalar(select(ImportBatch).where(ImportBatch.id == p.batch_id,
                                                    ImportBatch.business_id == business.id))
        if batch and batch.status != "validated":
            raise AppError(409, "batch_closed", "This import has already been committed or discarded.")
    if decision == "approve" and new_value is not None and p.change_type == "set_category":
        if not is_valid_category(new_value):
            raise AppError(422, "invalid_category", "Unknown category.")
        p.new_value = new_value  # user corrected the suggestion before approving
    before, after = p.old_value, p.new_value
    if p.target_type == "import_row":
        row = db.scalar(select(ImportRow).where(ImportRow.business_id == business.id, ImportRow.id == p.target_id))
        if row is None:
            raise AppError(404, "not_found", "Import row not found.")
        if p.change_type == "exclude_duplicate":
            row.include = decision != "approve"
        elif decision == "approve":
            row.parsed = {**row.parsed, p.field: p.new_value}
    else:
        t = db.scalar(select(Transaction).where(Transaction.business_id == business.id,
                                                Transaction.id == p.target_id))
        if t is None:
            raise AppError(404, "not_found", "Transaction not found.")
        if decision == "approve":
            if p.change_type == "set_category":
                t.category = p.new_value or UNCATEGORISED
            elif p.change_type == "exclude_duplicate":
                t.excluded = True
            elif p.change_type == "set_counterparty":
                t.counterparty = p.new_value
    p.status = "approved" if decision == "approve" else "rejected"
    p.decided_by, p.decided_at = user.id, datetime.now(UTC)
    db.commit()
    invalidate(business.id)
    audit_service.record(f"data.change_{p.status}", "data", request=request, user_id=user.id, actor=user.email,
                         business_id=business.id, resource_type=p.target_type, resource_id=str(p.target_id),
                         details={"change_type": p.change_type, "field": p.field, "before": before,
                                  "after": after if decision == "approve" else before, "source": p.source,
                                  "proposal_id": str(p.id)})
    return p


def get_batch(db: Session, business_id: uuid.UUID, batch_id: uuid.UUID) -> ImportBatch:
    b = db.scalar(select(ImportBatch).where(ImportBatch.business_id == business_id, ImportBatch.id == batch_id))
    if b is None:
        raise AppError(404, "not_found", "Import not found.")
    return b


def batch_rows(db: Session, business_id: uuid.UUID, batch_id: uuid.UUID) -> list[ImportRow]:
    return list(db.scalars(select(ImportRow).where(ImportRow.business_id == business_id,
                                                   ImportRow.batch_id == batch_id)
                           .order_by(ImportRow.row_number)).all())


def pending_count(db: Session, business_id: uuid.UUID, batch_id: uuid.UUID, change_type: str | None = None) -> int:
    q = select(func.count()).select_from(ProposedChange).where(
        ProposedChange.business_id == business_id, ProposedChange.batch_id == batch_id,
        ProposedChange.status == "pending")
    if change_type:
        q = q.where(ProposedChange.change_type == change_type)
    return int(db.scalar(q) or 0)


def commit_batch(db: Session, business: Business, user: User, batch_id: uuid.UUID,
                 request: Request | None) -> ImportBatch:
    b = get_batch(db, business.id, batch_id)
    if b.status != "validated":
        raise AppError(409, "batch_closed", f"This import is already {b.status}.")
    if pending_count(db, business.id, b.id, "exclude_duplicate"):
        raise AppError(409, "pending_duplicates", "Decide on every possible duplicate before committing.")
    n = 0
    for r in batch_rows(db, business.id, b.id):
        if not r.include or r.status == "error" or not r.parsed:
            continue
        p = r.parsed
        cp = p.get("counterparty")
        db.add(Transaction(business_id=business.id, txn_date=date.fromisoformat(p["date"]), direction=p["direction"],
                           amount=Decimal(p["amount"]), category=p.get("category") or UNCATEGORISED,
                           description=p["description"], counterparty=cp,
                           counterparty_type=("supplier" if p["direction"] == "outflow" else "customer") if cp else None,
                           reference=p.get("reference"), source="import", import_batch_id=b.id,
                           external_ref=f"{b.file_sha256[:8]}-{r.row_number}"))
        n += 1
    # Undecided row-level suggestions are closed; the ledger check re-proposes them against the
    # committed transactions so nothing is silently applied.
    for p in db.scalars(select(ProposedChange).where(ProposedChange.business_id == business.id,
                                                     ProposedChange.batch_id == b.id,
                                                     ProposedChange.status == "pending")):
        p.status = "expired"
    b.status, b.committed_at, b.committed_rows = "committed", datetime.now(UTC), n
    db.commit()
    invalidate(business.id)
    audit_service.record("data.import_committed", "data", request=request, user_id=user.id, actor=user.email,
                         business_id=business.id, resource_type="import_batch", resource_id=str(b.id),
                         details={"rows_committed": n, "rows_total": b.row_count})
    return b


def discard_batch(db: Session, business: Business, user: User, batch_id: uuid.UUID,
                  request: Request | None) -> ImportBatch:
    b = get_batch(db, business.id, batch_id)
    if b.status != "validated":
        raise AppError(409, "batch_closed", f"This import is already {b.status}.")
    b.status = "discarded"
    for p in db.scalars(select(ProposedChange).where(ProposedChange.business_id == business.id,
                                                     ProposedChange.batch_id == b.id,
                                                     ProposedChange.status == "pending")):
        p.status = "rejected"
    db.commit()
    audit_service.record("data.import_discarded", "data", request=request, user_id=user.id, actor=user.email,
                         business_id=business.id, resource_type="import_batch", resource_id=str(b.id))
    return b
