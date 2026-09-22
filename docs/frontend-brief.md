# Frontend brief — Mosaic

You are building the React UI. The Python backend in `AI/` is finished and is the single
source of truth for every number. **Do not compute, re-derive, round-trip or invent any
metric in the frontend.** Display what the API returns, formatted.

## Start the backend first

```powershell
cd AI
.\.venv\Scripts\python.exe -m app.forecast.train      # once, if AI/models/ is empty
.\.venv\Scripts\python.exe -m app.models.train_risk   # once, ~30 s
.\.venv\Scripts\python.exe -m app.main                # serves http://127.0.0.1:8000
```

Interactive docs and every exact payload: **http://127.0.0.1:8000/docs**. Read it before
coding; the shapes below are abridged.

CORS already allows `http://localhost:5173`. Use `fetch`. No auth, no keys, GET except one POST.

## What exists in `front-end/`

Vite + React 19, plain **JSX (not TypeScript)**, `npm run dev`. `src/App.jsx` is still the
Vite starter — replace it. No chart, router or styling library is installed yet. Add
**Recharts** for charts; keep styling to plain CSS unless you have a reason. Update
`package.json` and the lockfile together.

## The story the UI must tell

> Sales are recovering, but that is not the whole picture: 18 of 74 categories are shrinking
> faster than the business, some sellers are getting less reliable, and if volume grows,
> late deliveries and bad reviews grow with it.

Four screens, in this order of importance.

### 1. Overview (landing)

- `GET /api/sales/history` → line chart of `months[].sales` (BRL, 2017-01..2018-08) with
  `orders` available as a second series or tooltip value.
- `GET /api/sales/forecast?horizon=3` → continue the same line with `forecast[]`, drawn
  **visually distinct from history** (dashed), with a shaded band from `lower` to `upper`.
- Also plot `baselines.naive_last` and `baselines.mean_last_3` as thin reference lines, and
  show `evaluation` as a small table: for `model`, `naive_last`, `mean_last_3` show `mae` and
  `mape`. **The naive baseline currently beats the model — show that honestly, do not hide
  it.** A one-line note is enough: "a simple 'same as last month' rule scores better on the
  last 6 months".
- Headline cards: latest month sales, latest month orders, latest late rate
  (`GET /api/risk/delivery/summary` → last `monthly[]` entry), latest low-review rate
  (`GET /api/risk/reviews/summary`).
- Show `exclusions` from `/api/sales/history` behind a "data quality" disclosure
  (`statuses`, `orders_without_items`, `months_outside_range`).

### 2. Category health — the "hidden problem" screen

`GET /api/sales/categories?limit=20`, plus `?flag=underperforming_total` and
`?flag=latest_month_anomaly` for filter chips.

- Table sorted as returned: `category`, `recent`, `previous`, `change_pct`,
  `share_change_pp`, and badges from `flags`.
- Show `total_change_pct` prominently at the top ("the business as a whole: −12.7%") so a
  category's `change_pct` reads against it.
- Clicking a row → `GET /api/sales/categories/{category}`: its monthly `series` as a chart,
  plus `forecast[]` (may be `null` with `forecast_reason: "insufficient_history"` — handle
  that), and an **"why is this flagged?"** panel rendering `evidence.underperforming_total`
  (`change_pct`, `total_change_pct`, `gap_pp`, `threshold_pp`, `support_sales`) and
  `evidence.latest_month_anomaly` (`latest`, `expected`, `deviation`, `noise_std`,
  `threshold`). This evidence panel is a judging point — make it readable, not a JSON dump.

### 3. Delivery risk

- `GET /api/risk/delivery/summary` → `monthly[]` line of `late_rate` (plot as %), plus the
  `model` block: `evaluation.roc_auc`, `base_rate`, `top_10pct.precision`/`recall`, and
  `importances[]` as a small bar list. `model` is `null` when nothing is trained — render a
  "not trained yet" state, not a crash.
- `GET /api/risk/delivery/open-orders?limit=50` → table of in-flight orders sorted by `risk`.
  Show `risk` as a **0–100 score bar labelled "risk score", never as "% chance"** — the
  backend states these are ranking signals, not calibrated probabilities. Always show
  `days_since_purchase` beside it: many top-risk orders are 200+ days old.
- `GET /api/risk/delivery/sellers?min_orders=30` → table with `late_rate`,
  `handover_late_rate`, and `recent_late_rate` vs `earlier_late_rate` shown as a
  getting-worse / getting-better arrow. `recent_late_rate` can be `null`.

### 4. Scenario — "what if sales grow?"

