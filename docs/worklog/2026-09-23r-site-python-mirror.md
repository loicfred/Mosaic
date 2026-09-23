# 2026-09-23 — The site's Python folder mirrors AI/

Author: Claude

- `Java/OpportunityApp/config/py/mosaic` is now an exact mirror of `AI/` (`app`, `datasets`, `models`); only its `.venv` is its own. This replaces the database export and the models trained on it with the original CSVs and `AI/models`, and adds `small_business_cashflow.csv` and `cashflow_stress`.
- Added `.claude/hooks/mirror-python.ps1` (robocopy `/MIR`, `__pycache__` excluded), registered as a second Claude `Stop` hook in `.claude/settings.json`.
- `BusinessDatabase` exports only when a table's file is missing from the mirror's `datasets/`. All of them are present, so it no longer exports; if it does, the next mirror restores the originals.
- Updated `.claude/CLAUDE.md` (the mirror rule replaces "copy `AI/app`, never `AI/models`"), `Java/OpportunityApp/README.md` and `docs/code-organisation.md`.
- Verified: MD5 comparison of `app` (48 files), `datasets` (14) and `models` (8) shows no differences. With the mirror's `.venv`, `create_app(datasets, models)` loaded all four models: `/api/sales/forecast`, `/api/risk/delivery/summary`, `/api/risk/reviews/summary` and `/api/risk/cashflow/summary` returned 200, and `/api/risk/cashflow/records` returned 503 (the ROC-AUC gate). The Spring site itself was not restarted.
