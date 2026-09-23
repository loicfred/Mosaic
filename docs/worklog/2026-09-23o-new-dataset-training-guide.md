# 2026-09-23 — New-dataset model training guide

Author: Claude

- Added "Training a model on a new dataset `.csv`" to `.claude/CLAUDE.md`, an 11-step procedure based on `app/forecast/train.py`, `app/models/train_risk.py`, `app/models/prepare.py`, `app/api/deps.py` and `app/main.py`.
- Recorded a pitfall: files in `ALL_DATASET_FILES` are hashed at startup, and a missing one crashes the API. A new optional dataset must be hashed only when present and merged into `app.state.dataset_hashes`. Otherwise `require_model` always returns 409.
- The API no longer trains at startup: `app/main.py` now builds `app = create_app()` (`auto_train` defaults to `False`). Models are trained once with `python -m app.forecast.train` and `python -m app.models.train_risk`. `prepare_models` is still used by `tests/test_opportunities.py`.
- `.claude/CLAUDE.md` now has a "Train once, then only use" rule and a "Train it once" step in the new-dataset procedure.
- `python -m pytest tests -q` from `AI/`: 98 passed.
- The copy in `Java/OpportunityApp/config/py/mosaic/app/main.py` still has `auto_train=True` and was left unchanged.
