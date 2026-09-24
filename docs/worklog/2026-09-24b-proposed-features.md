# 2026-09-24 — Proposed features list

Author: Claude

Added `## Proposed features` to `docs/requirements.md`: 14 candidate features (PF-1 to PF-14) in three tiers, each with its reason, the existing modules or routes it builds on, a rough effort and a "done when" test. A short "Not recommended" list keeps out-of-scope ideas out. These are candidates, not agreed requirements; a chosen one moves into the FR table.

Tier 1 fills gaps in the core journey: source records behind a finding (PF-1), a what-if page on the existing `POST /api/scenarios/sales-impact` (PF-2), a data coverage page (PF-3) and one findings inbox (PF-4).

While checking paths, found that FR-4, FR-5 and FR-6 still name `category.html`, `risk.html` and `scenario.html`, which were removed with the trend pages. Recorded under `## Outstanding work` rather than rewritten here.

Verification: documentation only. Every existing file, route and function named in the new section was checked in the repository; `get_finding_records.py` is marked as new.
