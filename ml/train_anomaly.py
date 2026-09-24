"""Train and evaluate the transaction anomaly detector (Isolation Forest).

Unsupervised model; evaluated against anomalies deliberately injected into the
SYNTHETIC panel (unusual amounts and large payments to never-seen payees).
Duplicate payments are handled by a deterministic rule instead of the model,
and that rule is evaluated separately.

Usage:
    python ml/train_anomaly.py
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
from sklearn.ensemble import IsolationForest
from sklearn.metrics import average_precision_score, f1_score, precision_score, recall_score, roc_auc_score

UTC = timezone.utc  # datetime.UTC needs Python 3.11+

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.analytics.anomalies import (  # noqa: E402
    ANOMALY_FEATURES,
    anomaly_features,
    duplicate_groups,
    final_flags,
    materiality,
    rule_flags,
)
from app.core.taxonomy import group_of  # noqa: E402

TX = ROOT / "data" / "synthetic" / "panel_transactions.csv.gz"
OUT_DIR = ROOT / "models" / "anomaly"
SEED = 42


def main() -> None:
    tx = pd.read_csv(TX, parse_dates=["date"])
    tx["group"] = tx["category"].map(group_of)
    parts = []
    for key, g in tx.groupby("business_key"):
        f = anomaly_features(g)
        f["business_key"] = key
        f["rule"] = rule_flags(f, g["category"]).astype(int)
        f["amount"] = g.loc[f.index, "amount"]
        f["materiality"] = materiality(g)
        f["target"] = g.loc[f.index, "injected_anomaly"].isin(["unusual_amount", "new_payee"]).astype(int)
        parts.append(f)
    feats = pd.concat(parts)
    keys = feats["business_key"].unique()
    rng = np.random.default_rng(SEED)
    test_keys = set(rng.choice(keys, size=int(len(keys) * 0.2), replace=False))
    tr = feats[~feats["business_key"].isin(test_keys)]
    te = feats[feats["business_key"].isin(test_keys)]

    model = IsolationForest(n_estimators=300, max_samples=4096, contamination="auto", random_state=SEED)
    model.fit(tr[ANOMALY_FEATURES])
    s_tr = -model.score_samples(tr[ANOMALY_FEATURES])
    s_te = -model.score_samples(te[ANOMALY_FEATURES])

    grid = np.quantile(s_tr, np.linspace(0.90, 0.999, 100))
    f1s = [f1_score(tr["target"], (s_tr >= t).astype(int), zero_division=0) for t in grid]
    thr = float(grid[int(np.argmax(f1s))])
    pred = (s_te >= thr).astype(int)

    def prf(y, p):
        return {"precision": round(float(precision_score(y, p, zero_division=0)), 4),
                "recall": round(float(recall_score(y, p, zero_division=0)), 4),
                "f1": round(float(f1_score(y, p, zero_division=0)), 4), "flag_rate": round(float(p.mean()), 5)}

    rule_only = prf(te["target"], te["rule"].to_numpy())
    combined = prf(te["target"], ((s_te >= thr) | (te["rule"] == 1)).astype(int).to_numpy())
    used = final_flags(te, pd.Series(s_te >= thr, index=te.index), te["rule"] == 1, te["amount"], 0.0)
    used &= te["amount"] >= te["materiality"]
    production = prf(te["target"], used.astype(int).to_numpy())

    # Duplicate rule evaluation on the test businesses
    dup_eval = {}
    tte = tx[tx["business_key"].isin(test_keys)].copy()
    dup_flag = tte.groupby("business_key", group_keys=False).apply(lambda g: duplicate_groups(g).notna())
    truth = tte["injected_anomaly"].eq("duplicate_payment")
    # The rule flags both copies; count a hit when the injected copy is flagged.
    dup_eval = {
        "recall_injected_duplicates": round(float(dup_flag[truth].mean()), 4) if truth.any() else None,
        "flagged_rows": int(dup_flag.sum()),
        "injected_duplicates": int(truth.sum()),
    }

    data_hash = hashlib.sha256(TX.read_bytes()).hexdigest()[:16]
    meta = {
        "model_name": "transaction_anomaly",
        "version": f"anomaly-{datetime.now(UTC):%Y%m%d}-{data_hash[:6]}",
        "trained_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "sklearn_version": sklearn.__version__,
        "algorithm": "IsolationForest(n_estimators=300, max_samples=4096)",
        "features": ANOMALY_FEATURES,
        "threshold": round(thr, 6),
        "training_data": {
            "source": "SYNTHETIC SME panel (outflows, excluding financing flows)",
            "sha256_prefix": data_hash,
            "n_train": int(len(tr)), "n_test": int(len(te)),
            "n_test_businesses": len(test_keys),
            "injected_rate_test": round(float(te["target"].mean()), 5),
        },
        "test": {
            "roc_auc": round(float(roc_auc_score(te["target"], s_te)), 4),
            "pr_auc": round(float(average_precision_score(te["target"], s_te)), 4),
            "precision": round(float(precision_score(te["target"], pred, zero_division=0)), 4),
            "recall": round(float(recall_score(te["target"], pred, zero_division=0)), 4),
            "f1": round(float(f1_score(te["target"], pred, zero_division=0)), 4),
            "flag_rate": round(float(pred.mean()), 5),
        },
        "rule_only_test": rule_only,
        "combined_model_or_rule_test": combined,
        "production_flags_test": production,
        "production_rule": "(model flag AND larger than usual) OR 4x rule, AND amount >= 1% of average monthly "
                           "outflows (materiality)",
        "rule": "amount >= 4x payee median with >= 3 prior payments (tax and payroll excluded)",
        "duplicate_rule": dup_eval,
        "limitations": [
            "Ground truth exists only for anomalies we injected into synthetic data; real-world "
            "anomalies are more varied.",
            "Flags are prompts for review, never automatic corrections.",
        ],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, OUT_DIR / "model.joblib")
    (OUT_DIR / "metadata.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps({k: meta[k] for k in ("threshold", "test", "rule_only_test", "combined_model_or_rule_test",
                                          "production_flags_test", "duplicate_rule")}, indent=2))


if __name__ == "__main__":
    main()
