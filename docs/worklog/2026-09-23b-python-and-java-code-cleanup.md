# 2026-09-23b — Python and Java code cleanup

Author: Codex

## Why

Make the current code easier to navigate and maintain, preserving the API contract and
existing work. The requested structure is one Python endpoint per `get_*` file, with
descriptive names and shared implementations for repeated logic.

## What changed

- Split the eleven Python endpoints into `AI/app/api/get_*.py`, registered explicitly
  in `AI/app/api/__init__.py`. Model loading, guards and summaries live in `deps.py`;
  startup assembly stays in `AI/app/main.py`. The sales-impact endpoint remains POST.
- Consolidated date and known-outcome selection in `AI/app/analysis/populations.py`.
  Removed unused scenario-helper parameters and repeated seller-capacity comparisons.
- Fixed an existing empty-period bug: assigning an unfiltered month Series to an empty
  DataFrame restored excluded rows through index alignment. Added regression coverage
  in `AI/tests/test_observed_rates.py` for both delivery and review reporting.
- Consolidated nested Java JSON access in `obj/ApiData.java`. Split API error decoding
  and validation-message formatting into named helpers in `service/MosaicApi.java`.
  Clarified formatting and assistant-tool variable names and reused the scenario prompt
  instead of building it twice.
- Preserved concurrent Java package/class changes, including the rename to
  `service/Formatter.java`. Updated the README layouts and `docs/code-organisation.md`.

Java paths above are relative to
`Java/OpportunityApp/src/main/java/mu/mosaic/opportunity/`.

## Verification

- Baseline: 75 Python tests and 72 Java tests passed before the refactor.
- `.venv/Scripts/python.exe -m pytest tests -q --tb=short`, run from `AI/`:
  77 passed, with two dependency deprecation warnings.
- `mvnw.cmd -o clean test`, run from `Java/OpportunityApp/`: 72 passed, zero failures,
  errors or skips. The clean build regenerated only Maven's `target/` directory and
  verified the concurrent class renames without stale compiled classes.
- The complete generated OpenAPI document is identical before and after the endpoint
  split. Diff whitespace checks passed for the changed Python and Java files.
- No live language-model quality evaluation or manual browser session was performed.
  Existing unrelated items remain in `docs/requirements.md`.

The initial sandbox test attempts could not access pytest temporary files or Maven's
local cache. Approved runs with access to the existing local environment passed.
Java compilation caught a temporary error in the mechanical variable-renaming pass;
it was corrected before both the focused and full suites passed.
