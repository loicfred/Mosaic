"""Model names and their saved artifacts: ``<name>.joblib`` plus ``<name>.json`` metadata in the models folder."""
import json
from pathlib import Path

import joblib

SALES_MODEL = "sales_forecast"
LATE_MODEL = "late_delivery"
REVIEW_MODEL = "low_review"
CASHFLOW_MODEL = "cashflow_stress"
MODEL_NAMES = (SALES_MODEL, LATE_MODEL, REVIEW_MODEL, CASHFLOW_MODEL)


def save_artifact(models_dir: Path, name: str, model: object, metadata: dict) -> None:
    models_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, models_dir / f"{name}.joblib")
    (models_dir / f"{name}.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def load_artifact(models_dir: Path, name: str) -> tuple[object | None, dict | None]:
    artifact, metadata = models_dir / f"{name}.joblib", models_dir / f"{name}.json"
    if not artifact.exists() or not metadata.exists():
        return None, None
    return joblib.load(artifact), json.loads(metadata.read_text(encoding="utf-8"))
