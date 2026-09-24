"""Data access for actual financial records. Every query is scoped by business_id
(and additionally protected by row-level security in PostgreSQL)."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

import pandas as pd
from sqlalchemy import Select, func, or_, select, text
from sqlalchemy.orm import Session

from app.models import Invoice, Transaction

TX_FIELDS = ("id, txn_date AS date, direction, amount, category, subcategory, description, counterparty, "
             "counterparty_type, reference, is_anomaly, excluded")


def load_frames(db: Session, business_id: uuid.UUID) -> tuple[pd.DataFrame, pd.DataFrame]:
    conn = db.connection()
    tx = pd.read_sql(text(f"SELECT {TX_FIELDS} FROM transactions WHERE business_id = :b AND NOT excluded "
                          "ORDER BY txn_date, created_at"), conn, params={"b": business_id})
    inv = pd.read_sql(text("SELECT invoice_no, customer, issue_date, due_date, amount, paid_date FROM invoices "
                           "WHERE business_id = :b"), conn, params={"b": business_id})
    if len(tx):
        tx["id"] = tx["id"].astype(str)
        tx["amount"] = tx["amount"].astype(float)
    if len(inv):
        inv["amount"] = inv["amount"].astype(float)
    return tx, inv


def data_version(db: Session, business_id: uuid.UUID) -> str:
    """Changes whenever rows are added, excluded or re-categorised (not when only
    derived flags such as anomaly scores are refreshed)."""
    row = db.execute(text(
        "SELECT count(*), coalesce(max(created_at)::text, ''), "
        "coalesce(sum(hashtext(category || excluded::text || coalesce(counterparty, ''))), 0) "
        "FROM transactions WHERE business_id = :b"), {"b": business_id}).one()
    inv = db.execute(text("SELECT count(*), coalesce(max(created_at)::text, '') FROM invoices "
                          "WHERE business_id = :b"), {"b": business_id}).one()
    return f"{row[0]}|{row[1]}|{row[2]}|{inv[0]}|{inv[1]}"


def _filtered(business_id: uuid.UUID, f: dict[str, Any]) -> Select:
    q = select(Transaction).where(Transaction.business_id == business_id)
    if f.get("q"):
        like = f"%{f['q'].strip()[:80]}%"
        q = q.where(or_(Transaction.description.ilike(like), Transaction.counterparty.ilike(like),
                        Transaction.reference.ilike(like)))
    if f.get("category"):
        q = q.where(Transaction.category == f["category"])
    if f.get("direction"):
        q = q.where(Transaction.direction == f["direction"])
    if f.get("counterparty"):
        q = q.where(Transaction.counterparty == f["counterparty"])
    if f.get("date_from"):
        q = q.where(Transaction.txn_date >= f["date_from"])
    if f.get("date_to"):
        q = q.where(Transaction.txn_date <= f["date_to"])
    if f.get("min_amount") is not None:
        q = q.where(Transaction.amount >= f["min_amount"])
    if f.get("max_amount") is not None:
        q = q.where(Transaction.amount <= f["max_amount"])
    if f.get("flag") == "anomaly":
        q = q.where(Transaction.is_anomaly.is_(True))
    elif f.get("flag") == "duplicate":
        q = q.where(Transaction.duplicate_group.is_not(None))
    elif f.get("flag") == "uncategorised":
        q = q.where(Transaction.category == "Uncategorised")
    elif f.get("flag") == "excluded":
        q = q.where(Transaction.excluded.is_(True))
    return q


SORTS = {
    "date_desc": (Transaction.txn_date.desc(), Transaction.created_at.desc()),
    "date_asc": (Transaction.txn_date.asc(), Transaction.created_at.asc()),
    "amount_desc": (Transaction.amount.desc(),),
    "amount_asc": (Transaction.amount.asc(),),
}


def list_transactions(db: Session, business_id: uuid.UUID, f: dict[str, Any], page: int, page_size: int,
                      sort: str) -> tuple[list[Transaction], int]:
    base = _filtered(business_id, f)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.scalars(base.order_by(*SORTS.get(sort, SORTS["date_desc"]))
                      .offset((page - 1) * page_size).limit(page_size)).all()
    return list(rows), int(total)


def get_transaction(db: Session, business_id: uuid.UUID, txn_id: uuid.UUID) -> Transaction | None:
    return db.scalar(select(Transaction).where(Transaction.business_id == business_id, Transaction.id == txn_id))


def get_transactions(db: Session, business_id: uuid.UUID, ids: list[str]) -> list[Transaction]:
    valid = []
    for i in ids:
        try:
            valid.append(uuid.UUID(str(i)))
        except ValueError:
            continue
    if not valid:
        return []
    return list(db.scalars(select(Transaction).where(Transaction.business_id == business_id,
                                                      Transaction.id.in_(valid))).all())


def facets(db: Session, business_id: uuid.UUID) -> dict[str, Any]:
    cats = db.execute(select(Transaction.category, func.count()).where(Transaction.business_id == business_id)
                      .group_by(Transaction.category).order_by(Transaction.category)).all()
    cps = db.execute(select(Transaction.counterparty, func.count()).where(
        Transaction.business_id == business_id, Transaction.counterparty.is_not(None))
        .group_by(Transaction.counterparty).order_by(func.count().desc()).limit(200)).all()
    span = db.execute(select(func.min(Transaction.txn_date), func.max(Transaction.txn_date))
                      .where(Transaction.business_id == business_id)).one()
    return {"categories": [{"name": c, "count": n} for c, n in cats],
            "counterparties": [{"name": c, "count": n} for c, n in cps],
            "date_min": str(span[0]) if span[0] else None, "date_max": str(span[1]) if span[1] else None}


def invoices_for(db: Session, business_id: uuid.UUID, invoice_nos: list[str]) -> list[Invoice]:
    if not invoice_nos:
        return []
    return list(db.scalars(select(Invoice).where(Invoice.business_id == business_id,
                                                  Invoice.invoice_no.in_(invoice_nos))).all())


def last_date(db: Session, business_id: uuid.UUID) -> date | None:
    return db.scalar(select(func.max(Transaction.txn_date)).where(Transaction.business_id == business_id))
