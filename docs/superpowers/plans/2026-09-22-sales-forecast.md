# Sales Forecast Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Train a monthly whole-business sales forecast on the Olist CSVs and serve history, forecast, baselines and backtest metrics from a FastAPI backend.

**Architecture:** `app/data/olist.py` turns the orders + items CSVs into one monthly series with exclusion counts. `app/forecast/sales.py` holds pure functions (features, ridge model, baselines, rolling-origin backtest, recursive forecast). `app/forecast/train.py` writes a joblib artifact plus JSON metadata; `app/main.py` loads them and exposes three JSON endpoints.

**Tech Stack:** Python 3.13 (`AI/.venv`), pandas, scikit-learn, joblib, FastAPI, pytest, httpx.

**Spec:** `docs/superpowers/specs/2026-09-22-sales-forecast-design.md`

## Global Constraints

- Backend root is `AI/`; run every command from `AI/` with `.venv/Scripts/python.exe`.
- Sales = sum of item `price`; statuses `canceled`, `unavailable` excluded; data range `2017-01`..`2018-08`.
- Model: `StandardScaler` + `Ridge(alpha=1.0)`; features `trend, lag_1, lag_2, lag_3, mean_last_3`; backtest = last 6 months, one step ahead; interval = ±1.96 × residual std.
- Horizon 1–6, default 3. Errors: 422 bad horizon, 503 no artifact, 409 stale artifact.
- No business logic in route handlers. `AI/models/` is gitignored. Do not commit unless asked.

---

### Task 1: Project scaffold and dependencies

**Files:**
- Create: `AI/requirements.txt`, `AI/.gitignore`, `AI/app/__init__.py`, `AI/app/data/__init__.py`, `AI/app/forecast/__init__.py`, `AI/tests/__init__.py`, `AI/app/config.py`

**Produces:** `app.config` constants: `DATASETS_DIR`, `MODELS_DIR`, `DATA_RANGE`, `EXCLUDED_STATUSES`, `ORDERS_FILE`, `ITEMS_FILE`, `CORS_ORIGINS`.

- [ ] **Step 1:** Write `AI/requirements.txt` with `fastapi[standard]`, `pandas`, `scikit-learn`, `joblib`, `pytest`, `httpx` pinned to the newest versions that install on Python 3.13; record resolved versions with `pip freeze > requirements.lock`.
- [ ] **Step 2:** Write `AI/.gitignore`: `.venv/`, `models/`, `__pycache__/`, `.pytest_cache/`, `*.pyc`.
- [ ] **Step 3:** Write `AI/app/config.py`:

```python
import os
from pathlib import Path

AI_ROOT = Path(__file__).resolve().parent.parent
DATASETS_DIR = Path(os.environ.get("MOSAIC_DATASETS_DIR", AI_ROOT / "datasets"))
MODELS_DIR = Path(os.environ.get("MOSAIC_MODELS_DIR", AI_ROOT / "models"))
CORS_ORIGINS = os.environ.get("MOSAIC_CORS_ORIGINS", "http://localhost:5173").split(",")

ORDERS_FILE = "olist_orders_dataset.csv"
ITEMS_FILE = "olist_order_items_dataset.csv"

# Olist has near-empty stub months before and after this range.
DATA_RANGE = ("2017-01", "2018-08")
EXCLUDED_STATUSES = frozenset({"canceled", "unavailable"})
```

- [ ] **Step 4:** `pip install -r requirements.txt`, then `python -c "import fastapi, pandas, sklearn"` — expected: no error.

### Task 2: Monthly sales series from Olist CSVs

**Files:**
- Create: `AI/app/data/olist.py`, `AI/tests/conftest.py`, `AI/tests/test_olist.py`

**Produces:**

```python
@dataclass(frozen=True)
class MonthlySales:
    months: pd.DataFrame   # columns: month (str YYYY-MM), orders (int), sales (float), freight (float)
    exclusions: dict       # {"statuses": {status: n}, "orders_without_items": n, "months_outside_range": {month: n}}

def load_orders(datasets_dir: Path) -> pd.DataFrame
def load_order_items(datasets_dir: Path) -> pd.DataFrame
def build_monthly_sales(orders, items, data_range=DATA_RANGE, excluded_statuses=EXCLUDED_STATUSES) -> MonthlySales
def dataset_hashes(datasets_dir: Path) -> dict[str, str]   # {filename: sha256}
```

- [ ] **Step 1:** `conftest.py` fixture `datasets_dir(tmp_path)` writes 12 months (2017-01..2017-12) of orders: per month 2 delivered orders (order `<month>-a` with items price 100 and 50 → sales 150; order `<month>-b` with one item 200), plus in 2017-03: one `canceled` order with an item price 999, one `unavailable` order with price 999, one delivered order with **no items**; plus one delivered order dated 2016-10 with price 777. Expected monthly sales: 350 for every month.
- [ ] **Step 2:** Tests: excluded statuses not summed and counted in `exclusions["statuses"]`; two-item order counted once in `orders`, both prices in `sales`; order without items → 0 sales, `orders_without_items == 1`; 2016-10 absent from `months` and present in `months_outside_range` with count 1; empty frames → empty `months` with the right columns and zero counts; missing month inside observed span is filled with zeros (test by deleting 2017-06 rows).
- [ ] **Step 3:** Run → FAIL (module missing). Implement per spec: aggregate items to order grain, left-merge onto kept orders, groupby month, reindex over `pd.period_range(min, max, freq="M")` inside the data range, fill zeros. Run → PASS.

