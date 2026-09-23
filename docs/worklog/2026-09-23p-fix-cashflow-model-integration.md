# 2026-09-23 — Fix the cash-flow model integration

Author: Claude

- Reviewed commits `be3f241` and `efe7e64`, which add the `cashflow_stress` model on `small_business_cashflow.csv`.
- `be3f241` had retrained and committed `sales_forecast`, `late_delivery` and `low_review` on a copy of the Olist CSVs with different SHA-256 hashes, so those models returned 409 on machines with the canonical files. They were retrained on the canonical CSVs. The held-out evaluations are unchanged (late_delivery ROC-AUC 0.682, low_review 0.739, sales_forecast MAE 92,044.62).
- `/api/risk/cashflow/records` now returns 503 when the CSV is absent, and 503 when the model's held-out ROC-AUC is below `MIN_ROC_AUC` (0.6). The current artefact scores 0.53, so it is refused. `beats_baseline` is in `app/models/cashflow.py`. When the route is served, it scores only held-out months (`scored_months` in the response) and never training rows.
- The test fixture now has `CASHFLOW_ROWS_PER_MONTH = 12`. Before, the classifier had too few rows to split, which gave a constant ROC-AUC of 0.5 that no test caught. Added tests for the near-chance refusal and for `beats_baseline`.
- Updated `AI/README.md` and FR-12 in `docs/requirements.md`, and added three model rules to `.claude/CLAUDE.md` (retrain only your model; gate models that do not beat their baseline; copy `AI/app` into the config folder).
- Rebuilt `mosaic-python.zip` and copied `AI/app` into `Java/OpportunityApp/config/py/mosaic/app` (identical by `diff -rq`). The site's own models were left unchanged.
- Verified: `python -m pytest tests -q` from `AI/` gives 109 passed. `python -m app.main` served `/api/health`, `/openapi.json`, `/api/sales/forecast` and `/api/risk/cashflow/summary` with 200. The cash-flow CSV is not on this machine, so the cash-flow model could not be retrained or served here.
