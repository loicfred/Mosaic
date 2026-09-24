"""Declarative base and shared column helpers."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def created_at_col() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


def business_fk() -> Mapped[uuid.UUID]:
    """Tenant key. Every tenant-owned table has one and is protected by RLS."""
    return mapped_column(PGUUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"),
                         index=True, nullable=False)


# Tables protected by PostgreSQL row-level security (see alembic migration 0001).
TENANT_TABLES = (
    "transactions",
    "invoices",
    "import_batches",
    "import_rows",
    "proposed_changes",
    "opportunities",
    "opportunity_events",
    "scenarios",
    "predictions",
)
