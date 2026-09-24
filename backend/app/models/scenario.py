"""Saved scenario simulations. Kept separate from actual financial records."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, business_fk, created_at_col, uuid_pk


class Scenario(Base):
    __tablename__ = "scenarios"
    id: Mapped[uuid.UUID] = uuid_pk()
    business_id: Mapped[uuid.UUID] = business_fk()
    name: Mapped[str] = mapped_column(String(120))
    created_by: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="SET NULL"))
    assumptions: Mapped[dict[str, Any]] = mapped_column(JSONB)
    result_summary: Mapped[dict[str, Any]] = mapped_column(JSONB)
    data_as_of: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = created_at_col()


class Prediction(Base):
    """Every cash-pressure prediction is stored with the model version and the
    exact features used, so it can be traced and audited later."""

    __tablename__ = "predictions"
    id: Mapped[uuid.UUID] = uuid_pk()
    business_id: Mapped[uuid.UUID] = business_fk()
    model_version: Mapped[str] = mapped_column(String(80))
    as_of: Mapped[date] = mapped_column(Date)
    mode: Mapped[str] = mapped_column(String(16))  # model | deterministic
    probability: Mapped[float | None]
    band: Mapped[str] = mapped_column(String(10))
    features: Mapped[dict[str, Any]] = mapped_column(JSONB)
    contributions: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = created_at_col()
