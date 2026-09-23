# 2026-09-23j — Centralize config loading and Python startup

Author: Codex

## What changed

- SolarFramework's AI, database, mail and backup managers now expose only `LoadFromFile()` and read their default files through `JSONItem.ReadOrCreate`. The path-taking load methods and mail/backup config-file properties were removed. SolarERP's AI and database startup calls were updated to the new API.
- Mosaic's chatbots use SolarFramework's AI manager directly. `PythonApiLauncher` extracts a bundled `app/` into SolarHome's `config/py/mosaic/` while preserving `datasets/` and `models/` beside it.
- The Python API now trains missing or stale models from its own dataset folder at production startup. Training failures leave observed analytics available. Category translation is shared by order features and category summaries, and the Java assistant separates turn execution from answer validation.
- The dataset endpoint strips a UTF-8 byte-order mark from CSV headers. The Help page and setup docs now describe the current data/model paths and the archived React brief no longer lists removed AI endpoints.

## Verification

- SolarFramework's affected-module and full-reactor tests passed; SolarERP's affected modules compiled with the pathless API.
- `OpportunityImpl` installed with its tests passing, and `OpportunityApp` tests and `PagesRenderTest` passed.
- Python category/order tests passed (19), and API route tests passed (22). Production startup with a fresh model folder trained all three models and reported them loaded; the temporary artifacts were removed.
