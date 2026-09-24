"""Benchmark on the hackathon-provided dataset data/public/small_business_cashflow.csv.

We report this honestly as an external benchmark. The file contains one monthly
snapshot per row with no business identifier and no history, so temporal
features (trends, collections drift, cash trajectory) cannot be computed. In our
tests every model scored close to chance on it; this script reproduces that.

Usage:
    python ml/benchmark_provided_csv.py
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

UTC = timezone.utc  # datetime.UTC needs Python 3.11+

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "data" / "public" / "small_business_cashflow.csv"
OUT = ROOT / "models" / "benchmark_provided_csv.json"


def main() -> None:
    df = pd.read_csv(CSV)
    y = df["cashflow_stress_next_month"].astype(int)
    X = pd.get_dummies(df.drop(columns=["record_id", "cashflow_stress_next_month", "month"]),
                       columns=["sector"], dtype=float)
    X["net_margin"] = (df["revenue_usd"] - df["opex_usd"]) / df["revenue_usd"]
    X["loan_to_revenue"] = df["loan_balance_usd"] / df["revenue_usd"]
    X["injections_to_revenue"] = df["owner_injections_usd"] / df["revenue_usd"]

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    models = {
        "logistic_regression": make_pipeline(StandardScaler(), LogisticRegression(max_iter=3000)),
        "random_forest": RandomForestClassifier(n_estimators=300, random_state=42, class_weight="balanced"),
        "hist_gradient_boosting": HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05,
                                                                 random_state=42),
    }
    results = {}
    for name, m in models.items():
        s = cross_val_score(m, X, y, cv=cv, scoring="roc_auc")
        results[name] = {"roc_auc_mean": round(float(s.mean()), 4), "roc_auc_std": round(float(s.std()), 4)}

    univariate = {}
    for c in X.columns:
        a = roc_auc_score(y, X[c])
        univariate[c] = round(float(max(a, 1 - a)), 4)

    report = {
        "dataset": str(CSV.relative_to(ROOT)),
        "sha256_prefix": hashlib.sha256(CSV.read_bytes()).hexdigest()[:16],
        "evaluated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "rows": int(len(df)),
        "positive_rate": round(float(y.mean()), 4),
        "months_covered": [str(df["month"].min()), str(df["month"].max())],
        "sectors": sorted(df["sector"].unique().tolist()),
        "scheme": "StratifiedKFold(5), ROC-AUC",
        "models": results,
        "best_univariate_auc": dict(sorted(univariate.items(), key=lambda kv: -kv[1])[:5]),
        "finding": "All models score close to chance (ROC-AUC ~0.5-0.6). Each row is an independent "
                   "snapshot without a business identifier or history, so trend features cannot be "
                   "derived. We therefore use this file as an external benchmark only and train the "
                   "production model on a documented synthetic panel with full ledger history.",
        "currency_note": "Amounts are USD; OpportunityOS works in MUR, which is another reason the "
                         "production model uses only scale-free ratio features.",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    assert np.isfinite(list(r["roc_auc_mean"] for r in results.values())).all()


if __name__ == "__main__":
    main()