### Task 3: Forecast functions

**Files:**
- Create: `AI/app/forecast/sales.py`, `AI/tests/test_sales_forecast.py`

**Produces:**

```python
LAGS = 3; BACKTEST_MONTHS = 6; MIN_MONTHS = LAGS + 1 + BACKTEST_MONTHS
FEATURE_NAMES = ["trend", "lag_1", "lag_2", "lag_3", "mean_last_3"]
def feature_row(values: Sequence[float], t: int) -> list[float]
def training_matrix(values) -> tuple[np.ndarray, np.ndarray]
def build_model() -> Pipeline
def fit_model(values) -> Pipeline
def recursive_forecast(model, values, horizon) -> list[float]
def naive_last(values, horizon) -> list[float]
def mean_last_3(values, horizon) -> list[float]
def error_metrics(actuals, predictions) -> dict   # {"mae","mape","skipped_zero_actuals"}
def backtest(values, backtest_months=BACKTEST_MONTHS) -> dict  # {"model": {..., "points": [{"month_index","actual","predicted"}]}, "naive_last": {...}, "mean_last_3": {...}, "residual_std": float}
def forecast_months(last_month: str, horizon: int) -> list[str]
def validate_series_length(values) -> None  # raises ValueError below MIN_MONTHS
```

- [ ] **Step 1:** Tests: `feature_row([10,20,30,40], 3) == [3, 30, 20, 10, 20.0]`; `training_matrix` on 12 values gives 9 rows; `backtest` on a perfectly linear series has model MAE < naive MAE and each point's `actual` equals the series value; `recursive_forecast` returns `horizon` floats; `naive_last([1,2,3], 2) == [3,3]`, `mean_last_3([1,2,3,4], 2) == [3,3]`; `forecast_months("2018-08", 3) == ["2018-09","2018-10","2018-11"]` and crosses the year boundary; `validate_series_length` raises `ValueError` for 9 values; `error_metrics([0, 10], [5, 12])` gives `mape == 20.0` and `skipped_zero_actuals == 1`.
- [ ] **Step 2:** Run → FAIL. Implement. Run → PASS.

### Task 4: Training CLI and artifact

**Files:**
- Create: `AI/app/forecast/train.py`, test in `AI/tests/test_sales_forecast.py` (`test_train_writes_artifact`)

**Produces:**

```python
MODEL_VERSION = "sales-ridge-v1"
ARTIFACT_NAME = "sales_forecast.joblib"; METADATA_NAME = "sales_forecast.json"
def train(datasets_dir: Path, models_dir: Path) -> dict   # returns metadata written
def main() -> None  # python -m app.forecast.train
```

Metadata keys: `model_version, trained_at, data_range {start,end}, n_months, dataset_hashes, feature_names, evaluation, residual_std, exclusions, limitations`.

- [ ] **Step 1:** Test: `train(datasets_dir, tmp_models)` writes both files; metadata `n_months == 12`, `dataset_hashes` keys are the two filenames, `evaluation["model"]["mae"]` is a float.
- [ ] **Step 2:** Implement. Run test → PASS. Run `python -m app.forecast.train` on real data and record the printed metrics in the final report.

### Task 5: FastAPI app

**Files:**
- Create: `AI/app/main.py`, `AI/tests/test_api.py`

**Produces:** `create_app(datasets_dir=DATASETS_DIR, models_dir=MODELS_DIR) -> FastAPI`, module-level `app = create_app()`. Startup (lifespan) computes `MonthlySales`, dataset hashes, and loads the artifact if present into `app.state`.

- [ ] **Step 1:** Tests with `TestClient(create_app(...))` as context manager: `/api/health` → 200 `model_loaded` false before training; `/api/sales/history` → 12 months, `sum(sales) == 4200`, exclusions present; `/api/sales/forecast` → 503 without artifact; after `train()` and a fresh app → 200 with 3 forecast rows, `lower <= sales <= upper`, baselines and evaluation present; `?horizon=7` → 422; after appending a line to the orders CSV and creating a fresh app → 409.
- [ ] **Step 2:** Implement; handlers only validate, call `app.forecast.sales` / metadata, and serialise. Run → PASS.

### Task 6: README and full verification

- [ ] Write `AI/README.md`: setup, train, run (`uvicorn app.main:app --reload`), test, endpoints, data definition and limitations (copy from spec).
- [ ] Run `pytest -q` from `AI/`; start the server and `curl` the three endpoints against real data; report results.
