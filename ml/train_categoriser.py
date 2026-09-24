"""Train the transaction category suggester (TF-IDF + logistic regression).

Used by the Data Health workflow to PROPOSE a category for uncategorised
transactions. Suggestions are never applied without user approval.

Training data:
  * descriptions from the SYNTHETIC panel (templated, so easy)
  * a small hand-written keyword lexicon (data/reference/category_lexicon.csv)
Evaluation:
  * held-out synthetic businesses (in-distribution, expected to be near-perfect)
  * a hand-written out-of-distribution set (data/eval/categoriser_handwritten.csv)
    that never appears in training - this is the honest number.

Usage:
    python ml/train_categoriser.py
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
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.pipeline import Pipeline

UTC = timezone.utc  # datetime.UTC needs Python 3.11+

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.taxonomy import CATEGORIES  # noqa: E402

TX = ROOT / "data" / "synthetic" / "panel_transactions.csv.gz"
LEXICON = ROOT / "data" / "reference" / "category_lexicon.csv"
OOD = ROOT / "data" / "eval" / "categoriser_handwritten.csv"
OUT_DIR = ROOT / "models" / "categoriser"
SEED = 42


def text_of(df: pd.DataFrame) -> pd.Series:
    return (df["direction"].astype(str) + " " + df["description"].astype(str)).str.lower()


def build() -> Pipeline:
    feats = ColumnTransformer([
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=1, sublinear_tf=True), "text"),
        ("word", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=1, sublinear_tf=True,
                                 token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z]+\b"), "text"),  # noqa: S106
    ])
    return Pipeline([("features", feats),
                     ("clf", LogisticRegression(C=4.0, max_iter=3000, class_weight="balanced"))])


def main() -> None:
    tx = pd.read_csv(TX, usecols=["business_key", "direction", "description", "category"])
    tx = tx[tx["category"].isin(CATEGORIES)]
    keys = tx["business_key"].unique()
    rng = np.random.default_rng(SEED)
    test_keys = set(rng.choice(keys, size=int(len(keys) * 0.2), replace=False))
    tr = tx[~tx["business_key"].isin(test_keys)]
    te = tx[tx["business_key"].isin(test_keys)]
    # Cap per category so frequent 'Sales' rows do not dominate.
    tr = pd.concat([g.sample(min(len(g), 3000), random_state=SEED) for _, g in tr.groupby("category")])
    lex = pd.read_csv(LEXICON)
    lex_rep = pd.concat([lex] * 20, ignore_index=True)  # upweight the small lexicon
    train = pd.concat([tr[["direction", "description", "category"]], lex_rep], ignore_index=True)
    train["text"] = text_of(train)

    model = build().fit(train[["text"]], train["category"])

    te = te.sample(min(len(te), 20_000), random_state=SEED).copy()
    te["text"] = text_of(te)
    p_te = model.predict(te[["text"]])
    ood = pd.read_csv(OOD)
    ood["text"] = text_of(ood)
    p_ood = model.predict(ood[["text"]])
    proba_ood = model.predict_proba(ood[["text"]]).max(axis=1)
    misses = ood.loc[p_ood != ood["category"], ["description", "category"]].assign(predicted=p_ood[p_ood != ood["category"]])

    data_hash = hashlib.sha256(TX.read_bytes() + LEXICON.read_bytes()).hexdigest()[:16]
    meta = {
        "model_name": "category_suggester",
        "version": f"categoriser-{datetime.now(UTC):%Y%m%d}-{data_hash[:6]}",
        "trained_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "sklearn_version": sklearn.__version__,
        "algorithm": "TF-IDF (char 2-5 + word 1-2) + LogisticRegression",
        "classes": sorted(model.classes_.tolist()),
        "training_data": {"synthetic_rows": int(len(tr)), "lexicon_rows": int(len(lex)),
                          "sha256_prefix": data_hash},
        "test_in_distribution": {
            "description": "held-out synthetic businesses (templated descriptions)",
            "n": int(len(te)),
            "accuracy": round(float(accuracy_score(te["category"], p_te)), 4),
            "macro_f1": round(float(f1_score(te["category"], p_te, average="macro")), 4),
        },
        "test_handwritten_ood": {
            "description": "hand-written descriptions never seen in training",
            "n": int(len(ood)),
            "accuracy": round(float(accuracy_score(ood["category"], p_ood)), 4),
            "macro_f1": round(float(f1_score(ood["category"], p_ood, average="macro")), 4),
            "mean_confidence": round(float(proba_ood.mean()), 4),
            "misclassified_examples": misses.head(10).to_dict(orient="records"),
        },
        "suggestion_policy": "Suggestions below 0.45 confidence are shown as 'needs review'; "
                             "no suggestion is applied without explicit approval.",
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, OUT_DIR / "model.joblib")
    (OUT_DIR / "metadata.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps({k: meta[k] for k in ("test_in_distribution", "test_handwritten_ood")}, indent=2))


if __name__ == "__main__":
    main()
