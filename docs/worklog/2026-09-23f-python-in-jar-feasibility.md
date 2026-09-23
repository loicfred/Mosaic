# 2026-09-23f — Python in JAR feasibility

Author: Codex

## Why

Clarify whether OpportunityImpl can launch Python code stored in JAR resources.

## What changed

No application code changed. Inspection found that `PythonApiLauncher` currently requires a real `AI/app/main.py` path and launches `app.main` from that directory. `OpportunityImpl` has no main resource directory containing Python code. A packaged resource would need extraction to a normal filesystem directory before the external Python process could run it.

## Verification

Read `PythonApiLauncher.java`, the module POM, and the host application's Python settings. No build or runtime test was run because this session only assessed feasibility.
