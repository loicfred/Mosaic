"""Minimal client for Groq's OpenAI-compatible chat completions API (JSON mode).

The API key is read from settings on the server and never reaches the browser.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.core.config import get_settings

log = logging.getLogger("opportunityos.llm")


class LLMError(Exception):
    """The model could not be reached or returned something unusable."""


def chat_json(messages: list[dict[str, str]], max_tokens: int = 900) -> dict[str, Any]:
    s = get_settings()
    if not s.external_ai_enabled:
        raise LLMError("GROQ_API_KEY is not set")
    try:
        r = httpx.post(f"{s.groq_base_url.rstrip('/')}/chat/completions",
                       headers={"Authorization": f"Bearer {s.groq_api_key.strip()}"},
                       json={"model": s.groq_model, "messages": messages, "temperature": 0.2,
                             "max_tokens": max_tokens, "response_format": {"type": "json_object"}},
                       timeout=s.llm_timeout_seconds)
    except httpx.HTTPError as e:
        raise LLMError(f"request failed: {type(e).__name__}") from None
    if r.status_code != 200:
        # Groq error bodies do not contain the key; log the status and code only.
        try:
            code = (r.json().get("error") or {}).get("code")
        except (ValueError, AttributeError):
            code = None
        log.warning("groq returned status=%s code=%s", r.status_code, code)
        raise LLMError(f"status {r.status_code}")
    try:
        content = r.json()["choices"][0]["message"]["content"]
        out = json.loads(content)
    except (KeyError, IndexError, TypeError, ValueError):
        raise LLMError("response was not valid JSON") from None
    if not isinstance(out, dict):
        raise LLMError("response was not a JSON object")
    return out
