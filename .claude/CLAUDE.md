# AGENTS.md — FinTech Hackathon Project

## Shared agent instructions

**Codex and Claude share these instructions.** Both assistants must inspect the current repository before editing, preserve each other's work and leave the project in a state that another session can continue. The root `AGENTS.md` is a symbolic link to this file so both tools use one source of truth.

Keep guidance, requirements and history separate:

- This file defines durable project context and rules for working in the repository. Do not turn it into a progress log.
- Put product or implementation documentation in `docs/` when that directory exists. Do not invent files, paths, endpoints or completed features in documentation; verify each referenced artefact first.
- Git history records completed changes. The final response records what changed, what was verified and any remaining limitations. Do not leave essential handoff information only in chat when it belongs in project documentation.

**Three files, three jobs, as in SolarERP. Nothing belongs in two of them, and nothing may end only in the chat.**

- **This file — the guidelines.** How to work on the code. No status, no history, no requirements.
- **`docs/requirements.md` — the requirements and the open list.** Actors, scope, the FR/NFR tables and `## Outstanding work`. Add an open item the moment it appears and remove it the moment it is done, in the same pass as the job. Whatever is still open when a session stops is written there before answering.
- **`docs/worklog/` — what is finished, with dates.** One file per session, named `YYYY-MM-DD<letter>-<kebab-title>.md`, opening with the dated `#` heading and then `Author: Codex` or `Author: Claude`; `docs/worklog.md` holds only this convention. **Write an entry at the end of every session.** Never read the whole log: `ls docs/worklog/`, then `grep` for the session.
- **Every class, method, file and path named in these files must exist.** Check before writing it down, and re-check the nearby ones after a rename.

## Purpose and scope

This file carries the project context into new Codex and Claude sessions. It is the project's development guide and brief, not a claim that the application has already been implemented.

Inspect the repository, existing instructions, dependency manifests and current work before changing anything. Preserve existing user changes. The user's latest explicit instructions take precedence over this brief.

## Working rules

- Read the relevant files completely before editing them. Search for existing patterns and reuse them instead of introducing a competing convention.
- Check `git status` before and after work. Treat all pre-existing modifications and untracked files as user-owned; never discard or rewrite them unless explicitly asked.
- Make minimal, targeted edits. Do not reformat, rename or reorganise unrelated code. Never use destructive Git commands to clean the workspace.
- Prefer the simplest implementation that completes one end-to-end user journey. Avoid speculative abstractions, duplicate helpers, premature services and dependencies with no immediate use.
- Keep functions focused on one named task. Use descriptive names, early returns and small cohesive modules. Comments should explain a non-obvious reason or constraint, not restate the code.
- Follow the established style in the file being changed. Remove debug logging, dead code and unused imports introduced by the task before finishing.
- Keep frontend presentation separate from backend calculations and data access. The backend is authoritative for metrics, evidence and financial calculations.
- Never expose secrets, credentials, unrestricted database access or provider keys to the browser. Do not commit `.env`, downloaded private data, generated databases or large raw datasets.
- Add dependencies only when they are used, prefer official maintained packages and update the appropriate manifest and lockfile together.
- Do not silently broaden scope. When a decision is uncertain but reversible, state the assumption and proceed; ask only when the choice materially changes the product or data contract.

## Verification rules

- A task is not complete merely because code was written. Run the narrowest relevant test, lint, type-check or build first, then broader checks when proportionate to the change.
- Tests must protect realistic regressions, especially financial arithmetic, aggregation grain, missing data, zero denominators, API validation and evidence retrieval. Avoid tests that only repeat constants or library behaviour.
- Test both the successful path and important empty, invalid and unavailable-service states. The deterministic product must remain useful when an optional AI provider is unavailable.
- Never claim a command passed unless it was run in the current workspace and its result was checked. Report commands that could not run and the exact blocker.
- After implementation, review the diff for unrelated edits, duplicated logic, unsupported claims, leaked secrets and generated artefacts before handing off.

## Adding endpoints or models without breaking the app

The running application is the demo. Adding things must never take down what already works. The Spring site (`Java/OpportunityImpl/.../service/MosaicApi.java`) calls the Python API on port 8000, and the Help page reads `/openapi.json` live.

New endpoint (`AI/app/api/`):

