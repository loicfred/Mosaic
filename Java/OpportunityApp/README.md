# OpportunityApp — the Mosaic website

Spring Boot and Thymeleaf website on SolarFramework (`WebUtils` for Thymeleaf and request logging, `core`
for utilities), laid out like SolarERP: the same header, sidebar, breadcrumb bar, footer and `mod-*`
page components, with pages assembled from fragments. It replaces the React client in `../../front-end/`,
which is left untouched.

The Python API in `config/py/mosaic/` stays the single source of truth for every number: this app calls it
server-side and only formats what it returns (see `../../docs/frontend-brief.md` for the rules it follows).

## Requirements

- Java 25. Maven comes with the wrapper (`mvnw.cmd`); nothing else to install.
- Access to SolarFramework 1.0, which Maven downloads from GitHub Packages (declared in `pom.xml`). GitHub
  asks for a token even to read it, so run this once from the repository root:

  ```powershell
  powershell -ExecutionPolicy Bypass -File Java\setup-github-packages.ps1
  ```

  It opens GitHub's token page (tick only `read:packages`, generate, copy), asks you to paste the token, checks
  that it can download SolarFramework, saves it as the user variables `GITHUB_ACTOR`/`GITHUB_TOKEN` and adds the
  `github` server to `%USERPROFILE%\.m2\settings.xml` (the file only refers to the variables). Then quit IntelliJ
  completely and start it again: it reads new variables only when it starts.

  With a SolarFramework checkout instead, installing it locally works too and needs no token. This site needs
  `WebUtils`, `core`, `AIAPI`, `AIImpl`, `DatabaseImpl` and `PythonRunner`, with what they depend on:

  ```powershell
  cd <path to>\SolarFramework
  .\mvnw.cmd install -pl web-modules/WebUtils,core,core-modules/AIAPI,core-modules/AIImpl,core-modules/DatabaseImpl,runners/PythonRunner -am -DskipTests
  ```

- `../OpportunityImpl` installed in the local Maven repository (the site depends on it by version):

  ```powershell
  cd Java\OpportunityImpl
  .\mvnw.cmd install
  ```

  IntelliJ links the two modules itself (both `pom.xml` files are listed in `.idea/misc.xml`), so its run
  configuration needs this only after a change to `OpportunityImpl` when building from a terminal.
- The Python API set up as in `config/py/mosaic/README.md` (`config/py/mosaic/.venv` with its requirements).

## Modules

| Module | Holds |
| --- | --- |
| `../OpportunityImpl` | Everything that is not web, as a plain Spring library: the Python API client (`MosaicApi`) and launcher (`PythonApiLauncher`), `Formatter`, the local AI (`service/ai/`), `ApiResult` and the typed API replies (`obj/api/`). No controllers, templates or database. |
| `OpportunityApp` (here) | The website: controllers, templates, static files, `WebConfig`, `Breadcrumbs`, `HelpService`, and the business database. |

Both keep the package `mu.mosaic.opportunity`, so Spring's component scan finds the library's beans unchanged.

## Business database

The site keeps the Olist records in a SQLite database, `config/Default.db` (git-ignored), through
SolarFramework's `DatabaseImpl`, and every figure the Python API returns is computed from what that database holds:

