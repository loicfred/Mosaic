# Data dictionary

## Datasets and their labels

| Dataset | Path | Label | Use |
|---|---|---|---|
| Hackathon-provided small business cash-flow file | `data/public/small_business_cashflow.csv` | **Provided dataset** (origin as supplied by the organisers; USD; 1,600 monthly snapshots) | External benchmark only - see `models/benchmark_provided_csv.json` |
| Synthetic training panel | `data/synthetic/` | **Synthetic** (210 fictional SMEs, 7 archetypes, Jan 2023 - Dec 2025, MUR) | Train and evaluate all models |
| Synthetic demo tenants | created in PostgreSQL by `scripts/seed_demo.py` | **Synthetic demo** (Coastal Home & Kitchen Ltd, Tamarind Cafe - fictional) | Live demo; shown with a "Synthetic demo data" badge |
| Demo import file | `data/demo/coastal_petty_cash_sep2026.csv` | **Synthetic, deliberately messy** | Data Health demo |
| Category lexicon | `data/reference/category_lexicon.csv` | Hand-written keyword examples | Extra training text for the category suggester |
| Categoriser evaluation set | `data/eval/categoriser_handwritten.csv` | Hand-written, never used for training | Honest out-of-distribution accuracy |

No real business or personal data is included. Counterparty names in synthetic
data are fictional; `CEB`, `CWA` and `MRA` appear as generic Mauritian payee
labels (electricity, water, revenue authority) on synthetic transactions only.

## Category taxonomy (`backend/app/core/taxonomy.py`)

| Category | Direction | Group |
|---|---|---|
| Sales | inflow | revenue |
| Other income | inflow | other_income |
| Owner contribution, Loan proceeds | inflow | financing |
| Inventory & supplies | outflow | cogs |
| Payroll, Rent, Utilities, Telecom & internet, Software & subscriptions, Marketing, Insurance, Repairs & maintenance, Professional fees, Transport & logistics, Bank fees, Equipment, Other expenses | outflow | operating |
| Taxes (VAT) | outflow | tax |
| Loan repayment, Owner drawings | outflow | financing |
| Uncategorised | either | uncategorised (excluded from revenue and expense metrics until categorised) |

## Metric definitions (cash basis)

| Metric | Definition |
|---|---|
| Revenue | Sum of inflows in group `revenue` |
| Cost of goods (supplier cost) | Sum of outflows in group `cogs` |
| Operating expenses | Sum of outflows in group `operating` |
| Expenses | Cost of goods + operating expenses + tax |
| Gross margin | (revenue - cost of goods) / revenue |
| Operating cash flow | revenue + other income - cost of goods - operating expenses - tax |
| Net cash flow | all inflows - all outflows (includes owner and loan flows) |
| Cash balance | opening balance + cumulative net cash flow, per day |
| Committed outflows | all outflows except owner drawings |
| Cash buffer (days) | cash / average daily committed outflows over the last 90 days |
| 14-day safety buffer | 14 x average daily committed outflows |
| Collection days | amount-weighted average (paid date - issue date) of invoices paid in the window |
| Overdue receivables | open invoices past their due date |
| Top customer share | largest named customer's revenue / all revenue, last 180 days (walk-in POS sales count as unidentified) |
| Top supplier share | largest supplier's purchases / all stock purchases, last 180 days |
| HHI | Herfindahl-Hirschman index over named counterparties (0-10,000) |
| Recurring commitment | outflow stream (payee + category) seen in several months with a regular cadence; monthly run-rate = latest payment (monthly), latest / 3 (quarterly) or average (irregular) |
| Fixed commitments | recurring streams in Rent, Software & subscriptions, Telecom & internet, Insurance, Professional fees with stable amounts (CV <= 0.2) |
| Period comparisons | last three complete calendar months vs the three before |
| Data Health score | 100 x (0.4 valid rows + 0.2 duplicate-free + 0.2 categorised + 0.2 payee recorded), floored |

## Database tables

