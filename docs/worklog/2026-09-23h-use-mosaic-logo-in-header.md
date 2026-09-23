# 2026-09-23h — Use Mosaic logo in header

Author: Codex

## Why

The shared header displayed a placeholder tile, while the Help sidebar repeated the full Mosaic logo and used space needed for navigation.

## What changed

- The shared header now uses the existing `Java/OpportunityApp/src/main/resources/static/img/logo.jpg` asset.
- Removed the duplicate logo from `Java/OpportunityApp/src/main/resources/templates/help.html` and its unused rules in `Java/OpportunityApp/src/main/resources/static/css/help.css`.

## Verification

- Checked the template references and confirmed that the image asset exists.
- `PagesRenderTest` could not run: the Maven wrapper was denied access to `C:\Users\user\.m2` before Maven started.