- One module per route, named `get_<thing>.py`, exposing `router`. Register it in the tuple in `AI/app/api/__init__.py`, or it will not exist.
- Keep the handler thin: calculations go in `app/analysis/`, loading in `app/data/`, model code in `app/models/` or `app/forecast/`.
- Give the route a `summary=` (the Help page shows it) and a Pydantic-typed or clearly documented response.
- Never rename, remove or change the response shape of an existing route unless you also update every caller in `MosaicApi.java` and its templates, in the same change. Prefer adding a new field or a new route.
- Model-backed routes must use `require_model` from `app/api/deps.py`, so a missing model returns 503 and a stale one 409. Never let them return 500.
- Add a test in `AI/tests/` for the success path and for the missing-model or empty-data case.

New or retrained model:

- Add a training module with a `main()` runnable as `python -m app.<package>.<module>`. Save `<name>.joblib` plus `<name>.json` metadata to `AI/models/`, including `dataset_hashes`, the evaluation and its limitations, as the existing trainers do.
- Add the name to `MODEL_NAMES` in `app/models/__init__.py`, and add it to `prepare_models` in `app/models/prepare.py` only if it trains quickly. Training failures must be logged and skipped. They must never stop the API from starting.
- Do not overwrite an existing artefact with a worse or untested model. Compare the held-out evaluation with the current `.json` before replacing it.
- Do not change the input features of an existing model without retraining it and updating every place that builds those features.

### Training a model on a new dataset `.csv`

Follow these steps in order. The existing trainers are the templates: `app/forecast/train.py` (single model) and `app/models/train_risk.py` (several models, temporal split).

1. **Inspect the file before writing code.** Record its source URL, licence, download date, row count, columns, types, date range, currency and grain (what one row is). Confirm the target column exists and is known at the moment of prediction. Check for duplicates, missing values and one-to-many keys. Write this into `docs/` (dataset dictionary) and state the decision the model supports. If no decision needs it, do not train it.
2. **Place the file.** Put it in `AI/datasets/` (or `MOSAIC_DATASETS_DIR`), unchanged. Never commit it; large or restricted raw data stays out of Git. A small permitted fixture for tests may go in `AI/tests/`.
3. **Register the file name** as a constant in `app/config.py`, next to the Olist `*_FILE` constants. Do **not** add it to `ALL_DATASET_FILES` unless it is guaranteed present: startup hashes every file there with `_sha256` in `app/data/olist.py`, and a missing file crashes the API. Instead, hash an optional file only when it exists and merge it into `app.state.dataset_hashes` in `app/main.py`. Otherwise `require_model` sees no current hash and always returns 409.
4. **Write a loader** in `app/data/<dataset>.py` (one module per dataset, not inside `olist.py`). It should read only the needed `usecols` with explicit dtypes, parse dates, and count excluded rows instead of silently dropping them. Do not join it to Olist as if it were the same business. Keep it a separate profile.
5. **Put the model code** (features, split, fit, predict, baseline) in `app/models/<name>.py` or `app/forecast/<name>.py`, and the training script in `train_<name>.py` with `train(datasets_dir, models_dir) -> dict` and `main()`, runnable as `python -m app.<package>.train_<name>`.
6. **Evaluate honestly.** Use a temporal split when rows have dates (as in `SPLIT_DATE`/`TEST_END_DATE`). Exclude post-outcome and leaking fields. Always compare against a simple baseline (naive/majority/mean) and report both. If the model does not beat the baseline, say so and do not wire it into the product.
7. **Save the artefact** as `AI/models/<name>.joblib` plus `<name>.json`. The metadata must contain the keys `model_summary` in `app/api/deps.py` reads (`model_version`, `trained_at`, `prediction_time`, `split_date`, `test_end`, `evaluation`, `importances`, `limitations`) plus `dataset_hashes` for the new file only, `feature_names`, `data_range` and exclusion counts. Use `None` for keys that do not apply rather than omitting them.
8. **Register the model.** Add a `<NAME>_MODEL` constant and put it in `MODEL_NAMES` in `app/models/__init__.py`, and add a `<NAME>_TRAIN_COMMAND` in `app/api/deps.py`. Add it to `prepare_models` in `app/models/prepare.py` only if it trains in seconds, wrapped in `try/except` with `log.exception`, and skipped when the dataset file is absent.
9. **Serve it** through a new `app/api/get_<thing>.py` route using `require_model(request, NAME, TRAIN_COMMAND)`, following the endpoint rules above.
10. **Test it** in `AI/tests/test_<name>.py`: the loader on a small fixture (missing values, bad dates, empty file), the baseline comparison, and the API route for success, missing model (503), changed data (409) and missing dataset file (the API still starts).
11. **Document it.** Add the dataset and model to `docs/requirements.md` and write the session's worklog entry. Include the evaluation numbers and limitations exactly as saved in the `.json`.

