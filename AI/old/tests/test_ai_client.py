import httpx

from app.ai import client as ai_client

BASE_URL = "http://localhost:1234"


def transport_returning(status: int, payload: dict, captured: dict | None = None):
    def handler(request: httpx.Request) -> httpx.Response:
        if captured is not None:
            captured["url"] = str(request.url)
            captured["body"] = request.read().decode()
        return httpx.Response(status, json=payload)

    return httpx.MockTransport(handler)


def test_successful_completion_returns_text_and_model():
    captured = {}
    transport = transport_returning(
        200,
        {"model": "gemma-3-4b", "choices": [{"message": {"content": " Sales rise. "}}]},
        captured,
    )
    result = ai_client.complete("explain this", base_url=BASE_URL, model="", timeout=5, transport=transport)
    assert result.text == "Sales rise."
    assert result.model == "gemma-3-4b"
    assert result.error is None
    assert captured["url"] == f"{BASE_URL}/v1/chat/completions"


def test_request_uses_a_single_user_message_and_omits_empty_model():
    captured = {}
    transport = transport_returning(200, {"choices": [{"message": {"content": "ok"}}]}, captured)
    ai_client.complete("the prompt", base_url=BASE_URL, model="", timeout=5, transport=transport)
    body = captured["body"]
    assert '"role": "user"' in body or '"role":"user"' in body
    assert "system" not in body
    assert '"model"' not in body


def test_model_is_sent_when_configured():
    captured = {}
    transport = transport_returning(200, {"choices": [{"message": {"content": "ok"}}]}, captured)
    ai_client.complete("p", base_url=BASE_URL, model="gemma-3-4b", timeout=5, transport=transport)
    assert "gemma-3-4b" in captured["body"]


def test_non_200_returns_error_without_raising():
    transport = transport_returning(500, {"error": "model not loaded"})
    result = ai_client.complete("p", base_url=BASE_URL, model="", timeout=5, transport=transport)
    assert result.text is None
    assert "500" in result.error


def test_connection_failure_returns_error_without_raising():
    def handler(request):
        raise httpx.ConnectError("connection refused")

    result = ai_client.complete(
        "p", base_url=BASE_URL, model="", timeout=5, transport=httpx.MockTransport(handler)
    )
    assert result.text is None
    assert "connect" in result.error.lower()


def test_empty_choices_is_reported_as_an_error():
    transport = transport_returning(200, {"choices": []})
    result = ai_client.complete("p", base_url=BASE_URL, model="", timeout=5, transport=transport)
    assert result.text is None
    assert result.error


def test_list_models_returns_ids_and_empty_list_when_unreachable():
    transport = transport_returning(200, {"data": [{"id": "gemma-3-4b"}, {"id": "nomic-embed"}]})
    assert ai_client.list_models(BASE_URL, timeout=5, transport=transport) == ["gemma-3-4b", "nomic-embed"]

    def handler(request):
        raise httpx.ConnectError("refused")

    assert ai_client.list_models(BASE_URL, timeout=5, transport=httpx.MockTransport(handler)) == []
