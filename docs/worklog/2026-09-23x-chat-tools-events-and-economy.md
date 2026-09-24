# 2026-09-23 — Tools for the follow-up chat, Brazilian events and economy context

Author: Claude

- The follow-up chat (`service/ai/PanelChat`) can now call 14 read-only tools in `service/ai/PanelTools`:
  - Sales and categories: `salesHistory`, `salesForecast`, `listCategories`, `categoryDetails`, `whatIfSalesChange`.
  - Measures and panels: `measureTrend`, `suggestion`, `caveats`.
  - Delivery and reviews: `deliveryAndReviews`, `leastReliableSellers`, `riskiestOpenOrders`, `ordersAtRiskOfLowReview`.
  - Outside context: `events`, `economy`.

  Only the annotated methods are approved (`PanelTools.names()`). Arguments are checked before any API call: month `YYYY-MM`, category codes `[a-z0-9_]`, what-if −50…100% over 1…6 months.
- The `PanelChat` chatbot in `config/ai/agents.json` now allows tools (`maxSteps` 4). Its prompt lists the tools, asks for at most three calls, and requires each figure to be labelled as observed, predicted, hypothetical or outside context.
- The number check (`PanelChat.allowedNumbers`) accepts figures from the panel's evidence, the system prompt and the tool replies of this conversation only, never from the history the page sends back.
- New `MosaicApi` methods: `categories`, `category`, `deliverySummary`, `reviewSummary`, `deliverySellers`, `openOrders`, `unreviewedOrders`, `events`, `economy`.
- Python, external context (not Olist data):
  - `app/data/events.py` combines three sources:
    - public holidays from the Nager.Date API, downloaded once with `python -m app.data.events` into `datasets/external/brazil_holidays_2017_2018.json` (28 holidays);
    - retail dates calculated by rule (Mother's and Father's Day, Dia dos Namorados, Children's Day, Black Friday, Cyber Monday);
    - three one-off events with source links (the 2017 general strike, the 2018 truckers' strike, the 2018 World Cup).
  - `app/data/economy.py`: `python -m app.data.economy` downloads Central Bank of Brazil SGS series 433 (IPCA), 3698 (USD/BRL), 4390 (Selic in the month), 432 (Selic target) and 24369 (unemployment) for 2017-01 to 2018-08 into `datasets/external/brazil_economy_2017_2018.csv`.
  - Routes `GET /api/context/events` and `GET /api/context/economy`, each with an optional `month`. Without the downloads, they say so rather than fail.
- The three datasets in the user's Downloads were assessed and not used:
  - `retail_store_inventory.csv`: units sold do not move with weather, promotion, discount, price or competitor price, and its "Demand Forecast" column correlates 0.997 with units sold (a leak).
  - `Financial Transactions.csv`: balances never follow from the transactions.
  - `small_business_cashflow.csv`: identical to the project's copy.
- Tests:
  - `tests/test_context.py`: retail-date rules, events by month with and without the holiday download, merge order, month validation, and economy unavailable, then filtered, with a missing value kept as `None`.
  - `PanelToolsTest`: the tool list, bad arguments never reaching the API, the outside-context label, and the unavailable economy and API.
  - `PanelChatTest`: a tool figure may be quoted, and an unlisted tool is denied.
- Verified: `python -m pytest tests -q` gives 161 passed; `mvnw install` for OpportunityImpl and `mvnw test` for OpportunityApp pass. The zip and mirror were rebuilt. Not yet checked live: the tool calls on the running site with Groq.
