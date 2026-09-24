"""Import staging, data-quality issues and approval-based changes.

Imported rows are staged first; nothing reaches `transactions` until a user
commits the batch. Every proposed fix is a row in `proposed_changes` that must
be approved or rejected, and every decision is written to the audit log.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, business_fk, created_at_col, uuid_pk


class ImportBatch(Base):
    __tablename__ = "import_batches"
    id: Mapped[uuid.UUID] = uuid_pk()
    business_id: Mapped[uuid.UUID] = business_fk()
    filename: Mapped[str] = mapped_column(String(200))
    file_sha256: Mapped[str] = mapped_column(String(64))
    uploaded_by: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(16), default="validated")  # validated|committed|discarded
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    valid_count: Mapped[int] = mapped_column(Integer, default=0)
    warning_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0)
    health: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = created_at_col()
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    committed_rows: Mapped[int] = mapped_column(Integer, default=0)


class ImportRow(Base):
    __tablename__ = "import_rows"
    id: Mapped[uuid.UUID] = uuid_pk()
    business_id: Mapped[uuid.UUID] = business_fk()
    batch_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True),
                                                ForeignKey("import_batches.id", ondelete="CASCADE"), index=True)
    row_number: Mapped[int] = mapped_column(Integer)
    raw: Mapped[dict[str, Any]] = mapped_column(JSONB)
    parsed: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(12))  # valid|warning|error|duplicate
    issues: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    include: Mapped[bool] = mapped_column(Boolean, default=True)


class ProposedChange(Base):
    __tablename__ = "proposed_changes"
    id: Mapped[uuid.UUID] = uuid_pk()
    business_id: Mapped[uuid.UUID] = business_fk()
    batch_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True),
                                                       ForeignKey("import_batches.id", ondelete="CASCADE"))
    target_type: Mapped[str] = mapped_column(String(16))  # import_row | transaction
    target_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    change_type: Mapped[str] = mapped_column(String(32))  # set_category | exclude_duplicate
    field: Mapped[str] = mapped_column(String(40))
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(80))  # e.g. rule:duplicate, model:categoriser@v
    status: Mapped[str] = mapped_column(String(12), default="pending")  # pending|approved|rejected
    decided_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at_col()
