# Proposed features implementation plan

**Goal:** Complete all fourteen features selected from `docs/requirements.md` in the existing application.

**Architecture:** Python remains authoritative for every figure and evidence population. Extend the existing Spring website with same-origin API access, using its current visual styles and reusable charts. The user confirmed that `Java/OpportunityApp/config/py/mosaic` is now the canonical Python source; preserve the ongoing migration and all existing changes.

**Execution:** Independent financial analytics and scenario work run in parallel; evidence/filtering and integration stay with the primary agent. No model retraining or dependency additions are needed.

## Work sequence

- [ ] Shared evidence: expose stable finding identifiers, source order populations, pooled numerators/denominators, exact period/filter settings and dataset hashes; test pagination, missing IDs, empty sets and exports.
- [ ] Findings and controls: reuse existing sales/delivery/review/seller checks, preserve default results, add explicit comparison windows, category/state selection, bounded request-local thresholds, and financial exposure. Use one response for the inbox and evidence browser.
- [ ] Financial analytics: implement quality, payments, freight, cohorts, model metadata and entity history; test financial grain, missing values, repeat timing and absent/stale models.
- [ ] What-if: add category selection and decimal monetary arithmetic around the existing scenario route; render observed and hypothetical results with deterministic narration available without AI.
- [ ] Website: add navigation, financial pages, findings on the overview, evidence pagination/filtering, CSV and print, trend controls and optional external context on the sales chart.
- [ ] Integration: register routes, package canonical Python, run Python suite, API startup/health/OpenAPI, Java tests and rendered-page checks. Record any real blockers in requirements and session worklog.

## Review focus

- Category sales use item grain while outcome rates use the highest-priced item's category; evidence must distinguish these populations.
- Multiple payment/review/item rows must not multiply orders or money.
- Explicit periods must apply equally to trends, findings and exported evidence; unavailable labels remain unknown.
- Settings stay request-local and defaults return on reload; invalid settings produce validation errors.
- Optional AI and downloaded context must never prevent deterministic views from working.

## Verification commands

Run the existing Python interpreter with `-m pytest tests -q` from the canonical Python directory. Start its API on a free local port for health, OpenAPI and new-route smoke checks. Run the existing Maven setup for both Java modules, including `PagesRenderTest` and new page tests. Inspect the final diff without discarding any pre-existing work.
