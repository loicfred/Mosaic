# AI backend — analytics and prediction API

Python backend for the Mosaic hackathon app. It turns the Olist CSVs in `datasets/` into
monthly series and an order-level feature table, trains four small models, and serves
observed statistics, forecasts and risk scores over a FastAPI JSON API.

Designs: `../docs/superpowers/specs/2026-09-22-sales-forecast-design.md` and
`../docs/superpowers/specs/2026-09-22-risk-and-category-models-design.md`.

## Setup

Requires Python 3.13 and the Olist CSVs in `datasets/`.

`datasets/small_business_cashflow.csv` (a separate, synthetic small-business practice dataset,
unrelated to Olist) is optional: put it in `datasets/` to train and serve the cash-flow-stress
model, or leave it out — the API still starts and every other endpoint works, `cashflow_stress`
just stays untrained. It is gitignored; see "Cash-flow stress" under Models and honest evaluation, below, for provenance.

```powershell
cd AI
.\.venv\Scripts\Activate.ps1          # or: python -m venv .venv
pip install -r requirements.txt       # exact versions used: requirements.lock
```

## Train

Train once, then only use: the API never trains at startup or per request (`create_app` defaults to
`auto_train=False`). Run each trainer by hand, once, after placing its dataset file:

```powershell
python -m app.forecast.train          # sales forecast      -> models/sales_forecast.*
python -m app.models.train_risk       # late-delivery + low-review classifiers (~30 s)
python -m app.models.train_cashflow   # cash-flow-stress classifier (~1 s, needs the CSV above)
```

Every model stores the SHA-256 of the CSV(s) it was trained on; an endpoint refuses to serve a model
whose data changed since (HTTP 409) or that was never trained (HTTP 503). Observed statistics keep
working without any model. Retrain only when the dataset file changes or the model code/features change.

## Run

```powershell
uvicorn app.main:app --reload --port 8000
```

Startup builds all series and the order feature table once and loads whatever models were already
trained (see Train, above); it does not train anything itself. Interactive docs at http://127.0.0.1:8000/docs. CORS allows `http://localhost:5173` (Vite) by default;
override with `MOSAIC_CORS_ORIGINS`. `MOSAIC_DATASETS_DIR` / `MOSAIC_MODELS_DIR` override paths.

## Test

```powershell
python -m pytest tests -q  # active suite, using a small synthetic fixture
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
| `GET /api/risk/cashflow/summary` | observed stress rate by sector and month from the practice cash-flow dataset + model evaluation (`available: false` if the CSV isn't present) | – |
| `GET /api/risk/cashflow/records?limit=50` | business-month snapshots ranked by predicted next-month stress risk | cashflow_stress |
| `POST /api/scenarios/sales-impact` | what a sales change would do to orders, late deliveries, low reviews, seller capacity and sales exposed to late delivery | – |

Errors: `422` invalid query, `503` model not trained, `409` model trained on different data.

## Scenario: what a sales change would do

`POST /api/scenarios/sales-impact` with `{"horizon": 1-6, "sales_change_pct": -50..100}`.
It needs no trained model — everything comes from observed history.

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

## Plain-language explanation (Java)

The Python API returns calculated figures only. Scenario narration and the contextual
assistant live in `Java/OpportunityImpl/src/main/java/mu/mosaic/opportunity/service/ai/`.
They use SolarFramework's configured chatbots through `LocalAi`; the model configuration
is in `Java/OpportunityApp/config/ai/agents.json`.

The scenario page asks `ScenarioNarrator` for the explanation. It checks numbers in the
model's reply against the evidence and falls back to a deterministic template when the
model is unavailable or supplies unsupported figures. Python analytics work independently
of that service. The former Python LLM implementation is archived in `old/`.

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

**Cash-flow stress** (separate profile, not Olist) — `HistGradientBoostingClassifier`
(class-balanced) on `datasets/small_business_cashflow.csv`, a synthetic practice dataset for
this hackathon (1,600 business-month rows, 6 sectors, Jan 2024–Aug 2025, no provenance/licence
attached — treat it as a method demonstration, not real data). Each row is independent (no
business id links rows across months), so the split is chronological: trained on Jan 2024–Apr
2025, evaluated on the last 4 months held out:

| Test n | Base rate | ROC-AUC | Avg precision | Top-10% precision / recall |
| --- | --- | --- | --- | --- |
| 312 | 15.7% | 0.53 | 0.17 | 25.0% / 16.3% |

An ROC-AUC of 0.53 is barely above the 0.50 a coin flip would score — this dataset carries
very little learnable signal for this label, and the model should be read as a demonstration
of the method (loader → temporal split → classifier → honest evaluation → API), not as a
usable risk score. Per-feature importances are not computed for this model (empty list).

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
app/data/category_names.py shared category translation
app/data/geo.py            zip centroids, haversine distance
app/data/records.py        DataFrame -> JSON-safe records
app/forecast/sales.py      ridge forecast, baselines, backtest (pure functions)
app/forecast/train.py      sales forecast training CLI
app/models/risk.py         classifier specs, temporal split, fit/evaluate/predict
app/models/train_risk.py   risk model training CLI
app/data/cashflow.py       cash-flow snapshot loader (separate profile, not Olist)
app/models/cashflow.py     cash-flow split, fit/evaluate/predict
app/models/train_cashflow.py cash-flow model training CLI
app/models/prepare.py      startup training when models are missing or stale (skips cashflow if its CSV is absent)
app/analysis/categories.py category change, flags, evidence, short forecasts
app/analysis/delivery.py   observed late rates, seller table, open-order scoring
app/analysis/reviews.py    observed low-review rates, unreviewed-order scoring
app/analysis/impact.py     sales-change consequences (orders, lateness, reviews, capacity)
app/analysis/populations.py shared date and known-outcome filtering
app/api/deps.py            artifact loading, 503/409 guards, model summaries
app/api/get_*.py           one endpoint per file: validate, delegate, serialise
app/api/__init__.py        explicit route registration
app/main.py                app assembly and startup cache
tests/                     pytest suite with a synthetic fixture dataset
datasets/external/         downloaded candidate datasets (gitignored; see its README)
```

See [code organisation](../docs/code-organisation.md) for the endpoint-to-file mapping
and the Python/Java responsibility boundary. `old/` holds the archived Python LLM code;
the active LLM integration is in the Java application.
