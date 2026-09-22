import pytest
from fastapi.testclient import TestClient

from app.ai.client import ChatResult
from app.main import create_app


@pytest.fixture(autouse=True)
def never_contact_a_real_llm(monkeypatch):
    """Any test that reaches the real endpoint fails loudly instead of using the network."""
    def fail(*args, **kwargs):
        raise AssertionError("tests must not contact LM Studio; stub the client")

    monkeypatch.setattr("app.ai.explain.default_complete", fail)
    monkeypatch.setattr("app.api.scenarios.ai_client.list_models", lambda *a, **k: [])


@pytest.fixture
def client(datasets_dir, tmp_path):
    with TestClient(create_app(datasets_dir=datasets_dir, models_dir=tmp_path / "models")) as client:
        yield client


def post(client, **body):
    return client.post("/api/scenarios/sales-impact", json=body)


def test_scenario_works_without_any_trained_model(client):
    body = post(client, horizon=3, sales_change_pct=20.0, explain=False).json()
    assert body["scenario"] == {"horizon": 3, "sales_change_pct": 20.0, "recent_months": 3}
    consequences = body["consequences"]
    assert consequences["projected_monthly_orders"] == pytest.approx(
        body["baseline"]["monthly_orders"] * 1.2
    )
    assert consequences["late"]["rate_held"]["expected_late_per_month"] >= 0
    assert "sellers_at_capacity" in consequences
    assert body["assumptions"] and body["limitations"]
    assert body["evidence"]["aov"] > 0


def test_explain_false_uses_template_and_never_calls_the_model(client):
    body = post(client, explain=False).json()
    assert body["narrative"]["source"] == "template"
    assert body["narrative"]["reason"] == "llm_disabled"
    assert body["narrative"]["text"]


def test_explain_true_falls_back_to_template_when_model_unreachable(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.scenarios.explain",
        lambda evidence, settings: {
            "text": "fallback", "source": "template",
            "model": None, "reason": "llm_unreachable: ConnectError",
        },
    )
    body = post(client, explain=True).json()
    assert body["narrative"]["source"] == "template"
    assert body["narrative"]["reason"].startswith("llm_unreachable")


def test_llm_narrative_is_returned_when_the_model_answers_faithfully(client, monkeypatch):
    def fake_complete(prompt, **kwargs):
        assert "only the numbers" in prompt.lower()
        return ChatResult("Orders could rise. Watch late deliveries.", model="gemma-3-4b")

    monkeypatch.setattr("app.ai.explain.default_complete", fake_complete)
    body = post(client, explain=True).json()
    assert body["narrative"]["source"] == "llm"
    assert body["narrative"]["model"] == "gemma-3-4b"


def test_request_validation(client, monkeypatch):
    monkeypatch.setattr(
        "app.ai.explain.default_complete",
        lambda prompt, **kwargs: ChatResult(None, error="stubbed"),
    )
    assert post(client, horizon=0).status_code == 422
    assert post(client, horizon=7).status_code == 422
    assert post(client, sales_change_pct=-80).status_code == 422
    assert post(client, sales_change_pct=200).status_code == 422
    assert post(client, horizon=6, sales_change_pct=-50).status_code == 200


def test_negative_scenario_is_supported(client):
    body = post(client, sales_change_pct=-20.0, explain=False).json()
    assert body["consequences"]["extra_orders_per_month"] < 0


def test_ai_health_reports_unreachable_without_raising(client):
    body = client.get("/api/ai/health").json()
    assert body["reachable"] is False
    assert body["models"] == []
    assert body["base_url"].startswith("http")


def test_ai_health_lists_models_when_reachable(client, monkeypatch):
    monkeypatch.setattr("app.api.scenarios.ai_client.list_models", lambda *a, **k: ["gemma-3-4b"])
    body = client.get("/api/ai/health").json()
    assert body["reachable"] is True and body["models"] == ["gemma-3-4b"]
