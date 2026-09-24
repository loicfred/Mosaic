from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.llm import groq


def test_ask_without_key_is_unavailable(client: TestClient, owner: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "groq_api_key", "")
    r = client.post("/api/v1/insight/ask", json={"question": "How much cash do we have?"}, headers=owner)
    assert r.status_code == 503 and r.json()["error"]["code"] == "llm_unavailable"


def test_ask_answers_from_computed_figures(client: TestClient, owner: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "groq_api_key", "test-key")
    seen: dict[str, Any] = {}

    def fake(messages: list[dict[str, str]], max_tokens: int = 900) -> dict[str, Any]:
        seen["messages"] = messages
        return {"status": "answer", "headline": "Cash is MUR 1.2M.", "facts": [{"label": "Cash", "value": "MUR 1.2M"}],
                "kind": "actual", "visual": "cash_90d", "sources": ["cash", "made-up"], "follow_ups": ["Why?"]}

    monkeypatch.setattr(groq, "chat_json", fake)
    r = client.post("/api/v1/insight/ask", headers=owner,
                    json={"question": "How much cash do we have?", "history": [{"question": "Hi", "answer": "Hello"}]})
    assert r.status_code == 200
    a = r.json()
    assert a["via"] == "llm" and a["headline"] == "Cash is MUR 1.2M."
    assert [s["label"] for s in a["sources"]] == ["Cash balance"]  # unknown source keys are dropped
    assert a["visual"]["type"] == "spark" and len(a["visual"]["values"]) == 90
    data = next(m["content"] for m in seen["messages"] if m["content"].startswith("DATA = "))
    assert '"cash_actual"' in data and "transaction_ids" not in data
    assert seen["messages"][-1] == {"role": "user", "content": "How much cash do we have?"}


def test_ask_falls_back_cleanly_when_the_model_fails(client: TestClient, owner: dict,
                                                      monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "groq_api_key", "test-key")

    def boom(*_: Any, **__: Any) -> dict[str, Any]:
        raise groq.LLMError("status 429")

    monkeypatch.setattr(groq, "chat_json", boom)
    r = client.post("/api/v1/insight/ask", json={"question": "How much cash do we have?"}, headers=owner)
    assert r.status_code == 503 and r.json()["error"]["code"] == "llm_unavailable"
