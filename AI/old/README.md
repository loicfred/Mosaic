# Archived: the Python LLM client

Kept for reference only; nothing imports it and pytest skips this folder (`conftest.py`).

On 2026-09-23 the team moved every language-model call into the Spring app
(`../../Java/OpportunityApp`, SolarFramework's AIImpl), so the project has one LLM client instead of
two. The Python API now only computes figures and returns no prose.

| Archived file | Was | Now in OpportunityApp |
| --- | --- | --- |
| `ai/client.py` | OpenAI-compatible HTTP client for LM Studio | AIImpl's `IAIService` |
| `ai/explain.py` | Scenario narrative: prompt, number check, template fallback | `ai/ScenarioNarrator`, `ai/NumberCheck` |
| `tests/test_ai_client.py`, `tests/test_explain.py` | Their tests | `ScenarioNarratorTest`, `NumberCheckTest` |

Also removed from the API: the `explain` field of `POST /api/scenarios/sales-impact`, the `narrative`
in its response, `GET /api/ai/health`, and the `MOSAIC_LLM_*` settings in `app/config.py`:

```python
LLM_BASE_URL = os.environ.get("MOSAIC_LLM_BASE_URL", "http://localhost:1234").rstrip("/")
LLM_MODEL = os.environ.get("MOSAIC_LLM_MODEL", "")  # empty: whatever the server has loaded
LLM_TIMEOUT_SECONDS = float(os.environ.get("MOSAIC_LLM_TIMEOUT_SECONDS", "120"))
# Reasoning models spend part of this budget on hidden reasoning before any visible text.
LLM_MAX_TOKENS = int(os.environ.get("MOSAIC_LLM_MAX_TOKENS", "1500"))
LLM_ENABLED = os.environ.get("MOSAIC_LLM_ENABLED", "true").strip().lower() not in {"0", "false", "no"}
```

To run this code again it would have to go back to `app/ai/` with those settings restored.
