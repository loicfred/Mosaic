"""Append-only security and data audit log.

Never stores passwords, tokens or raw financial records - only identifiers,
event types and minimal context.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Identity, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_col


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    created_at: Mapped[datetime] = created_at_col()
    business_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), index=True)
    actor: Mapped[str | None] = mapped_column(String(254))  # email at time of event (no secrets)
    event_type: Mapped[str] = mapped_column(String(60), index=True)
    category: Mapped[str] = mapped_column(String(20))  # auth | access | data | opportunity | security
    outcome: Mapped[str] = mapped_column(String(10))  # success | failure | denied
    resource_type: Mapped[str | None] = mapped_column(String(40))
    resource_id: Mapped[str | None] = mapped_column(String(64))
    ip_hash: Mapped[str | None] = mapped_column(String(16))
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
