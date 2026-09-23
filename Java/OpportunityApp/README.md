# OpportunityApp — the Mosaic website

Spring Boot and Thymeleaf website on SolarFramework (`WebUtils` for Thymeleaf and request logging, `core`
for utilities), laid out like SolarERP: the same header, sidebar, breadcrumb bar, footer and `mod-*`
page components, with pages assembled from fragments. It replaces the React client in `../../front-end/`,
which is left untouched.

The Python API in `../../AI/` stays the single source of truth for every number: this app calls it
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
- The Python API set up as in `../../AI/README.md` (`AI/.venv` with its requirements).

## Modules

| Module | Holds |
| --- | --- |
| `../OpportunityImpl` | Everything that is not web, as a plain Spring library: the Python API client (`MosaicApi`) and launcher (`PythonApiLauncher`), `Formatter`, the local AI (`service/ai/`), `ApiResult`/`ApiData`. No controllers, templates or database. |
| `OpportunityApp` (here) | The website: controllers, templates, static files, `WebConfig`, `Breadcrumbs`, `HelpService`, and the business database. |

Both keep the package `mu.mosaic.opportunity`, so Spring's component scan finds the library's beans unchanged.

## Business database

The site keeps the Olist records in a SQLite database, `config/Default.db` (git-ignored), through
SolarFramework's `DatabaseImpl`, and every figure the Python API returns is computed from what that database holds:

