# 2026-09-23i — Unpack bundled Python on startup

Author: Codex

## Why

Allow OpportunityImpl to run the Python API from a bundled archive in SolarHome.

## What changed

- `PythonApiLauncher` now uses SolarFramework's `SolarHome.pathTo` for `config/py/mosaic`. With no explicit project directory, it extracts a bundled archive there when present, then starts the package from that directory.
- Extraction rejects entries outside its staging directory, requires `app/main.py`, and replaces only the older extracted `app/` package after validation. Sibling `datasets/` and `models/` remain in place.
- `.claude/settings.json` registers a Claude `Stop` hook. `.claude/hooks/package-python.ps1` creates the archive from Python source files after a completed Claude turn. The archive itself was not added in this session.
- The website README, configuration comment, code organisation, and requirements open list describe the behavior and remaining packaged-JAR verification.

## Verification

- A synthetic hook run produced an archive with `app/main.py` and excluded a `.pyc` file.
- `Java/OpportunityImpl`: `mvnw.cmd -q test` passed after the launcher changes.
- The focused `PackagedPythonTest`, `PythonApiLauncherTest`, and `LocalAiTest` suites passed after the SolarHome path adjustment.
- Packaged startup was not run because the archive is intentionally absent.
