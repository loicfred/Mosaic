# Trend pages: the overview's suggestion and caveat system for three more measures

Date: 2026-09-23. Author: Claude. Status: approved in chat, awaiting spec review.

## Goal

The overview shows monthly sales and three buttons: **Show evidence**, **Suggest investment** and **View possible
caveats**. Build three pages that work the same way for other measures, and replace the pages the user called useless.

- Remove the site pages **Category health** (`/categories`, `/categories/{name}`), **Delivery and reviews** (`/risk`)
  and **What if sales change?** (`/scenario`).
- Add three pages, each a copy of the overview for one measure:

| Page (path) | Measure | Good direction | Suggestion: where the opportunity is | Caveats checked |
| --- | --- | --- | --- | --- |
| Delivery speed (`/delivery`) | Late-delivery rate of delivered orders | down | Customer states whose late rate fell, with enough orders, to promote faster delivery there | freight share of price rising; order volume falling; promised delivery time lengthening; states whose late rate rose |
| Customer satisfaction (`/reviews`) | Share of reviewed orders scored 1 or 2 | down | Categories whose low-review rate fell while their sales grew | late orders still get low reviews; categories whose low-review rate rose; share of delivered orders not yet reviewed rising |
| Seller base (`/sellers`) | Active sellers per month (sellers of an order's priciest item) | up | Categories where active sellers grew and orders grew too, so new sellers are finding customers | orders per seller falling; order volume falling; orders from first-time sellers delivered late more often; categories where sellers grew but orders fell |

Figures seen in the data while designing (last 3 months Jun–Aug 2018 against Mar–May): late rate ≈ 10% → 3.6%,
low-review rate ≈ 14.6% → 9.7%, freight share ≈ 21.7% → 24%, active sellers 1,574 → 1,810 while orders fell
20,975 → 18,885. Average basket was the first choice for the third page, but it fell in this window (141.9 → 138.5 BRL),
so it would never show a good result; the seller base replaced it. The checks compute these from the data at request
time; nothing in this table is hard-coded.

## What stays

- Every Python route stays, including `/api/sales/categories*`, `/api/risk/*` and `/api/scenarios/sales-impact`: the
  Help page lists them and phase 2 (below) needs the scenario route. Only the Java pages that call them go.
- The overview and its sales suggestion and caveats are unchanged.
- No new model is trained. The trend is observed data: the last 3 months against the 3 before, pooled
  (sum of counts over sum of totals, not a mean of monthly rates), as `caveats.window_rate` already does.

## Python (`AI/`)

One analysis module per measure, and the shared window helpers in one place:

- `app/analysis/trends.py`: the window split (last `RECENT_MONTHS` against the ones before), pooled window values
  (`pooled_mean`: sum over count of known values, so a rate is late orders over delivered orders, not a mean of
  monthly rates; `pooled_ratio`: sum over sum), `change(recent, previous, unit)` (percentage points for rates,
  the unit's own difference otherwise, plus a relative %; `None` whenever either side is unknown or the base is 0),
  `trend(...)` with `improving` read against `good_direction`, the per-group windows and business comparison for
  suggestions, and three caveat builders. Each caveat is `{id, kind, triggered, title, comparison | groups | gap,
  threshold, evidence}` with `kind` one of `change` (recent against previous for one figure), `groups` (how many
  states or categories moved the wrong way, with the worst three) and `gap` (one group against another, such as late
  against on-time orders). Units are `rate | brl | days | count`, so Java writes any check from its kind without a
  per-id switch.
- `app/analysis/delivery_speed.py`, `app/analysis/satisfaction.py`, `app/analysis/seller_base.py`: each has
  `monthly(frame)`, `opportunities(frame, limit)` and `caveats(frame)`.

Suggestions reuse the sales rules: a group (state or category) needs at least `MIN_RATE_ORDERS` (30) orders in
**both** windows; it must have improved at least as much as the business. Each candidate carries its recent and
previous values, its change, its size (share of recent orders) and the same `better / in_line / worse` checks
against the business with `RATE_TOLERANCE_PP`, plus `readiness` (`ready / fix_first / unknown`) and its monthly
series for the chart. When the business measure did not improve, `candidates` is empty and `reason` is
`not_improving`, as sales returns `sales_not_increasing`.

Routes, one module each, registered in `app/api/__init__.py`, each with `summary=`:

| Module | Route |
| --- | --- |
| `get_delivery_trend.py`, `get_delivery_opportunities.py`, `get_delivery_caveats.py` | `/api/delivery/trend`, `/opportunities`, `/caveats` |
| `get_reviews_trend.py`, `get_reviews_opportunities.py`, `get_reviews_caveats.py` | `/api/reviews/trend`, `/opportunities`, `/caveats` |
| `get_sellers_trend.py`, `get_sellers_opportunities.py`, `get_sellers_caveats.py` | `/api/sellers/trend`, `/opportunities`, `/caveats` |

Every response has the same top-level shape per kind (`measure`, `unit`, `good_direction`, `trend`, `rules`,
`limitations`, then `monthly`, `candidates` or `checks`), so one Java page and one pair of writers handle all three.
Every response states its limitations: past change is not proof of cause; sales are not profit; the latest months
can still have orders in transit or unreviewed.

Populations: delivery uses delivered orders with a delivery date (`late` known); satisfaction uses orders with a
review (`low_review` known), latest review per order; seller base uses orders with items, status not in `EXCLUDED_STATUSES`, in
`DATA_RANGE`. All three use the one-row-per-order frame `app.state.orders.frame`, so items and payments are never
double counted.

Tests (`AI/tests/test_trends.py`, `test_delivery_speed.py`, `test_satisfaction.py`, `test_seller_base.py`): pooled rates
against a mean of rates; zero denominators and empty windows give `None`, never 0; the improving direction per
measure; candidates below the order minimum excluded; a caveat triggers exactly at its threshold; and each route answers 200 on the test app with the documented keys.

## Java (`Java/`)

- `MosaicApi`: `trend(Measure)`, `opportunities(Measure)`, `caveats(Measure)`, where `Measure` is an enum
  `DELIVERY, REVIEWS, SELLERS` holding its API path, page title and question, so no free text reaches a URL.
  Remove `categories`, `category`, `deliverySummary`, `openOrders`, `sellers`, `reviewSummary`, `unreviewed` and
  their tests and fixtures. `salesImpact` stays: phase 2 answers "what if sales change" through it.
- `TrendController`: `GET /delivery`, `/reviews`, `/sellers` → `trend.html` with the fragment `fragments/trend/page.html`
  (chart, the three buttons, the evidence panel with its rules and limitations).
- `TrendAiController`: `GET /api/trend/{measure}/advice` and `/api/trend/{measure}/caveats`, answering as
  `OverviewAiController.answer` does (text, source, model, reason, evidence).
- `TrendAdvisor` and `TrendCaveatWriter` in `service/ai`: a fixed template from the structured fields, rewritten by the
  new chatbots `TrendAdvisor` and `TrendCaveats` in `config/ai/agents.json` through `CheckedWriter`, so an
  unavailable model or an invented number keeps the template.
- `ScenarioNarrator` and its chatbot stay for phase 2, which writes what-if answers with them; only the scenario
  page's controllers go.
- Remove `CategoryController`, `RiskController`, `ScenarioController`, `ScenarioSummaryController`, the templates
  `categories.html`, `category.html`, `risk.html`, `scenario.html` and `fragments/{categories,category,risk,scenario}/`.
- Sidebar, footer and Help guide list Overview, Delivery speed, Customer satisfaction, Seller base, Help. The
  sidebar's "Flagged categories" links go.
- The page script copies the overview's `sales.html` pattern: each panel fetches once per page load
  (`panel.dataset.requested`) and draws its evidence charts from the returned `evidence`, as `adviceCharts` and
  `caveatCharts` do there.
- `charts.js`: the existing `rate`, `lines` and `bars` draw the trend and the panel charts; a `days` unit is added
  to `fmt`.
- `PagesRenderTest`: each trend page renders from a fixture and still renders with the API down; the removed pages'
  tests go. Writer tests cover the template, the "not improving" case and the number check.

## Phase 2 (after this, separate spec)

Turn each panel into a conversation box: the person can ask follow-ups such as "what if sales fall 10% next month?",
and the answer uses the predictive models through allowlisted API calls (`/api/scenarios/sales-impact`,
`/api/sales/forecast`), with the same number check. The assistant and `MosaicToolbox` were deleted in the working
tree by another session; whether to restore their tool calling or build smaller is decided in that spec.

## Out of scope

New models, new datasets, payments data, restyling the overview, removing unused Python routes or CSS.