`POST /api/scenarios/sales-impact` with
`{"horizon": 1-6, "sales_change_pct": -50..100, "explain": true}`.

- A slider for `sales_change_pct` (default +20) and `horizon` (default 3). Debounce; each
  change is one POST. **Mark everything on this screen as hypothetical** — different visual
  treatment from observed data.
- Result cards from `consequences`: `projected_monthly_orders` (and `extra_orders_per_month`),
  then from `late.rate_held`: `expected_late_per_month`, `expected_low_reviews_per_month`,
  `sales_exposed_per_month`.
- Show **both** late-delivery variants side by side: `late.rate_held` ("if the recent rate
  holds") and `late.rate_fitted` ("if the volume–lateness link holds"), with
  `late.rate_fitted.fit.r_squared` displayed and the word **association** next to it. Never
  label it a cause or a prediction. `rate_fitted` may be `null`.
- `sellers_at_capacity`: "`count` of `active_sellers` sellers would be handling more orders in
  a month than they ever have", with `top[]` as a table (`recent_monthly_orders`,
  `projected_monthly_orders`, `historical_peak`, `over_peak_pct`).
- Render `assumptions[]` and `limitations[]` as visible list items on the screen, not hidden
  in a tooltip.
- `narrative`: show `text` in a panel clearly labelled as generated. If
  `narrative.source === "template"`, do not call it AI; label it "summary". If
  `source === "llm"`, label it "AI explanation (<model>)". The narrative is **commentary
  only** — every number must also appear in the cards above it.
- `consequences` can be `null` with `reason: "no_baseline_activity"` — handle it.

Optional: `GET /api/ai/health` → a small indicator ("local AI: connected / offline"). When
`reachable` is false the scenario still works and returns the template narrative.

## Rules

1. **Backend owns the numbers.** No arithmetic in the frontend beyond formatting and
   percentage display (`0.0361` → `3.61%`).
2. **Three visually distinct states**: observed history, model prediction, hypothetical
   scenario. A judge must never mistake one for another.
3. **Every screen handles loading, empty, and error.** The backend legitimately returns
   `503` (model not trained), `409` (data changed since training), `422` (bad query), and
   `null` fields. Show a useful message; never blank-screen.
4. **Currency is BRL** (Brazilian real, historical 2017–2018 marketplace data). Label it.
   Do not convert to MUR or imply this is Mauritian data.
5. Never write "profit", "cash", "revenue lost" or "guaranteed". The backend measures gross
   item sales; `sales_exposed_per_month` is **exposure, not loss**.
6. Don't claim accuracy, causation or uniqueness anywhere in the UI copy.

## Response shapes (abridged — confirm at `/docs`)