Before handing off, all of these must pass. Report any that fail; do not hide them:

1. `python -m pytest tests -q` from `AI/`.
2. The API starts: `python -m app.main`, then `GET /api/health` and `GET /openapi.json` return 200.
3. If Java callers were touched, `PagesRenderTest` passes and the affected page renders.

## Team and constraints

- Five BSc Software Engineering students participating in a 72-hour FinTech hackathon in Mauritius.
- Basic finance knowledge; the team does not want a cybersecurity-focused project.
- Approximately 20 competing teams. The goal is a distinctive, understandable, working demonstration backed by defensible evidence.
- Prefer free downloadable public datasets and a demo with no additional spending. Do not assume unlimited free AI API usage or hosting.
- Explain decisions in simple language and keep the project achievable within the available time.

## Confirmed direction versus open choices

Confirmed:

- Challenge 3: **Turning Financial Data into Opportunity**.
- Use financial/transactional data to produce actionable insights, reveal opportunities or anticipate changes. Go beyond charts and generic reporting.
- React frontend and Python backend in one repository are the working architecture.
- The central proposed experience combines discovery, evidence, interpretation and decision support.

Still open:

- Final product name. “WhatIf” was a working suggestion only.
- Final dataset and business sector. Olist and DataCo are leading candidates; AdventureWorks is an alternative for broader departmental data.
- Business users are the current working audience. Personal finance was explored but no switch was confirmed.
- PostgreSQL, FastAPI, TypeScript, chart library, styling library and LLM provider are recommended defaults, not existing dependencies to assume blindly.
- Exact alert definitions, thresholds, deployment target and authentication scope.

Do not default back to the bakery-specific product. The user explicitly requested broader business data. Do not build several industries or both personal and business finance at once. Ask a focused question only when an unresolved choice materially blocks useful work; otherwise make reversible assumptions explicit.

## Product proposition

Help a small-business owner recognise when an apparently positive result hides deterioration elsewhere, inspect the evidence and decide what to investigate or change.

Working promise: **“Spot the hidden problem. Inspect the evidence. Explore the next step.”**

Example tension: order volume increases while the late-delivery rate also increases and customer ratings decline.

“Contradiction” means conflicting business indicators or a trade-off, not a logical impossibility. Detect these patterns from actual data; do not invent them to fit the pitch.

Evidence is a core strength, but not the sole differentiator. Existing tools already offer natural-language analytics, record drill-down and scenario planning. Position the product as a focused, accessible workflow for the chosen audience. Do not claim to be the first in Mauritius or better than all existing platforms without evidence.

Keep financial relevance visible through recorded sales values, payment patterns or clearly labelled financial scenarios. An operational dashboard alone is not enough for this challenge.

## Recommended MVP

Build one complete journey:

1. Load one documented dataset through a repeatable import.
2. Show dataset coverage, currency, dates and important quality issues.
3. Calculate and display up to three useful conflicting-indicator alerts.
4. Open an alert to inspect its formula, comparison periods, denominators, filters and supporting records.
5. Explain the finding in plain language, separating observations from possible explanations.
6. Offer a relevant next investigation and, where supported, one editable scenario.

Suggested screens:

- Data/import and quality summary.
- Overview with prioritised findings and a few useful charts.
- Evidence detail with metric comparisons and paginated source records.
- Optional scenario comparison and contextual question panel.

Start with deterministic analytics and working evidence retrieval. Add language-model explanations afterward. Forecasting or prediction is optional unless it strengthens the chosen decision. Do not add ML solely for presentation value.

Out of initial scope: real payments, bank integrations, autonomous financial actions, full ERP/accounting, unrestricted chat-to-SQL, custom transformer training, multiple unrelated datasets combined as one business, and production-scale infrastructure.

## Dataset options

