# 2026-09-23 — Cloud API keys handled by SolarFramework

Author: Claude

- SolarFramework (separate repository, not committed): new `core/.../util/EnvValue.java` resolves a setting written as `${NAME}` from `-DNAME`, else the environment variable `NAME`. `AIService` keeps the reference as its key and resolves it only for the request, so `SaveAsFile` writes `${NAME}` back, never the secret.
- SolarFramework `LMStudioModelManager` now sends the key as a bearer token, falls back to the standard `/v1/models` list when `/api/v0/models` is missing, and runs the `lms` CLI only for a server on this machine. `isAvailable()` therefore works for Groq and any other OpenAI-compatible endpoint. Documented in SolarFramework `docs/AI.md`.
- Mosaic: `config/ai/agents.json` gives the `Groq` service `"apiKey": "${GROQ_API_KEY}"`. `LocalAi` no longer reads the environment itself or treats every `https://` address as up: `useCloud` switches the bots to Groq when its key resolves, and `reachable` asks the service. `status()` reports tool support as unknown when the endpoint gives no model state.
- Verified: SolarFramework `./mvnw.cmd -o clean install -pl core,core-modules/AIImpl -am` passed (core 189 tests, AIImpl 56, including the new `EnvValueTest`, `AIServiceKeyTest` and `LMStudioModelManagerTest` cases). OpportunityImpl `clean install` passed with 72 tests, and OpportunityApp `test` passed with 23 tests, including `PagesRenderTest`. SolarERP only calls `isAvailable()` and the key getter and setter, and no existing signature changed. SolarERP was not built.
- Not checked live: a real Groq call through the new path, and the site in a browser.
- Open: SolarFramework must be republished before this `LocalAi` is pushed (see `docs/requirements.md`).
