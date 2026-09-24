# 2026-09-24 — Fix the open issues found by the 24 Sep app/data/AI check

Author: Claude

Fixed the items opened in `2026-09-24e-app-data-and-ai-check.md`. Codex was rewriting the same files concurrently
(`CaveatWriter.java` moved to a typed `SalesCaveats`/`Check` model, `Breadcrumbs` to a constructor); each fix below
was reapplied against the current file, not the version first inspected.

Python (`app/analysis`):
- `seller_base.py`: `RULES["seller"]` states the priciest-item limitation that made the active-sellers count run
  13–17 low a month.
- `caveats.py`: `late_orders_hurt_reviews` now carries `"period": {"start": DATA_RANGE[0], "end": DATA_RANGE[1]}`,
  since that check pools the whole range while its neighbours use the 3-month windows.
- `impact.py`: the `rate_held` What-if variant's expected low reviews now scale from the baseline's own
  `monthly_low_reviews` (`low_per_order`) instead of mixing the whole-range late/on-time review rates with the
  recent late-delivery rate. `_labelled_orders`'s `reviewed` set is now `recent_labelled`, the same window as the
  baseline. The `rate_fitted` variant (`_fitted_late_outcome`) is now `None` unless the fitted line reproduces the
  recent late rate within `FIT_TOLERANCE` (1 pp) at the recent volume — it no longer shows an inflated rate that
  contradicts the baseline it is supposed to extend. New tests: `test_low_reviews_scale_with_orders_when_rates_hold`,
  `test_fitted_variant_is_dropped_when_its_line_misses_the_recent_rate`.

Java:
- `SalesCaveats.SalesCheck.sentence` (was `CaveatWriter.sentence`): the late-orders/low-reviews sentence now reads
  "From 2017-01 to 2018-08, late orders got..." using the new `Evidence.period` (`DateRange` record), reapplied
  after Codex's typed-record rewrite replaced the plain-map version this was first written against.
- `MosaicApi.describeApiError`: the 422 branch no longer adds a second full stop to a validation message that
  already ends in one (`sentence()` helper).
- `ScenarioPageController.calculate`: an API 422 (e.g. an unknown What-if category) now returns 400, not 502 — the
  caller's mistake, not a backend fault.
- `ScenarioNarrator.template`: "A 10% change in sales" is now "A 10% rise/fall in sales", matching the sign.
- `NumberCheck.java`: fixed five regex fields that had single backslashes instead of Java's required `\\d`/`\\b`/
  `\\s`/`\\$` — a compile error blocking the whole module, unrelated to this task but found while building it.

`config/ai/agents.json` (chatbot prompts, one added rule per bot, JSON re-validated after editing):
- `InvestmentAdvisor`, `TrendAdvisor`: a level of `in_line` is close to the business, not better; only mention a
  risk (seller share, freight, basket) that is marked triggered.
- `TrendAdvisor`: say a group improved, never that it "drove" or "caused" the business figure.
- `CaveatWriter`, `TrendCaveats`: write "including" before named examples when the count is larger than the names
  given, so "4 categories" isn't followed by only 3.
- `PanelChat`: call a tool (`measureTrend`, `events`) for a question about a month, an event or a cause, instead of
  saying the figures aren't available; a decline names what the data can show instead; `in_line` is not "better".
  **Not re-verified against a live model** — Groq in this environment is rate-limited to about one call a minute,
  and the user asked not to spend more of it on repeated test calls this session.

CSS (`static/css/mosaic.css`): `.chat-log` gained `overscroll-behavior: contain`, matching `#sidebar`. Investigated
the user's report that "conversation messages are still scrollable and not the chatbox directly": confirmed by
direct DOM/scroll measurement that the box does scroll internally (`scrollTop` moves, `window.scrollY` does not)
under a discrete wheel scroll, both mid-conversation and at the bottom boundary; could not reproduce a leak with
that method, and could not test trackpad momentum scrolling or a real narrow viewport (the browser window would not
resize in this environment). `overscroll-behavior: contain` is the standard fix for exactly this symptom and costs
nothing when the leak doesn't occur, but the fix is unconfirmed against the reported case; noted in
`docs/requirements.md`.

Verified: `OpportunityImpl` `mvnw.cmd -o install` — 13 test classes, all passed. `OpportunityApp` `mvnw.cmd -o test`
— 12 test classes, all passed. `python -m pytest tests -q` — 161 passed. Not run this session: a live AI call, the
packaged JAR, and a phone-width Chrome pass (all pre-existing gaps, see `docs/requirements.md`).
