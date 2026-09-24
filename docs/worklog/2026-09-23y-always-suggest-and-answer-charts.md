# 2026-09-23 — The suggestion always answers; chat answers carry charts

Author: Claude

- The sales forecast now uses the method with the lowest backtest error (`naive_last`, a change made outside this session), which forecasts −1.7%. The suggestion therefore said "no category is suggested". At the user's request it now always suggests:
  - `opportunities.investment_candidates` gives each candidate a `basis`: `growing` when any category grows at least as fast as the business; otherwise `beats_business` (falling less than the business); otherwise `best_available` (the smallest falls). Categories below `MIN_RECENT_SALES` are never suggested.
  - `/api/sales/opportunities` no longer stops when the forecast does not rise. The forecast is context (`trend.increasing`), `rules.basis` and a limitation explain this, and `reason` is only `no_categories_with_enough_sales`.
  - `InvestmentAdvisor` frames a non-rising forecast as "where to hold or shift effort". The prompt gains `forecast_direction` and each candidate's `basis`, and the `InvestmentAdvisor` system prompt in `config/ai/agents.json` says to frame it that way and state the basis.
  - On the real data: forecast −1.7%, and the 5 growing categories are all `ready`.
- Chat answers now show charts of the data behind them:
  - `PanelTools` records a chart spec (`lines` or `bars`, with title, caption and unit) from the same API reply as its text, for `salesHistory`, `salesForecast` (observed plus the forecast and its range), `listCategories`, `categoryDetails`, `whatIfSalesChange`, `measureTrend`, `deliveryAndReviews` and `leastReliableSellers`.
  - One `PanelTools` is made per question, so charts never mix between visitors; it is no longer a Spring bean.
  - `PanelChat.ask` returns `Answer(narrative, charts)`. Only an answer that passed the number check carries charts. `PanelChatController` adds `charts` to the JSON, and `panels.js` draws them under the answer with `MosaicCharts.lines` or `bars`.
- Checked live before these changes: switching tabs keeps each panel's answer, charts and chat, and the forecast tool answered correctly in about 4 s.
- Tests:
  - Python: the three `basis` fallbacks, and the endpoint answering whatever the forecast.
  - Java: `InvestmentAdvisorTest` for a flat forecast (still suggests) and for no candidates (never asks the model); `PanelToolsTest` for chart recording.
  - `python -m pytest tests -q` gives 164 passed, and both Java modules' tests pass.
- Not yet checked live: charts under chat answers, and the suggestion with a falling forecast (the site needs a restart).
- Live test after the restart:
  - The suggestion works again with a falling forecast (5 candidates, 5 charts).
  - A forecast follow-up was answered from the panel's own figures, without a tool.
  - Two tool questions sent 6 s apart failed on Groq's per-minute limit; the same question 15 s later used `categoryDetails` and returned its chart.
- Follow-ups from that test:
  - Each panel's charts now sit directly under its answer, with the conversation below (`panel-charts` before `panel-chat-slot` in `sales.html` and `trend/page.html`).
  - `PanelChat` retries once after a refused call (`retryWaitMillis`, 4 s).
  - A follow-up answer that used no tool gets the panel's main chart attached (`panelChart` in `panels.js`, labelled "From this panel's figures").
  - The `PanelChat` prompt asks the model to call the matching tool so the owner sees the chart.
  - `InvestmentAdvisor`, `CaveatWriter`, `TrendAdvisor` and `TrendCaveats` now forbid profit and margin talk; the live suggestion had said "better margin potential".
- Both Java modules' tests pass; `node --check panels.js` passes.