1. One entity per Olist file (`entity/Olist*.java`): table = file name without `.csv`, columns = the file's
   headers (the file's `lenght` typos included), plus SolarFramework's `ID`, `CreatedAt`, `UpdatedAt`, `DeletedAt`.
2. On start, a table that is still empty is filled from `../../AI/datasets` (`mosaic.data.source-dir`), one
   transaction per table, IDs in file order. The first start takes about 25 s for the 1.55 million rows, of which
   9 s is the million geolocation rows; later starts skip it.
3. If a table's file is missing from SolarHome's `config/py/mosaic/datasets/`, the whole database is written there with
   `IDatabaseService.exportCsv` (about 35 s). Delete the folder to write it again.
4. `PythonApiLauncher` starts the extracted package from SolarHome's `config/py/mosaic/`. Python reads
   `datasets/` and `models/` beside its `app/` package.

The export's columns come out in the database's order (`ID`, `CreatedAt`, `DeletedAt`, `UpdatedAt`, then the
file's columns alphabetically), and it also holds SolarFramework's two AI tables (`ai_chat_message.csv`,
`ai_conversation.csv`). The API reads columns by name and ignores extra files, so no figure changes; only
`/api/datasets` lists the extra columns. Prices lose trailing zeros (`58.90` becomes `58.9`), which parse to the
same number.

The API refuses a model trained on other files, so the models in `AI/models` (trained on the originals) do not
serve the export. The Python API never trains at startup; it only loads saved models. Train the export's models
once, after the first export or whenever the export changes (model pages then report the model as stale). Training
takes about 50 s. Until then, observed analytics remain available and model-backed pages report that the model is
unavailable:

```powershell
cd AI
$env:MOSAIC_DATASETS_DIR = "..\Java\OpportunityApp\config\py\mosaic\datasets"
$env:MOSAIC_MODELS_DIR = "..\Java\OpportunityApp\config\py\mosaic\models"
.\.venv\Scripts\python.exe -m app.forecast.train
.\.venv\Scripts\python.exe -m app.models.train_risk
```

An API already answering on port 8000 is reused as
it is, so stop one started on `AI/datasets` before starting the site.

## Run

From IntelliJ: the project lists `Java/OpportunityImpl/pom.xml` and `Java/OpportunityApp/pom.xml` as Maven projects (`.idea/misc.xml`, each module with its `.iml` in `.idea/modules.xml`) and ships a shared
**OpportunityApp** run configuration (`.idea/runConfigurations/`). If IntelliJ was open while these were
added, reload the Maven projects once.

From a terminal:

```powershell
cd Java\OpportunityApp
.\mvnw.cmd spring-boot:run
```

Open http://localhost:8080. On startup the site starts the Python API with `python -m app.main`
when an extracted Python project is available in SolarHome, unless one is already answering on port 8000.
It stops the process on normal shutdown (Ctrl+C, IntelliJ's stop button). While the bundled archive is absent,
start the Python API separately from `AI/` with the dataset and model paths above.
The first start imports the database first (see above). The dataset takes about 10–15 s to load;
pages show "not answering" until then, and the log prints `Analytics API ready.`

A hard kill of the Java process (Task Manager, `taskkill /F`) cannot run shutdown code, so the Python
process is left running; the next start finds it on port 8000 and reuses it.

`OpportunityImpl` can use a bundled `mosaic-python.zip` resource.
The archive must contain `app/main.py` at its root. The launcher extracts it under
`config/py/mosaic` in SolarHome (`-Dsolar.home`, else the working directory) before starting Python.
Claude's project `Stop` hook runs `.claude/hooks/package-python.ps1` after each completed Claude turn
to build that archive from the `.py` files in `AI/app`; it does not include datasets, models, a Python
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
| `mosaic.data.source-dir` | `../../AI/datasets` | The original Olist CSV files, read only. |

The scenario summary and the chat box need LM Studio serving the model named in `config/ai/agents.json`.
The scenario page shows its template summary at once and swaps in the model's version when it answers;
without LM Studio it keeps the template, and the chat box says the model is offline.

## Pages

| Path | Template | Shows |
| --- | --- | --- |
| `/` | `index.html` | The hidden problem (categories falling behind the business), latest-month figures, sales history with forecast, forecast accuracy against simple baselines, data exclusions |
| `/categories?flag=` | `categories.html` | Every category's recent change against the whole business; filters `underperforming_total`, `latest_month_anomaly` |
| `/categories/{name}` | `category.html` | Why a category is flagged: each rule, its inputs and threshold; monthly series and forecast |
| `/risk` | `risk.html` | Late-delivery and low-review rates, model evaluation, riskiest open orders, least reliable sellers |
| `/scenario?change=&horizon=` | `scenario.html` | Hypothetical sales change and its effect on orders, late deliveries, reviews and seller capacity |

Every figure carries one of three markers: solid teal edge = observed, dashed violet = model
prediction, amber hatching = hypothetical.

## Templates, as in SolarERP

```
templates/
  index.html, categories.html, category.html, risk.html, scenario.html   one per page
  fragments/
    head.html      pageHead(title)     every page's <head>: Bootstrap, main.css, mosaic.css, scripts
    header.html    mainHeader          menu button, logo, sidebar, state key, breadcrumb bar
    footer.html    mainFooter
    items/         pieces shared by several pages: sidebar, breadcrumb, statekey, notice, score
    index/         the parts of index.html        (statement, latest, sales, next)
    categories/    the parts of categories.html   (table)
    category/      the parts of category.html     (summary, evidence, series)
    risk/          the parts of risk.html         (delivery, open-orders, sellers, reviews)
    scenario/      the parts of scenario.html     (controls, baseline, results, capacity, narrative, assumptions)
```

A page part that draws a chart carries its own `<script>`, which calls `MosaicCharts` on
`DOMContentLoaded`. `static/css/main.css` holds SolarERP's rules unchanged (only the ones used here);
Mosaic's own rules are in `static/css/mosaic.css`. Bootstrap 5.3.8 and Chart.js come from WebJars, so
a demo needs no CDN.

## Code layout (`src/main/java/mu/mosaic/opportunity`, with `../OpportunityImpl` in the same packages)

| Package | Module | Holds |
| --- | --- | --- |
| `.` | App | `OpportunityApp`, the Spring Boot application (UTC default time zone, SolarFramework's AI and database configs) |
| `config` | App | `WebConfig` (SolarFramework's request logger) |
| `controller` | App | Page controllers |
| `controller/api` | App | Browser-facing JSON: the assistant, the scenario's AI summary |
| `service` | App | `HelpService` |
| `service` | Impl | `MosaicApi` (Python API calls), `PythonApiLauncher` (SolarFramework's `PythonRunner` in the Spring lifecycle), `Formatter` (template formatting, `${@format.brl(x)}`) |
| `service/ai` | Impl | Local AI configuration, assistant tools, scenario narration and numeric checks |
| `obj` | App | `Breadcrumbs` (with `addTo(model, page, crumbs…)`) |
| `obj` | Impl | `ApiResult` (with `addTo(model, name)`), shared nested JSON access in `ApiData` |
| `entity` | App | The nine Olist tables |
| `data` | App | `BusinessDatabase` (import and export on start), `CsvImport` (one file into one table), `CsvReader` (RFC 4180) |

See [code organisation](../../docs/code-organisation.md) for the shared helpers and
the Python endpoint layout.

## Test

```powershell
cd Java\OpportunityImpl; .\mvnw.cmd install    # also installs the jar and the test fixtures the site's tests use
cd ..\OpportunityApp;   .\mvnw.cmd test       # 23 tests
```

`OpportunityImpl` tests cover formatting, the API client against a real local HTTP server (errors, encoding, the
POST body), the AI tools and narration, and the launcher starting and stopping a stand-in Python process through
an application context. The launcher tests skip themselves
when `AI/.venv` is missing. `OpportunityApp` tests render every page from trimmed real API responses and with the
API failing, check the shared shell (sidebar, breadcrumbs, title), and import a few real rows of every Olist file
(`src/test/resources/olist-sample`: quoted ids, a multi-line review, blank timestamps, a BOM) into SQLite, export
them and compare with the source. `src/test/resources/config/application.properties` keeps every test context off
`config/Default.db` and `AI/datasets`.
