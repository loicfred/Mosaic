"""Train the cash-flow stress classifier and save it with its evaluation.

Run from ``AI/``: ``python -m app.models.train_cashflow``
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib

from app.config import CASHFLOW_FILE, CASHFLOW_SPLIT_MONTH, DATASETS_DIR, MODELS_DIR
from app.data.cashflow import load_cashflow
from app.data.olist import dataset_hashes
from app.models import CASHFLOW_MODEL, cashflow as cf

MODEL_VERSION = "cashflow-hgb-v1"
LIMITATIONS = [
    "Synthetic practice data supplied for this hackathon, not real transactional or bank data;"
    " treat scores as a demonstration of the method, not a live risk assessment.",
    "Each row is an independent business-month snapshot; the same business cannot be tracked"
    " across months, so the model cannot learn a business's own trend.",
    "Evaluated on the last few months only, held out chronologically; a longer or more varied"
    " period could score differently.",
    "Scores are a ranking signal, not a calibrated probability of cash-flow stress.",
]


def train(
    datasets_dir: Path = DATASETS_DIR,
    models_dir: Path = MODELS_DIR,
    split_month: str = CASHFLOW_SPLIT_MONTH,
) -> dict:
    frame = load_cashflow(datasets_dir)
    test_end = _next_month(frame["month"].max())
    train_rows, test_rows = cf.temporal_split(frame, split_month, test_end)
    model = cf.fit(train_rows)
    evaluation = cf.evaluate(model, test_rows)

    metadata = {
        "model_version": MODEL_VERSION,
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "prediction_time": "at_snapshot",
        "split_date": split_month,
        "test_end": test_end,
        "dataset_hashes": dataset_hashes(datasets_dir, (CASHFLOW_FILE,)),
        "feature_names": cf.FEATURE_NAMES,
        "n_rows": len(frame),
        "evaluation": evaluation,
        "importances": [],
        "limitations": LIMITATIONS,
    }
    models_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, models_dir / f"{CASHFLOW_MODEL}.joblib")
    (models_dir / f"{CASHFLOW_MODEL}.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def _next_month(month: str) -> str:
    year, m = (int(part) for part in month.split("-"))
    year, m = (year + 1, 1) if m == 12 else (year, m + 1)
    return f"{year:04d}-{m:02d}"


def main() -> None:
    metadata = train()
    evaluation = metadata["evaluation"]
    print(
        f"{CASHFLOW_MODEL}: n_train={evaluation['n_train']} n_test={evaluation['n_test']} "
        f"base_rate={evaluation['base_rate']} roc_auc={evaluation['roc_auc']} "
        f"average_precision={evaluation['average_precision']}"
    )
    print(f"Saved to {MODELS_DIR / (CASHFLOW_MODEL + '.joblib')}")


if __name__ == "__main__":
    main()
