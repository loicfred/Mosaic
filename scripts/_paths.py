"""Make the backend package importable from scripts/ and ml/."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
DATA = ROOT / "data"
MODELS = ROOT / "models"

if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
