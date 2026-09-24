"""Builds the per-business analysis bundle used by every analytics endpoint.

The bundle is cached in-process and keyed by a cheap "data version" (row counts
+ last update time), so it is recomputed automatically after any import,
approval or exclusion, and never served across tenants.
"""

from __future__ import annotations

import threading
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.analytics.ledger import Ledger, build_ledger
from app.analytics.projection import Drivers, backtest, build_drivers, project, summarise_projection
from app.analytics.quality import ledger_health
from app.ml.inference import find_duplicates, predict_cash_pressure, score_anomalies
from app.models import Business
from app.repositories import ledger_repo


@dataclass
class Analysis:
    business_id: uuid.UUID
    version: str
    ledger: Ledger
    as_of: pd.Timestamp
    prediction: dict[str, Any]
    drivers: Drivers
    projection: dict[str, Any]
    projection_series: list[dict[str, Any]]
    backtest: dict[str, Any]
    anomalies: pd.DataFrame
    duplicates: list[dict[str, Any]]
    health: dict[str, Any]
    extras: dict[str, Any] = field(default_factory=dict)

    def anomaly_list(self, recent_days: int | None = None) -> list[dict[str, Any]]:
        fl = self.anomalies[self.anomalies["is_anomaly"]] if len(self.anomalies) else self.anomalies
        out = []
        tx = self.ledger.tx
        for i in fl.index:
            d = tx.at[i, "date"]
            if recent_days is not None and d <= self.as_of - pd.Timedelta(days=recent_days):
                continue
            out.append({"id": str(tx.at[i, "id"]), "date": str(d.date()), "counterparty": tx.at[i, "counterparty"],
                        "category": tx.at[i, "category"], "amount": float(tx.at[i, "amount"]),
                        "reason": fl.at[i, "reason"], "typical": float(fl.at[i, "typical"]),
                        "score": None if pd.isna(fl.at[i, "score"]) else round(float(fl.at[i, "score"]), 4),
                        "detected_by": fl.at[i, "detected_by"]})
        return out


_cache: OrderedDict[tuple[uuid.UUID, str], Analysis] = OrderedDict()
_lock = threading.Lock()
MAX_ENTRIES = 16


def invalidate(business_id: uuid.UUID) -> None:
    with _lock:
        for k in [k for k in _cache if k[0] == business_id]:
            _cache.pop(k, None)


def get_analysis(db: Session, business: Business) -> Analysis:
    version = ledger_repo.data_version(db, business.id)
    key = (business.id, version)
    with _lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key]
    analysis = _compute(db, business, version)
    with _lock:
        _cache[key] = analysis
        while len(_cache) > MAX_ENTRIES:
            _cache.popitem(last=False)
    return analysis


def _compute(db: Session, business: Business, version: str) -> Analysis:
    tx, inv = ledger_repo.load_frames(db, business.id)
    ledger = build_ledger(tx, inv, float(business.opening_cash), business.opening_date)
    as_of = ledger.end
    anomalies = score_anomalies(ledger) if len(tx) else pd.DataFrame(
        columns=["score", "is_anomaly", "reason", "typical", "detected_by"])
    duplicates = find_duplicates(ledger) if len(tx) else []
    all_tx = pd.read_sql(text("SELECT txn_date AS date, direction, amount, category, counterparty, description, "
                              "excluded FROM transactions WHERE business_id = :b"), db.connection(),
                         params={"b": business.id})
    if len(all_tx):
        all_tx["amount"] = all_tx["amount"].astype(float)
    n_flagged = int(anomalies["is_anomaly"].sum()) if len(anomalies) else 0
    health = ledger_health(all_tx, n_flagged) if len(all_tx) else {"score": None, "checks": [], "totals": {}}
    if len(tx) >= 30 and (as_of - ledger.start).days >= 120:
        prediction = predict_cash_pressure(ledger, as_of)
        drivers = build_drivers(ledger, as_of)
        proj_df = project(drivers)
        projection = summarise_projection(proj_df, drivers)
        series = [{"date": str(d.date()), "cash": round(float(c), 2)} for d, c in zip(proj_df["date"], proj_df["cash"],
                                                                                        strict=True)]
        bt = backtest(ledger)
    else:
        prediction = {"mode": "insufficient_data", "band": "UNKNOWN", "probability": None, "contributions": [],
                      "features": {}, "model_version": None,
                      "reason": "At least 120 days of history are needed."}
        drivers = build_drivers(ledger, as_of) if len(tx) else None  # type: ignore[assignment]
        projection, series, bt = {}, [], {"points": [], "median_abs_error_pct_of_monthly_outflow": None}
    return Analysis(business_id=business.id, version=version, ledger=ledger, as_of=as_of, prediction=prediction,
                    drivers=drivers, projection=projection, projection_series=series, backtest=bt,
                    anomalies=anomalies, duplicates=duplicates, health=health)
