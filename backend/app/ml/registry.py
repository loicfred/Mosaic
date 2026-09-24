"""Loads the locally trained models and their metadata.

Models are plain scikit-learn artefacts produced by the scripts in ml/. If an
artefact is missing or was trained with a different scikit-learn version, the
service degrades gracefully: cash-pressure falls back to the deterministic
buffer rule, and anomaly/category suggestions are simply not offered.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import sklearn

from app.core.config import get_settings

log = logging.getLogger("opportunityos.ml")


@dataclass
class LoadedModel:
    name: str
    model: Any | None
    meta: dict[str, Any]
    status: str  # loaded | missing | version_mismatch | error
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.model is not None


def _load(name: str) -> LoadedModel:
    base: Path = get_settings().models_dir / name
    meta_path, model_path = base / "metadata.json", base / "model.joblib"
    if not model_path.exists() or not meta_path.exists():
        return LoadedModel(name, None, {}, "missing", "Run scripts/train_all.py to train local models.")
    meta = json.loads(meta_path.read_text())
    trained = meta.get("sklearn_version")
    if trained and trained.split(".")[:2] != sklearn.__version__.split(".")[:2]:
        return LoadedModel(name, None, meta, "version_mismatch",
                           f"Trained with scikit-learn {trained}, running {sklearn.__version__}. "
                           "Re-run scripts/train_all.py.")
    try:
        return LoadedModel(name, joblib.load(model_path), meta, "loaded")
    except Exception as exc:  # pragma: no cover - defensive
        log.exception("model load failed: %s", name)
        return LoadedModel(name, None, meta, "error", type(exc).__name__)


@lru_cache
def cash_pressure_model() -> LoadedModel:
    return _load("cash_pressure")


@lru_cache
def anomaly_model() -> LoadedModel:
    return _load("anomaly")


@lru_cache
def categoriser_model() -> LoadedModel:
    return _load("categoriser")


def benchmark_report() -> dict[str, Any] | None:
    p = get_settings().models_dir / "benchmark_provided_csv.json"
    return json.loads(p.read_text()) if p.exists() else None


def reset_cache() -> None:
    cash_pressure_model.cache_clear()
    anomaly_model.cache_clear()
    categoriser_model.cache_clear()