| Dataset | Useful coverage | Important limitations |
| --- | --- | --- |
| Olist: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce | Orders, items, sellers, products, customers, payments, delivery dates, reviews and geography | Historical Brazilian data. Not full costs, inventory, profit or seller settlement cash flow. |
| DataCo: https://data.mendeley.com/datasets/8gx2fvg2k6/5 | Supply-chain records for clothing, sports and electronic supplies; variable dictionary and separate clickstream data | Inspect field definitions and prediction-time availability before selecting features. Original release lists CC BY 4.0. |
| AdventureWorks: https://learn.microsoft.com/en-us/sql/samples/adventureworks-install-configure | Sample relational business database; full versions provide broader business functions than lightweight versions | Sample business data, not real-world validation. SQL Server backup format may require export for a PostgreSQL app. |
| Store Sales: https://www.kaggle.com/competitions/store-sales-time-series-forecasting/data | Store/product-family sales, promotions and supporting calendar data | Competition rules apply. Does not supply complete costs or inventory; observing promotions is not causal evidence. |

Prefer one coherent dataset. Confirm its actual schema, provenance, licence and download requirements before implementation. Never bypass account requirements. If download is blocked, report the exact blocker and support a user-provided local copy.

Keep raw data immutable and record download source, version/date and checksums where practical. Store large raw data outside Git; include a small permitted fixture and reproducible import instructions. Do not redistribute data without checking its licence.

Preserve original currencies, dates and geographic context. A Mauritian use case does not turn Brazilian records into Mauritian evidence. Clearly distinguish observed data, forecasts and hypothetical user inputs.

## Evidence contract — essential

Every finding must be reproducible from versioned data and explicit calculations. A finding should contain:

- Stable ID, title, analysis timestamp and dataset/import version.
- Current and comparison periods, entity scope and filters.
- Metric names, units, definitions and calculation version.
- Values, numerators, denominators and sample sizes.
- Absolute change and percentage/percentage-point change as appropriate.
- Direction/threshold rules and minimum support used to trigger the alert.
- Evidence references sufficient to retrieve the relevant source records.
- Missing/excluded record counts and known limitations.
- Observations, hypotheses and suggested investigation as separate fields.

Evidence links must resolve to real records used by the calculation. Do not substitute invented citations, generated numbers or generic explanations for evidence.

Important calculation rules:

- Prevent double counting across one-to-many joins. In Olist, aggregate items and payments separately to the required grain before joining them. Multiple reviews also need an explicit selection/aggregation rule.
- Define eligible populations consistently. Delivery metrics need appropriate delivered orders and date fields; handle cancelled, pending and incomplete orders explicitly.
- Compare suitable periods/cohorts. Consider incomplete recent deliveries, different period lengths, small samples and changing seller/category composition.
- Use rates as well as counts. More late orders with more total orders is not automatically worsening reliability.
- Report a rise from 10% to 25% as 15 percentage points, or a 150% relative increase, with the chosen meaning clear.
- Handle zero denominators and zero baselines explicitly. Missing values are not automatically zero.
- Correlation does not establish causation. Do not state that growth caused delays merely because they coincide.
- Revenue is not profit; customer payment data is not necessarily the merchant's bank cash balance. Do not claim unsupported financial quantities.
- Financial scenario calculations must expose all assumptions and use decimal arithmetic or integer minor units.

## Architecture and dependencies

One application, two development processes, one repository:

- `frontend/`: React + TypeScript + Vite; recommended Bootstrap/custom CSS and Recharts. Use browser `fetch` unless existing conventions favour another client.
- `backend/`: Python + FastAPI, with separate import, analytics, evidence, scenario and LLM modules.
- PostgreSQL for persisted imports, findings and scenario records; SQLAlchemy and Psycopg are recommended.
- `data/`: raw/processed data locations, fixtures and provenance notes; exclude large/restricted data from Git.
- `docs/`: setup, API contracts, decisions, dataset dictionary, evaluation and demo instructions.

Recommended Python packages, adding only those used:

- `fastapi[standard]`, `pydantic`, `pydantic-settings`.
- `pandas`, `sqlalchemy`, `psycopg[binary]`.
- `pytest`, `httpx` for meaningful backend/API verification.
- `scikit-learn`, `joblib` only if implementing a trained model.
- `google-genai` if Gemini is selected; otherwise the chosen provider's official SDK.
- `alembic` if database migrations are needed.

Use compatible stable releases and committed lockfiles. Match existing repository tooling where possible. Keep database and AI credentials on the backend. Provide `.env.example` with placeholders; never commit `.env` or secrets.

