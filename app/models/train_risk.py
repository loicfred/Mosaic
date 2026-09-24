"""Train the late-delivery and low-review classifiers and save them with metadata.

Run from ``AI/``: ``python -m app.models.train_risk``
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib

from app.config import ALL_DATASET_FILES, DATASETS_DIR, MODELS_DIR, SPLIT_DATE, TEST_END_DATE
from app.data.olist import dataset_hashes
from app.data.orders import build_order_features
from app.models import risk

MODEL_VERSION_SUFFIX = "hgb-v1"
LIMITATIONS = {
    "late_delivery": [
        "Scores are ranking signals from a class-balanced model, not calibrated probabilities.",
        "Late orders purchased near the end of the data may still be undelivered, so recent late rates are under-counted.",
        "Seller history uses earlier orders by purchase date; a prior order's outcome may not have been known yet at that time.",
        "Feature importance measures association on held-out data, not cause.",
        "Trained on a Brazilian marketplace (Olist, 2017-2018); it describes that data only.",
    ],
    "low_review": [
        "Scores are ranking signals from a class-balanced model, not calibrated probabilities.",
        "Predicts after delivery: delivery outcome is an input, so it cannot be used at purchase time.",
        "Orders without a review are excluded from training; reviewers may differ from non-reviewers.",
        "Lateness and low reviews move together in this data; that is an association, not proof of cause.",
        "Trained on a Brazilian marketplace (Olist, 2017-2018); it describes that data only.",
    ],
}


def artifact_paths(models_dir: Path, name: str) -> tuple[Path, Path]:
    return models_dir / f"{name}.joblib", models_dir / f"{name}.json"


def train_all(
    datasets_dir: Path = DATASETS_DIR,
    models_dir: Path = MODELS_DIR,
    split_date: str = SPLIT_DATE,
    test_end: str = TEST_END_DATE,
) -> dict[str, dict]:
    features = build_order_features(datasets_dir)
    hashes = dataset_hashes(datasets_dir, ALL_DATASET_FILES)
    models_dir.mkdir(parents=True, exist_ok=True)

    metadata = {}
    for name, spec in risk.MODEL_SPECS.items():
        train, test = risk.temporal_split(spec.population(features.frame), split_date, test_end)
        model = risk.fit(spec, train)
        meta = {
            "model_version": f"{name}-{MODEL_VERSION_SUFFIX}",
            "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "label": spec.label,
            "prediction_time": spec.prediction_time,
            "split_date": split_date,
            "test_end": test_end,
            "dataset_hashes": hashes,
            "feature_names": spec.features,
            "categorical_features": spec.categorical,
            "evaluation": risk.evaluate(model, spec, test),
            "importances": risk.feature_importances(model, spec, test),
            "exclusions": features.exclusions,
            "limitations": LIMITATIONS[name],
        }
        artifact, meta_path = artifact_paths(models_dir, name)
        joblib.dump(model, artifact)
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        metadata[name] = meta
    return metadata


def main() -> None:
    for name, meta in train_all().items():
        ev = meta["evaluation"]
        print(f"{name}: train={ev['n_train']:,} test={ev['n_test']:,} base_rate={ev['base_rate']:.3f} "
              f"roc_auc={ev['roc_auc']:.3f} avg_precision={ev['average_precision']:.3f} "
              f"top10%: precision={ev['top_10pct']['precision']:.3f} recall={ev['top_10pct']['recall']:.3f}")
        print("  top features:", ", ".join(f"{i['feature']} ({i['auc_drop_mean']:.3f})" for i in meta["importances"][:5]))
    print(f"Saved to {MODELS_DIR}")


if __name__ == "__main__":
    main()
