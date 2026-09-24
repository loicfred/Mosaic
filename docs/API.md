# API reference (v1)

Base path `/api/v1`. Interactive OpenAPI docs: `http://127.0.0.1:8000/docs`
(development only). All endpoints except `/health`, `/auth/login`,
`/auth/register`, `/auth/refresh` and `/auth/logout` require `Authorization: Bearer <access token>`.
Errors always have this shape:

```json
{"error": {"code": "not_found", "message": "Transaction not found.", "details": null, "request_id": "a1b2c3d4e5f60718"}}
```

Roles: **O** owner, **A** accountant, **V** viewer.

## Auth

| Method | Path | Roles | Notes |
|---|---|---|---|
| POST | `/auth/login` | public | `{email, password}` -> `{access_token, expires_in}` + refresh cookie. Rate-limited, lockout. |
| POST | `/auth/register` | public | `{full_name, email, password, business_name, sector, opening_cash, opening_date}` -> 201 `{access_token}` + refresh cookie. Creates an owner, an empty `user_data` business (MUR) and the owner membership in one transaction. 5 per hour per IP; 409 if the email exists; disabled with `REGISTRATION_ENABLED=false`. |
| POST | `/auth/refresh` | cookie | Header `X-Requested-With: Valora` required. Rotates the refresh token. |
| POST | `/auth/logout` | cookie | Same header. Revokes the session family. |
| GET | `/auth/me` | O A V | User, role, business, memberships, permissions |
| POST | `/auth/switch-business` | O A V | `{business_id}`; membership required |
| POST | `/auth/change-password` | O A V | `{current_password, new_password}`; signs out other sessions |

## Business

| GET | `/business` | O A V | profile, data label, data as-of |
| GET | `/business/members` | O | team list |

## Transactions

| GET | `/transactions` | O A V | filters: `q`, `category`, `direction`, `counterparty`, `date_from`, `date_to`, `min_amount`, `max_amount`, `flag` (anomaly/duplicate/uncategorised/excluded), `sort`, `page`, `page_size` (max 200) |
| GET | `/transactions/facets` | O A V | categories, counterparties, date range |
| GET | `/transactions/{id}` | O A V | detail + payee history, duplicates, pending changes, opportunities that cite it (audited) |
| POST | `/transactions/lookup` | O A V | body: list of up to 50 ids; returns only this tenant's records |

## Data quality and import

| GET | `/data-quality/health` | O A V | ledger Data Health score, checks, totals |
| GET | `/data-quality/proposals?status=&batch_id=` | O A V | proposed changes |
| POST | `/data-quality/proposals/{id}/decision` | O A | `{decision: approve|reject, new_value?}` (audited with before/after) |
| POST | `/data-quality/proposals/bulk-decision` | O A | `{ids: [...], decision}` |
| POST | `/data-quality/imports` | O A | multipart `file` (.csv, <= 5 MB) -> staged batch with health and issues |
| GET | `/data-quality/imports` | O A V | history |
| GET | `/data-quality/imports/{id}` | O A V | rows, issues, proposals, pending counts |
| POST | `/data-quality/imports/{id}/commit` | O A | 409 while duplicate decisions are pending; re-runs the engine |
| POST | `/data-quality/imports/{id}/discard` | O A | |

## Analytics and insights

| GET | `/analytics/overview` | O A V | cash, KPIs (last 3 complete months vs previous 3), cash series, projection, prediction summary, data health |
| GET | `/insights` | O A V | monthly series, comparison, expense categories, product lines, concentration, recurring commitments, collections |

## Opportunities

| GET | `/opportunities?status=&include_inactive=` | O A V | cards with evidence, impact, confidence, provenance, outcome |
| GET | `/opportunities/{id}` | O A V | + event timeline; outcome recomputed |
| PATCH | `/opportunities/{id}/status` | O A | `{status, note?}`; allowed transitions enforced (409 otherwise) |
| POST | `/opportunities/{id}/notes` | O A | `{note}` |
| POST | `/opportunities/refresh` | O A | re-runs the engine (audited) |

## Scenarios

| GET | `/scenarios/levers` | O A V | lever definitions and ranges |
| POST | `/scenarios/simulate` | O A V | `{assumptions: {...}, horizon_days}` -> baseline vs simulated projection. Nothing stored. |
| GET | `/scenarios` | O A V | saved scenarios |
| POST | `/scenarios` | O A | `{name, assumptions, opportunity_id?}` |
| DELETE | `/scenarios/{id}` | O A | |

Assumption bounds: supplier_cost_pct, staffing_cost_pct, inventory_spend_pct -30..30;
price_pct -20..20; sales_volume_pct and recurring_expense_pct -50..50;
marketing_spend_pct -100..100; collection_days_change -30..30 (days).

## ML

| GET | `/ml/cash-pressure` | O A V | prediction with per-feature contributions, projection, back-test |
| GET | `/ml/models` | O A V | model cards: metrics, calibration, confusion matrix, benchmark |
| GET | `/ml/categorise?description=&direction=` | O A | category suggestion with alternatives |

## Audit and reports

| GET | `/audit/events?category=&outcome=&limit=` | O A | this tenant's events + the caller's own sign-in events |
| GET | `/audit/security-summary` | O A V | implemented controls, RLS status read from PostgreSQL |
| GET | `/reports/decision-brief` | O A V | printable brief (audited) |
| GET | `/health` | public | database and model status |
