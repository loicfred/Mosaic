"""Actual financial records. Scenario simulations never write to these tables."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, business_fk, created_at_col, uuid_pk


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_txn_amount_positive"),
        CheckConstraint("direction IN ('inflow','outflow')", name="ck_txn_direction"),
        Index("ix_txn_business_date", "business_id", "txn_date"),
    )
    id: Mapped[uuid.UUID] = uuid_pk()
    business_id: Mapped[uuid.UUID] = business_fk()
    txn_date: Mapped[date] = mapped_column(Date)
    direction: Mapped[str] = mapped_column(String(8))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    category: Mapped[str] = mapped_column(String(60), index=True)
    subcategory: Mapped[str | None] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(String(300))
    counterparty: Mapped[str | None] = mapped_column(String(160), index=True)
    counterparty_type: Mapped[str | None] = mapped_column(String(16))
    reference: Mapped[str | None] = mapped_column(String(80))
    payment_method: Mapped[str | None] = mapped_column(String(24))
    source: Mapped[str] = mapped_column(String(16), default="import")  # seed | import | manual
    import_batch_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("import_batches.id", ondelete="SET NULL"))
    external_ref: Mapped[str | None] = mapped_column(String(64))
    anomaly_score: Mapped[float | None] = mapped_column(Float)
    is_anomaly: Mapped[bool] = mapped_column(Boolean, default=False)
    anomaly_reason: Mapped[str | None] = mapped_column(Text)
    duplicate_group: Mapped[str | None] = mapped_column(String(200))
    # Records are never deleted. A confirmed duplicate is excluded from analytics
    # (with an audit event) but stays visible in the transaction list.
    excluded: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),
                                                 onupdate=func.now())


class Invoice(Base):
    """Receivables issued to business customers; used for collection behaviour."""

    __tablename__ = "invoices"
    __table_args__ = (UniqueConstraint("business_id", "invoice_no"),
                      CheckConstraint("amount > 0", name="ck_invoice_amount_positive"))
    id: Mapped[uuid.UUID] = uuid_pk()
    business_id: Mapped[uuid.UUID] = business_fk()
    invoice_no: Mapped[str] = mapped_column(String(40))
    customer: Mapped[str] = mapped_column(String(160), index=True)
    issue_date: Mapped[date] = mapped_column(Date)
    due_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    paid_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = created_at_col()
