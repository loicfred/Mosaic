"""Minimal client for an OpenAI-compatible local server (LM Studio by default).

Never raises: every failure is returned as ``ChatResult.error`` so the caller can fall back to
a deterministic explanation. No API key is used or supported; the endpoint is local.
"""
from dataclasses import dataclass

import httpx

from app.config import LLM_MAX_TOKENS


@dataclass(frozen=True)
class ChatResult:
    text: str | None
    error: str | None = None
    model: str | None = None


def complete(
    prompt: str, *, base_url: str, model: str, timeout: float, temperature: float = 0.2,
    max_tokens: int = LLM_MAX_TOKENS, transport: httpx.BaseTransport | None = None,
) -> ChatResult:
    # Gemma's chat template has no system role, so the instructions go in the user turn.
    payload = {
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    if model:
        payload["model"] = model
    try:
        with httpx.Client(timeout=timeout, transport=transport) as client:
            response = client.post(f"{base_url}/v1/chat/completions", json=payload)
        if response.status_code != 200:
            return ChatResult(None, error=f"llm_http_{response.status_code}")
        body = response.json()
    except httpx.HTTPError as exc:
        return ChatResult(None, error=f"llm_unreachable: {type(exc).__name__}: {exc}")
    except ValueError as exc:
        return ChatResult(None, error=f"llm_bad_json: {exc}")

    choices = body.get("choices") or []
    if not choices:
        return ChatResult(None, error="llm_empty_response", model=body.get("model"))
    text = (choices[0].get("message") or {}).get("content") or ""
    if not text.strip():
        # Reasoning models can spend the whole token budget before writing any visible text.
        return ChatResult(None, error="llm_empty_response", model=body.get("model"))
    return ChatResult(text.strip(), model=body.get("model"))


def list_models(base_url: str, timeout: float, transport: httpx.BaseTransport | None = None) -> list[str]:
    """Model ids the server currently exposes; empty when it is unreachable."""
    try:
        with httpx.Client(timeout=timeout, transport=transport) as client:
            response = client.get(f"{base_url}/v1/models")
        if response.status_code != 200:
            return []
        return [entry["id"] for entry in response.json().get("data", []) if "id" in entry]
    except (httpx.HTTPError, ValueError, KeyError):
        return []
