# 2026-09-23e — Impl/App split, business database and Mosaic colours

Author: Claude

## Why

The user wants the website's non-web logic reusable, possibly as a SolarERP module later, and wants the figures to
come from a real business database rather than loose CSV files. They also objected that the site had copied
SolarERP's colours: SolarERP's code structure is the model, not its look. The design is in
`docs/superpowers/specs/2026-09-23-impl-app-split-and-business-database-design.md`. The user agreed there is
no separate interfaces-only `*API` module, because the Python service is the only implementation. Three
subagents did the work, as the user authorised.

## What changed

- **SolarFramework:** `IDatabaseService.exportCsv(Path dir)` in `DatabaseAPI`, implemented in `DatabaseImpl`'s
  `DatabaseService`. It writes one CSV per table, ordered by primary key, with SQLite timestamps printed as
  `yyyy-MM-dd HH:mm:ss`. Tests are in `CsvExportTest`. Installed to `~/.m2` from an uncommitted working tree.
- **Split:** `Java/OpportunityImpl` now holds `MosaicApi`, `PythonApiLauncher`, `Formatter`, `service/ai/*`,
  `ApiResult` and `ApiData`, with no web stack. `Java/OpportunityApp` keeps the controllers, templates and static
  files and depends on it. Each module builds with its own `mvnw.cmd`; the user asked for no aggregator pom. Both
  modules are registered in `.idea/`.
- **Business database:**
  - `Java/OpportunityApp` has 9 Olist entities under `entity/`, stored in SQLite at `config/Default.db`.
  - On the first start, `data/BusinessDatabase` imports `AI/datasets` with JDBC batches: 1.55M rows in about 23 s.
    It then exports the database to `data/export/`.
  - `PythonApiLauncher` points Python at that export and at its own models folder, `data/models/`, through
    `MOSAIC_DATASETS_DIR` and `MOSAIC_MODELS_DIR`.
  - The JVM runs in UTC so timestamps survive the round trip. `AI/models` is untouched.
- **Look:**
  - The palette in `static/css/main.css` comes from the user's logo, now at `static/img/logo.jpg`: near-black
    surfaces, a blue-cyan accent, and the logo's violet-to-green gradient on three brand touches.
  - `mosaic.svg` is recoloured to match.
  - The Help page is rebuilt on SolarERP's Help page code: `help.html`, `fragments/help/{guide,endpoints,data}/`
    and `static/css/help.css`.
- **Chrome fixes:** the chart legend dashes, the category filter strip, and evidence values on phone width. On the
  Help page: side-list overflow, which came from Bootstrap's `.nav` wrap, and deep links when only the `#hash`
  changes.

## Verification

- Before the database work, one Python API instance on the original CSVs and one on the database export (with its
  own models) answered 94 requests. 88 were identical. Five differed only in `trained_at`. `/api/datasets` lists
  the extra record columns (`ID`, `CreatedAt`, ...), which are recorded in `requirements.md`.
- Tests:
  - `CsvExportTest`: 6 passed.
  - `Java/OpportunityImpl`: `mvnw install`, 53 tests.
  - `Java/OpportunityApp`: `mvnw test`, 23 tests, including `BusinessDatabaseTest`.
  - `AI/`: `pytest`, 78 passed.
  - I re-ran both Java suites after the subagents finished: both exit 0.
- In Chrome, every page was checked at desktop and 390px-frame width on the running app before the split, with no
  console errors. The window could not be resized, so phone width was checked inside iframes.
- Not checked yet: a Chrome pass on the restarted site reading the database export.
