# 2026-09-23 — Chart kinds, example questions, eight more tools and new breakdowns

Author: Claude

- Chart kinds:
  - Every chart a chat answer carries now has a `shape` (`time` or `categories`), a `kind` and the `kinds` that suit it: `line`/`area`/`bar` for values over months; `bar`/`hbar` for comparisons; `doughnut`/`pie`/`bar`/`hbar` only for parts of one whole (sales mix, star ratings), so a pie is never offered for data that does not add up.
  - `MosaicCharts.render(id, spec, kind)` in `charts.js` draws any of them.
  - `PanelChat.withAskedKind` applies a kind the question names ("as a pie chart", "horizontal bars") where it suits the data.
  - Each chart card has buttons to switch between its kinds (`panels.js`).
- Easier to ask: five clickable example questions under each chat box (`EXAMPLES` in `panels.js`, one set for suggestions and one for caveats).
- Chat layout: the whole conversation scrolls as one (`.chat-log` capped at `min(70vh, 720px)`) with the question box below. Messages and chart cards no longer shrink, which is what made a single message scroll.
- New Python data (`app/analysis/business_profile.mix`, new `app/analysis/breakdowns.py`) and routes:
  - `GET /api/sales/mix?by=category|payment_type|customer_state|seller_state&months=` groups the largest 8 and folds the rest into "other"; orders with no value in the column are counted separately.
  - `GET /api/sales/metrics` gives average order value, freight share, cancellations, instalments and returning customers by month.
  - `GET /api/breakdowns/buying-times?by=weekday|hour` covers every slot, with empty ones as 0 orders.
  - `GET /api/breakdowns/customer-states` leaves a rate empty below `min_orders`.
  - `GET /api/breakdowns/review-scores` counts 1 to 5 stars.
- On the real data: 78.5% of recent sales are paid by credit card; 58% of rated orders get 5 stars and 10.7% get 1 star. SP customers wait 8.7 days with 4.5% late orders; RJ customers wait 15.2 days with 12.1% late.
- Eight new tools in `PanelTools` (22 in all): `salesMix`, `businessMetricByMonth`, `compareCategories`, `economyTrend`, `eventsBetween`, `buyingTimes`, `customerStates`, `reviewScores`. Each validates its arguments and labels its figures, and the `PanelChat` prompt in `config/ai/agents.json` lists them.
- Tests:
  - `tests/test_breakdowns.py`, plus mix and metrics tests in `tests/test_caveats.py`.
  - `PanelToolsTest`: the tool list, the new chart format, pies only for parts of a whole, argument checks.
  - `PanelChatTest`: the question picks the kind only where it suits.
  - Verified: Python 170 passed; OpportunityImpl `install` and OpportunityApp `test` pass; `node --check` passes on `charts.js` and `panels.js`. The zip and mirror were rebuilt.
- Not yet checked live: the chart kinds, the example questions and the new tools (the site needs a restart).
