# Code organisation

The Python API owns data loading, calculations and model inference. The Java application
calls that API, renders pages and supplies the optional language-model explanations.
Java follows the SolarERP pattern of controllers, services and data objects.

## Python

`AI/app/main.py` assembles the application and loads its startup state.
`AI/app/api/__init__.py` explicitly registers the endpoint modules. Each `get_*` module
owns one endpoint, including validation and response formatting; calculations remain
in `analysis/` and `forecast/`, while CSV access remains in `data/`.

| Endpoint | Module under `AI/app/api/` |
| --- | --- |
| GET `/api/health` | `get_health.py` |
| GET `/api/sales/history` | `get_sales_history.py` |
| GET `/api/sales/forecast` | `get_sales_forecast.py` |
| GET `/api/sales/categories` | `get_sales_categories.py` |
| GET `/api/sales/categories/{category}` | `get_category_detail.py` |
| GET `/api/risk/delivery/summary` | `get_delivery_summary.py` |
| GET `/api/risk/delivery/open-orders` | `get_delivery_open_orders.py` |
| GET `/api/risk/delivery/sellers` | `get_delivery_sellers.py` |
| GET `/api/risk/reviews/summary` | `get_review_summary.py` |
| GET `/api/risk/reviews/unreviewed` | `get_unreviewed_orders.py` |
| POST `/api/scenarios/sales-impact` | `get_sales_impact.py` |

The `get_` prefix is a filename convention. The scenario endpoint remains POST.
`deps.py` centralises artifact loading, model availability/staleness checks and model
evaluation summaries. `analysis/populations.py` provides the shared purchase-month and
known-outcome filter used by delivery, review and scenario calculations. It preserves
empty selections and does not mutate the source frame.

## Java

Two Maven modules under `Java/`, both in the package `mu.mosaic.opportunity` and both with SolarFramework as parent;
each is built on its own with its `mvnw.cmd`, and the site depends on the library by version.

`Java/OpportunityImpl/` is a plain Spring library with no web layer, templates or database, so it can later
become a SolarERP module:

- `service/MosaicApi.java` owns HTTP calls and readable API errors.
- `service/PythonApiLauncher.java` owns the Python process lifecycle and extracts a bundled Python archive to
  SolarHome's `config/py/mosaic`. Python reads `datasets/` and `models/` beside the extracted `app/` package.
- `service/Formatter.java` owns display formatting, including missing values and signed rounding.
- `service/ai/` owns chatbot setup, allowed tools, narration and numeric evidence checks.
- `obj/ApiResult.java` and `obj/ApiData.java` hold API responses; `ApiData` centralises optional nested JSON access.

`Java/OpportunityApp/` is the website:

- `controller/` assembles template models; `controller/api/` handles browser JSON requests.
- `config/WebConfig.java`, `obj/Breadcrumbs.java` and `service/HelpService.java` serve the pages.
- `entity/` holds one SolarFramework entity per Olist file (table = file name, columns = the file's headers).
- `data/BusinessDatabase.java` runs once all beans exist and before any starts: it fills empty tables from
  `AI/datasets` through `data/CsvImport.java` (JDBC batches, one transaction per table) and, when SolarHome's
  `config/py/mosaic/datasets/` lacks a table's file, writes the database there with SolarFramework's `IDatabaseService.exportCsv`.

Data flow: `AI/datasets/*.csv` → `Java/OpportunityApp/config/Default.db` (SQLite) → `Java/OpportunityApp/config/py/mosaic/datasets/*.csv`
→ the Python API, with models trained on that export in `Java/OpportunityApp/config/py/mosaic/models/`
(`Java/OpportunityApp/README.md` has the training command). The export matches the originals figure for figure;
it adds SolarFramework's record columns (`ID`, `CreatedAt`, `UpdatedAt`, `DeletedAt`), which the loaders ignore.

Shared helpers remove repeated logic without requiring unrelated endpoints or services
to inherit from a common base class. API response fields and template formatting method
names remain stable for callers.

## Verification

Run the active Python suite from `AI/`:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

Run the Java suites, the library first (its install also provides the fixtures the site's tests use):

```powershell
cd Java\OpportunityImpl; .\mvnw.cmd install
cd ..\OpportunityApp;   .\mvnw.cmd test
```

`AI/old/` is archived code, not part of the active Python suite. The tests cover observed
metrics, model availability, scenario calculations, API calls, page rendering and AI
fallbacks. `AI/tests/test_observed_rates.py` additionally checks reporting boundaries,
unknown outcomes, missing dates and empty periods.
