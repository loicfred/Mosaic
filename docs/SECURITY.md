# Security

This page lists controls that are **implemented and tested**. The in-app
"Security & Audit" page reads the same facts from the running system (including
whether PostgreSQL row-level security is effective for the current DB role).
See `docs/THREAT_MODEL.md` for the threat analysis.

## Authentication

* Passwords hashed with **Argon2id** (64 MiB memory, 3 iterations, parallelism 2); rehash on login when parameters change. Minimum length 12.
* **Access token:** HS256 JWT, 15 minutes, contains only user id and business id; kept in browser memory, never in localStorage or URLs.
* **Refresh token:** 48 random bytes, stored only as a SHA-256 hash, sent as an `httpOnly`, `SameSite=Strict`, path-scoped cookie (`Secure` when `APP_ENV=production` or `COOKIE_SECURE=true`). Rotated on every use; replaying a rotated token revokes the whole session family. Logout and password change revoke sessions.
* **Self-service sign-up** (`POST /auth/register`) creates only an owner of a new, empty business: it cannot join an existing business or pick a role. Same password rules, Argon2id, 5 sign-ups per hour per IP, unknown fields rejected, audited (`auth.register`). Turn it off with `REGISTRATION_ENABLED=false`.
* **Brute-force protection:** 5 attempts per minute per IP+email, 20 per IP; account locked for 15 minutes after 5 failures; identical error for unknown email and wrong password; dummy hash verification to equalise timing.

## Authorisation (RBAC)

| Capability | Owner | Accountant | Viewer |
|---|:-:|:-:|:-:|
| View dashboards, transactions, insights, opportunities | yes | yes | yes |
| Run simulations | yes | yes | yes |
| Save scenarios | yes | yes | - |
| Import data, approve/reject data changes | yes | yes | - |
| Change opportunity status, add notes, re-run engine | yes | yes | - |
| View audit trail | yes | yes | - |
| View team members | yes | - | - |

Enforced server-side by `security/deps.py::require_roles` on every route. The
role is re-read from the database on each request, so revocations apply
immediately. Denials are written to the audit log.

## Tenant isolation

1. Every repository query filters by the `business_id` taken from the verified token.
2. PostgreSQL **row-level security** (`FORCE`) on `transactions`, `invoices`, `import_batches`, `import_rows`, `proposed_changes`, `opportunities`, `opportunity_events`, `scenarios`, `predictions`. The session sets `app.business_id` at the start of each transaction; without it, zero rows are visible. `WITH CHECK` prevents writing rows for another tenant.
3. The application database role must not be a superuser or have `BYPASSRLS` (see `scripts/create_database.sql`).

## Input and API security

* Pydantic schemas with `extra="forbid"`; enums for sort/filter parameters; bounded numbers.
* SQLAlchemy parameterised queries only.
* CSV: `.csv` only, 5 MB streaming limit, 20,000 rows, NUL-byte/binary rejection, UTF-8/CP-1252 decoding, header validation, formula-injection characters (`= + - @`) stripped from text, text length caps, staged import with approvals.
* Strict CORS allow-list with credentials; methods and headers limited.
* Security headers on every response: `Content-Security-Policy`, `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Permissions-Policy`, `Cross-Origin-Opener-Policy`, `Cache-Control: no-store` for the API, HSTS in production. The built frontend is served with its own CSP (`vite.config.ts`).
* Central error handling: generic messages with a request id; validation errors never echo submitted values; no stack traces to clients; OpenAPI docs disabled in production.
* API versioned under `/api/v1`; per-user rate limit of 300 requests per minute.

## Secrets

* No secrets in the frontend or in source control. `backend/.env` is git-ignored; `backend/.env.example` holds placeholders only.
* `scripts/bootstrap.py` generates a random `JWT_SECRET` and `AUDIT_IP_SALT`.
* Settings refuse to start without a JWT secret of at least 32 characters.

## Data protection and privacy

* Minimal data: no card numbers, bank account numbers or personal IDs are stored; counterparties are business names.
* Client IPs are stored only as salted SHA-256 prefixes in the audit log.
* Tokens and passwords are never logged; access logs contain method, path, status and duration only.
* At-rest encryption is a deployment responsibility (encrypted volume or managed PostgreSQL).

## Privacy-first AI

* All analytics and all three models run locally. The core product works fully offline.
* Finding narratives are generated locally from structured, already-verified findings.

## AI assistant

* **Valora Insight** (the "Ask Valora" panel) answers with an LLM on Groq (`GROQ_MODEL`, default `llama-3.3-70b-versatile`) when `GROQ_API_KEY` is set in `backend/.env`. The key stays on the server; the browser only calls `POST /api/v1/insight/ask`.
* The model receives a compact summary of figures Valora already computed (cash, projection, cash-pressure estimate, monthly totals, top categories, customers, suppliers, receivables, recurring payments, open findings, data-health warnings) plus the question and up to six earlier turns. It never receives raw transactions, descriptions, invoice numbers, user details, credentials or tokens. Counterparty names in the top-5 lists are sent.
* Imported names are marked as untrusted data in the prompt. The model can only cite sources and charts from server-built catalogues, so links and plotted numbers always come from the analysis.
* Questions are rate-limited per user (`LLM_RATE_LIMIT`, default 20 per minute). If the key is missing or Groq fails, the panel falls back to the local rule-based router (`frontend/src/lib/insight/engine.ts`) and says so under the answer.

## Audit logging

Events recorded: login success/failure/lockout/rate limit, refresh-token reuse,
logout, password change, business switch, authorisation denials, transaction
detail views, report generation, import staged/rejected/committed/discarded,
every approved or rejected data change (with before/after values), opportunity
status changes, engine runs and saved scenarios. The `audit_events` table is
append-only: a database trigger rejects `UPDATE` and `DELETE`.

## Security tests

`backend/tests/test_auth.py`, `test_authorization.py`, `test_tenant_isolation.py`,
`test_import_and_quality.py` (malformed CSV, injection), `test_api.py` (headers,
error hygiene) and `frontend/src/test/api.test.ts` (token handling).
