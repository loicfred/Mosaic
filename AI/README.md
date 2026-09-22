# AI backend — analytics and prediction API

Python backend for the Mosaic hackathon app. It turns the Olist CSVs in `datasets/` into
monthly series and an order-level feature table, trains three small models, and serves
observed statistics, forecasts and risk scores over a FastAPI JSON API.

Designs: `../docs/superpowers/specs/2026-09-22-sales-forecast-design.md` and
`../docs/superpowers/specs/2026-09-22-risk-and-category-models-design.md`.

## Setup

Requires Python 3.13 and the Olist CSVs in `datasets/`.

```powershell
cd AI
.\.venv\Scripts\Activate.ps1          # or: python -m venv .venv
pip install -r requirements.txt       # exact versions used: requirements.lock
```

## Train

```powershell
python -m app.forecast.train          # sales forecast      -> models/sales_forecast.*
python -m app.models.train_risk       # late-delivery + low-review classifiers (~30 s)
```

`models/` is gitignored: retrain after cloning or whenever the CSVs change. Every model
stores the SHA-256 of the CSVs it was trained on; an endpoint refuses to serve a model whose
data changed (HTTP 409) or that was never trained (HTTP 503). Observed statistics keep
working without any model.

## Run

```powershell
uvicorn app.main:app --reload --port 8000
```

Startup builds all series and the order feature table once (a few seconds). Interactive docs
at http://127.0.0.1:8000/docs. CORS allows `http://localhost:5173` (Vite) by default;
override with `MOSAIC_CORS_ORIGINS`. `MOSAIC_DATASETS_DIR` / `MOSAIC_MODELS_DIR` override paths.

## Test

```powershell
python -m pytest -q        # 95 tests on a small synthetic fixture (tests/conftest.py)
```

## Endpoints

| Endpoint | Returns | Needs model |
| --- | --- | --- |
| `GET /api/health` | status and which models are loaded | – |
| `GET /api/sales/history` | monthly `orders`, `sales`, `freight` (2017-01..2018-08) + exclusion counts | – |
| `GET /api/sales/forecast?horizon=3` | 1–6 month sales forecast with interval, two baselines, backtest metrics | sales_forecast |
| `GET /api/sales/categories?limit=20&flag=` | per category: recent vs previous 3 months, share change, flags with evidence, 3-month forecast | – |
| `GET /api/sales/categories/{category}` | the same plus the monthly series; 404 if unknown | – |
| `GET /api/risk/delivery/summary` | observed monthly late rate + model evaluation (`model: null` if untrained) | – |
| `GET /api/risk/delivery/open-orders?limit=50` | in-flight orders ranked by late-delivery risk score | late_delivery |
| `GET /api/risk/delivery/sellers?min_orders=30&limit=50` | per seller: late and handover-late rates, recent (last 3 months) vs earlier | – |
| `GET /api/risk/reviews/summary` | observed low-review rate by month and late vs on-time + model evaluation | – |
| `GET /api/risk/reviews/unreviewed?limit=50` | delivered orders with no review yet, ranked by low-review risk score | low_review |
| `POST /api/scenarios/sales-impact` | what a sales change would do to orders, late deliveries, low reviews, seller capacity and sales exposed to late delivery, plus a plain-language narrative | – |
| `GET /api/ai/health` | whether the local LLM is reachable and which models it lists | – |

Errors: `422` invalid query, `503` model not trained, `409` model trained on different data.

## Scenario: what a sales change would do

`POST /api/scenarios/sales-impact` with `{"horizon": 1-6, "sales_change_pct": -50..100,
"explain": true}`. It needs no trained model — everything comes from observed history.

Worked example, +20% over 3 months (real data):

| Figure | Value | How |
| --- | --- | --- |
| Projected orders | 7,520/month (+1,253) | projected sales ÷ AOV of BRL 137.78 |
| Expected late, rate held | 272/month | recent 3-month late rate 3.61% |
| Expected late, if the volume link holds | 672/month | fitted line, +1.12 pp per 1,000 orders, **R² = 0.26** |
| Expected 1-2 star reviews | ~840/month | late × 62.4% + on-time × 9.2% |
| Sales exposed to late delivery | BRL 37,426/month | expected late × AOV — **exposure, not loss** |
| Sellers past their busiest month ever | 41 of 1,810 | each seller's recent 3-month average × 1.2 vs their peak month |

Both late-delivery variants are always returned. The fitted one is an **association over 20
months with R² = 0.26**, never a cause, and the response carries `assumptions` and
`limitations` saying so.

## Plain-language explanation (local LLM)

The narrative is written by a pretrained model served locally by **LM Studio** (no key, no
cost, nothing leaves the machine). Only aggregated figures are sent — no order, customer or
seller identifiers.

1. In LM Studio open **Developer → Start Server** (default `http://localhost:1234`).
2. Load a chat model; check with `GET /api/ai/health`.
3. Call the scenario endpoint with `"explain": true`.

