# Sales Impact Scenario Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn a sales change into evidence-backed downstream consequences, and let a local Gemma (LM Studio) narrate them without inventing numbers.

**Architecture:** `app/analysis/impact.py` computes consequences from data already cached in `app.state`. `app/ai/client.py` talks to LM Studio's OpenAI-compatible endpoint; `app/ai/explain.py` builds the prompt, verifies every number in the reply against the evidence, and falls back to a deterministic template. `app/api/scenarios.py` exposes both.

**Tech Stack:** pandas, numpy, httpx, FastAPI, pytest.

**Spec:** `docs/superpowers/specs/2026-09-22-sales-impact-scenario-design.md`

## Global Constraints

- Run from `AI/` with `.venv/Scripts/python.exe`. No new dependencies (`httpx` is already present).
- The narrative is presentation only; authoritative numbers live in `consequences`/`evidence`.
- No test may contact LM Studio — stub the client.
- Endpoints must work with no LLM running and with no trained model artifacts.
- No commits unless asked.

---

### Task 1: Config

**Files:** Modify `app/config.py`.

- [ ] Add `LLM_BASE_URL` (env `MOSAIC_LLM_BASE_URL`, default `http://localhost:1234`), `LLM_MODEL` (env `MOSAIC_LLM_MODEL`, default `""`), `LLM_TIMEOUT_SECONDS` (env, default `20.0`), `LLM_ENABLED` (env `MOSAIC_LLM_ENABLED`, default true, parsed so `"0"`/`"false"` disable).

### Task 2: Consequence engine

**Files:** Create `app/analysis/impact.py`, `tests/test_impact.py`.

**Produces:**
```python
RECENT_MONTHS = 3
P_LOW_GIVEN_LATE / P_LOW_GIVEN_ON_TIME computed from data, not constants
def fit_volume_late_rate(monthly_orders, monthly_late_rate) -> dict  # slope, intercept, r_squared, n_months, slope_pp_per_1000_orders
def seller_capacity_strain(orders_frame, extra_orders_per_month, recent_months, top) -> dict
def compute_sales_impact(monthly, orders_frame, horizon, sales_change_pct) -> dict
```

- [ ] Tests first, per the spec's Tests section (fixture arithmetic, negative change, zero baseline `None` + reason, clipping, low-review split, strain counting, horizon totals).
- [ ] Implement; run → PASS.

### Task 3: LM Studio client

**Files:** Create `app/ai/__init__.py`, `app/ai/client.py`, `tests/test_ai_client.py`.

**Produces:** `ChatResult(text, error, model)`, `complete(prompt, *, base_url, model, timeout, temperature=0.2) -> ChatResult`, `list_models(base_url, timeout) -> list[str]`.

- [ ] Tests with `httpx.MockTransport`: 200 returns text; 500 returns `error`; connection error returns `error`; a single user message is sent (no system role) and `model` is omitted when empty.
- [ ] Implement; run → PASS.

### Task 4: Prompt, numeric guard, fallback

**Files:** Create `app/ai/explain.py`, `tests/test_explain.py`.

**Produces:** `build_prompt`, `allowed_numbers`, `verify_numbers`, `template_narrative`, `explain(evidence, *, settings, client=...) -> dict`.

- [ ] Tests: guard passes a faithful narrative, flags an invented figure, ignores small numbers; template used on client error / non-200 / guard failure with correct `reason`; `explain=False` makes zero client calls; prompt contains no raw order ids.
- [ ] Implement; run → PASS.

### Task 5: API routes

**Files:** Create `app/api/scenarios.py`; modify `app/main.py`; create `tests/test_api_scenarios.py`.

- [ ] Tests: `POST /api/scenarios/sales-impact` success shape with stubbed LLM; 422 on `horizon=0/7` and `sales_change_pct=-80/200`; works with no model artifacts; `explain=false` returns `source="template"`; `GET /api/ai/health` returns 200 with `reachable: false` when nothing listens.
- [ ] Implement (Pydantic request model; router mounted in `create_app`); run → PASS.

### Task 6: Docs and verification

- [ ] Update `AI/README.md` (new endpoints, LM Studio setup, env vars, the assumptions and their evidence).
- [ ] `pytest -q`; start the server; call the scenario endpoint with `explain=false` and, if LM Studio is running, with `explain=true`; report both.
