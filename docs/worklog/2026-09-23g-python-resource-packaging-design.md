# 2026-09-23g — Python resource packaging design

Author: Codex

## Why

Clarify how the Python application can ship with the Java implementation JAR.

## What changed

No application code changed. Proposed that Maven include `AI/app/**/*.py` as `py/mosaic/app/...` JAR resources, and that `PythonApiLauncher` extract them to a writable directory before launching `app.main`. A separate ZIP is unnecessary. Dataset exports, model files, the Python interpreter and third-party Python packages remain external.

## Verification

Read the current Python application startup, configuration, Java launcher, launcher tests, and Maven module POM. The design is awaiting user confirmation; no build or runtime test was run.
