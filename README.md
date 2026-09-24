# Valora

**Turn raw financial data into evidence-backed decisions for small businesses.**
Finnovate Web & AI Hackathon 2026 · Challenge 3 "Turning Financial Data into Opportunity".

> Existing financial software can tell a business what happened. Valora
> connects what happened to what should be investigated, what could be done,
> what the financial impact could be, and whether the action actually worked.

```
DATA -> CLEAN -> UNDERSTAND -> DETECT -> EXPLAIN -> QUANTIFY -> SIMULATE -> ACT -> MEASURE
```

## The problem

SME owners have bank exports and spreadsheets, not analysts. Dashboards show
totals, but they do not say *which* supplier is eroding the margin, *how much*
it is worth fixing, *what happens* to cash if they act, or *whether* the action
they took last quarter paid off. Data usually arrives messy, and owners are right
to be wary of sending their books to an AI service.

## The solution

| Stage | What Valora does |
|---|---|
| Clean | CSV import with validation, a Data Health score, duplicate detection, category suggestions from a local model. Every fix is a proposal that needs approval and is logged. |
| Understand | A deterministic engine computes revenue, costs, margin, cash, recurring commitments, concentration and collection behaviour. |
| Detect + explain | The **Opportunity Engine** turns metrics into findings (cash pressure, supplier cost inflation, slow collections, cost creep, overlapping tools, concentration risk, unusual payments, growing product lines), each with evidence, supporting transactions, confidence and a narrative written only from computed numbers. |
| Predict | A logistic-regression model estimates the probability of cash pressure in the next 30 days, with per-feature drivers, evaluated against a rule-of-thumb baseline. |
| Quantify | Every finding carries an impact range with its stated basis. |
| Simulate | The Scenario Lab changes supplier prices, selling prices, volume, collection speed, recurring costs, marketing, staffing and inventory and re-projects 90 days of cash. Actual records are never modified. |
| Act + measure | Findings move through New -> Reviewed -> Planned -> In progress -> Completed. When an action starts, the target metric's baseline is frozen and re-measured on later data ("Outcome achieved", "Partly achieved", "Too early"...). |
| Ask | **Valora Insight** ("Ask Valora") answers questions about the business from figures Valora already computed, shows the source of every figure, and refuses what the data cannot answer. It uses an LLM on Groq (free tier works) over a summary of computed figures, and falls back to built-in rules without a key. |
| Onboard | A new business can sign up (owner account + empty business), then import its own CSV. |
| Trust | RBAC, PostgreSQL row-level security, Argon2id, rotating refresh tokens, an append-only audit log; the only external AI call is the optional Groq assistant, which never sees raw transactions. |

## Architecture

React + TypeScript (Vite, Tailwind, Radix/shadcn-style components, Recharts,
TanStack Query) -> FastAPI (`/api/v1`, Pydantic, service and repository layers)
-> PostgreSQL 16 with row-level security. Analytics and ML use pandas, NumPy and
scikit-learn and run locally. Details: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

```
backend/    FastAPI app, Alembic migrations, pytest suite
frontend/   React app and Vitest tests
ml/         model training and evaluation scripts
scripts/    synthetic data, seeding, bootstrap, training
data/       public/ (provided dataset), synthetic/, demo/, reference/, eval/
models/     trained artefacts + evaluation metadata
notebooks/  model_evaluation.ipynb
docs/       architecture, threat model, security, model card, data dictionary, API, demo script
tests/e2e/  browser walkthrough of the demo
```

## Setup

Requirements: **Python 3.10-3.13**, **Node.js 20+**, **PostgreSQL 14+** (16 recommended).

### 1. Database

Either install PostgreSQL and run, as the `postgres` superuser:

```bash
psql -U postgres -f scripts/create_database.sql
```

or use Docker: `docker compose up -d db`.

The application role must **not** be a superuser (row-level security does not
apply to superusers). The Security page warns you if it is.

