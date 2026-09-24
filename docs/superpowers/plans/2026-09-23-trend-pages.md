# Trend pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Three overview-style pages (Delivery speed, Customer satisfaction, Seller base) with evidence, suggestion and caveat buttons, replacing the Category health, Delivery and reviews and What-if pages.

**Architecture:** Python owns every figure: a shared `app/analysis/trends.py` plus one analysis module and three routes per measure. Java gets one `Measure` enum, one page controller and template, one AI controller and two generic writers that turn the structured JSON into text, rewritten by a chatbot through the existing `CheckedWriter`.

**Tech Stack:** Python 3.13, FastAPI, pandas, pytest; Java 21+, Spring Boot, Thymeleaf, JUnit/MockMvc, Chart.js.

**Spec:** `docs/superpowers/specs/2026-09-23-trend-pages-design.md`

Execution: the user said "go" after the spec, and subagents are only spawned on request, so this plan is executed natively in the session that wrote it. Tasks name the interfaces and the tests; the code is written during execution.

## Global Constraints

- Window: last `RECENT_MONTHS` (3) months of `DATA_RANGE` against the 3 before; values pooled, never a mean of monthly rates.
- Group minimum: `MIN_RATE_ORDERS` (30) orders in both windows; tolerance `RATE_TOLERANCE_PP` (2.0).
- Unknown is `None`, never 0; a zero base gives no relative change.
- No new model, no new dataset, no Python route removed or reshaped.
- Every caveat is "where to look, not why"; limitations travel in each response.
- `Java/OpportunityApp/config/py/mosaic` is refreshed only with `.claude/hooks/mirror-python.ps1`, never edited by hand.

## Review Focus

1. A group present in only one window must not appear as a candidate or as "worsening"; test in Task 2.
2. A measure that did not improve returns `candidates: []` with `reason: "not_improving"`, and the page still renders; tests in Tasks 3 and 6.
3. An API that is down or answers an error makes the page show the notice rather than a 500 page; test in Task 6.
4. An unknown measure in `/api/trend/{measure}/…` answers 404 and never reaches the Python URL; test in Task 5.
5. The AI rewrite quoting a number not in the template falls back to the template; covered by `CheckedWriter`, pinned by a writer test in Task 5.

---

### Task 1: Shared trend helpers (`AI/app/analysis/trends.py`)

**Files:** Create `AI/app/analysis/trends.py`, `AI/tests/test_trends.py`. `opportunities.py` and `caveats.py` are being changed by another session, so they are not touched: `trends.py` keeps its own business comparison, with the same constants imported from `opportunities`.

**Produces:**
- `windows(months: list[str], n=RECENT_MONTHS) -> tuple[list[str], list[str]]` (recent, previous)
- `pooled_mean(frame, column, months) -> {"value": float|None, "orders": int}`
- `pooled_ratio(frame, numerator, denominator, months) -> {"value", "orders"}`
- `change(recent: float|None, previous: float|None, unit: str) -> {"change", "change_unit", "change_pct"}`
- `trend(recent: dict, previous: dict, unit, good_direction, recent_months, previous_months) -> {..., "improving": bool}`
- `group_windows(frame, column, group, recent, previous, min_orders=MIN_RATE_ORDERS, value=pooled_mean) -> list[dict]` with `name, recent, previous, change…`, only groups meeting the minimum in both windows
- `group_rates(frame, label, group, months) -> {"business": {...}, "by_group": {...}}`
- `candidate_checks(rates: dict, name: str) -> (checks, readiness)`
- `change_check(check_id, title, label, unit, recent, previous, worse_when, threshold, evidence=None, triggered=None)`, `groups_check(check_id, title, label, unit, groups, worse_when, threshold)`, `gap_check(check_id, title, label, unit, worse: dict, better: dict, threshold_ratio)`

Tests: pooled rate ≠ mean of rates; empty window → `None`; zero base → `change_pct None`; `improving` for up/down; `change_check` triggers exactly at threshold and not below; `groups_check` counts only groups past the threshold, worst three first; `gap_check` with zero on the better side triggers when the worse side is positive.

### Task 2: Measure modules

**Files:** Create `AI/app/analysis/delivery_speed.py`, `satisfaction.py`, `seller_base.py` and `AI/tests/test_delivery_speed.py`, `test_satisfaction.py`, `test_seller_base.py`.

