"""Opportunity Engine persistence: findings, lifecycle events, outcomes."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, DateTime, Float, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, business_fk, created_at_col, uuid_pk

OPPORTUNITY_STATUSES = ("new", "reviewed", "planned", "in_progress", "completed", "dismissed")


class Opportunity(Base):
    __tablename__ = "opportunities"
    __table_args__ = (UniqueConstraint("business_id", "fingerprint"),)
    id: Mapped[uuid.UUID] = uuid_pk()
    business_id: Mapped[uuid.UUID] = business_fk()
    fingerprint: Mapped[str] = mapped_column(String(120))  # stable id so re-runs update, not duplicate
    detector: Mapped[str] = mapped_column(String(60))
    kind: Mapped[str] = mapped_column(String(12))  # risk | opportunity
    category: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(Text)
    why_it_matters: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(10))  # low | medium | high | critical
    priority_score: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    confidence_basis: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    impact_low: Mapped[float | None] = mapped_column(Float)
    impact_high: Mapped[float | None] = mapped_column(Float)
    impact_basis: Mapped[str | None] = mapped_column(Text)
    impact_kind: Mapped[str] = mapped_column(String(20), default="none")
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    supporting_records: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    actions: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    scenario_preset: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    provenance: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    target_metric: Mapped[str | None] = mapped_column(String(60))
    target_params: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    baseline_value: Mapped[float | None] = mapped_column(Float)
    expected_change: Mapped[float | None] = mapped_column(Float)  # signed, in target metric units
    status: Mapped[str] = mapped_column(String(16), default="new")
    is_active: Mapped[str] = mapped_column(String(8), default="yes")  # 'no' when detector stops firing
    action_started_at: Mapped[date | None] = mapped_column(Date)
    completed_at: Mapped[date | None] = mapped_column(Date)
    outcome: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    data_as_of: Mapped[date] = mapped_column(Date)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),
                                                 onupdate=func.now())


class OpportunityEvent(Base):
    __tablename__ = "opportunity_events"
    id: Mapped[uuid.UUID] = uuid_pk()
    business_id: Mapped[uuid.UUID] = business_fk()
    opportunity_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True),
                                                      ForeignKey("opportunities.id", ondelete="CASCADE"),
                                                      index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    event_type: Mapped[str] = mapped_column(String(24))  # detected | status_change | note | outcome
    from_status: Mapped[str | None] = mapped_column(String(16))
    to_status: Mapped[str | None] = mapped_column(String(16))
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_col()
