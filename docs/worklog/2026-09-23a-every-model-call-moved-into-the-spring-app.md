# 2026-09-23a — Every model call moved into the Spring app

Author: Claude

## Why

The project had two LLM clients: Python wrote the scenario summary, and the planned chatbot would have been a
second one. The user chose one client, in Java, through SolarFramework's AIImpl, because Java is easier for the
team to follow.

## What changed

- Python: `AI/app/ai/` and its two test files moved to `AI/old/` (kept for reference, skipped by pytest through `AI/old/conftest.py`, explained in `AI/old/README.md`). `POST /api/scenarios/sales-impact` now returns figures only (no `explain` field, no `narrative`), `GET /api/ai/health` is gone, and the `MOSAIC_LLM_*` settings left `AI/app/config.py`.
- The model and both chatbots' instructions live in `Java/OpportunityApp/config/ai/agents.json`, SolarFramework's own AI config format, as in SolarERP: one service (`LMStudio`, `google/gemma-4-e4b` on `http://localhost:1234`), `MosaicAssistant` and `ScenarioNarrator`. `service/ai/LocalAi` loads it only if it exists, because SolarFramework's loader writes a new file when it finds none. No file means AI off.
- `service/ai/ScenarioNarrator`: the Python summary ported — same evidence, same template, and any figure not in the evidence sends it back to the template (`NumberCheck`, which also accepts numbers written inside evidence text such as "2018" in "2018-06").
- `service/ai/Assistant` + `MosaicToolbox`: a chat box in the header on every page (`fragments/items/assistant.html`, `static/js/assistant.js`), one in-memory conversation per session, never saved. Six read-only tools call the API and answer in text formatted like the site. Only those six tool names are approved. An answer with a figure not found in the tools' replies, the visitor's words or the instructions is withheld and struck from the transcript. Endpoint: `controller/api/AssistantController` (`POST`/`DELETE /api/assistant`, `GET /api/assistant/status`).
- SolarFramework: `AIImpl`'s `AIService.chatModel()` now passes a retry template with no retries. Spring AI's default retries a failed call ten times with back-off; with Gemma answering in over 120 s on this machine, one scenario page waited through retry after retry. Rebuilt and reinstalled only `AIImpl` (the installed jars had been built from the same uncommitted working copy). `AIServiceRetryTest` checks a failing server is called once.

## Verification

- Python: `python -m pytest -q` — 75 passed.
- Java: `mvnw.cmd clean test` in `Java/OpportunityApp` — 72 passed, including the shipped `agents.json` loading (`LocalAiTest`) and the summary and assistant on a scripted model (`FakeAIService`).
- SolarFramework: `AIServiceRetryTest` passed, and `AIImpl` reinstalled with its tests.
- A real start loaded the config ("Loaded 1 service(s) and 2 chatbot(s)") and started the API. The real model has not yet answered a summary or a question: the first attempt is what exposed the retries, and the run was stopped there.
