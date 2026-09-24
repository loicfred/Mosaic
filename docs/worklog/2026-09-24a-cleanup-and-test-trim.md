# 2026-09-24 — Clean-up of duplicated code and low-value tests

Author: Claude

Behaviour-preserving clean-up of `AI/app` and the Java site, plus a trim of `AI/tests`.

Python (`AI/app`):
- One implementation each, where there were two: `opportunities.group_rates` and `opportunities.compare_with_business` (previously copied in `trends.py` and as `opportunities._check`), `caveats.rate_rising` with an optional threshold (was also `rate_rising_by`), `populations.monthly_rate` (behind `delivery.monthly_late_rate` and `reviews.monthly_low_review_rate`), `risk.rank` (behind `delivery.score_open_orders` and `reviews.score_unreviewed`), `trends.group_value` (was `satisfaction._share` and a lambda in `seller_base`), `cashflow._stress_rate`, and `trends.sold` (was also `breakdowns._sold`).
- `app/models/__init__.py` now holds `save_artifact` and `load_artifact`; the three trainers and `main.py` use them instead of their own joblib/json code (`load_artifact` moved out of `app/api/deps.py`).
- Removed single-use helpers and dead parameters: `business_profile.MIX_BY` (an identity map), `trends._head`, the unused `triggered` argument of `trends.change_check`, `train_risk.artifact_paths`, `risk._n_train`, `train_cashflow._next_month` (now `sales.forecast_months`), `get_sales_categories._without_series`, and the build-then-patch body in `get_sales_opportunities.py`.
- The nine trend routes (`delivery`, `reviews`, `sellers` × `trend`, `opportunities`, `caveats`) are registered from one table in `app/api/get_trends.py`, replacing nine near-identical modules; `name=` keeps their OpenAPI operationIds, and `/openapi.json` is byte-identical to before. `.claude/CLAUDE.md` now allows this exception to one module per route, as agreed with the user.
- Verified by snapshotting all 37 GET/POST responses on the real Olist data before and after: byte-identical.

Tests (`AI/tests`): 170 → 145, 47 s → 23 s. Removed tests of features that no longer exist (`explain` flag, `/api/ai/health`), of FastAPI's own 422 validation, a test that asserted nothing when its `if` was false, and tests that re-read constants; merged the three trend-route tests per measure and the model tests that each refitted the same model. The double-counting, zero-denominator, period, 503/409 and missing-file tests are kept.

Java:
- `service/ai/CheckedWriter` is now the abstract base of `InvestmentAdvisor`, `CaveatWriter`, `TrendAdvisor`, `TrendCaveatWriter` and `ScenarioNarrator`: one `explain(figures)` holds the fixed-text / model / number-check flow each class had copied. `ScenarioNarrator` overrides `allowedNumbers` to keep accepting figures from the raw scenario JSON. The advisors' `advise` is now the inherited `explain`, and their `evidence` is the former `prompt` (it had been a one-line alias).
- `Narrative` is its own file instead of a record nested in `ScenarioNarrator`.
- `OverviewAiController` and `TrendAiController` merged into `controller/api/AiButtonsController.java`; the URLs are unchanged.
- The two caveat writers share `CheckedWriter.checkList`; `PanelTools` has `last(rows, n)` and `dates(event)` helpers for code it repeated.
- `ScenarioNarrator` was briefly deleted as unused, then restored from git once `docs/superpowers/plans/2026-09-23-trend-pages.md` showed it is kept for phase 2; its chatbot entry in `config/ai/agents.json` is identical to the committed one.
- Verified: `OpportunityImpl` `mvnw.cmd -o install` 80 tests passed; `OpportunityApp` `mvnw.cmd -o test` 24 tests passed, `PagesRenderTest` included.

One Python copy, as the user asked:
- The Python project moved from `AI/` to `Java/OpportunityApp/config/py/mosaic/` (code, tests, datasets, models, requirements, README, `.gitignore`, `AI.iml`), and `AI/` was removed. The folder's previous mirror (`app/` older than this session's clean-up, `datasets/` and `models/` identical to `AI/`) was replaced. Its uv `.venv` (Python 3.12, same scikit-learn 1.9.1, pandas 2.3.3, numpy 2.5.3 as the old one) is the one used now.
- `.claude/hooks/mirror-python.ps1` and its `Stop` entry were removed; `.claude/hooks/package-python.ps1` and the `generate-resources` zip step in `Java/OpportunityImpl/pom.xml` build `mosaic-python.zip` from the new `app/` (62 files, checked).
- `PythonApiLauncher` no longer replaces `app/` when the folder is the source project (it has `requirements.txt`); `BusinessDatabase` never exports into its own source folder, which would rewrite the original CSVs and make every model answer 409. New tests: `PythonApiLauncherTest.theSourceProjectsAppIsNeverReplacedButAnInstalledOneIs`, `BusinessDatabaseTest.theOriginalFilesAreNeverOverwrittenWhenTheyAreTheExportFolder`.
- `ModuleHome` and `application.properties` read the Olist CSVs from `config/py/mosaic/datasets`; `.idea/modules.xml` points at the moved `AI.iml`.
- `Java/OpportunityApp/.gitignore`: dropped the `config/py/` rule, and anchored `data/` to `/data/`. The unanchored rule had also hidden `src/main/java/.../data/` (`BusinessDatabase`, `CsvImport`, `CsvReader`) and its tests, which were never committed; they now show as untracked, to be committed.
- Verified after the move: Python `pytest` 145 passed from the new folder; all 37 API responses byte-identical to the start of the session (so the models still accept the datasets); `OpportunityImpl` install 81 tests passed, `OpportunityApp` 25 passed.
- `.claude/CLAUDE.md`, `Java/OpportunityApp/README.md`, the Python README, `docs/code-organisation.md`, `docs/frontend-brief.md` and `docs/requirements.md` name the new location. Earlier worklog entries and plans keep the paths they had.