### 2. Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate      macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
cd ..
python scripts/bootstrap.py
```

`bootstrap.py` creates `backend/.env` with random secrets (edit `DATABASE_URL`
if your database password differs from `change-me-locally`), applies the
migrations, retrains the models if your scikit-learn version differs from the
one used for the shipped artefacts, and seeds the demo.

To turn on the AI assistant, add a free Groq key (https://console.groq.com/keys)
to `backend/.env`: `GROQ_API_KEY=gsk_...` (optional: `GROQ_MODEL=...`).

Run the API:

```bash
cd backend
python -m uvicorn app.main:app --port 8000
```

OpenAPI docs: http://127.0.0.1:8000/docs

### 3. Frontend

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173 (proxies /api to :8000)
```

For a production-like build with a strict Content-Security-Policy:
`npm run build && npm run preview` (http://localhost:4173).

### Demo accounts (synthetic data)

Password for all: `Coastal-Demo-2026!`

| Email | Role | Business |
|---|---|---|
| owner@coastal.demo | Owner | Coastal Home & Kitchen Ltd (main demo) |
| accountant@coastal.demo | Accountant | Coastal Home & Kitchen Ltd |
| viewer@coastal.demo | Viewer (read-only) | Coastal Home & Kitchen Ltd |
| owner@tamarind.demo | Owner | Tamarind Cafe (shows tenant isolation) |

Reset the demo at any time with `python scripts/seed_demo.py`. The walkthrough is
in [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md).

## Data

| Dataset | Label |
|---|---|
| `data/public/small_business_cashflow.csv` | Hackathon-provided dataset - used only as an external benchmark |
| `data/synthetic/` | **Synthetic** training panel: 210 fictional SMEs, 7 archetypes |
| Demo tenants in the database | **Synthetic** fictional businesses, labelled in the UI |
| `data/demo/coastal_petty_cash_sep2026.csv` | **Synthetic**, deliberately messy import file |

No real business or personal data is used. Definitions:
[`docs/DATA_DICTIONARY.md`](docs/DATA_DICTIONARY.md).

### Regenerating data and models

```bash
python scripts/generate_synthetic.py      # ~5 min, writes data/synthetic/
python scripts/train_all.py               # trains and evaluates all models (~1 min)
python scripts/train_all.py --regenerate  # both
python scripts/make_demo_import.py        # rewrites the messy demo CSV
```

## Model evaluation (held-out synthetic businesses)

| Model | Result |
|---|---|
| 30-day cash pressure (logistic regression) | ROC-AUC **0.943** vs 0.911 for a buffer-only rule; PR-AUC 0.702 vs 0.603; F1 at HIGH 0.686 vs 0.602; Brier 0.057 |
| Same approach on the provided CSV | ROC-AUC 0.52-0.57 (no history per business) - reported, not used |
| Unusual payments (Isolation Forest + 4x rule + materiality) | precision 0.694, recall 0.783 on injected anomalies |
| Category suggestions | 86.9% accuracy on a hand-written set never used in training |
| 90-day cash projection | median 30-day back-test error 13.3% of monthly outflows (demo business) |

Full details, limitations and responsible use: [`docs/ML_MODEL_CARD.md`](docs/ML_MODEL_CARD.md)
and `notebooks/model_evaluation.ipynb`. The same figures appear in the app under
Settings -> Models & data.

## Tests and quality checks

```bash
# backend (uses database opportunityos_test; override with TEST_DATABASE_URL)
cd backend && python -m pytest && ruff check app tests ../scripts ../ml

# frontend
cd frontend && npm test && npm run typecheck && npm run lint && npm run build

# end-to-end demo in a real browser (servers running, demo freshly seeded)
pip install playwright && python -m playwright install chromium
python tests/e2e/demo_flow.py
```

Backend tests cover authentication (Argon2id, lockout, rate limiting, refresh
rotation and reuse detection), RBAC, cross-tenant access (API and row-level
security), malformed CSVs, SQL-injection attempts, analytics, scenarios,
opportunity lifecycle and outcomes, ML inference and error hygiene.

## Security

See [`docs/SECURITY.md`](docs/SECURITY.md) and [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md).
Only implemented controls are listed there and on the in-app Security page.

## API

[`docs/API.md`](docs/API.md) - versioned under `/api/v1`.
