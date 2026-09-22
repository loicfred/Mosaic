"""Model artifact loading and the 503/409 guards shared by every model-backed route."""
import json
from pathlib import Path

import joblib
from fastapi import HTTPException, Request


def load_artifact(models_dir: Path, name: str) -> tuple[object | None, dict | None]:
    artifact, metadata = models_dir / f"{name}.joblib", models_dir / f"{name}.json"
    if not artifact.exists() or not metadata.exists():
        return None, None
    return joblib.load(artifact), json.loads(metadata.read_text(encoding="utf-8"))


def require_model(request: Request, name: str, train_command: str) -> tuple[object, dict]:
    """Return (model, metadata) or raise 503 (not trained) / 409 (data changed since training)."""
    model, metadata = request.app.state.models.get(name, (None, None))
    if model is None:
        raise HTTPException(503, f"No trained '{name}' model found. Run: {train_command}")
    current = request.app.state.dataset_hashes
    trained_on = metadata["dataset_hashes"]
    if any(current.get(file) != digest for file, digest in trained_on.items()):
        raise HTTPException(409, f"Dataset files changed since '{name}' was trained; retrain first: {train_command}")
    return model, metadata
