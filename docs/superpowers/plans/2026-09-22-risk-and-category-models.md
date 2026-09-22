# Risk and Category Models Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add late-delivery risk, low-review risk and category health analyses to the `AI/` backend with held-out evaluation and evidence-carrying API responses.

**Architecture:** One shared order-grain feature table (`app/data/orders.py`) feeds two `HistGradientBoostingClassifier` models (`app/models/risk.py`, trained by `app/models/train_risk.py`). Category health is deterministic (`app/data/categories.py` → `app/analysis/categories.py`) and reuses the ridge forecast for short per-category forecasts. `app/main.py` gains routes that only validate, delegate and serialise; response building lives in `app/api/` modules.

**Tech Stack:** pandas, scikit-learn (HistGradientBoosting, permutation_importance), numpy, FastAPI, pytest.

**Spec:** `docs/superpowers/specs/2026-09-22-risk-and-category-models-design.md`

## Global Constraints

- Run from `AI/` with `.venv/Scripts/python.exe`. Reuse `app.config` constants; add `SPLIT_DATE = "2018-06-01"`, `OPEN_STATUSES`, and file-name constants for products, sellers, customers, geolocation, reviews, translation.
- Never join a one-to-many table without aggregating to order grain first.
- Model endpoints: 503 without artifact, 409 on hash mismatch. Handlers contain no business logic.
- No commits unless asked. `models/` and `datasets/external/` are gitignored.

---

### Task 1: Config, fixture extension

**Files:** Modify `app/config.py`, `.gitignore`; modify `tests/conftest.py`.

- [ ] Add constants: `PRODUCTS_FILE, SELLERS_FILE, CUSTOMERS_FILE, GEOLOCATION_FILE, REVIEWS_FILE, TRANSLATION_FILE, ALL_DATASET_FILES`, `SPLIT_DATE = "2018-06-01"`, `OPEN_STATUSES = frozenset({"shipped","processing","invoiced","approved","created"})`.
- [ ] Add `datasets/external/` to `.gitignore`.
- [ ] Extend the fixture writer so every order also has product/seller/customer/geolocation/review rows: two sellers (`s1` in SP zip `01000`, `s2` in RJ zip `20000`), customers alternating SP/RJ, geolocation centroids for the three zip prefixes, products with categories `cat_a`/`cat_b` and dimensions, reviews for most delivered orders (two reviews for one order, none for another), delivery dates such that roughly 25% of delivered orders are late (deterministic pattern: `s2` orders late). Keep the 12 × 350.0 monthly sales invariant so existing tests still pass. Expose helper constants for expected values.
- [ ] Run `pytest -q` → existing 24 tests still pass.

### Task 2: Order feature table

**Files:** Create `app/data/orders.py`, `tests/test_orders.py`.

**Produces:** `OrderFeatures(frame, exclusions)`, `build_order_features(datasets_dir) -> OrderFeatures`, `PURCHASE_TIME_FEATURES`, `DELIVERY_OUTCOME_FEATURES`, `CATEGORICAL_FEATURES`, `haversine_km(lat1, lng1, lat2, lng2)`.

- [ ] Tests per spec "Order features" bullet (multi-item sums, priciest-item category/seller, distance vs NaN, promised_days, seller prior late rate shifted/NaN first, latest review chosen, NaN labels where not applicable, exclusion counts).
- [ ] Implement; run → PASS.

### Task 3: Classifiers and training CLI

**Files:** Create `app/models/__init__.py`, `app/models/risk.py`, `app/models/train_risk.py`, `tests/test_risk.py`.

**Produces:** `MODEL_SPECS = {"late_delivery": ModelSpec(label="late", features=PURCHASE_TIME_FEATURES, population=...), "low_review": ...}`, `temporal_split(frame, split_date) -> (train, test)`, `fit(spec, train) -> Pipeline`, `evaluate(model, spec, test) -> dict`, `predict_risk(model, spec, frame) -> np.ndarray`, `train_all(datasets_dir, models_dir) -> dict[str, dict]`, artifact names `f"{name}.joblib"`, `f"{name}.json"`.

- [ ] Tests: split correctness; training on fixture yields both artifacts and metrics within [0,1]; `predict_risk` length and range; unknown category at prediction does not crash.
- [ ] Implement (ordinal-encode categoricals with `OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=np.nan)` inside a `Pipeline` with `ColumnTransformer`, then `HistGradientBoostingClassifier(categorical_features=...)`). Run → PASS. Train on real data; record metrics.

### Task 4: Category monthly series and analysis

**Files:** Create `app/data/categories.py`, `app/analysis/__init__.py`, `app/analysis/categories.py`, `tests/test_categories.py`.

**Produces:** `build_category_monthly(datasets_dir) -> pd.DataFrame`, `analyse_categories(monthly, recent_months=3, min_recent_sales=10_000.0) -> list[dict]`.

- [ ] Tests per spec "Categories" bullet.
- [ ] Implement; run → PASS.

### Task 5: API routes

**Files:** Create `app/api/__init__.py`, `app/api/risk.py`, `app/api/categories.py`; modify `app/main.py`; create `tests/test_api_risk.py`, `tests/test_api_categories.py`.

- [ ] Tests per spec "API" bullet for all seven endpoints.
- [ ] Implement: lifespan additionally builds `OrderFeatures`, category analysis, loads both risk artifacts; routers mounted in `create_app`. Run → PASS.

### Task 6: Docs and verification

- [ ] Update `AI/README.md` (train both CLIs, new endpoints, evaluation table, limitations). Write `AI/datasets/external/README.md` provenance (source URLs, versions, SHA-256, licences, not used by code yet).
- [ ] `pytest -q`; start server, curl every endpoint on real data; report.
