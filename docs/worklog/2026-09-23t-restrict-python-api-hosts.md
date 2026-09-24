# 2026-09-23t — Restrict Python API hosts

Author: Codex

## Why

The local Python API accepted requests with any HTTP Host header. A browser could reach a loopback service through a DNS rebinding hostname, despite the API binding only to 127.0.0.1.

## What changed

- `AI/app/main.py` now accepts only `127.0.0.1`, `localhost`, and the test client's `testserver` host. Other hosts receive HTTP 400 before an API route runs.
- `AI/tests/test_api.py` checks an allowed loopback host and a rejected unrelated host.
- Ran the required mirror script so `Java/OpportunityApp/config/py/mosaic/app/main.py` matches `AI/app/main.py`.

## Verification

- `python -m pytest tests -q -p no:cacheprovider --basetemp=tests/.pytest-security-temp`: 111 passed, 2 dependency deprecation warnings. The temporary directory was removed afterward.
- The new host test failed with HTTP 200 before the middleware and passed after it.
- `python -m app.main` completed startup but could not bind to port 8000 because another process already occupied it. The updated app started on 127.0.0.1:8001 through Uvicorn; `/api/health` and `/openapi.json` both returned 200.
- This is a local demo boundary. The Python API still has no independent user authentication; it must remain bound to loopback behind the authenticated Spring site.
