# 2026-09-23 — Evidence charts for the suggestion and caveats; chatbot removed

Author: Claude

- The overview's "Suggest investment" and "View possible caveats" panels now draw charts from the figures their text was written from:
  - Suggestion: monthly sales of the top 3 suggested categories, and their late-delivery and low-review rates against the whole business.
  - Caveats: monthly sales of the categories falling furthest behind, monthly late-delivery and low-review rates (only when those caveats trigger), and the low-review rate on late against on-time orders.
- Python (new fields only, no existing field changed): `caveats.window_rate` adds `monthly`, the `worst` categories carry `series`, and `/api/sales/opportunities` candidates carry `series` plus a top-level `business_series`.
- `OverviewAiController` returns `{text, source, model, reason, evidence}`, where `evidence` is the Python API body. The prompts are built as before, so the extra series never reach the language model. `MosaicCharts.lines` and `MosaicCharts.bars` were added to `charts.js`, with the colours `--series-1..3` in `main.css`.
- Each AI button asks the site once per page load, even when that fails (`panel.dataset.requested`). Further clicks only show or hide the panel; reloading asks again.
- The Ask Mosaic chatbot was removed: `Assistant`, `MosaicToolbox`, `AssistantController`, their tests, `items/assistant.html`, `assistant.js`, the `.assistant-*` CSS, the help guide section, the `MosaicAssistant` entry in `config/ai/agents.json`, `LocalAi.ASSISTANT` and the Caffeine dependency. FR-8 in `docs/requirements.md` now describes the evidence charts.
- Verified: `python -m pytest tests -q` from `AI/` gives 111 passed. `mvnw install` for `OpportunityImpl` and `mvnw test` for `OpportunityApp` pass, including the new `OverviewAiControllerTest` and `PagesRenderTest`. `node --check` passes on `charts.js` and the page script. On the real data the suggestion has 5 candidates with 20 months each; the triggered caveats are the falling categories and low reviews on late orders. Not verified: the charts in a browser (the site was not started).
