# Late-delivery risk, category health and low-review risk — design

Date: 2026-09-22. Status: approved for implementation. Builds on
`2026-09-22-sales-forecast-design.md` (same backend, same data rules).

## Goal

Three further analyses on the Olist data, each exposed by the FastAPI backend:

1. **Late-delivery risk** — probability that an order reaches the customer after the promised
   date, predicted from information known at purchase time. Used to rank in-flight orders and
   to show the monthly late rate next to the sales trend.
2. **Category health** — per product category: monthly sales, recent change, share change,
   short forecast, and deterministic flags for categories that are falling behind the total
   or behaving abnormally in the latest month.
3. **Low-review risk** — probability that a delivered order receives a 1–2 star review,
   predicted after delivery (so delivery outcome is a legitimate input). Used to rank
   delivered-but-unreviewed orders and to show how lateness and low reviews move together.

Every number the API returns is either observed (with numerator, denominator and period) or
a model output labelled as such with its held-out evaluation beside it.

## Data facts driving the design (checked on the real files)

- 96,478 delivered orders; 8 lack a customer delivery date and are excluded from labels.
- Customer-facing late rate 8.1%. Seller hands the parcel to the carrier after
  `shipping_limit_date` in 9.0% of orders; those orders are late 24% of the time vs 6.5%.
- 1,729 orders are still in flight (`shipped`, `processing`, `invoiced`, `approved`, `created`).
- 1,275 orders (1.3%) involve more than one seller; 9,635 have more than one item.
- 547 orders have more than one review; 768 orders have none. Low-review (≤2★) rate is 14.7%
  overall, 54% for late orders and 9% for on-time orders.
- Last purchase 2018-10-17; last recorded delivery 2018-10-17.

## Shared order feature table — `app/data/orders.py`

`build_order_features(datasets_dir) -> OrderFeatures` (dataclass: `frame: pd.DataFrame`,
`exclusions: dict`). One row per order. Sources: orders, items, products, sellers, customers,
geolocation, reviews, category translation.

Item aggregation to order grain (never join a one-to-many table un-aggregated):

| feature | definition |
| --- | --- |
| `n_items`, `n_sellers` | item rows, distinct sellers |
| `total_price`, `total_freight` | sums of item price / freight |
| `total_weight_g`, `max_volume_cm3` | sum of product weight, max of length×height×width (NaN if missing) |
| `category` | English category of the highest-price item (NaN if unknown) |
| `seller_id`, `seller_state` | seller of the highest-price item |
| `shipping_limit` | earliest `shipping_limit_date` across items |

Order/customer features: `customer_state`, `same_state` (seller_state == customer_state),
`distance_km` (haversine between the mean lat/lng of the seller and customer zip prefixes;
NaN if either prefix is missing from the geolocation file), `purchase_month` (1–12),
`purchase_weekday` (0–6), `purchase_ts`, `promised_days` (estimated delivery date − purchase
date, in days), `freight_ratio` (`total_freight / total_price`, NaN if price is 0).

Seller history (leak-controlled): orders are sorted by `purchase_ts`; per seller, the
expanding count and late rate over *earlier* orders (shifted by one so an order never includes
itself): `seller_prior_orders`, `seller_prior_late_rate` (NaN when no prior order). Known
simplification: the prior order's outcome may not have been observable yet at purchase time.

Outcomes (NaN where not applicable): `delivered` (bool), `delivery_days` (customer delivery −
purchase), `days_late` (customer delivery − estimated; negative when early), `late`
(`days_late > 0`, only for delivered orders with a delivery date), `handover_late`
(carrier date > `shipping_limit`), `review_score` (latest review by
`review_answer_timestamp`, tie → highest `review_id` for determinism), `low_review`
(`review_score <= 2`, NaN if no review).

`exclusions` reports: delivered orders without delivery date, orders without items, orders
without geolocation match, orders without review, orders with >1 review (count collapsed).

## Classifiers — `app/models/risk.py`

Both models use `sklearn.ensemble.HistGradientBoostingClassifier` (handles NaN natively;
categorical features `category`, `seller_state`, `customer_state` passed via
`categorical_features` after ordinal encoding with unknown → NaN) with
`max_iter=300, learning_rate=0.05, max_leaf_nodes=31, class_weight="balanced"` and
`random_state=42`.

Temporal split: train = purchases before `2018-06-01`, test = purchases in
`2018-06-01..2018-08-31`. The split date is a constant in `app/config.py`.

| model | population | label | features |
| --- | --- | --- | --- |
| `late_delivery` | delivered orders with delivery date | `late` | `PURCHASE_TIME_FEATURES` = n_items, n_sellers, total_price, total_freight, freight_ratio, total_weight_g, max_volume_cm3, category, seller_state, customer_state, same_state, distance_km, purchase_month, purchase_weekday, promised_days, seller_prior_orders, seller_prior_late_rate |
| `low_review` | delivered orders with a review | `low_review` | `PURCHASE_TIME_FEATURES` + `DELIVERY_OUTCOME_FEATURES` = delivery_days, days_late, late, handover_late |

Evaluation on the test period: `roc_auc`, `average_precision`, `base_rate`, `n_train`,
`n_test`, `n_positive_test`, and precision/recall when flagging the top 10% highest-risk
orders. Permutation importance (5 repeats on the test set) for the top 10 features, stored in
metadata as observed importance, not causal effect.