| Table | Key columns | Notes |
|---|---|---|
| `users` | email, full_name, password_hash (Argon2id), failed_logins, locked_until | |
| `businesses` | name, sector, currency (MUR), opening_cash, opening_date, data_label | tenant root |
| `memberships` | user_id, business_id, role (owner/accountant/viewer) | unique per user+business |
| `refresh_tokens` | token_hash (SHA-256), family_id, expires_at, revoked_at, replaced_by | rotation + reuse detection |
| `transactions` (RLS) | txn_date, direction, amount > 0, category, subcategory, description, counterparty, reference, source, import_batch_id, is_anomaly, anomaly_score, anomaly_reason, duplicate_group, excluded | actual records; never deleted by the app |
| `invoices` (RLS) | invoice_no, customer, issue_date, due_date, amount, paid_date | receivables |
| `import_batches` (RLS) | filename, file_sha256, status, counts, health (JSON) | staging |
| `import_rows` (RLS) | row_number, raw (JSON), parsed (JSON), status, issues (JSON), include | staging |
| `proposed_changes` (RLS) | target_type, target_id, change_type, field, old_value, new_value, reason, confidence, source, status, decided_by, decided_at | approval workflow |
| `opportunities` (RLS) | fingerprint, detector, kind, category, title, summary, explanation, severity, confidence (+basis), impact_low/high/kind/basis, evidence, supporting_records, actions, scenario_preset, provenance, target_metric/params, baseline_value, expected_change, status, action_started_at, completed_at, outcome, data_as_of | |
| `opportunity_events` (RLS) | event_type, from_status, to_status, note, user_id | lifecycle log |
| `scenarios` (RLS) | name, assumptions, result_summary, opportunity_id, data_as_of | separate from actuals |
| `predictions` (RLS) | model_version, as_of, mode, probability, band, features, contributions | every stored prediction is reproducible |
| `audit_events` | event_type, category, outcome, actor, resource, ip_hash, details | append-only (trigger) |

## Import file format

Required columns (case-insensitive, common synonyms accepted): `date`,
`description`, and either `amount` (negative = money out) or `debit` + `credit`.
Optional: `category`, `payee`/`counterparty`, `reference`, `type`/`direction`.
Dates: `YYYY-MM-DD`, `DD/MM/YYYY`, `DD-MM-YYYY`, `DD.MM.YYYY`, `DD Mon YYYY`.
Amounts may include `MUR`/`Rs`, thousands separators, parentheses or trailing `-` for negatives.

## Cash-pressure features (`backend/app/analytics/features.py`)

| Feature | Meaning |
|---|---|
| buffer_days | cash / average daily committed outflows (90 d) |
| net_margin_90d | (operating inflows - committed outflows) / operating inflows, 90 d |
| revenue_growth_30d | revenue last 30 d vs average 30 d of the prior 90 d |
| expense_growth_30d | cost of goods + operating, same comparison |
| supplier_cost_growth_30d | cost of goods, same comparison |
| recurring_share | recurring-category outflows / committed outflows, 90 d |
| collection_days | collection days of invoices paid in the last 90 d |
| collection_days_trend | last 60 d minus the 120 d before |
| overdue_receivables_ratio | overdue receivables / monthly revenue |
| top_customer_share, top_supplier_share | concentration, 180 d |
| cashflow_volatility | std of weekly net flow / mean weekly committed outflow, 13 weeks |
| cash_trend_30d | cash change over 30 d / monthly committed outflow |
| scheduled_obligations_ratio | known obligations in the next 30 d (recurring run-rate, VAT due on the 20th of Jan/Apr/Jul/Oct, 13th-month bonus) / monthly committed outflow |
| seasonal_index_next_30d | revenue in the same 30 d last year / last year's average 30 d |
| txn_frequency_change | transactions last 30 d vs prior monthly average |

Label: 1 if the daily cash balance falls below the 14-day safety buffer at any
point in the following 30 days; rows are used only when the current buffer is at
least 14 days (onset prediction).
