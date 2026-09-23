# Impl/App split, business database and Mosaic colours — design

Date: 23 Sep 2026. Approved in conversation by the user; built by three subagents (A, B, C below).

## Goal

1. Split the Java website so its non-web logic can become a SolarERP module later.
2. Give the website a real business database whose records feed every figure, so the demo can say
   "these figures come from the database".
3. Give the website its own colour scheme (layout stays SolarERP's) and a Help page built on SolarERP's Help page.

No separate `*API` (interfaces-only) module: there is one implementation, the Python service in `AI/`.

## A — SolarFramework: CSV export (repo `D:\Programming\Project\Java\API\SolarFramework`)

- Add `void exportCsv(Path dir)` to `core-modules/DatabaseAPI/.../db/api/IDatabaseService.java`, implemented in
  `core-modules/DatabaseImpl/.../db/spring/DatabaseService.java`.
- Writes one `<table>.csv` per table of this source (every row, every column, header = column names), rows in a
  deterministic order (primary key, else first column), RFC 4180 quoting, UTF-8 without BOM, `\n` line ends.
  NULL is an empty field (never `0`). Plain JDBC over `getDataSource()`; nothing domain-specific.
- Timestamps must come out as the database holds their text form (for SQLite: `yyyy-MM-dd HH:mm:ss` when stored
  that way), decimals without scientific notation.
- Tests on a small SQLite/in-memory table: ordering, quoting (comma, quote, newline), NULL, decimal, timestamp.
- Install the changed modules into `~/.m2`.

## B — Hackathon repo: module split, then business database (`Java/`)

### Split
- `Java/pom.xml`: aggregator (packaging `pom`) with modules `OpportunityImpl`, `OpportunityApp`.
- `Java/OpportunityImpl/`: plain Spring library (no web controllers, templates or static files). Package stays
  `mu.mosaic.opportunity.*` so imports do not change. Moves: `service/MosaicApi`, `service/PythonApiLauncher`,
  `service/Formatter`, `service/ai/*`, `obj/ApiResult`, `obj/ApiData`, and their tests/fixtures.
- `Java/OpportunityApp/`: controllers, `config/WebConfig`, `obj/Breadcrumbs`, `service/HelpService`, templates,
  static files, main class, `application.properties`; depends on `OpportunityImpl`.
- Register both in `.idea/` (explicit `.iml` in `modules.xml`; keep the shared run configuration working).

### Business database (App only)
- SQLite by default, as SolarERP: `spring.datasource.url=jdbc:sqlite:config/Default.db` + SolarFramework
  `DatabaseImpl`/`DatabaseConfig`. `config/*.db` and the export folder are git-ignored.
- One `@Entity` per Olist file (9): orders, order items, payments, reviews, customers, sellers, products,
  geolocation, category-name translation. Each extends `DatabaseObject.ID_RECORD_OBJ<Long, …>` (surrogate `ID`,
  insertion order = CSV order). `@Table(name)` = CSV file name without `.csv`; `@Column(name)` = CSV header;
  typed fields (`LocalDateTime` timestamps, `BigDecimal` money, `Integer`/`Double` where the CSV is numeric).
- First start with empty tables: import the original CSVs from `AI/datasets/` with batched inserts (geolocation
  may use raw JDBC batches if entity inserts are too slow). Later starts skip the import.
- On start, when `data/export/` lacks the files, call `exportCsv` into it; `PythonApiLauncher` starts Python with
  `MOSAIC_DATASETS_DIR` pointing there (Python already reads that variable).
- Retrain the three Python models once on the exported files (their dataset hashes must match the export).

### Acceptance
- Every Python endpoint returns identical figures from the original CSVs and from the database export
  (compare JSON). Any difference is reported, not hidden. Check pandas reads timestamps/decimals identically and
  the extra `ID` column breaks no loader.
- Tests: import of a small Olist sample; export then reload gives the same rows. Existing Java suite and
  `AI/` pytest suite pass.

## C — Look (`Java/OpportunityApp/src/main/resources/`)

- Keep SolarERP's page layout; replace SolarERP's colour scheme with Mosaic's own palette (CSS variables).
- Rebuild the Help page on the actual HTML/CSS structure of SolarERP's
  `ERP/src/main/resources/templates/help.html` and its fragments, with Mosaic's content and colours.
- Check every page in Chrome (Claude in Chrome) for console errors, broken layout and overlapping elements, at
  desktop and phone widths; fix what is found.

## Order

A and C run first in parallel (different repos/files). B runs after A is installed and C has finished, so no two
agents edit the same module at once. Final Chrome pass after B.