```jsonc
// GET /api/sales/history
{ "unit": "BRL", "measure": "gross_item_sales",
  "range": {"start": "2017-01", "end": "2018-08"},
  "months": [{"month": "2017-01", "orders": 787, "sales": 120098.27, "freight": 16845.19}],
  "exclusions": {"statuses": {"canceled": 625, "unavailable": 609},
                 "orders_without_items": 8, "months_outside_range": {"2016-10": 293}} }

// GET /api/sales/forecast?horizon=3
{ "model_version": "sales-ridge-v1", "trained_at": "...", "unit": "BRL", "horizon": 3,
  "forecast": [{"month": "2018-09", "sales": 892715.5, "lower": 737185.4, "upper": 1048245.6}],
  "baselines": {"naive_last": [{"month": "2018-09", "sales": 848860.1}], "mean_last_3": [...]},
  "evaluation": {"model": {"mae": 92044.6, "mape": 10.41, "points": [{"month","actual","predicted"}]},
                 "naive_last": {...}, "mean_last_3": {...}},
  "limitations": ["..."] }

// GET /api/sales/categories?limit=20&flag=underperforming_total
{ "recent_months": 3, "total_change_pct": -12.7, "count": 18,
  "categories": [{"category": "sports_leisure", "recent": 151905.0, "previous": 211600.0,
    "change_abs": -59695.0, "change_pct": -28.2, "share_recent": 0.058,
    "share_previous": 0.071, "share_change_pp": -1.3, "total_change_pct": -12.7,
    "flags": {"underperforming_total": true, "latest_month_anomaly": false},
    "evidence": {"underperforming_total": {"change_pct","total_change_pct","gap_pp",
                   "threshold_pp","support_sales","min_support_sales"},
                 "latest_month_anomaly": {"latest","expected","deviation","noise_std",
                   "threshold","sigma"}},
    "forecast": [{"month": "2018-09", "sales": 48123.4}] | null,
    "forecast_reason": null | "insufficient_history" }] }
// GET /api/sales/categories/{category} adds: "series": [{"month","orders","items","sales"}]

// GET /api/risk/delivery/summary
{ "monthly": [{"month": "2018-08", "delivered": 6351, "late": 394, "late_rate": 0.062}],
  "exclusions": {...},
  "model": null | {"model_version","trained_at","prediction_time","split_date","test_end",
    "evaluation": {"n_train","n_test","n_positive_test","base_rate","roc_auc",
      "average_precision","top_10pct": {"threshold","flagged","precision","recall"}},
    "importances": [{"feature","auc_drop_mean","auc_drop_std"}], "limitations": ["..."]} }

// GET /api/risk/delivery/open-orders?limit=50   (503 if late_delivery not trained)
{ "model_version": "late_delivery-hgb-v1", "prediction_time": "at_purchase",
  "orders": [{"order_id","order_status","purchase_ts","order_estimated_delivery_date",
    "seller_id","seller_state","customer_state","category","total_price",
    "days_since_purchase": 223, "risk": 0.925}] }

// GET /api/risk/delivery/sellers?min_orders=30&limit=50
{ "min_orders": 30, "sellers": [{"seller_id","orders","late","handover_known","handover_late",
    "late_rate","handover_late_rate","recent_late_rate": null|float,"earlier_late_rate"}] }

// GET /api/risk/reviews/summary
{ "monthly": [{"month","reviewed","low","low_rate"}],
  "by_lateness": {"late": {"reviewed": 6378, "low": 3981, "low_rate": 0.624},
                  "on_time": {"reviewed": 89182, "low": 8247, "low_rate": 0.092}},
  "exclusions": {...}, "model": null | {...same shape as delivery...} }

// GET /api/risk/reviews/unreviewed?limit=50   (503 if low_review not trained)
{ "model_version", "prediction_time": "after_delivery",
  "orders": [{"order_id","purchase_ts","order_delivered_customer_date","seller_id",
    "seller_state","customer_state","category","total_price","delivery_days","days_late","risk"}] }

// POST /api/scenarios/sales-impact  {"horizon":3,"sales_change_pct":20,"explain":true}
{ "scenario": {"horizon": 3, "sales_change_pct": 20.0, "recent_months": 3},
  "baseline": {"months": ["2018-06","2018-07","2018-08"],
               "monthly_sales": 863390.0, "monthly_orders": 6266.3},
  "consequences": null | {
    "projected_monthly_sales": 1036068.0, "projected_monthly_orders": 7519.6,
    "extra_orders_per_month": 1253.3, "horizon_sales": ..., "horizon_orders": ...,
    "late": {
      "rate_held":  {"basis":"recent_3_month_rate","late_rate":0.0361,
        "expected_late_per_month":271.6,"expected_late_over_horizon":...,
        "expected_low_reviews_per_month":840.0,"expected_low_reviews_over_horizon":...,
        "sales_exposed_per_month":37426.1,"sales_exposed_over_horizon":...},
      "rate_fitted": null | {"basis":"fitted_volume_relationship","late_rate":0.0893, ...,
        "fit": {"slope","intercept","slope_pp_per_1000_orders":1.12,"r_squared":0.26,"n_months":20}}},
    "sellers_at_capacity": {"count": 41, "active_sellers": 1810, "growth_factor": 1.2,
      "top": [{"seller_id","recent_monthly_orders","historical_peak",
               "projected_monthly_orders","over_peak_pct"}]}},
  "reason": null | "no_baseline_activity",
  "evidence": {"aov": 137.78, "recent_late_rate": 0.0361, "recent_late_orders",
    "recent_delivered_orders", "p_low_given_late": 0.624, "p_low_given_on_time": 0.092,
    "volume_late_fit": {...}, "baseline_months": [...]},
  "assumptions": ["..."], "limitations": ["..."],
  "narrative": {"text": "...", "source": "llm"|"template", "model": null|"google/gemma-4-e4b",
                "reason": null|"llm_disabled"|"llm_unreachable: ..."|"unsupported_numbers: ..."} }

// GET /api/ai/health
{ "enabled": true, "base_url": "http://localhost:1234", "configured_model": null,
  "reachable": true, "models": ["google/gemma-4-e4b", "..."] }
```

## Order of work

1. Overview with history + forecast (the core demo).
2. Category health with the evidence panel (the differentiator).
3. Scenario screen.
4. Delivery risk tables.

Ship each screen working end to end before starting the next. If an endpoint's shape differs
from this brief, `/docs` is authoritative — tell the team rather than adapting the numbers.
