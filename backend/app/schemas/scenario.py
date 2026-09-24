from __future__ import annotations

import uuid

from pydantic import Field

from app.schemas.common import StrictModel


class AssumptionsIn(StrictModel):
    supplier_cost_pct: float = Field(0, ge=-30, le=30)
    price_pct: float = Field(0, ge=-20, le=20)
    sales_volume_pct: float = Field(0, ge=-50, le=50)
    recurring_expense_pct: float = Field(0, ge=-50, le=50)
    collection_days_change: float = Field(0, ge=-30, le=30)
    marketing_spend_pct: float = Field(0, ge=-100, le=100)
    staffing_cost_pct: float = Field(0, ge=-30, le=30)
    inventory_spend_pct: float = Field(0, ge=-30, le=30)


class SimulateIn(StrictModel):
    assumptions: AssumptionsIn
    horizon_days: int = Field(90, ge=30, le=180)


class SaveScenarioIn(StrictModel):
    name: str = Field(min_length=1, max_length=120)
    assumptions: AssumptionsIn
    opportunity_id: uuid.UUID | None = None