1. One entity per Olist file (`entity/Olist*.java`): table = file name without `.csv`, columns = the file's
   headers (the file's `lenght` typos included), plus SolarFramework's `ID`, `CreatedAt`, `UpdatedAt`, `DeletedAt`.
2. On start, a table that is still empty is filled from `config/py/mosaic/datasets` (`mosaic.data.source-dir`), one
   transaction per table, IDs in file order. The first start takes about 25 s for the 1.55 million rows, of which
   9 s is the million geolocation rows; later starts skip it.
3. SolarHome's `config/py/mosaic/` is the Python project itself, the only copy: `app/`, `tests/`, `datasets/`
   (the original CSVs, including `small_business_cashflow.csv`), `models/` and its `.venv`.
4. `PythonApiLauncher` starts `app.main` there. In the repository the folder has `requirements.txt`, so the launcher
   runs it as it is and never replaces `app/` from the zip; elsewhere (a packaged jar) it unpacks the zip's `app/`.

`BusinessDatabase` writes the database into `config/py/mosaic/datasets/` with `IDatabaseService.exportCsv` when a
table's file is missing there, except when that folder is `mosaic.data.source-dir` itself, as in the repository:
there an export would rewrite the original CSVs and the models would answer 409.

The Python API never trains at startup; it only loads saved models. Train in `config/py/mosaic` (see its README).

An API already answering on port 8000 is reused as it is.

## Run

From IntelliJ: the project lists `Java/OpportunityImpl/pom.xml` and `Java/OpportunityApp/pom.xml` as Maven projects (`.idea/misc.xml`, each module with its `.iml` in `.idea/modules.xml`) and ships a shared
**OpportunityApp** run configuration (`.idea/runConfigurations/`). If IntelliJ was open while these were
added, reload the Maven projects once.

Any working directory works: `ModuleHome.pin()` in `OpportunityApp.main` points SolarHome, `.env` and
`mosaic.data.source-dir` at `Java/OpportunityApp` (found from the compiled classes in its `target/`), unless
`-Dsolar.home`, `SOLAR_HOME` or those system properties are already set.

From a terminal:

```powershell
cd Java\OpportunityApp
.\mvnw.cmd spring-boot:run
```

Open http://localhost:8080. On startup the site starts the Python API with `python -m app.main`
when an extracted Python project is available in SolarHome, unless one is already answering on port 8000.
It stops the process on normal shutdown (Ctrl+C, IntelliJ's stop button). While the bundled archive is absent,
start the Python API separately from `config/py/mosaic` with `python -m app.main`.
The first start imports the database first (see above). The dataset takes about 10–15 s to load;
pages show "not answering" until then, and the log prints `Analytics API ready.`

A hard kill of the Java process (Task Manager, `taskkill /F`) cannot run shutdown code, so the Python
process is left running; the next start finds it on port 8000 and reuses it.

`OpportunityImpl` can use a bundled `mosaic-python.zip` resource.
The archive must contain `app/main.py` at its root. The launcher extracts it under
`config/py/mosaic` in SolarHome (`-Dsolar.home`, else the working directory) before starting Python.
Claude's project `Stop` hook runs `.claude/hooks/package-python.ps1` after each completed Claude turn
to build that archive from the `.py` files in `config/py/mosaic/app`, as every Maven build of `OpportunityImpl`
also does; it does not include datasets, models, a Python
interpreter or installed packages. When the archive is absent, an already extracted package in
SolarHome remains usable.

## Configuration (`src/main/resources/application.properties`)

| Property | Default | Meaning |
| --- | --- | --- |
| `mosaic.api.base-url` | `http://127.0.0.1:8000` | The Python API. It always serves on this address; keep them in step. |
| `mosaic.api.timeout-seconds` | `30` | The API only computes figures, so a slow answer means something is wrong. |
| `mosaic.python.autostart` | `true` | `false` to start the Python API yourself. |
| `mosaic.python.executable` | empty | Empty: SolarHome's `config/py/mosaic/.venv` interpreter if present, else `python` from `PATH`. |
| `spring.datasource.url` | `jdbc:sqlite:config/Default.db` | The business database; a relative file lives under SolarHome (`-Dsolar.home`, else the working directory). |
| `spring.datasource.username`, `.password` | `mosaic` | SQLite ignores them, but SolarFramework registers no data source without them. Placeholders, not secrets. |
| `mosaic.data.prepare-on-start` | `true` | Import empty tables and write a missing export on start. |
| `mosaic.data.source-dir` | `config/py/mosaic/datasets` | The original Olist CSV files, read only. |

The written suggestions and caveats need LM Studio serving the model named in `config/ai/agents.json`,
or the `GROQ_API_KEY` environment variable, which moves every bot to the file's `Groq` service. That service's
`apiKey` is `${GROQ_API_KEY}`, which SolarFramework reads from the environment, so the key is never in the file.
Without either, each panel shows its fixed text, written from the same figures.

## Pages

| Path | Template | Shows |
| --- | --- | --- |
| `/` | `sales.html` | Sales: sales by month with the forecast; tabs for its evidence (accuracy against simple rules, limitations, data left out), a suggested opportunity and the possible caveats |
| `/delivery` | `trend.html` | Delivery: the late-delivery rate by month; the same tabs, for the customer states where it improved most |
| `/reviews` | `trend.html` | Reviews: the share of 1 or 2 star reviews by month; the same tabs, for categories whose reviews improved while sales grew |
| `/sellers` | `trend.html` | Sellers: active sellers a month; the same tabs, for categories where new sellers also find more orders |
| `/about` | `about.html` | The application and its five authors |

The four data pages share one layout: a switcher between them, the question the page asks and its answer in
figures, the monthly chart, then the Evidence / Suggested opportunity / Possible caveats tabs.
Every figure carries one of three markers: solid teal edge = observed, dashed violet = model
prediction, amber hatching = hypothetical. The Help page explains them.

## Templates, as in SolarERP

```
templates/
  sales.html     the Sales page (script in static/js/sales.js)
  trend.html     the Delivery, Reviews and Sellers pages (Measure; script in static/js/trend.js)
  fragments/
    head.html      pageHead(title)     every page's <head>: Bootstrap, main.css, mosaic.css, scripts
    header.html    mainHeader          menu button, logo, sidebar, account icon, breadcrumb bar
    footer.html    mainFooter
    items/         pieces shared by several pages: sidebar, breadcrumb, notice,
                   pages (the data-page switcher), panels (the three tabs and the two answer panels)
    sales/         the part of sales.html         (page: chart, tabs, evidence)
    trend/         the part of trend.html         (page: chart, tabs, evidence)
```

A page's script calls `MosaicCharts` on `DOMContentLoaded`. `static/css/main.css` holds the palette, fonts and
the shell (header, sidebar, breadcrumb, footer, card, table); what goes inside a page is in
`static/css/mosaic.css`. Bootstrap 5.3.8 and Chart.js come from WebJars and the two fonts from
`static/fonts/`, so a demo needs no CDN.

## Code layout (`src/main/java/mu/mosaic/opportunity`, with `../OpportunityImpl` in the same packages)

| Package | Module | Holds |
| --- | --- | --- |
| `.` | App | `OpportunityApp`, the Spring Boot application (UTC default time zone, SolarFramework's AI and database configs) |
| `config` | App | `WebConfig` (SolarFramework's request logger) |
| `controller` | App | Page controllers |
| `controller/api` | App | Browser-facing JSON: the overview's and the trend pages' suggestion and caveats with their evidence |
| `service` | App | `HelpService` |
| `service` | Impl | `MosaicApi` (Python API calls), `PythonApiLauncher` (SolarFramework's `PythonRunner` in the Spring lifecycle), `Formatter` (template formatting, `${@format.brl(x)}`) |
| `service/ai` | Impl | Local AI configuration, scenario, suggestion and caveat narration, and numeric checks |
| `obj` | App | `Breadcrumbs` (`new Breadcrumbs(page, crumbs…).addTo(model)`), `Selection` (the periods and filters in the URL) |
| `obj` | Impl | `ApiResult` (with `addTo(model, name)` and `as(Type.class)`), `Measure` (the trend pages) |
| `obj/api` | Impl | The API's replies as typed records (Gson), each with its own behaviour, e.g. `TrendCheck.sentence(fmt)` |
| `entity` | App | The nine Olist tables |
| `data` | App | `BusinessDatabase` (import and export on start), `EntityTable` (one entity's table, filled from its file), `CsvReader` (RFC 4180) |

See [code organisation](../../docs/code-organisation.md) for the shared helpers and
the Python endpoint layout.

## Test

```powershell
cd Java\OpportunityImpl; .\mvnw.cmd install    # NumberCheckTest
cd ..\OpportunityApp;   .\mvnw.cmd test       # PagesRenderTest
```

Only the essential tests are kept. `NumberCheckTest` guards the check that stops the model from inventing figures.
`PagesRenderTest` renders every page from trimmed real API responses (`src/test/resources/api`) and with the API
failing. `src/test/resources/config/application.properties` keeps the test context off `config/Default.db` and the
Olist CSVs.
