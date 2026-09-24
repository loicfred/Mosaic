"""Scenario simulation. Reads the analysis bundle; never writes financial records."""

from __future__ import annotations

import uuid
from dataclasses import fields
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.projection import LEVER_LABELS, Assumptions, simulate
from app.core.errors import AppError
from app.models import Business, Opportunity, Scenario, User
from app.services.analysis_service import get_analysis

LEVER_RANGES = {
    "supplier_cost_pct": (-30, 30, 1), "price_pct": (-20, 20, 1), "sales_volume_pct": (-50, 50, 1),
    "recurring_expense_pct": (-50, 50, 1), "collection_days_change": (-30, 30, 1),
    "marketing_spend_pct": (-100, 100, 5), "staffing_cost_pct": (-30, 30, 1), "inventory_spend_pct": (-30, 30, 1),
}


def levers() -> list[dict[str, Any]]:
    return [{"key": f.name, "label": LEVER_LABELS[f.name], "min": LEVER_RANGES[f.name][0],
             "max": LEVER_RANGES[f.name][1], "step": LEVER_RANGES[f.name][2],
             "unit": "days" if f.name == "collection_days_change" else "%"} for f in fields(Assumptions)]


def run(db: Session, business: Business, assumptions: dict[str, float], horizon: int = 90) -> dict[str, Any]:
    a = get_analysis(db, business)
    if a.drivers is None or not a.projection:
        raise AppError(409, "insufficient_data", "At least 120 days of history are needed to simulate.")
    result = simulate(a.drivers, Assumptions(**assumptions), horizon)
    result["drivers"] = {
        "walk_in_sales_per_week": round(sum(a.drivers.b2c_weekday), 2),
        "supplier_purchases_per_month": round(a.drivers.cogs_daily * 30.44, 2),
        "payroll_per_month": round(a.drivers.payroll_monthly, 2),
        "open_invoices": len(a.drivers.open_invoices),
        "open_invoice_amount": round(sum(i["amount"] for i in a.drivers.open_invoices), 2),
        "recurring_commitments": len(a.drivers.recurring),
    }
    result["backtest_median_error_pct"] = a.backtest.get("median_abs_error_pct_of_monthly_outflow")
    return result


def save(db: Session, business: Business, user: User, name: str, assumptions: dict[str, float],
         opportunity_id: uuid.UUID | None) -> Scenario:
    if opportunity_id and db.scalar(select(Opportunity.id).where(Opportunity.business_id == business.id,
                                                                 Opportunity.id == opportunity_id)) is None:
        raise AppError(404, "not_found", "Opportunity not found.")
    r = run(db, business, assumptions)
    sc = Scenario(business_id=business.id, name=name, created_by=user.id, opportunity_id=opportunity_id,
                  assumptions=r["assumptions"], data_as_of=get_analysis(db, business).as_of.date(),
                  result_summary={"baseline": r["baseline"], "scenario": r["scenario"],
                                  "difference": r["difference"]})
    db.add(sc)
    db.commit()
    return sc


def list_saved(db: Session, business_id: uuid.UUID) -> list[tuple[Scenario, str | None]]:
    rows = db.execute(select(Scenario, User.full_name).join(User, User.id == Scenario.created_by)
                      .where(Scenario.business_id == business_id).order_by(Scenario.created_at.desc())).all()
    return [(s, n) for s, n in rows]


def delete(db: Session, business_id: uuid.UUID, scenario_id: uuid.UUID) -> None:
    sc = db.scalar(select(Scenario).where(Scenario.business_id == business_id, Scenario.id == scenario_id))
    if sc is None:
        raise AppError(404, "not_found", "Scenario not found.")
    db.delete(sc)
    db.commit()
