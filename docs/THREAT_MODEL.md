# Threat model - Valora

Method: asset-centred STRIDE review of this repository's actual data flows.
Scope: the FastAPI backend, the React client, PostgreSQL, CSV import, the local
ML models and the demo deployment described in the README.

## 1. Assets

| Asset | Where | Sensitivity |
|---|---|---|
| Financial transactions and invoices | `transactions`, `invoices` | High - reveals a business's revenue, margins, suppliers, customers |
| Business profile, opening balance | `businesses` | Medium |
| Customer and supplier names | `transactions.counterparty`, `invoices.customer` | Medium (third-party business data) |
| Credentials | `users.password_hash` (Argon2id), `refresh_tokens.token_hash` (SHA-256) | High |
| Session tokens | access JWT (browser memory), refresh token (httpOnly cookie) | High |
| Findings, decisions, scenarios | `opportunities`, `opportunity_events`, `scenarios`, `predictions` | Medium-high (business intent) |
| Audit records | `audit_events` | High integrity |
| ML models and training data | `models/`, `data/synthetic/` | Integrity (poisoning), low confidentiality (synthetic) |
| Secrets | `backend/.env` (JWT secret, DB password, IP salt) | Critical |

## 2. Trust boundaries

```
[Browser] --HTTPS--> [Vite static / reverse proxy] --> [FastAPI] --> [PostgreSQL]
    ^ untrusted input: JSON, query strings, CSV files, cookies, headers
                                        [FastAPI] --reads--> [models/*.joblib]  (trusted, local files)
```

1. Browser -> API: everything is untrusted.
2. API -> database: the API role is not a superuser and has no BYPASSRLS; RLS is a second barrier.
3. Uploaded CSV -> parser: file content is hostile until validated.
4. Model artefacts -> API: loaded with joblib (pickle). Trusted only because they are produced locally by `scripts/train_all.py`; never loaded from uploads.

## 3. Attacker profiles

| Attacker | Capabilities |
|---|---|
| Anonymous internet user | Reach the login and health endpoints, brute-force passwords, send malformed requests |
| Authenticated user of business B | Valid token for B; tries to read or modify business A (IDOR, forged ids, token tampering) |
| Low-privilege insider (Viewer) | Valid token with viewer role; tries writes, imports, audit access |
| Malicious file supplier | Crafts a CSV (formula injection, binary, huge, malformed) given to an accountant |
| Token thief | Steals a refresh cookie (e.g. from a shared machine) |
| Developer mistake | Forgets a `WHERE business_id` clause, logs sensitive data, commits a secret |

## 4. Threats, mitigations and tests

