# 2026-09-24 — Java object model and test cleanup

Author: Claude

The user found the Java app too procedural: static helpers over `Map<String, Object>`, one-line wrappers, members
widened only for tests, and many tests and fixtures they did not need. Other sessions were editing some of the
same files at the time; every change below was made on the file as it stood on disk.

OpportunityImpl:
- API replies are typed records in `obj/api/`, read with `ApiResult.as(Type.class)` through SolarFramework's
  `JSONItem.SimpleGSON` (new `json` dependency in `pom.xml`). Pages still render `ApiResult.data()` unchanged.
  `obj/ApiData.java` and `service/ai/TrendText.java` are gone; the trend wording moved into `Formatter`
  (`movement`, `groupName`, `threshold`, `unitChange(Moved)`, `percentNumber`, `num(value, digits, missing)`).
- Behaviour sits on the objects: `SalesCaveats.SalesCheck` and `TrendCheck` write their own sentence (`Check`),
  `SalesOpportunities.Profile.line`, `Risk.describe`, `Events.Event.touches`, `TrendMeasure.better()`.
- Writers are instances: `CheckedWriter<T>` with `template`/`evidence`/`nothingToSay`, `CheckListWriter<T>` for
  the two caveat writers. `Panels` maps (topic, advice|caveats) to its API call and writer, used by
  `AiButtonsController`, `PanelChatController` and `PanelTools`.
- `LocalAi` has a `Bot` enum instead of name constants, no test-only constructor, and `reachable` is an instance
  method. `NumberCheck` is an object (`new NumberCheck().allow(text).unsupported(answer)`). `ApiResult` has
  constructors instead of static factories. One-line private helpers were inlined where they were used.

OpportunityApp:
- `Breadcrumbs` is a record (`new Breadcrumbs(page, crumbs…).addTo(model)`); `Selection` replaces the static
  selection helpers of `FindingsController`; `data/EntityTable` replaces the static `CsvImport`.
- `PanelChatController.Question.problem()` validates a question; the size limits moved there from `PanelChat`.

Tests: kept only `NumberCheckTest` (OpportunityImpl) and `PagesRenderTest` (OpportunityApp). `PagesRenderTest`
now loads its five fixtures from `OpportunityApp/src/test/resources/api`; the OpportunityImpl test-jar and every
other test, fixture and the `olist-sample` CSVs were deleted.

Verified:
- `mvnw -o install` in `Java/OpportunityImpl`: `NumberCheckTest` 9 tests, 0 failures.
- `mvnw -o test` in `Java/OpportunityApp`: `PagesRenderTest` 9 tests, 0 failures.
- A one-off program outside the repository read the saved real replies (sales and trend caveats and opportunities,
  scenario, trend, forecast, history) through the new records and printed every writer's evidence and the
  scenario template in full.

Not verified: the AI buttons and the follow-up chat on the running site (open in `docs/requirements.md`).
