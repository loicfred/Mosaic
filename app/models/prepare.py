"""Train missing or stale models from the datasets the API is about to serve."""

import json
import logging
from pathlib import Path

from app.models import LATE_MODEL, REVIEW_MODEL, SALES_MODEL
from app.forecast.train import train as train_sales
from app.models.train_risk import train_all as train_risk

log = logging.getLogger(__name__)


def _current(models_dir: Path, name: str, hashes: dict[str, str]) -> bool:
    artifact = models_dir / f"{name}.joblib"
    metadata = models_dir / f"{name}.json"
    if not artifact.is_file() or not metadata.is_file():
        return False
    try:
        trained_on = json.loads(metadata.read_text(encoding="utf-8"))["dataset_hashes"]
    except (OSError, ValueError, KeyError, TypeError):
        return False
    return isinstance(trained_on, dict) and bool(trained_on) and all(hashes.get(file) == digest for file, digest in trained_on.items())


def prepare_models(datasets_dir: Path, models_dir: Path, hashes: dict[str, str]) -> None:
    if not _current(models_dir, SALES_MODEL, hashes):
        try:
            train_sales(datasets_dir, models_dir)
        except Exception:
            log.exception("Sales forecast training failed; analytics will continue without that model")

    if any(not _current(models_dir, name, hashes) for name in (LATE_MODEL, REVIEW_MODEL)):
        try:
            train_risk(datasets_dir, models_dir)
        except Exception:
            log.exception("Risk model training failed; analytics will continue without those models")
