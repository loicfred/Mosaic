"""Opportunity lifecycle: detect -> explain -> quantify -> simulate -> act -> measure."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

import pandas as pd
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.ml.registry import anomaly_model, cash_pressure_model
from app.models import Business, Opportunity, OpportunityEvent, Prediction, Transaction, User
from app.opportunities.engine import ENGINE_VERSION, EngineContext, Finding, run_engine
from app.opportunities.targets import TARGETS, measure_outcome
from app.services.analysis_service import Analysis, get_analysis

UTC = timezone.utc  # datetime.UTC needs Python 3.11+

TRANSITIONS: dict[str, set[str]] = {
    "new": {"reviewed", "planned", "in_progress", "dismissed"},
    "reviewed": {"planned", "in_progress", "dismissed"},
    "planned": {"in_progress", "reviewed", "dismissed"},
    "in_progress": {"completed", "planned", "dismissed"},
    "completed": {"in_progress"},
    "dismissed": {"new"},
}
PRE_ACTION = {"new", "reviewed", "planned", "dismissed"}


def _provenance(a: Analysis, f: Finding) -> dict[str, Any]:
    cp, an = cash_pressure_model(), anomaly_model()
    models = []
    if f.detector == "cash_pressure":
        models.append({"name": "cash_pressure_30d", "version": a.prediction.get("model_version"),
                       "status": cp.status})
    if f.detector == "unusual_transactions":
        models.append({"name": "transaction_anomaly", "version": an.meta.get("version"), "status": an.status})
    return {
        "engine_version": ENGINE_VERSION,
        "detector": f.detector,
        "data_window": [str(a.ledger.start.date()), str(a.as_of.date())],
        "data_version": a.version,
        "transactions_analysed": int(len(a.ledger.tx)),
        "invoices_analysed": int(len(a.ledger.invoices)),
        "data_health_score": a.health.get("score"),
        "models": models,
        "facts_source": "deterministic financial engine (pandas) - narrative generated from the same numbers",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }


def engine_context(a: Analysis, as_of: pd.Timestamp | None = None) -> EngineContext:
    return EngineContext(
        ledger=a.ledger, as_of=as_of or a.as_of, data_health=float(a.health.get("score") or 90),
        prediction=a.prediction if a.prediction.get("mode") in ("model", "deterministic") else None,
        projection=a.projection or None,
        projection_error_pct=a.backtest.get("median_abs_error_pct_of_monthly_outflow"),
        anomalies=a.anomaly_list(recent_days=60), duplicates=a.duplicates,
    )


def _store_prediction(db: Session, a: Analysis) -> uuid.UUID | None:
    p = a.prediction
    if p.get("mode") not in ("model", "deterministic"):
        return None
    existing = db.scalar(select(Prediction).where(Prediction.business_id == a.business_id,
                                                  Prediction.as_of == a.as_of.date(),
                                                  Prediction.model_version == p["model_version"]))
    if existing:
        return existing.id
    row = Prediction(business_id=a.business_id, model_version=p["model_version"], as_of=a.as_of.date(),
                     mode=p["mode"], probability=p.get("probability"), band=p["band"],
                     features={k: (round(v, 4) if isinstance(v, float) else v) for k, v in p["features"].items()},
                     contributions=p.get("contributions", []))
    db.add(row)
    db.flush()
    return row.id


def _sync_anomaly_flags(db: Session, a: Analysis) -> None:
    db.execute(update(Transaction).where(Transaction.business_id == a.business_id)
               .values(is_anomaly=False, anomaly_score=None, anomaly_reason=None, duplicate_group=None))
    tx = a.ledger.tx
    for i in a.anomalies.index[a.anomalies["is_anomaly"]] if len(a.anomalies) else []:
        sc = a.anomalies.at[i, "score"]
        db.execute(update(Transaction).where(Transaction.business_id == a.business_id,
                                             Transaction.id == uuid.UUID(str(tx.at[i, "id"])))
                   .values(is_anomaly=True, anomaly_score=None if pd.isna(sc) else float(sc),
                           anomaly_reason=a.anomalies.at[i, "reason"]))
    for g in a.duplicates:
        ids = [uuid.UUID(i) for i in g["transaction_ids"]]
        db.execute(update(Transaction).where(Transaction.business_id == a.business_id, Transaction.id.in_(ids))
                   .values(duplicate_group=g["key"][:200]))


def upsert_findings(db: Session, business_id: uuid.UUID, a: Analysis, findings: list[Finding],
                    as_of: date, user: User | None, mark_inactive: bool = True) -> list[Opportunity]:
    existing = {o.fingerprint: o for o in db.scalars(select(Opportunity).where(
        Opportunity.business_id == business_id)).all()}
    seen = set()
    out = []
    for f in findings:
        seen.add(f.fingerprint)
        o = existing.get(f.fingerprint)
        fields = dict(
            detector=f.detector, kind=f.kind, category=f.category, title=f.title, summary=f.summary,
            why_it_matters=f.why_it_matters, explanation=f.explanation, severity=f.severity,
            priority_score=f.priority_score, confidence=f.confidence, confidence_basis=f.confidence_basis,
            impact_low=f.impact_low, impact_high=f.impact_high, impact_basis=f.impact_basis,
            impact_kind=f.impact_kind, evidence=f.evidence, supporting_records=f.supporting_records,
            actions=f.actions, scenario_preset=f.scenario_preset, provenance=_provenance(a, f),
            target_metric=f.target_metric, target_params=f.target_params, data_as_of=as_of, is_active="yes",
        )
        if o is None:
            o = Opportunity(business_id=business_id, fingerprint=f.fingerprint, status="new",
                            baseline_value=f.baseline_value, expected_change=f.expected_change, **fields)
            db.add(o)
            db.flush()
            db.add(OpportunityEvent(business_id=business_id, opportunity_id=o.id, event_type="detected",
                                    to_status="new", user_id=user.id if user else None,
                                    note=f"Detected on data up to {as_of.isoformat()}"))
        else:
            for k, v in fields.items():
                setattr(o, k, v)
            if o.status in PRE_ACTION:
                o.baseline_value, o.expected_change = f.baseline_value, f.expected_change
        out.append(o)
    if mark_inactive:
        for fp, o in existing.items():
            if fp not in seen and o.is_active == "yes":
                o.is_active = "no"
    return out


def refresh(db: Session, business: Business, user: User | None) -> dict[str, Any]:
    a = get_analysis(db, business)
    pred_id = _store_prediction(db, a)
    if pred_id:
        a.prediction["id"] = str(pred_id)
    _sync_anomaly_flags(db, a)
    findings = run_engine(engine_context(a))
    opps = upsert_findings(db, business.id, a, findings, a.as_of.date(), user)
    for o in db.scalars(select(Opportunity).where(Opportunity.business_id == business.id,
                                                  Opportunity.status.in_(["in_progress", "completed"]))):
        o.outcome = outcome_for(a, o)
    db.commit()
    return {"detected": len(opps), "as_of": str(a.as_of.date()), "prediction_band": a.prediction.get("band")}


def outcome_for(a: Analysis, o: Opportunity) -> dict[str, Any]:
    return measure_outcome(a.ledger, o.target_metric, o.target_params or {}, o.baseline_value, o.expected_change,
                           pd.Timestamp(o.action_started_at) if o.action_started_at else None, a.as_of)


def list_opportunities(db: Session, business_id: uuid.UUID, status: str | None, include_inactive: bool) -> list[Opportunity]:
    q = select(Opportunity).where(Opportunity.business_id == business_id)
    if status:
        q = q.where(Opportunity.status == status)
    if not include_inactive:
        q = q.where((Opportunity.is_active == "yes") | Opportunity.status.in_(["in_progress", "completed"]))
    return list(db.scalars(q.order_by(Opportunity.priority_score.desc())).all())


def get(db: Session, business_id: uuid.UUID, opp_id: uuid.UUID) -> Opportunity:
    o = db.scalar(select(Opportunity).where(Opportunity.business_id == business_id, Opportunity.id == opp_id))
    if o is None:
        raise AppError(404, "not_found", "Opportunity not found.")
    return o


def events(db: Session, business_id: uuid.UUID, opp_id: uuid.UUID) -> list[tuple[OpportunityEvent, str | None]]:
    rows = db.execute(select(OpportunityEvent, User.full_name).outerjoin(User, User.id == OpportunityEvent.user_id)
                      .where(OpportunityEvent.business_id == business_id,
                             OpportunityEvent.opportunity_id == opp_id)
                      .order_by(OpportunityEvent.created_at)).all()
    return [(e, n) for e, n in rows]


def change_status(db: Session, business: Business, user: User, opp_id: uuid.UUID, to: str,
                  note: str | None) -> Opportunity:
    o = get(db, business.id, opp_id)
    if to not in TRANSITIONS.get(o.status, set()):
        raise AppError(409, "invalid_transition", f"Cannot move from {o.status} to {to}.")
    frm = o.status
    o.status = to
    today = date.today()
    if to == "in_progress" and o.action_started_at is None:
        o.action_started_at = today
    if to == "completed":
        o.completed_at = today
    if to in ("new", "reviewed", "planned") and frm in ("in_progress",):
        o.action_started_at = None
    db.add(OpportunityEvent(business_id=business.id, opportunity_id=o.id, user_id=user.id,
                            event_type="status_change", from_status=frm, to_status=to, note=(note or None)))
    if to in ("in_progress", "completed"):
        o.outcome = outcome_for(get_analysis(db, business), o)
    db.commit()
    return o


def add_note(db: Session, business: Business, user: User, opp_id: uuid.UUID, note: str) -> None:
    o = get(db, business.id, opp_id)
    db.add(OpportunityEvent(business_id=business.id, opportunity_id=o.id, user_id=user.id, event_type="note",
                            note=note))
    db.commit()


def target_meta(key: str | None) -> dict[str, Any] | None:
    return {"key": key, **TARGETS[key]} if key else None