Candidate APIs, adapted to the final schema:

- `POST /api/imports`: validate/import a supported dataset.
- `GET /api/imports/{id}/quality`: coverage and validation results.
- `POST /api/analyses`: calculate findings for an import and period.
- `GET /api/findings`: filtered findings list.
- `GET /api/findings/{id}`: finding and evidence summary.
- `GET /api/findings/{id}/records`: paginated supporting records.
- `POST /api/scenarios`: evaluate a validated hypothetical change.
- `POST /api/assistant`: answer about a selected finding or propose a structured scenario change.

Agree on request/response examples early. Keep business logic outside API route handlers. The frontend owns presentation; the backend owns authoritative calculations. Do not introduce microservices, queues or vector databases without a concrete need.

## AI and optional ML

Use a pretrained LLM to interpret questions, summarise permitted review text and explain verified results. Training a transformer from scratch is out of scope.

- Send only the minimum relevant structured evidence, not the entire database.
- Treat uploaded text and reviews as untrusted data, not instructions.
- Validate model output against schemas and business rules. Structured JSON alone does not establish truth.
- Give the LLM only allowlisted application operations; never arbitrary SQL, Python execution, unrestricted database access or financial actions.
- Keep observed numbers in authoritative UI fields. Generated explanations must not introduce unsupported quantitative claims.
- Confirm proposed scenario changes before applying them. Preserve the original data.
- Configure provider/model through environment variables and verify current pricing, quotas and data-use terms. Do not assume a free service accepts confidential records.
- Time out failed calls and retain useful deterministic findings and manual controls when the AI is unavailable.

If building forecasts/classifiers: start with a baseline, preserve temporal ordering where relevant, avoid post-outcome fields and report held-out evaluation honestly. Sales are not necessarily unconstrained demand. Save model provenance and load only trusted model artifacts. Do not imply predictions or hypothetical interventions are guaranteed outcomes.

## Five-person work split

Suggested ownership, adjusted to members' skills:

1. Frontend: layout, filters, charts, evidence views and interaction states.
2. Backend/data storage: schemas, import APIs, persistence and integration.
3. Data analysis/ML: cleaning, metrics, alert detection and optional model evaluation.
4. Evidence/scenarios: reproducibility, drill-down, scenario mathematics and calculation tests.
5. AI/demo integration: interpretation, grounded explanations, failure handling and demo coordination; assist frontend integration.

Every member tests their own work. Define interfaces early, merge small changes frequently and keep one working demo branch. No teammate should wait until the final night to integrate. These are human team roles, not instructions to spawn AI agents automatically.

## Build order and acceptance criteria

When asked to implement:

1. Inspect existing code and record unresolved high-impact choices.
2. Select/inspect one dataset and define one demonstrable decision problem.
3. Establish the smallest working frontend/backend/data path.
4. Implement one correct finding and its complete evidence view.
5. Add further findings only after the first works end to end.
6. Add the contextual AI explanation and one useful scenario if time allows.
7. Verify failure cases and rehearse the demo; freeze optional features before the final hours.

Done means:

- Setup is documented and reproducible with the declared dependencies.
- At least one real finding is recomputable from the selected data, or a clearly labelled fixture demonstrates the mechanics if no real pattern qualifies.
- Evidence totals match the finding after joins, filters and pagination.
- Tests cover duplicate-join inflation, missing dates, zero denominators, period comparison and any monetary calculations implemented.
- The interface distinguishes loading, empty, error, observed and hypothetical states.
- An unavailable LLM does not break analytics or evidence inspection.
- No unsupported claims about accuracy, causation, uniqueness, security or scalability appear in the UI or pitch.
- Builds, type checks and relevant tests have actually been run; report any remaining failures or untested limits.

For a local single-business demo, keep the deployment scope explicit. Before accepting real customer data or public multi-user access, implement authentication, server-side authorisation, business-data isolation and appropriate upload/access controls. Never describe a local prototype as production-ready merely because it works in the demo.

## Communication and handoff

Use simple language. State what changed, why, what was verified and what remains uncertain. Do not repeatedly reopen settled choices or silently turn tentative suggestions into requirements. Keep the user informed of material blockers and scope changes.

This handoff authorises creation of this instructions file only; implementation should follow the user's next request. When implementation is requested, use the current repository and this brief rather than restarting the entire concept discussion.