Each module exposes `MEASURE: dict` (`name`, `label`, `unit`, `good_direction`, `group`, `group_label`) and:
- `monthly(frame) -> list[{"month", "orders", "value", ...}]`
- `trend(frame) -> dict` (as `trends.trend`)
- `opportunities(frame, limit) -> {"candidates", "business", "reason"}`
- `caveats(frame) -> list[check]`

Checks: delivery: `freight_share_rising` (≥ 1 pp), `orders_falling` (≤ −5%), `promised_days_rising` (≥ 1 day), `states_getting_later` (groups, ≥ 2 pp). Satisfaction: `late_orders_get_low_reviews` (gap, ratio ≥ 2), `categories_getting_worse` (groups, ≥ 2 pp), `unreviewed_share_rising` (≥ 1 pp). Seller base: `orders_per_seller_falling` (≤ −5%), `orders_falling` (≤ −5%), `new_sellers_late_more_often` (gap, ratio ≥ 1.5, first-time-seller orders vs others, recent window), `categories_crowding` (groups: sellers up, orders down).

Tests on the shared fixture (`conftest.datasets_dir`, built through `build_order_features`) plus small hand-built frames: a group in one window only is excluded; each measure's `improving` direction; seller counts are distinct sellers per month.

### Task 3: Routes

**Files:** Create nine `AI/app/api/get_{delivery,reviews,sellers}_{trend,opportunities,caveats}.py`; modify `AI/app/api/__init__.py`; test `AI/tests/test_api_trends.py`.

Route bodies: trend `{measure, label, unit, good_direction, trend, monthly, rules, limitations}`; opportunities `{measure, label, unit, good_direction, group_label, trend, business, candidates, rules, limitations, reason}`; caveats `{measure, label, unit, trend, checks, triggered, limitations}`. `limit` query 1–20 (default 5) on opportunities.

Tests: each route 200 on the fixture app with those keys; `limit=0` → 422; `/openapi.json` lists the nine paths.

### Task 4: Remove the three pages (Java)

Delete `CategoryController`, `RiskController`, `ScenarioController`, `ScenarioSummaryController`, templates `categories.html`, `category.html`, `risk.html`, `scenario.html`, fragment folders `categories`, `category`, `risk`, `scenario`, and the `MosaicApi` methods only they used (+ their `MosaicApiTest` cases and fixtures). `ScenarioNarrator`, its chatbot and `salesImpact` stay for phase 2. Update `PagesRenderTest` (remove their tests). Run both modules' tests.

### Task 5: Java trend services

**Files:** Create `OpportunityImpl/.../obj/Measure.java` (enum `DELIVERY("delivery", "Delivery speed", …)`, `REVIEWS("reviews", "Customer satisfaction", …)`, `SELLERS("sellers", "Seller base", …)`, `fromPath(String) -> Optional<Measure>`), `service/ai/TrendAdvisor.java`, `service/ai/TrendCaveatWriter.java`, their tests; modify `MosaicApi` (`trend`, `trendOpportunities`, `trendCaveats`), `LocalAi` (`TREND_ADVISOR`, `TREND_CAVEATS`), `config/ai/agents.json` (two chatbots). Create `OpportunityApp/.../controller/api/TrendAiController.java` + test.

Tests: templates for improving / not improving / no candidates; every `kind` of caveat written; unknown measure → 404; a fake AI reply with an invented number falls back.

### Task 6: Java trend pages

**Files:** Create `OpportunityApp/.../controller/TrendController.java`, `templates/trend.html`, `templates/fragments/trend/page.html`; modify `charts.js` (`days` unit, `trend` drawer), sidebar, footer, help guide; test fixtures `OpportunityImpl/src/test/resources/api/trend-*.json` from the real API; `PagesRenderTest` cases.

Tests: each page renders its chart id, three buttons and `data-url="/api/trend/<m>/advice"`; API down shows the notice; a not-improving trend renders.

### Task 7: Verify, document, mirror

Run `python -m pytest tests -q` (AI), both Maven modules' tests, start the API and fetch `/api/health`, `/openapi.json` and the nine routes against the real data, rebuild mirror and zip, open each page in the browser. Update `docs/requirements.md` and write `docs/worklog/2026-09-23t-trend-pages.md`.
