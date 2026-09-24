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

Guiding rule: show what the owner needs to know now; keep everything else one
click away. "Simplify the presentation, not the product."

**Card style.** Every page is built from white rounded panels (20 px radius, soft
shadow) on a cool grey page. A card has a title and one-line subtitle, one large
figure where there is one, supporting detail, and at most one *insight strip* at
its foot: a single sentence built from real figures plus one next step
(`components/ui/insight-strip.tsx`). Tabs, filters and search are pill-shaped;
the active tab or menu item is a charcoal pill.

**Overview as a Z.** The eye travels: logo (top left) → profile and display
settings (top right) → cash position (left) → recommended next step (right, the
one highlighted periwinkle card with the primary action) → last 3 months (left) →
cash outlook chart (right) → other important findings (full width). On phones the
same order becomes one column.

* **One primary action per screen.** On the Overview it is "See what to do" in
  the highlighted card; everything else is a secondary button or a text link.
* **One AI entry point.** "Ask Valora" is a single labelled button, bottom right,
  on every page; its suggested questions follow the page you are on.
* **Numbers always have context** in words ("18 days of outflows covered",
  "2.6% lower"); changes carry an arrow, a colour and the words, never colour alone.
* **Actual, projected, predicted, simulated** are named in the text or a label;
  synthetic demo data is disclosed in the header.
* **Colour.** Charcoal `#2C2C2C` text and structure; periwinkle `#6770F7`
  interaction (buttons `#4F57EB`, highlighted card `#4F57EB`); sage `#7DB356`
  positive; gold `#F5B82E` highlights and simulated figures (`#B07A06` on charts);
  coral `#FF6B45` warnings and risks.
* **States.** Loading placeholders have the page's shape; errors say what
  happened, what it means and offer "Try again"; empty sections say what will
  appear there and when.

**Accessibility, for every kind of user.**

* *Display settings* (header, accessibility icon): text size Standard / Large /
  Larger (the whole interface scales, sizes are in rem), High contrast (darker
  secondary text, stronger borders, underlined links, thicker focus ring) and
  Reduce motion. Saved in the browser only (`lib/a11y.ts`); the operating
  system's reduced-motion setting is also honoured.
* "Skip to main content" link as the first focusable element; landmarks (nav,
  main, aside); one h1 per page and ordered h2/h3; visible focus everywhere; all
  menus, tabs and sliders work from the keyboard; 40-44 px touch targets for
  primary controls; no text under 12 px.
* Checked with axe-core (WCAG 2 A/AA + best practice): no violations on login,
  Overview, Opportunities, Scenario Lab, Transactions, Data Health and the
  Ask Valora panel, including with Larger text and High contrast switched on.

## Valora Insight

"Ask Valora" opens a panel that answers questions about the signed-in business
with an LLM (Groq). `POST /insight/ask` (`backend/app/services/assistant_service.py`)
builds a compact JSON summary of the analysis bundle (the same figures as
`/analytics/overview`, `/insights`, `/opportunities`, `/data-quality/health`),
sends it with the question and recent turns, and requires a JSON reply
(headline, body, facts, data kind, follow-ups). The model picks a chart and
sources by key from catalogues the server builds, so every plotted number and
every link comes from the analysis. See docs/SECURITY.md "AI assistant".

When `GROQ_API_KEY` is not set or the call fails, the panel falls back to a
deterministic router in the browser:

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