Env vars: `MOSAIC_LLM_BASE_URL`, `MOSAIC_LLM_MODEL` (empty = whatever is loaded),
`MOSAIC_LLM_TIMEOUT_SECONDS` (default 120), `MOSAIC_LLM_MAX_TOKENS` (default 1500),
`MOSAIC_LLM_ENABLED=false` to switch the LLM off entirely.

**The model never supplies numbers.** Every number in its reply is checked against the computed
evidence; if it invents one, the reply is discarded and a deterministic template is returned
instead. The response reports which was used:

```json
"narrative": {"text": "...", "source": "llm" | "template", "model": "...", "reason": null}
```

`source: "template"` with a `reason` means the model was off (`llm_disabled`), unreachable
(`llm_unreachable: ...`), silent (`llm_empty_response`), or caught inventing figures
(`unsupported_numbers: ...`). The endpoint always answers.

Practical notes from testing on this machine: a 12B model on CPU took over 3 minutes and timed
out; prefer a small model. Reasoning models (e.g. Gemma 4 e4b) spend part of the token budget
on hidden reasoning before any visible text — that is why `MOSAIC_LLM_MAX_TOKENS` defaults to
1500 rather than a few hundred.

## Definitions

- **Sales**: sum of order-item `price` by purchase month, BRL; `canceled`/`unavailable`
  orders excluded; freight reported separately. Gross merchandise sales — **not profit**
  (no costs in Olist) and **not cash received**.
- **Late**: delivered to the customer after `order_estimated_delivery_date` (calendar days).
  **Handover late**: seller passed the parcel to the carrier after `shipping_limit_date`.
- **Low review**: latest review for the order (by answer timestamp) has score ≤ 2.
- **Category** of an order: category of its highest-priced item. Category series count each
  item once, so category totals equal the business total.
- One row per order everywhere: items and reviews are aggregated before joining.

## Models and honest evaluation (real data)

**Sales forecast** — ridge regression on lags (`trend, lag_1..3, mean_last_3`), rolling-origin
backtest over the last 6 months:

| Method | MAE (BRL) | MAPE |
| --- | --- | --- |
| model (ridge) | 92,045 | 10.4% |
| naive_last | 54,998 | 6.0% |
| mean_last_3 | 87,833 | 9.5% |

The model does **not** beat "same as last month": it learned 2017's growth and kept projecting
it while sales fell ~13% in June 2018 and stayed flat. Both baselines are returned so the UI
shows the comparison.

**Risk classifiers** — `HistGradientBoostingClassifier` (class-balanced), trained on purchases
before 2018-06-01, evaluated on Jun–Aug 2018:

| Model | Test n | Base rate | ROC-AUC | Avg precision | Top-10% precision / recall |
| --- | --- | --- | --- | --- | --- |
| late_delivery (at purchase) | 18,603 | 3.6% | 0.68 | 0.07 | 7.1% / 19.6% |
| low_review (after delivery) | 18,873 | 10.9% | 0.74 | 0.41 | 44.4% / 40.6% |

Late-delivery risk is a modest signal (2× lift over the base rate; `promised_days` dominates,
then the seller's past late rate). Low-review risk is a strong one (4× lift; driven by
`n_items`, `days_late`, `category`, `delivery_days`). Scores are **ranking signals, not
calibrated probabilities**. The test window has an unusually low late rate, and late orders
purchased in August 2018 may still be undelivered in the data.

**Category health** is deterministic: `underperforming_total` fires when a category's
recent-3-months change is ≥10 pp worse than the whole business (with ≥ BRL 10k support);
`latest_month_anomaly` fires when the latest month deviates more than 2σ of the category's
usual month-to-month noise from the mean of the previous three. Every flag carries its inputs
under `evidence`. On the real data 18 categories are underperforming the −12.7% total.

## Layout

```
app/config.py              paths, file names, data range, split dates, excluded statuses
app/data/loaders.py        CSV loaders (only the columns used)
app/data/olist.py          monthly business sales series, dataset hashes
app/data/categories.py     monthly category sales series
app/data/orders.py         order-grain feature table and labels
app/data/geo.py            zip centroids, haversine distance
app/data/records.py        DataFrame -> JSON-safe records
app/forecast/sales.py      ridge forecast, baselines, backtest (pure functions)
app/forecast/train.py      sales forecast training CLI
app/models/risk.py         classifier specs, temporal split, fit/evaluate/predict
app/models/train_risk.py   risk model training CLI
app/analysis/categories.py category change, flags, evidence, short forecasts
app/analysis/delivery.py   observed late rates, seller table, open-order scoring
app/analysis/reviews.py    observed low-review rates, unreviewed-order scoring
app/analysis/impact.py     sales-change consequences (orders, lateness, reviews, capacity)
app/ai/client.py           OpenAI-compatible local LLM client (LM Studio)
app/ai/explain.py          prompt, numeric guard, deterministic template fallback
app/api/deps.py            artifact loading, 503/409 guards
app/api/{sales,categories,risk,scenarios}.py   routers: validate, delegate, serialise
app/main.py                app assembly and startup cache
tests/                     pytest suite with a synthetic fixture dataset
datasets/external/         downloaded candidate datasets (gitignored; see its README)
```
