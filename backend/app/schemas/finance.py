from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import Page, StrictModel


class TransactionOut(BaseModel):
    id: uuid.UUID
    date: date
    direction: str
    amount: float
    category: str
    subcategory: str | None
    description: str
    counterparty: str | None
    reference: str | None
    source: str
    is_anomaly: bool
    anomaly_reason: str | None
    duplicate_group: str | None
    excluded: bool


class TransactionPage(Page):
    items: list[TransactionOut]


class TransactionDetail(TransactionOut):
    counterparty_type: str | None
    payment_method: str | None
    anomaly_score: float | None
    import_batch_id: uuid.UUID | None
    created_at: datetime
    related_opportunities: list[dict]
    counterparty_history: dict | None
    duplicates: list[dict]
    pending_changes: list[dict]


class DecisionIn(StrictModel):
    decision: Literal["approve", "reject"]
    new_value: str | None = Field(default=None, max_length=60)


class BulkDecisionIn(StrictModel):
    ids: list[uuid.UUID] = Field(min_length=1, max_length=500)
    decision: Literal["approve", "reject"]
