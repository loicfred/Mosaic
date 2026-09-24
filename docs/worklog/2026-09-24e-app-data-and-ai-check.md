# 2026-09-24 — App, data and AI answer check

Author: Claude

- Python: `python -m pytest tests -q` in `Java/OpportunityApp/config/py/mosaic`: 159 passed. Every GET route in `/openapi.json` answered 200, except the intended 503 on `/api/risk/cashflow/records` and 404 for an invented finding id.
- Recomputed from the raw Olist CSVs and matched the API: monthly sales (BRL 13,449,529.68 for 2017-01 to 2018-08), late-delivery counts per month (date-only comparison with the promised date), latest-review low counts, category sales changes (health_beauty +20.3%, pet_shop +45.0%, perfumery +16.8%, computers_accessories −37.0%, sports_leisure −28.2%, baby −40.4%), forecast = last month's sales (the model loses to "same as last month"), state sales sum = history sum, shares summing to 1.
- Recent-order censoring is small: 0.7% to 1.2% of June–August 2018 orders are undelivered, so the delivery improvement holds even if all were late.
- AI (Groq `openai/gpt-oss-120b`, one call per 30 s): 8 tab answers read; 7 written by the model, 1 fixed text. Issues and data inconsistencies are listed under Outstanding work in `docs/requirements.md`.
- The data has 3,095 anonymous sellers (ID, city and state only, no names) and 74 product categories.
- Follow-up chat (4 questions) and pages checked in Chrome at desktop width: all 19 site addresses answer as expected (unknown entity 404 with a message, unknown page 404), no console errors on Findings, Payments, What-if and Cohorts. What-if baselines match the June–August averages; its issues are under Outstanding work. Phone width still unchecked: the window would not resize.
