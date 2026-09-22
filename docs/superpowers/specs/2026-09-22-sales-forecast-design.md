# Sales forecast (whole business, monthly) — design

Date: 2026-09-22. Status: approved for implementation.

## Goal

Give the application its first predictive capability: a monthly **sales forecast** for the
whole business, trained on the Olist dataset already in `AI/datasets/`, served by a FastAPI
backend so the React frontend can show history, forecast and model quality.

"Sales" means gross item sales (GMV): the sum of item `price` on orders, by purchase month.
It is not profit (no costs in Olist) and not cash received (payments show what the customer
paid, not seller settlement). The UI must label it as such.

Later work (late-delivery risk, review-score risk, per-segment breakdowns) builds on the same
monthly series and the same backend layout; it is out of scope here.

## Data definition

Source: `AI/datasets/olist_orders_dataset.csv` and `AI/datasets/olist_order_items_dataset.csv`.

Monthly series, one row per calendar month:

| column | definition |
| --- | --- |
| `month` | `order_purchase_timestamp` truncated to month (`YYYY-MM`) |
| `orders` | distinct `order_id` in that month after exclusions |
| `sales` | sum of `order_items.price` for those orders (float, BRL) |
| `freight` | sum of `order_items.freight_value` (reported, not part of `sales`) |

Rules:

- Exclude orders whose `order_status` is `canceled` or `unavailable`. All other statuses
  count as booked sales. Exclusion counts per status are reported as metadata.
- Aggregate items to order grain first, then to month. Never join payments or reviews here
  (one-to-many rows would inflate sales).
- Orders with no item rows contribute 0 sales but still count as an order; the count of such
  orders is reported as metadata.
- Drop stub months: keep only the contiguous range **2017-01 to 2018-08** (20 months).
  Months outside this range are reported as excluded with their order counts. The range is a
  constant in code, not hard-coded inside the aggregation function.
- Values use pandas float64; monetary precision at monthly grain (hundreds of thousands BRL,
  two decimals) does not need `Decimal`.

## Model

Module `AI/app/forecast/sales.py`, pure functions over a pandas Series indexed by month.

Features for month *t*: trend index (0-based month number), `sales[t-1]`, `sales[t-2]`,
`sales[t-3]`, mean of the last three. Target: `sales[t]`. The first three months have no
complete lags and are dropped from training.

Model: `sklearn.linear_model.Ridge` (alpha = 1.0, features standardised with
`StandardScaler` in a `Pipeline`). Multi-step forecasts are recursive: each predicted month
is appended to the series and used as a lag for the next.

Baselines, always computed alongside the model:

- `naive_last`: forecast = last observed month.
- `mean_last_3`: forecast = mean of the last three observed months.

Evaluation: rolling-origin backtest over the last 6 months of the series. For each origin
*k* in those months, fit on months before *k*, predict month *k* (one step ahead). Report
MAE, MAPE and the list of (month, actual, predicted) points for the model and both baselines.
Prediction interval for the forecast: point ± 1.96 × standard deviation of the model's
backtest residuals (same width for every horizon; documented as a simplification).

Forecast horizon: 1 to 6 months (default 3). Forecast months are labelled `YYYY-MM`
continuing after the last observed month.

Known limitation stated in metadata: 20 observations, a single Nov 2017 spike, no seasonal
term; treat the forecast as a trend indicator, not a guarantee.

## Training artifact

`AI/app/forecast/train.py` is a CLI (`python -m app.forecast.train`) that:

1. Builds the monthly series from the CSVs.
2. Runs the backtest, then fits the model on the full series.
3. Writes `AI/models/sales_forecast.joblib` (the fitted pipeline) and
   `AI/models/sales_forecast.json` with: `model_version`, `trained_at`, `data_range`,
   `n_months`, dataset file SHA-256 hashes, feature names, backtest metrics for model and
   baselines, residual std, exclusion counts.

`AI/models/` is gitignored. The API refuses to serve a forecast whose metadata hashes do not
match the current CSVs (returns 409 with a "retrain" message) so results stay reproducible.

## API

`AI/app/main.py`, FastAPI, JSON only, CORS open to the Vite dev origin.

- `GET /api/health` → `{"status": "ok", "model_loaded": bool}`.
- `GET /api/sales/history` → `{ "unit": "BRL", "measure": "gross_item_sales",
  "range": {"start","end"}, "months": [{"month","orders","sales","freight"}],
  "exclusions": {"statuses": {...}, "orders_without_items": n, "months_outside_range": {...}} }`.
- `GET /api/sales/forecast?horizon=3` → `{ "model_version", "trained_at", "horizon",
  "forecast": [{"month","sales","lower","upper"}], "baselines": {"naive_last": [...],
  "mean_last_3": [...]}, "evaluation": {"model": {"mae","mape","points"}, "naive_last": {...},
  "mean_last_3": {...}}, "limitations": [str] }`.
  Validation: horizon outside 1–6 → 422. No artifact → 503 with `{"detail": "..."}`.
  Stale artifact → 409.

Business logic stays in `app/data` and `app/forecast`; route handlers only validate, call and
serialise. The history series is computed once at startup and cached in memory.

## Layout and dependencies

```
AI/
  app/__init__.py
  app/config.py             # paths, data range constant, CORS origins from env
  app/data/olist.py
  app/forecast/sales.py
  app/forecast/train.py
  app/main.py
  tests/conftest.py         # small fixture CSVs written to tmp_path
  tests/test_olist.py
  tests/test_sales_forecast.py
  tests/test_api.py
  models/                   # gitignored
  requirements.txt
  README.md                 # setup, train, run, test
```

Dependencies (pinned in `requirements.txt`): `fastapi[standard]`, `pandas`, `scikit-learn`,
`joblib`, `pytest`, `httpx`. The existing `AI/.venv` (Python 3.13) is used.

## Tests

- Aggregation: canceled/unavailable excluded; an order with two items counts once in
  `orders` and both prices in `sales`; payments are never joined; order without items counts
  as 0 sales; months outside range excluded and reported; empty input yields an empty series
  with zero counts, not an error.
- Forecast: feature rows align with the right lags; backtest only uses months before each
  origin; recursive forecast returns `horizon` months with correct labels; baselines are
  exact; series shorter than the minimum (lags + 1 training row + backtest window) raises a
  clear `ValueError`; MAPE handles a zero actual by skipping that point and reporting it.
- API: history endpoint totals equal the sum of fixture sales; forecast validates horizon;
  missing artifact returns 503; stale hash returns 409.

## Out of scope

Per-category or per-seller forecasts, seasonality models, LLM explanations, database
persistence, frontend charts (the frontend consumes the two endpoints in a later task).
