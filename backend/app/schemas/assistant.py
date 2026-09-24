from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.common import StrictModel


class TurnIn(StrictModel):
    question: str = Field(max_length=200)
    answer: str = Field(max_length=800)


class AskContextIn(StrictModel):
    type: Literal["finding", "chart"]
    id: uuid.UUID | None = None
    chart: Literal["cash", "monthly", "kpis", "worth"] | None = None


class AskIn(StrictModel):
    question: str = Field(min_length=1, max_length=200)
    history: list[TurnIn] = Field(default_factory=list, max_length=6)
    context: AskContextIn | None = None


class FactOut(BaseModel):
    label: str
    value: str
    tone: Literal["good", "bad", "warn"] | None = None


class SourceOut(BaseModel):
    label: str
    detail: str
    to: str | None = None


class AnswerOut(BaseModel):
    """Same shape as the frontend's `Answer` (frontend/src/lib/insight/engine.ts)."""

    status: Literal["answer", "refusal", "empty"]
    intent: str = "llm"
    headline: str
    body: str | None = None
    facts: list[FactOut] = Field(default_factory=list)
    visual: dict[str, Any] | None = None
    kind: Literal["actual", "projected", "predicted"] | None = None
    sources: list[SourceOut] = Field(default_factory=list)
    followUps: list[str] = Field(default_factory=list)  # noqa: N815 - matches the frontend field name
    via: Literal["llm"] = "llm"
