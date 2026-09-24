from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import StrictModel

Status = Literal["new", "reviewed", "planned", "in_progress", "completed", "dismissed"]


class StatusIn(StrictModel):
    status: Status
    note: str | None = Field(default=None, max_length=1000)


class NoteIn(StrictModel):
    note: str = Field(min_length=1, max_length=1000)


class OpportunityOut(BaseModel):
    id: uuid.UUID
    detector: str
    kind: str
    category: str
    title: str
    summary: str
    why_it_matters: str
    explanation: str
    severity: str
    priority_score: float
    confidence: float
    confidence_basis: dict
    impact_low: float | None
    impact_high: float | None
    impact_kind: str
    impact_basis: str | None
    evidence: list[dict]
    supporting_records: dict
    actions: list[dict]
    scenario_preset: dict | None
    provenance: dict
    target: dict | None
    baseline_value: float | None
    expected_change: float | None
    status: str
    is_active: bool
    action_started_at: str | None
    completed_at: str | None
    outcome: dict | None
    data_as_of: str
    detected_at: str
    updated_at: str
