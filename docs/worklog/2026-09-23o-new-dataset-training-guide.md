# 2026-09-23 — New-dataset model training guide

Author: Claude

- Added "Training a model on a new dataset `.csv`" to `.claude/CLAUDE.md`, an 11-step procedure based on `app/forecast/train.py`, `app/models/train_risk.py`, `app/models/prepare.py`, `app/api/deps.py` and `app/main.py`.
- Recorded a pitfall: files in `ALL_DATASET_FILES` are hashed at startup, and a missing one crashes the API. A new optional dataset must be hashed only when present and merged into `app.state.dataset_hashes`. Otherwise `require_model` always returns 409.
- Only the documentation changed, so no tests were run.
