"""Inference helpers. Pure functions over a Ledger - no database access here."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from app.analytics.anomalies import ANOMALY_FEATURES, anomaly_features, duplicate_groups, final_flags, materiality, rule_flags
from app.analytics.features import BUFFER_DAYS_THRESHOLD, FEATURE_LABELS, FEATURE_NAMES, compute_features
from app.analytics.ledger import Ledger
from app.core.formatting import mur
from app.ml.registry import anomaly_model, cash_pressure_model, categoriser_model

PCT_FEATURES = {"net_margin_90d", "revenue_growth_30d", "expense_growth_30d", "supplier_cost_growth_30d",
                "recurring_share", "top_customer_share", "top_supplier_share", "txn_frequency_change"}


def display_feature(name: str, v: float) -> str:
    if name in PCT_FEATURES:
        return f"{v * 100:+.1f}%" if "growth" in name or "change" in name or "margin" in name else f"{v * 100:.1f}%"
    if name in ("buffer_days", "collection_days"):
        return f"{v:.0f} days"
    if name == "collection_days_trend":
        return f"{v:+.0f} days"
    if name in ("overdue_receivables_ratio", "scheduled_obligations_ratio", "cash_trend_30d"):
        return f"{v:+.2f} x monthly" if name == "cash_trend_30d" else f"{v:.2f} x monthly"
    return f"{v:.2f}"


def predict_cash_pressure(ledger: Ledger, as_of: pd.Timestamp | None = None) -> dict[str, Any]:
    as_of = pd.Timestamp(as_of or ledger.end)
    fr = compute_features(ledger, as_of)
    lm = cash_pressure_model()
    features = {**fr.values, **fr.support}
    base = {"as_of": str(as_of.date()), "features": features,
            "buffer_threshold_days": BUFFER_DAYS_THRESHOLD}
    if fr.values["buffer_days"] < BUFFER_DAYS_THRESHOLD:
        return {**base, "mode": "deterministic", "band": "HIGH", "probability": None,
                "model_version": "rule:buffer<14d", "contributions": [],
                "reason": f"Cash already covers only {fr.values['buffer_days']:.0f} days of committed outflows."}
    if not lm.ok:
        band = "MODERATE" if fr.values["buffer_days"] < 21 else "LOW"
        return {**base, "mode": "deterministic", "band": band, "probability": None,
                "model_version": f"rule:buffer (model {lm.status})", "contributions": [],
                "reason": "Model unavailable; using the buffer-days rule of thumb."}
    x = pd.DataFrame([fr.values])[FEATURE_NAMES]
    prob = float(lm.model.predict_proba(x)[0, 1])
    bands = lm.meta["bands"]
    band = "HIGH" if prob >= bands["high_threshold"] else "MODERATE" if prob >= bands["moderate_threshold"] else "LOW"
    contributions = []
    exp = lm.meta.get("explainability", {})
    if exp.get("method") == "logistic_contributions":
        for f in FEATURE_NAMES:
            v = float(fr.values[f])
            z = (v - exp["means"][f]) / (exp["scales"][f] or 1.0)
            c = exp["coefficients"][f] * z
            contributions.append({"feature": f, "label": FEATURE_LABELS[f], "value": round(v, 4),
                                  "display": display_feature(f, v), "contribution": round(float(c), 4),
                                  "direction": "raises risk" if c > 0 else "lowers risk"})
        contributions.sort(key=lambda c: -abs(c["contribution"]))
    return {**base, "mode": "model", "band": band, "probability": round(prob, 4),
            "model_version": lm.meta["version"], "contributions": contributions,
            "test_roc_auc": lm.meta.get("test", {}).get("roc_auc"),
            "thresholds": bands,
            "reason": f"Model probability {prob * 100:.0f}% (bands: MODERATE >= "
                      f"{bands['moderate_threshold'] * 100:.0f}%, HIGH >= {bands['high_threshold'] * 100:.0f}%)."}


def score_anomalies(ledger: Ledger) -> pd.DataFrame:
    """Returns rows (indexed like ledger.tx) with score, is_anomaly, reason."""
    lm = anomaly_model()
    feats = anomaly_features(ledger.tx)
    if feats.empty:
        return pd.DataFrame(columns=["score", "is_anomaly", "reason", "typical"])
    out = pd.DataFrame(index=feats.index)
    rule = rule_flags(feats, ledger.tx["category"])
    if lm.ok:
        out["score"] = -lm.model.score_samples(feats[ANOMALY_FEATURES])
        out["model_flag"] = out["score"] >= lm.meta["threshold"]
    else:
        out["score"] = np.nan
        out["model_flag"] = False
    out["rule_flag"] = rule
    out["is_anomaly"] = final_flags(feats, out["model_flag"], out["rule_flag"], ledger.tx["amount"],
                                    materiality(ledger.tx))
    tx = ledger.tx.loc[feats.index]
    reasons, typical = [], []
    for i, r in feats.iterrows():
        ratio = math.exp(r["log_ratio_counterparty_median"])
        who = tx.at[i, "counterparty"] or tx.at[i, "category"]
        if r["is_new_counterparty"] and ratio >= 1.5:
            reasons.append(f"First payment to {who}; {math.exp(r['log_ratio_category_median']):.1f}x the usual "
                           f"{tx.at[i, 'category']} payment")
        elif ratio >= 1.5:
            reasons.append(f"{ratio:.1f}x the usual payment to {who} (typical {mur(r['cp_median'])})")
        elif r["is_weekend"]:
            reasons.append("Weekend payment outside normal pattern")
        else:
            reasons.append("Unusual combination of amount, payee and timing")
        typical.append(float(r["cp_median"]))
    out["reason"] = reasons
    out["typical"] = typical
    out["detected_by"] = np.where(out["rule_flag"] & out["model_flag"], "rule+model",
                                  np.where(out["rule_flag"], "rule", "model"))
    return out


def find_duplicates(ledger: Ledger) -> list[dict[str, Any]]:
    tx = ledger.tx
    gid = duplicate_groups(tx)
    groups = []
    for key, g in tx[gid.notna()].groupby(gid[gid.notna()]):
        groups.append({"key": key, "date": str(g["date"].iloc[0].date()), "amount": float(g["amount"].iloc[0]),
                       "counterparty": g["counterparty"].iloc[0] or g["description"].iloc[0],
                       "direction": g["direction"].iloc[0], "count": int(len(g)),
                       "transaction_ids": g["id"].astype(str).tolist()})
    return groups


def suggest_category(description: str, direction: str) -> dict[str, Any] | None:
    lm = categoriser_model()
    if not lm.ok or not description:
        return None
    text = f"{direction} {description}".lower()
    proba = lm.model.predict_proba(pd.DataFrame({"text": [text]}))[0]
    classes = lm.model.classes_
    order = np.argsort(proba)[::-1][:3]
    return {"category": str(classes[order[0]]), "confidence": round(float(proba[order[0]]), 3),
            "alternatives": [{"category": str(classes[i]), "confidence": round(float(proba[i]), 3)} for i in order[1:]],
            "model_version": lm.meta["version"]}
