# 2026-09-23 — Site finds its folder from any working directory

Author: Claude

- Starting the site from the repository root failed with `SQLException: ...\Hackathon-Mosaic\config does not exist`, because SolarHome, `.env` and `mosaic.data.source-dir` resolve against the working directory.
- Added `Java/OpportunityApp/src/main/java/mu/mosaic/opportunity/ModuleHome.java`, called first in `OpportunityApp.main`. It finds the module folder above `target/` and sets `solar.home`, `spring.config.import` (the `.env`) and `mosaic.data.source-dir` there. `-Dsolar.home`, `SOLAR_HOME` or system properties that are already set still win.
- Verified: `mvnw spring-boot:run -Dspring-boot.run.workingDirectory=<repo root>` opened `Java/OpportunityApp/config/Default.db`, started Python from `Java/OpportunityApp/config/py/mosaic`, and `GET http://localhost:8080` returned 200. No `config/` folder was created at the root. `PagesRenderTest` was not run (no page or `MosaicApi` caller changed).
- Limitation: because `mosaic.data.source-dir` is now set as a system property, a `MOSAIC_DATA_SOURCE_DIR` environment variable no longer overrides it. Pass `-Dmosaic.data.source-dir=...` instead.
