"""Cash-flow stress classifier: split, fit, evaluate, predict.

Each row is an independent business-month snapshot (no id links a business across months),
so there is no per-business population/label rule like ``risk.py``'s — every row already has
a label. The split is chronological by month instead of by a business id, since a model that
only ever saw earlier months is the honest simulation of predicting a future month.
"""
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

LABEL = "cashflow_stress_next_month"
CATEGORICAL_FEATURES = ["sector"]
NUMERIC_FEATURES = [
    "employees", "revenue_usd", "opex_usd", "operating_margin", "accounts_receivable_days",
    "inventory_days", "loan_balance_usd", "owner_injections_usd", "calendar_month",
]
FEATURE_NAMES = CATEGORICAL_FEATURES + NUMERIC_FEATURES
TOP_SHARE = 0.10


def temporal_split(frame: pd.DataFrame, split_month: str, test_end: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Train on months before ``split_month``; test on ``[split_month, test_end)``."""
    train = frame[frame["month"] < split_month]
    test = frame[(frame["month"] >= split_month) & (frame["month"] < test_end)]
    return train, test


def _build_pipeline() -> Pipeline:
    preprocessor = ColumnTransformer(
        [
            (
                "cat",
                Pipeline([
                    ("impute", SimpleImputer(strategy="constant", fill_value="missing")),
                    ("onehot", OneHotEncoder(handle_unknown="ignore")),
                ]),
                CATEGORICAL_FEATURES,
            ),
            ("num", "passthrough", NUMERIC_FEATURES),
        ],
        sparse_threshold=0,
    )
    classifier = HistGradientBoostingClassifier(class_weight="balanced", random_state=0)
    return Pipeline([("prep", preprocessor), ("clf", classifier)])


def fit(train: pd.DataFrame) -> Pipeline:
    model = _build_pipeline()
    model.fit(train[FEATURE_NAMES], train[LABEL])
    model.n_train_ = len(train)
    return model


def predict_risk(model: Pipeline, frame: pd.DataFrame) -> np.ndarray:
    return model.predict_proba(frame[FEATURE_NAMES])[:, 1]


def evaluate(model: Pipeline, test: pd.DataFrame) -> dict:
    y_true = test[LABEL].to_numpy()
    n_test = len(test)
    n_positive = int(y_true.sum()) if n_test else 0
    single_class = n_test == 0 or len(np.unique(y_true)) < 2
    scores = predict_risk(model, test) if n_test else np.array([])

    roc_auc = None if single_class else float(roc_auc_score(y_true, scores))
    average_precision = None if single_class else float(average_precision_score(y_true, scores))

    top_n = max(1, int(np.ceil(n_test * TOP_SHARE))) if n_test else 0
    order = np.argsort(-scores)[:top_n] if top_n else np.array([], dtype=int)
    threshold = float(scores[order[-1]]) if top_n else None
    precision = float(y_true[order].mean()) if top_n else None
    recall = float(y_true[order].sum() / n_positive) if n_positive else None

    return {
        "n_train": getattr(model, "n_train_", None),
        "n_test": n_test,
        "n_positive_test": n_positive,
        "base_rate": n_positive / n_test if n_test else None,
        "roc_auc": roc_auc,
        "average_precision": average_precision,
        "top_10pct": {"threshold": threshold, "flagged": int(top_n), "precision": precision, "recall": recall},
    }
