"""Train and evaluate the 30-day cash-pressure early-warning model.

Problem framing
---------------
Target: will the business's cash balance fall below 14 days of committed
outflows at any point in the next 30 days?

Scope: the model is only used when the business is NOT already below that
threshold (buffer_days >= 14). When cash is already below it, simple arithmetic
answers the question, so the deterministic engine handles that case and we do
not dress it up as a prediction.

Evaluation
----------
* Group-aware split: test businesses never appear in training.
* 5-fold GroupKFold cross-validation on the training businesses.
* A naive rule-of-thumb baseline (lower buffer_days = riskier) is reported next
  to every model so the value added by ML is visible.
* Temporal check: train on earlier as-of dates, test on later dates of unseen
  businesses.
* Calibration (Brier score + reliability bins) because probabilities are shown
  to users.

Usage:
    python ml/train_cash_pressure.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.calibration import calibration_curve
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupKFold, GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

UTC = timezone.utc  # datetime.UTC needs Python 3.11+

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.analytics.features import (  # noqa: E402
    BUFFER_DAYS_THRESHOLD,
    FEATURE_LABELS,
    FEATURE_NAMES,
    HORIZON_DAYS,
)

PANEL = ROOT / "data" / "synthetic" / "cash_pressure_panel.csv"
OUT_DIR = ROOT / "models" / "cash_pressure"
SEED = 42
TEMPORAL_CUTOFF = "2025-04-01"


def make_lr(c: float = 1.0) -> Pipeline:
    return Pipeline([("scale", StandardScaler()),
                     ("clf", LogisticRegression(C=c, max_iter=5000))])


def make_hgb() -> HistGradientBoostingClassifier:
    return HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=250,
                                          l2_regularization=1.0, random_state=SEED)


def metrics_at(y: np.ndarray, p: np.ndarray, thr: float) -> dict:
    pred = (p >= thr).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "threshold": round(float(thr), 4),
        "precision": round(float(precision_score(y, pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y, pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y, pred, zero_division=0)), 4),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }


def rank_metrics(y: np.ndarray, score: np.ndarray) -> dict:
    return {
        "roc_auc": round(float(roc_auc_score(y, score)), 4),
        "pr_auc": round(float(average_precision_score(y, score)), 4),
    }


def main() -> None:
    panel = pd.read_csv(PANEL, parse_dates=["as_of"])
    elig = panel[panel["buffer_days"] >= BUFFER_DAYS_THRESHOLD].reset_index(drop=True)
    X, y, g = elig[FEATURE_NAMES], elig["label"].to_numpy(), elig["business_key"].to_numpy()

    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=SEED)
    tr_idx, te_idx = next(gss.split(X, y, g))
    Xtr, ytr, gtr = X.iloc[tr_idx], y[tr_idx], g[tr_idx]
    Xte, yte = X.iloc[te_idx], y[te_idx]

    # ---------------------------------------------------------------- CV model selection
    cv = GroupKFold(n_splits=5)
    candidates = {
        "logistic_regression_C0.1": lambda: make_lr(0.1),
        "logistic_regression_C1": lambda: make_lr(1.0),
        "hist_gradient_boosting": make_hgb,
    }
    cv_results: dict[str, dict] = {}
    oof: dict[str, np.ndarray] = {}
    for name, factory in candidates.items():
        pred = np.zeros(len(ytr))
        fold_auc = []
        for f_tr, f_va in cv.split(Xtr, ytr, gtr):
            m = factory().fit(Xtr.iloc[f_tr], ytr[f_tr])
            pred[f_va] = m.predict_proba(Xtr.iloc[f_va])[:, 1]
            fold_auc.append(roc_auc_score(ytr[f_va], pred[f_va]))
        oof[name] = pred
        cv_results[name] = {
            "roc_auc_mean": round(float(np.mean(fold_auc)), 4),
            "roc_auc_std": round(float(np.std(fold_auc)), 4),
            "pr_auc_oof": round(float(average_precision_score(ytr, pred)), 4),
            "brier_oof": round(float(brier_score_loss(ytr, pred)), 4),
        }
    baseline_cv = rank_metrics(ytr, -Xtr["buffer_days"].to_numpy())

    # Prefer the interpretable logistic model unless boosting is clearly better (> 0.01 AUC):
    # every prediction must be explainable feature-by-feature to an SME owner.
    lr_names = [n for n in candidates if n.startswith("logistic")]
    best_lr = max(lr_names, key=lambda n: cv_results[n]["roc_auc_mean"])
    chosen = best_lr
    if cv_results["hist_gradient_boosting"]["roc_auc_mean"] > cv_results[best_lr]["roc_auc_mean"] + 0.01:
        chosen = "hist_gradient_boosting"

    # ---------------------------------------------------------------- thresholds from OOF preds
    p_oof = oof[chosen]
    grid = np.linspace(0.05, 0.9, 86)
    f1s = [f1_score(ytr, (p_oof >= t).astype(int), zero_division=0) for t in grid]
    high_thr = float(grid[int(np.argmax(f1s))])
    # MODERATE: lowest threshold that still keeps precision >= 2x the base rate while
    # catching at least 85% of pressure events.
    mod_thr = high_thr
    for t in sorted(grid):
        if t >= high_thr:
            break
        r = recall_score(ytr, (p_oof >= t).astype(int))
        pr = precision_score(ytr, (p_oof >= t).astype(int), zero_division=0)
        if r >= 0.85 and pr >= 2 * ytr.mean():
            mod_thr = float(t)
    mod_thr = min(mod_thr, high_thr)

    # ---------------------------------------------------------------- final fit + test
    model = candidates[chosen]().fit(Xtr, ytr)
    p_te = model.predict_proba(Xte)[:, 1]
    frac_pos, mean_pred = calibration_curve(yte, p_te, n_bins=8, strategy="quantile")
    test = {
        **rank_metrics(yte, p_te),
        "brier": round(float(brier_score_loss(yte, p_te)), 4),
        "at_high_threshold": metrics_at(yte, p_te, high_thr),
        "at_moderate_threshold": metrics_at(yte, p_te, mod_thr),
        "calibration_bins": [
            {"mean_predicted": round(float(a), 4), "observed_rate": round(float(b), 4)}
            for a, b in zip(mean_pred, frac_pos, strict=True)
        ],
    }
    baseline_test = rank_metrics(yte, -Xte["buffer_days"].to_numpy())
    # Naive rule: flag when buffer < 21 days
    rule_pred = (Xte["buffer_days"].to_numpy() < 21).astype(float)
    baseline_test["rule_buffer_lt_21_days"] = metrics_at(yte, rule_pred, 0.5)

    # ---------------------------------------------------------------- temporal check
    tr_time = elig.iloc[tr_idx]
    te_time = elig.iloc[te_idx]
    early = tr_time[tr_time["as_of"] < TEMPORAL_CUTOFF]
    late = te_time[te_time["as_of"] >= TEMPORAL_CUTOFF]
    temporal = {}
    if len(late) and late["label"].nunique() == 2:
        tm = candidates[chosen]().fit(early[FEATURE_NAMES], early["label"])
        pt = tm.predict_proba(late[FEATURE_NAMES])[:, 1]
        temporal = {
            "train_until": TEMPORAL_CUTOFF, "test_from": TEMPORAL_CUTOFF,
            "n_train": int(len(early)), "n_test": int(len(late)),
            **rank_metrics(late["label"].to_numpy(), pt),
            "baseline_buffer_days": rank_metrics(late["label"].to_numpy(), -late["buffer_days"].to_numpy()),
        }

    # ---------------------------------------------------------------- explainability params
    explain: dict = {"method": "none"}
    if chosen.startswith("logistic"):
        scaler: StandardScaler = model.named_steps["scale"]
        clf: LogisticRegression = model.named_steps["clf"]
        explain = {
            "method": "logistic_contributions",
            "description": "contribution_i = coef_i * (x_i - mean_i) / std_i, in log-odds relative "
                           "to the average training business",
            "intercept": float(clf.intercept_[0]),
            "coefficients": {f: float(c) for f, c in zip(FEATURE_NAMES, clf.coef_[0], strict=True)},
            "means": {f: float(m) for f, m in zip(FEATURE_NAMES, scaler.mean_, strict=True)},
            "scales": {f: float(s) for f, s in zip(FEATURE_NAMES, scaler.scale_, strict=True)},
        }

    data_hash = hashlib.sha256(PANEL.read_bytes()).hexdigest()[:16]
    version = f"cash-pressure-{datetime.now(UTC):%Y%m%d}-{data_hash[:6]}"
    meta = {
        "model_name": "cash_pressure_30d",
        "version": version,
        "trained_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "sklearn_version": sklearn.__version__,
        "algorithm": chosen,
        "target": {
            "definition": f"Cash balance falls below {BUFFER_DAYS_THRESHOLD} days of committed outflows "
                          f"at any point in the next {HORIZON_DAYS} days",
            "horizon_days": HORIZON_DAYS,
            "eligibility": f"Applied only when current buffer_days >= {BUFFER_DAYS_THRESHOLD}; below that "
                           "the deterministic engine reports existing pressure instead of predicting it.",
        },
        "features": [{"name": f, "label": FEATURE_LABELS[f]} for f in FEATURE_NAMES],
        "bands": {"moderate_threshold": round(mod_thr, 4), "high_threshold": round(high_thr, 4)},
        "training_data": {
            "source": "SYNTHETIC SME panel generated by scripts/generate_synthetic.py (not real businesses)",
            "file": str(PANEL.relative_to(ROOT)),
            "sha256_prefix": data_hash,
            "n_rows_total": int(len(panel)),
            "n_rows_eligible": int(len(elig)),
            "n_businesses": int(elig["business_key"].nunique()),
            "n_train_rows": int(len(tr_idx)),
            "n_test_rows": int(len(te_idx)),
            "n_test_businesses": int(len(set(g[te_idx]))),
            "positive_rate_train": round(float(ytr.mean()), 4),
            "positive_rate_test": round(float(yte.mean()), 4),
        },
        "cross_validation": {"scheme": "GroupKFold(5) by business on training businesses",
                             "candidates": cv_results, "baseline_buffer_days": baseline_cv,
                             "selection_rule": "highest CV ROC-AUC logistic model unless boosting "
                                               "beats it by > 0.01"},
        "test": test,
        "baseline_test": baseline_test,
        "temporal_check": temporal,
        "explainability": explain,
        "limitations": [
            "Trained on synthetic data; performance on real SMEs is unknown until validated on real ledgers.",
            "The label depends on the synthetic generator's assumptions about shocks and owner behaviour.",
            "Cash-basis ledger only; accrual timing (e.g. unrecorded payables) is invisible to the model.",
        ],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, OUT_DIR / "model.joblib")
    (OUT_DIR / "metadata.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps({"chosen": chosen, "cv": cv_results, "baseline_cv": baseline_cv,
                      "test": {k: v for k, v in test.items() if k != "calibration_bins"},
                      "baseline_test": baseline_test, "temporal": temporal,
                      "bands": meta["bands"]}, indent=2))


if __name__ == "__main__":
    main()
