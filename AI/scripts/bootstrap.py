"""One-command setup for the demo.

    python scripts/bootstrap.py

1. creates backend/.env with random secrets if it does not exist
2. applies database migrations (Alembic)
3. trains the local models if they are missing or were built with another scikit-learn version
4. seeds the synthetic demo tenants
"""

from __future__ import annotations

import json
import secrets
import subprocess
import sys

import sklearn
from _paths import BACKEND, MODELS, ROOT


def ensure_env() -> None:
    env = BACKEND / ".env"
    if env.exists():
        print("backend/.env exists - keeping it")
        return
    text = (BACKEND / ".env.example").read_text()
    text = text.replace("CHANGE_ME_to_a_random_string_of_at_least_32_characters", secrets.token_urlsafe(48))
    text = text.replace("CHANGE_ME_random_hex", secrets.token_hex(16))
    text = text.replace("opportunityos:CHANGE_ME@", "opportunityos:change-me-locally@")
    env.write_text(text)
    print("created backend/.env with random secrets (edit DATABASE_URL if your password differs)")


def models_ok() -> bool:
    for name in ("cash_pressure", "anomaly", "categoriser"):
        meta = MODELS / name / "metadata.json"
        if not meta.exists() or not (MODELS / name / "model.joblib").exists():
            return False
        trained = json.loads(meta.read_text()).get("sklearn_version", "")
        if trained.split(".")[:2] != sklearn.__version__.split(".")[:2]:
            print(f"{name}: trained with scikit-learn {trained}, installed {sklearn.__version__} - retraining")
            return False
    return True


def main() -> None:
    ensure_env()
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=BACKEND, check=True)  # noqa: S603
    if not models_ok():
        subprocess.run([sys.executable, "scripts/train_all.py"], cwd=ROOT, check=True)  # noqa: S603
    subprocess.run([sys.executable, "scripts/seed_demo.py"], cwd=ROOT, check=True)  # noqa: S603
    print("\nReady. Start the API:  cd backend && python -m uvicorn app.main:app --port 8000")
    print("Start the web app:     cd frontend && npm install && npm run dev")


if __name__ == "__main__":
    main()
