# Sales impact scenario and LLM explanation — design

Date: 2026-09-22. Status: approved for implementation. Builds on
`2026-09-22-sales-forecast-design.md` and `2026-09-22-risk-and-category-models-design.md`.

## Goal

Answer one question with evidence: **if sales rise, what else changes?**

A deterministic engine turns a sales change into downstream consequences (orders, late
deliveries, low reviews, seller capacity strain, sales value exposed to late delivery), each
carrying the inputs it was computed from. A pretrained language model (Gemma served locally by
LM Studio) then writes a plain-language narrative **from those computed numbers only**.

Training a transformer from scratch is out of scope, per the project brief. The model here is
a pretrained LLM used as an explainer; it never produces the numbers.

## Data facts driving the design (measured on the real data, 2017-01..2018-08)

- Average order value, last 3 months: **BRL 137.86**.
- Late rate, last 3 months: **3.61%** (well below the 8.1% full-period rate).
- Monthly orders vs monthly late rate: fitted line `late_rate = 0.0032 + 1.124e-05 × orders`,
  so **+1,000 orders ≈ +1.12 pp**, but **R² = 0.27** over 20 points — weak, and driven by
  Nov 2017 and Feb–Mar 2018. Must never be stated as causal.
- Low-review rate: **62.4% when late**, **9.2% when on time**.
- 1,810 sellers were active in the last 3 months. At +20% volume, **41** would exceed their own
  busiest month ever, when each seller's recent volume is averaged over a fixed three months.
  (An earlier exploratory figure of 529 averaged only the months in which a seller was active,
  which inflates sellers who appear in one month; the fixed-three-month average is used.)

## Consequence engine — `app/analysis/impact.py`

`compute_sales_impact(monthly, orders_frame, horizon, sales_change_pct, ...) -> dict`, pure
functions over data already held in `app.state`.

Baseline: the last `RECENT_MONTHS = 3` observed months. Projected monthly sales =
`baseline_monthly_sales × (1 + sales_change_pct/100)`. Every derived figure below is per month
of the horizon and also totalled across the horizon.

| Output | Formula | Notes |
| --- | --- | --- |
| `aov` | `recent_sales / recent_orders` | BRL, observed |
| `projected_orders` | `projected_sales / aov` | Assumes basket size unchanged |
| `extra_orders` | `projected_orders − baseline_orders` | May be negative |
| `late_rate_held` | recent late rate | Variant A |
| `late_rate_fitted` | `intercept + slope × projected_orders`, clipped to `[0, 1]` | Variant B; reported with `slope_pp_per_1000_orders`, `r_squared`, `n_months` |
| `expected_late` | `projected_orders × late_rate` | One per variant |
| `expected_low_reviews` | `expected_late × p_low_given_late + (projected_orders − expected_late) × p_low_given_on_time` | Conditional rates observed over the data range |
| `sales_exposed_to_late` | `expected_late × aov` | Labelled **exposure, not loss** |
| `sellers_at_capacity` | Extra orders distributed by each seller's recent share; count and list sellers whose projected monthly orders exceed their own historical peak month | `{count, active_sellers, top: [{seller_id, recent_monthly_orders, projected_monthly_orders, historical_peak, over_peak_pct}]}` |

`assumptions` (returned, shown in the UI): basket size constant; seller mix constant; the
fitted volume→lateness line is association over 20 months, not cause; capacity proxied by a
seller's busiest observed month; sales are gross item sales, not profit or cash.

Edge cases: zero baseline orders or zero AOV → consequences are `None` with
`reason: "no_baseline_activity"` rather than a division error. `sales_change_pct` may be
negative (the engine is symmetric). Horizon 1–6.

## LLM explanation — `app/ai/`

`app/ai/client.py` — thin OpenAI-compatible client over `httpx`:

```python
@dataclass(frozen=True)
class ChatResult:
    text: str | None
    error: str | None
    model: str | None

def complete(prompt: str, *, base_url, model, timeout, temperature=0.2) -> ChatResult
def list_models(base_url, timeout) -> list[str]        # GET /v1/models
```

`POST {base_url}/v1/chat/completions` with a **single user message** (no system role: Gemma's
chat template has no system turn and some templates reject one), `temperature=0.2`,
`max_tokens=400`. Any connection error, timeout or non-200 returns `ChatResult(error=...)` —
never raises.

`app/ai/explain.py`:

- `build_prompt(evidence: dict) -> str` — embeds only the computed scenario JSON (no raw
  records, no customer data) and instructs: use only the given numbers, three short
  paragraphs (what changes / what to watch / what to check next), state that the
  volume–lateness link is an association, do not predict certainties.
- `allowed_numbers(evidence) -> set[str]` — every numeric value in the evidence, rendered in
  the formats the model might use (integer, thousands separator, one and two decimals,
  percentage forms).
- `verify_numbers(text, allowed) -> list[str]` — returns unsupported numbers found in the
  text. Numbers ≤ 12 and the horizon months are allowed as ordinary prose ("three months").
- `template_narrative(evidence) -> str` — deterministic paragraph built from the same values.
- `explain(evidence, settings) -> dict` → `{"text": str, "source": "llm"|"template",
  "model": str|None, "reason": str|None}`. Order: if disabled → template; call the model; on
  error → template with the error as `reason`; on unsupported numbers → template with
  `reason: "unsupported_numbers: ..."`.

The narrative is presentation only. Authoritative figures stay in `consequences`/`evidence`.

## API — `app/api/scenarios.py`

- `POST /api/scenarios/sales-impact`
  Body: `{"horizon": 1-6 (default 3), "sales_change_pct": -50..100 (default 20),
  "explain": bool (default true)}` → `{scenario, assumptions, consequences, evidence,
  narrative, limitations}`. Validation errors → 422. Needs no trained model artifact: it uses
  observed history, so it works when nothing is trained.
- `GET /api/ai/health` → `{"configured_base_url", "reachable": bool, "models": [...],
  "error": str|null}`; never raises, 200 even when LM Studio is down.

Config added to `app/config.py`: `LLM_BASE_URL` (`MOSAIC_LLM_BASE_URL`, default
`http://localhost:1234`), `LLM_MODEL` (`MOSAIC_LLM_MODEL`, default `""` meaning "whatever is
loaded"), `LLM_TIMEOUT_SECONDS` (default 20), `LLM_ENABLED` (`MOSAIC_LLM_ENABLED`, default
true).

## Tests

- Impact: extra-orders arithmetic against hand-computed fixture values; negative change
  reduces orders; zero baseline returns `None` with a reason; fitted late rate clipped into
  `[0, 1]`; low-review split uses both conditional rates; seller strain counts only sellers
  above their own peak; horizon totals equal per-month × horizon.
- Explain: guard accepts a narrative using only evidence numbers; rejects one containing an
  invented figure; small numbers and the horizon are not flagged; template fallback used on
  client error, on non-200, and when the guard fails, each with the right `reason`;
  `explain=false` never calls the client (stub asserts zero calls).
- Client: non-200 and connection error both produce `ChatResult(error=...)` without raising
  (stubbed transport — no test contacts LM Studio).
- API: success shape; 422 on out-of-range horizon and change; `/api/ai/health` returns 200
  with `reachable: false` when nothing is listening.

## Out of scope

Chat over the whole database, LLM-proposed scenario parameters, streaming responses, prompt
caching, any provider other than the OpenAI-compatible local endpoint (switching to a hosted
provider is a base-URL and key change, deliberately not built now).