Artifacts: `models/late_delivery.joblib/.json`, `models/low_review.joblib/.json` with the
same metadata shape as the sales forecast (`model_version`, `trained_at`, `dataset_hashes`
over all files used, `split_date`, `evaluation`, `feature_names`, `limitations`).

Limitations stated in metadata: late orders purchased in August 2018 may still be undelivered
and are therefore missing from the test labels (late rate under-counted); the seller-history
timing simplification above; a feature's importance is association, not cause; models are
trained on a Brazilian marketplace and describe that data only.

## Category health — `app/data/categories.py` and `app/analysis/categories.py`

`build_category_monthly(datasets_dir) -> pd.DataFrame` with columns `month, category, orders,
items, sales`: items joined to products and the translation table (untranslated names kept
as-is; missing category → `"unknown"`), orders filtered by the sales-forecast status and
date rules, aggregated per (month, category). Each item belongs to exactly one category so
there is no double counting. Missing (month, category) pairs inside the data range are filled
with zeros for categories that appear at least once.

`analyse_categories(monthly: pd.DataFrame, recent_months=3, min_recent_sales=10_000.0)
-> list[dict]`, one entry per category, sorted by recent sales descending:

- `recent`: sum of sales over the last `recent_months`; `previous`: the `recent_months` before
  that; `change_abs`, `change_pct` (None when `previous == 0`).
- `share_recent`, `share_previous`: category sales / total sales in the same windows;
  `share_change_pp` in percentage points.
- `total_change_pct`: the same recent-vs-previous change for the whole business (same for
  every row, so the UI can show the comparison).
- `flags`:
  - `underperforming_total`: `change_pct` is not None and
    `change_pct - total_change_pct <= -10` and `recent + previous >= min_recent_sales`
    (minimum support so tiny categories do not dominate the list).
  - `latest_month_anomaly`: with at least 6 earlier months, `|latest − mean(previous 3)| >
    2 × std(month-over-month differences of the earlier months)` and the std is > 0.
- `forecast`: next 3 months from `app.forecast.sales` when the category has ≥ `MIN_MONTHS`
  months in the series, else `None` with `forecast_reason = "insufficient_history"`.
- `series`: the monthly `[{"month","orders","items","sales"}]` for the category.

Every flag carries its inputs (the values compared and the threshold) under `evidence` so the
UI can show why it fired.

## API additions — `app/main.py` (routes) delegating to the modules above

- `GET /api/risk/delivery/summary` → `{ "monthly": [{"month","delivered","late","late_rate"}],
  "evaluation": {...}, "model_version", "trained_at", "limitations" }` (monthly rates are
  observed, by purchase month, over delivered orders in the data range).
- `GET /api/risk/delivery/open-orders?limit=50` → in-flight orders scored by the late model,
  sorted by `risk` desc: `order_id, status, purchase_ts, estimated_delivery, days_since_purchase,
  seller_id, seller_state, customer_state, category, total_price, risk`. `limit` 1–500.
- `GET /api/risk/delivery/sellers?min_orders=30&limit=50` → per seller, observed over the data
  range: `orders, late, late_rate, handover_late, handover_late_rate, recent_late_rate` (last
  3 months) and `earlier_late_rate`, sorted by `late_rate` desc. Deterministic; no model.
- `GET /api/risk/reviews/summary` → `{ "monthly": [{"month","reviewed","low","low_rate"}],
  "by_lateness": {"late": {...}, "on_time": {...}}, "evaluation", "importances", ... }`.
- `GET /api/risk/reviews/unreviewed?limit=50` → delivered orders without a review, scored by
  the low-review model, sorted by `risk` desc, with `days_late`, `delivery_days` and the same
  identification fields as the open-orders list.
- `GET /api/sales/categories?limit=20&flag=underperforming_total|latest_month_anomaly` →
  `{ "recent_months", "total_change_pct", "categories": [ ...without "series"... ] }`.
- `GET /api/sales/categories/{category}` → the full entry including `series`; 404 if unknown.

Model endpoints return 503 when the artifact is missing and 409 when its dataset hashes do
not match, exactly as the sales forecast does.

Startup cost: the order feature table is built once at startup (a few seconds) and cached in
`app.state`; category analysis is computed once at startup too.

## Training

`python -m app.models.train_risk` trains both classifiers and prints the evaluation table.
The sales-forecast CLI is unchanged.

## Tests (pytest, synthetic fixture extended in `tests/conftest.py`)

- Order features: multi-item order aggregated once with correct sums; category of priciest
  item; distance computed from zip centroids and NaN when missing; `promised_days` correct;
  seller prior late rate excludes the order itself and is NaN for a seller's first order;
  latest review chosen when an order has two; `late`/`low_review` NaN where not applicable.
- Classifiers: temporal split puts no test order before the split date; training with a
  fixture of ~60 synthetic orders produces metrics in [0, 1]; `predict_risk` returns one
  probability per row in [0, 1].
- Categories: zero-fill for missing pairs; `change_pct` None on zero previous;
  `underperforming_total` fires only with support and ≥10 pp gap; anomaly requires ≥6 months
  and fires on an injected spike; forecast `None` with reason when history is short.
- API: each endpoint's success shape, 503 without artifacts, 409 on stale hashes, 404 on
  unknown category, `limit`/`min_orders` validation.

## Out of scope

Frontend, LLM explanations, per-seller forecasts, calibration curves, any dataset other
than Olist (external datasets downloaded to `datasets/external/` are documented separately
and not used by this code).
