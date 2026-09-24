# Valora architecture

Valora turns an SME's raw ledger into evidence-backed decisions:

```
DATA -> CLEAN -> UNDERSTAND -> DETECT -> EXPLAIN -> QUANTIFY -> SIMULATE -> ACT -> MEASURE
```

Each stage has one owner in the code. Nothing in the React app calculates a financial figure.

## System view

```
 Browser (React + TypeScript, Vite)
   |  access token in memory only; refresh token in an httpOnly SameSite=Strict cookie
   v
 FastAPI  /api/v1/*   (routes -> services -> repositories)
   |- security/      JWT, Argon2id, RBAC dependencies, rate limiting
   |- services/      use cases (import, opportunities, scenarios, audit, insights)
   |- analytics/     deterministic engine (pure pandas / numpy functions, no DB)
   |- opportunities/ detectors, confidence, target metrics and outcome measurement
   |- ml/            model registry + inference (scikit-learn, loaded from models/)
   |- repositories/  SQL access, always scoped by business_id
   v
 PostgreSQL 16   row-level security on every tenant table, append-only audit log
```

Offline, reproducible pipeline (no network needed):

```
scripts/generate_synthetic.py  -> data/synthetic/*          (synthetic SME panel)
ml/train_cash_pressure.py      -> models/cash_pressure/     (model.joblib + metadata.json with metrics)
ml/train_anomaly.py            -> models/anomaly/
ml/train_categoriser.py        -> models/categoriser/
ml/benchmark_provided_csv.py   -> models/benchmark_provided_csv.json
scripts/seed_demo.py           -> demo tenants in PostgreSQL
```

## The three AI layers

| Layer | What it does | Where |
|---|---|---|
| A. Deterministic financial engine | Revenue, expenses, margins, cash, recurring commitments, concentration, collections, duplicates, 90-day cash projection, scenario maths | `backend/app/analytics/` |
| B. Machine learning | 30-day cash-pressure probability (logistic regression), unusual-payment detection (Isolation Forest + rule), category suggestions (TF-IDF + logistic regression) | `ml/` (training), `backend/app/ml/` (inference) |
| C. Explanation | Narratives written from the numbers the engine computed, per-feature model contributions, stated impact bases, confidence breakdowns | `backend/app/opportunities/engine.py` |

The explanation layer is template-based and runs locally. It receives only the
values already computed by layer A and B, so a sentence can never state a
number the engine did not produce. No external LLM is called (see
`docs/SECURITY.md`, "Privacy-first AI").

## One ledger, one set of definitions

`analytics/ledger.py` builds a single in-memory `Ledger` (transactions, invoices,
daily cash balance) per business. Every consumer uses it:

* the Overview and Insights endpoints (`services/insights_service.py`),
* the ML feature pipeline (`analytics/features.py`), shared by training and serving, so there is no train/serve skew,
* the projection and scenario simulator (`analytics/projection.py`),
* the Opportunity Engine (`opportunities/engine.py`).

Comparisons use the last three **complete calendar months** against the three
before them. Rolling 90-day windows were rejected because they can contain four
payroll runs against three and invent a 40% "increase".

The analysis bundle is cached per business and keyed by a data version (row
count, latest insert, and a checksum of categories/exclusions), so any import,
approval or exclusion invalidates it automatically.

## Opportunity lifecycle

```
detect (engine) -> new -> reviewed -> planned -> in_progress -> completed
                                   \-> dismissed (restorable)
```

* Each finding has a stable `fingerprint`; re-running the engine updates facts
  without duplicating cards or losing status.
* While a finding is still pre-action, its baseline follows the latest data.
  When it moves to `in_progress` the start date is recorded and the baseline is frozen.
* `opportunities/targets.py` recomputes the finding's target metric on data
  recorded after the start date and compares it with the expected change
  (`achieved`, `partial`, `no_change`, `worsened`, `too_early`).
* Every transition, note and engine run is stored in `opportunity_events` and the audit log.

## Actual vs projected vs simulated vs predicted

| Kind | Source | Stored? | UI label |
|---|---|---|---|
| Actual | `transactions`, `invoices` | yes | "Actual" |
| Projected | `analytics/projection.py` run on current drivers | no (computed) | "Projected", dashed line |
| Simulated | same projection with user assumptions | only the summary, in `scenarios` | "Simulated", orange |
| Predicted | cash-pressure model | yes, in `predictions` with model version and features | "Predicted" + probability |

Scenario endpoints never write to `transactions`; a test asserts this.

## Data-quality pipeline

`services/csv_import.py` (pure) parses and validates; `services/import_service.py`
stages rows (`import_batches`, `import_rows`) and creates `proposed_changes`
(category suggestions, duplicate exclusions, payee matches). Nothing reaches
`transactions` until a user commits, and commit is blocked while duplicate
decisions are pending. Existing records are never deleted: a confirmed
duplicate is flagged `excluded` and removed from analytics only.

## Directory map