| # | Threat (STRIDE) | Attack path | Mitigation in this repo | Verified by |
|---|---|---|---|---|
| T1 | Cross-tenant read (I) | Request another tenant's transaction/opportunity id | Every repository query filters by `business_id` from the verified token; membership is re-checked in the DB on each request | `test_tenant_isolation.py::test_other_tenant_cannot_read_records_by_id`, `test_lookup_only_returns_own_records` |
| T2 | Missing tenant filter by a developer (I) | Query without WHERE clause | PostgreSQL RLS with FORCE on 9 tenant tables; no tenant bound = zero rows; `WITH CHECK` blocks cross-tenant inserts | `test_row_level_security_blocks_queries_without_where_clause`; Security page shows RLS status |
| T3 | Token forgery / business switching (S, E) | Craft JWT with another business id | HS256 with 32+ char secret, issuer/exp/nbf required, DB membership check, `switch-business` checks membership | `test_forged_token_for_foreign_business_is_rejected`, `test_switching_to_a_business_without_membership_is_denied` |
| T4 | Privilege escalation (E) | Viewer calls write endpoints | `require_roles` on every write route; denials audited | `test_authorization.py` |
| T5 | Credential stuffing / brute force (S) | Many login attempts | Argon2id; per IP+email and per IP rate limits; lockout after 5 failures for 15 minutes; generic error message; dummy-hash timing equalisation | `test_login_rate_limit`, `test_account_lockout_after_repeated_failures`, `test_login_failure_is_generic` |
| T6 | Refresh-token theft (S) | Replay a stolen refresh cookie | Rotation on every use, hash-only storage, reuse of a rotated token revokes the whole family, 7-day expiry, logout revokes family | `test_refresh_rotation_and_reuse_detection`, `test_logout_revokes_refresh_token` |
| T7 | CSRF on cookie endpoints (T) | Cross-site POST to /auth/refresh | Cookie is SameSite=Strict and path-scoped to `/api/v1/auth`; custom `X-Requested-With` header required; strict CORS allow-list | `test_refresh_rotation_and_reuse_detection` (403 without header) |
| T8 | XSS stealing tokens (I) | Script injection via data fields | React escapes output; no `dangerouslySetInnerHTML`; access token only in memory; CSP on the built app and API | Code review; CSP headers in `vite.config.ts` and `core/middleware.py` |
| T9 | SQL injection (T, I) | Payloads in search, sort, filters, CSV | SQLAlchemy parameters only; sort/filter values are enums validated by Pydantic | `test_sql_injection_attempts_are_inert` |
| T10 | Malicious CSV (T, D) | Binary file, huge file, formula injection, bad encodings | Extension + NUL-byte check, 5 MB streaming limit, 20,000-row limit, encoding check, formula prefixes stripped, text length caps, staged import with approval | `test_malformed_files_are_rejected`, `test_demo_import_flow_requires_approval` |
| T11 | Silent data tampering (T, R) | Changing records without trace | All fixes are proposals needing approval; exclusions instead of deletes; append-only audit log (DB trigger rejects UPDATE/DELETE) with before/after values | `test_demo_import_flow_requires_approval` (audit assertions) |
| T12 | Information disclosure through errors (I) | Trigger exceptions | Central handler returns generic message + request id; validation errors never echo input; docs disabled in production | `test_errors_are_structured_and_do_not_echo_input` |
| T13 | Secrets leakage (I) | Committed `.env`, secrets in logs or URLs | `.env` git-ignored, `.env.example` placeholders only, bootstrap generates random secrets; audit and access logs exclude bodies/tokens; tokens never in URLs | `.gitignore`, `test_api.py`, `api.test.ts` |
| T14 | API abuse / DoS (D) | Flood authenticated endpoints | Per-user rate limit (300/min), body size limit, pagination caps (200/page), scenario inputs bounded | `test_unknown_fields_are_rejected`, schema bounds |
| T15 | Data leakage to third parties (I) | Sending ledgers to an external AI | No external AI calls in the codebase; explanations generated locally | Code search: no outbound HTTP clients in `backend/app` |
| T16 | Model/data poisoning (T) | Uploading crafted CSVs to skew models | Models are trained offline on the synthetic panel, never on uploaded data; imports only affect that tenant's analytics; anomaly flags and category suggestions are review prompts | Architecture; `ml/` scripts |
| T17 | Malicious model artefact (E) | Replacing `models/*.joblib` (pickle) | Artefacts come only from local training; registry checks version metadata; file system access is a deployment trust boundary | Documented; see residual risks |
| T19 | Sign-up abuse / account enumeration (S, D) | Script many sign-ups; probe which emails exist | Sign-up creates only an empty business owned by the new account (no access to others); 5 per hour per IP; duplicate email returns 409 (enumeration trade-off accepted for usability, rate-limited and audited as `auth.register_duplicate`); `REGISTRATION_ENABLED=false` switch | `test_register.py` |
| T18 | Insecure configuration (misc) | Running the app as a DB superuser | Security page detects superuser/BYPASSRLS and shows RLS as not effective; README uses a dedicated role | `audit.py::security_summary` |

## 5. Residual risks and next steps

* **Rate limiting is in-process.** With several API instances it must move to Redis.
* **Joblib/pickle artefacts** are trusted files. In production, sign artefacts (hash in
  a signed manifest) and mount `models/` read-only.
* **At-rest encryption** relies on the database host (disk or managed-service encryption).
  Field-level encryption was not added because it would break search and aggregation.
* **No MFA** yet. The next hardening step for owner accounts is TOTP.
* **The demo shows the demo password** on the login screen for judges. Remove it for any real deployment.
* **Audit append-only** is enforced for the application role; a database superuser can still alter it.
  Ship audit events to external storage for stronger guarantees.
