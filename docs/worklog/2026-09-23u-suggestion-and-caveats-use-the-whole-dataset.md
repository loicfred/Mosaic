# 2026-09-23 — The overview's suggestion and caveats use nearly the whole dataset

Author: Claude

- The order frame (`AI/app/data/orders.py`) now also reads `olist_order_payments_dataset.csv` (new `PAYMENTS_FILE` in `ALL_DATASET_FILES`) and the customers' `customer_unique_id`. New one-row-per-order columns:
  - `payment_total`, `installments` (the most of any payment), `payment_methods` and `payment_type` (the type that paid the most). Payments are reduced to the order before the join.
  - `returning_customer` (the same person ordered earlier).
  - `cancelled` (status in `EXCLUDED_STATUSES`).
  - `purchase_period` ("YYYY-MM", built once).
  - A new exclusion, `orders_without_payment`.
- New `AI/app/analysis/business_profile.py`: `placed_orders`, `profile`, `windows` and `monthly`. Each measure carries its count and total, and an empty denominator gives `None`. Cancellations count every order placed, because many cancelled orders have no items; the other measures use orders with items.
- Suggestion (`opportunities.py`, `/api/sales/opportunities`):
  - It adds a `cancel_rate` check and a per-candidate `profile` (recent and previous).
  - It adds `risks`, each with its threshold: `depends_on_one_seller` (top seller ≥ 50% of sales), `freight_heavy` (≥ 5 points above the business) and `basket_shrinking` (average order −5% or worse).
  - There is a new readiness, `watch`, and the response gains a top-level `business_profile`.
- Caveats (`caveats.py`, `/api/sales/caveats`), new checks: `cancellations_rising` (≥ 0.25 pp), `basket_shrinking` (≤ −2%), `freight_share_rising` (≥ 1 pp), `instalments_rising` (≥ 2 pp), `few_returning_customers` (< 10%), `sales_rest_on_few_sellers` (top 10 ≥ 25%) and `sales_rest_on_one_state` (≥ 50%). The thresholds were fixed before looking at which checks trigger.
- On the real data (last 3 months against the 3 before):
  - The triggered caveats are falling categories, low reviews on late orders, cancellations (0.49% → 0.91%), basket (BRL 141.9 → 137.8), freight share (16.4% → 18.0%) and returning customers (3.5%).
  - Seller concentration (top 10 at 12.2%) and SP's share (41.0%) did not trigger.
  - All 5 suggested categories are `ready`.
- `populations.labelled_orders_in_range` uses the new `purchase_month(frame)`, which prefers `purchase_period`. The results are unchanged, and the two endpoints went from about 3.4 s to 0.9 s and from 2.9 s to 0.5 s.
- Java: `CaveatWriter` has a sentence for each new check. `InvestmentAdvisor` passes the profiles and risks to the model and names a `watch` risk in its template, and it leaves out figures a response does not carry. Only the `InvestmentAdvisor` system prompt text in `config/ai/agents.json` changed.
- `sales.html` draws, for the suggestion, freight, instalments, returning customers and cancellations against the business, average order value before and after, and the biggest seller's share. For the caveats, it draws the monthly line of each triggered business check and the concentration bars. There is a new colour, `--series-4`.
- Verified:
  - `python -m pytest tests -q` gives 155 passed.
  - `CaveatWriterTest`, `InvestmentAdvisorTest`, `CheckedWriterTest`, `NumberCheckTest` and `LocalAiTest` pass.
  - `node --check` passes on the page script.
  - The page's chart functions ran in Node against the real API output with stubbed drawing: 5 suggestion charts and 6 caveat charts, with no missing values.
- Not verified:
  - The OpportunityApp tests. The other session was rebuilding the site's pages at the time, so the module did not compile.
  - The charts in a browser.
- Later the same day, once the trend pages compiled: `OverviewAiControllerTest` and `PagesRenderTest` in OpportunityApp pass (`mvnw test`).
