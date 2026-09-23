# 2026-09-23 — Rules for adding endpoints and models safely

Author: Claude

- Added the section "Adding endpoints or models without breaking the app" to `.claude/CLAUDE.md`. It covers how routes are registered in `AI/app/api/__init__.py`, the `require_model` 503/409 guards, keeping existing response shapes stable for `MosaicApi.java`, the model artefact and metadata convention, and the checks to run before handing off.
- Confirmed that the Help page's Endpoints tab reads FastAPI's `/openapi.json` and Spring's own route list at runtime, so new routes appear there without editing the page.
- Only documentation changed. No application code was touched.
