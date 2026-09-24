"""Gradient-boosted classifiers for late delivery and low review risk.

Pure functions over the order feature table. Evaluation always uses a time-ordered holdout
so reported scores come from orders placed after every training order.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder

from app.data.orders import CATEGORICAL_FEATURES, DELIVERY_OUTCOME_FEATURES, PURCHASE_TIME_FEATURES

TOP_RISK_FRACTION = 0.10
RANDOM_STATE = 42


@dataclass(frozen=True)
class ModelSpec:
    name: str
    label: str
    features: list[str]
    prediction_time: str

    def population(self, frame: pd.DataFrame) -> pd.DataFrame:
        return frame[frame[self.label].notna()]

    @property
    def categorical(self) -> list[str]:
        return [f for f in self.features if f in CATEGORICAL_FEATURES]


MODEL_SPECS = {
    "late_delivery": ModelSpec(
        name="late_delivery", label="late", features=list(PURCHASE_TIME_FEATURES),
        prediction_time="at_purchase",
    ),
    "low_review": ModelSpec(
        name="low_review", label="low_review",
        features=list(PURCHASE_TIME_FEATURES) + list(DELIVERY_OUTCOME_FEATURES),
        prediction_time="after_delivery",
    ),
}


def temporal_split(frame: pd.DataFrame, split_date: str, test_end: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    start, end = pd.Timestamp(split_date), pd.Timestamp(test_end)
    train = frame[frame["purchase_ts"] < start]
    test = frame[(frame["purchase_ts"] >= start) & (frame["purchase_ts"] < end)]
    return train, test


def build_pipeline(spec: ModelSpec) -> Pipeline:
    categorical = spec.categorical
    encoder = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=np.nan)
    # Encoded categoricals come first in the transformed matrix, then the numeric passthrough.
    columns = ColumnTransformer(
        [("cat", encoder, categorical)], remainder="passthrough", verbose_feature_names_out=False
    )
    classifier = HistGradientBoostingClassifier(
        max_iter=300, learning_rate=0.05, max_leaf_nodes=31, class_weight="balanced",
        categorical_features=list(range(len(categorical))), random_state=RANDOM_STATE,
    )
    return Pipeline([("columns", columns), ("classifier", classifier)])


def fit(spec: ModelSpec, train: pd.DataFrame) -> Pipeline:
    model = build_pipeline(spec).fit(train[spec.features], train[spec.label].astype(int))
    model.n_train_ = int(len(train))  # kept with the artifact so evaluation can report it
    return model


def predict_risk(model: Pipeline, spec: ModelSpec, frame: pd.DataFrame) -> np.ndarray:
    return model.predict_proba(frame[spec.features])[:, 1]


def rank(model: Pipeline, name: str, candidates: pd.DataFrame, limit: int) -> pd.DataFrame:
    """The `limit` candidates the named model scores riskiest, with their `risk`."""
    scored = candidates.assign(risk=predict_risk(model, MODEL_SPECS[name], candidates))
    return scored.sort_values("risk", ascending=False).head(limit)


def evaluate(model: Pipeline, spec: ModelSpec, test: pd.DataFrame) -> dict:
    y_true = test[spec.label].astype(int).to_numpy()
    scores = predict_risk(model, spec, test)
    both_classes = len(np.unique(y_true)) == 2
    return {
        "n_train": int(getattr(model, "n_train_", 0)),
        "n_test": int(len(test)),
        "n_positive_test": int(y_true.sum()),
        "base_rate": float(y_true.mean()) if len(y_true) else None,
        "roc_auc": float(roc_auc_score(y_true, scores)) if both_classes else None,
        "average_precision": float(average_precision_score(y_true, scores)) if both_classes else None,
        "top_10pct": _top_fraction_metrics(y_true, scores),
    }


def _top_fraction_metrics(y_true: np.ndarray, scores: np.ndarray) -> dict:
    """Precision and recall if the business acts on the top 10% highest-risk orders."""
    if len(scores) == 0:
        return {"threshold": None, "flagged": 0, "precision": None, "recall": None}
    threshold = float(np.quantile(scores, 1 - TOP_RISK_FRACTION))
    flagged = scores >= threshold
    positives = y_true.sum()
    true_positives = int((flagged & (y_true == 1)).sum())
    return {
        "threshold": threshold,
        "flagged": int(flagged.sum()),
        "precision": true_positives / flagged.sum() if flagged.sum() else None,
        "recall": true_positives / positives if positives else None,
    }


def feature_importances(model: Pipeline, spec: ModelSpec, test: pd.DataFrame, top: int = 10) -> list[dict]:
    """Permutation importance on held-out data: association strength, not causal effect."""
    y_true = test[spec.label].astype(int)
    if len(np.unique(y_true)) < 2:
        return []
    result = permutation_importance(
        model, test[spec.features], y_true, scoring="roc_auc", n_repeats=5, random_state=RANDOM_STATE
    )
    order = np.argsort(result.importances_mean)[::-1][:top]
    return [
        {"feature": spec.features[i], "auc_drop_mean": float(result.importances_mean[i]),
         "auc_drop_std": float(result.importances_std[i])}
        for i in order
    ]