```
backend/app/
  api/v1/          auth, business, transactions, data_quality, analytics, opportunities,
                   scenarios, ml, audit, reports
  core/            config, taxonomy, errors, middleware, logging, formatting
  db/              engine/session + tenant context for RLS
  models/          SQLAlchemy models
  schemas/         Pydantic request/response models
  repositories/    SQL access (tenant-scoped)
  services/        use cases
  analytics/       deterministic engine
  opportunities/   detectors, targets, outcomes
  ml/              registry and inference
  security/        passwords, tokens, rate limiting, auth dependencies
  synthetic/       synthetic data generator and demo specification
backend/alembic/   migrations (0002 adds RLS policies and the audit trigger)
backend/tests/     pytest suite (API, security, engine, ML)
frontend/src/
  pages/           one file per page
  components/      ui primitives, layout, domain components
  components/viz/  small HTML/SVG visuals (meter, band scale, composition bar,
                   before/after, dumbbell, range bars, diverging bars, sparkline,
                   score ring, timeline)
  charts/          Recharts wrappers following one chart style
  hooks/           TanStack Query hooks
  lib/             API client, formatting, types
ml/                training and evaluation scripts
scripts/           data generation, seeding, bootstrap
data/              public/, synthetic/, demo/, reference/, eval/
models/            trained artefacts + evaluation metadata
docs/              this documentation
tests/e2e/         browser walkthrough of the demo
```

## Interface principles

Every page follows the same order: one headline answer (what needs attention),
3-5 KPI tiles with a trend or meter, one or two primary charts, then detail
(tables, evidence) behind a click, a collapsible section or a side panel.

* **Insight, then evidence, then detail.** Each page opens with a sentence or a
  handful of facts in plain type, then one visual that carries the story, then
  cards or tables for the evidence. Cards are used for charts and findings, not for
  every number; related numbers share one panel separated by hairlines.
* **One typeface, a clear scale.** Inter (bundled locally, SIL OFL), 28-30 px page
  titles, 18 px section titles, 14-15 px body, 11-12 px labels.
* **Meaning, not decoration.** A visual is used only when it answers a question
  faster than the number alone: a meter against the 14-day buffer, a band scale
  for the cash-pressure probability, before-and-after bars for tracked outcomes, a
  dumbbell for days-to-pay, a composition bar for receivables ageing.
* **Colour carries one meaning.** The Valora palette: charcoal `#2C2C2C` for text
  and structure, periwinkle `#7A80F0` for interaction, selected navigation and
  actual figures, sage `#8CA573` for positive states and gains, gold `#E1BA58` for
  highlights (simulated figures use its deeper shade `#B5871D` so a thin line
  clears 3:1), coral `#EA7957` for warnings and risks. Projected is dashed grey,
  expenses are charcoal grey. Surfaces stay neutral off-white. Status colours
  (good, watch, serious, critical) are only used for state, always with an icon
  and a text label. Chart pairs were checked with a colour-vision validator.
* **No decoration.** No gradients, glass effects, glows or "AI" labels.
* **Nothing is colour-only or hover-only.** Every bar prints its value; meters
  expose `role="meter"` with values; method notes sit behind a focusable (i).
* **Responsive by container.** Bar lists switch layout with container queries,
  so a bar is never squeezed to nothing in a narrow card; the transaction table
  becomes a card list on phones.
* **Motion is brief and optional.** Bars grow once (450 ms); animations are
  disabled for `prefers-reduced-motion` and in print.

## Valora Insight

"Ask Valora" opens a panel that answers questions about the signed-in business
from data the app already loads (`/analytics/overview`, `/insights`,
`/opportunities`, `/data-quality/health`). It is a deterministic router, not a
chatbot or a language model:

1. The question is matched to one of about 18 intents (cash, cash outlook, cash
   pressure, revenue, costs, margin, customers, suppliers, receivables,
   recurring payments, product lines, findings, priorities, outcomes, data
   health...).
2. The intent reads figures the API computed and fills a template. Every answer
   shows its figures, a small chart where useful, the data kind (actual,
   projected, predicted) and a source line with a link to the page that shows
   the same figure.
3. Forecasts beyond Valora's 90-day cash projection, market or competitor
   questions, requests to decide for the owner, and anything unmatched get a
   refusal ("I can only answer questions using the business data available in
   Valora.").
4. "Ask Valora about this" on a chart or finding passes that item as context.

Code: `frontend/src/lib/insight/engine.ts` (tested in `src/test/insight.test.ts`),
UI in `frontend/src/components/insight/`.

## Scalability notes

* Stateless API: horizontal scaling needs only a shared rate-limit store (Redis) and
  moving the in-process analysis cache to Redis or a materialised table.
* Analytics are O(transactions) per business; a 3,700-row ledger is analysed in
  about 1.5 s cold and served from cache afterwards. Long ledgers can be windowed
  (all features look back at most 13 months).
* Model artefacts are versioned files; the registry refuses artefacts trained with a
  different scikit-learn minor version and falls back to deterministic rules.
