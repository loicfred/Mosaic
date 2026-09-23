# 2026-09-22a — Spring website OpportunityApp replaces the React client

Author: Claude

## Why

The team found React too complex and prefers Spring and Java. The website became a Spring Boot + Thymeleaf
module on the user's own SolarFramework, laid out like SolarERP. The React client in `front-end/` was left
untouched but is no longer the target.

## What changed

- `Java/OpportunityApp/` (Maven parent `org.solarframework.mu:SolarFramework:1.0`, package `mu.mosaic.opportunity`, main class `OpportunityApp`) with five pages: `index.html`, `categories.html`, `category.html`, `risk.html`, `scenario.html`.
- Pages are assembled from fragments as in SolarERP: `fragments/head.html` (`pageHead(title)`), `header.html` (menu button, sidebar, breadcrumb bar), `footer.html`, shared pieces in `fragments/items/`, and one folder per page named after its template (`fragments/index/`, `categories/`, `category/`, `risk/`, `scenario/`).
- `static/css/main.css` holds SolarERP's rules unchanged (only the ones used); `static/css/mosaic.css` holds Mosaic's own, including the three markers: solid teal edge = observed, dashed violet = model prediction, amber hatching = hypothetical.
- Java packages mirror SolarERP's `application/`: `config/WebConfig` (SolarFramework's request logger), `controller/` and `controller/api/`, `obj/` (`ApiResult`, `Breadcrumbs` with its `Crumb` record), `service/` (`MosaicApi`, `PythonApiLauncher`, `Formatter`).
- `PythonApiLauncher` starts `python -m app.main` from the nearest `AI/` above the working directory, using `AI/.venv`, unless the API already answers on port 8000, and stops it with the site.
- Bootstrap 5.3.8 and Chart.js come from WebJars, so the demo needs no CDN.
- IntelliJ: the pom is listed in `.idea/misc.xml` (JDK 25) and a shared run configuration is in `.idea/runConfigurations/OpportunityApp.xml`. A hand-written `.iml` was not enough — IntelliJ only resolved the libraries once the pom was added as a Maven project from the IDE, after which it keeps the module in its own external storage and dropped the `.iml` from `.idea/modules.xml`.

## Traps found on the way

- Spring Boot 4 no longer provides a `RestClient.Builder` bean without its separate module; `MosaicApi` builds its own client.
- The JDK HTTP client attempts an h2c upgrade on plain HTTP, and uvicorn then drops the POST body. `MosaicApi` forces HTTP/1.1.
- `Set.of(...).contains(null)` throws, which broke `/categories` without a filter.
- Thymeleaf's restricted mode refuses bean calls (`@format`) inside fragment parameters; `Breadcrumbs.addTo` puts a plain `title` in the model instead.
- A hard kill of the Java process cannot stop Python; the next start reuses the API it finds on port 8000.
- The harness's own working directory inside `web/` blocked renaming the folder on Windows.

## Verification

- Every page rendered against the real API and with the API failing; screenshots taken with headless Edge at desktop and narrow widths.
- Maven test suite passing at the end of the session; the launcher tests start and stop a stand-in Python process, directly and through the whole application context.
- Not verified: the sidebar opening (headless screenshots cannot click), a real phone browser.
