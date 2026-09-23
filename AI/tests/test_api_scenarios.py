import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(datasets_dir, tmp_path):
    with TestClient(create_app(datasets_dir=datasets_dir, models_dir=tmp_path / "models")) as client:
        yield client


def post(client, **body):
    return client.post("/api/scenarios/sales-impact", json=body)


def test_scenario_works_without_any_trained_model(client):
    body = post(client, horizon=3, sales_change_pct=20.0).json()
    assert body["scenario"] == {"horizon": 3, "sales_change_pct": 20.0, "recent_months": 3}
    consequences = body["consequences"]
    assert consequences["projected_monthly_orders"] == pytest.approx(
        body["baseline"]["monthly_orders"] * 1.2
    )
    assert consequences["late"]["rate_held"]["expected_late_per_month"] >= 0
    assert "sellers_at_capacity" in consequences
    assert body["assumptions"] and body["limitations"]
    assert body["evidence"]["aov"] > 0


def test_scenario_returns_figures_only(client):
    # The Spring app writes the summary; prose here would be a second, unchecked source of numbers.
    body = post(client).json()
    assert "narrative" not in body


def test_old_explain_flag_is_ignored(client):
    assert post(client, explain=True).status_code == 200


def test_request_validation(client):
    assert post(client, horizon=0).status_code == 422
    assert post(client, horizon=7).status_code == 422
    assert post(client, sales_change_pct=-80).status_code == 422
    assert post(client, sales_change_pct=200).status_code == 422
    assert post(client, horizon=6, sales_change_pct=-50).status_code == 200


def test_negative_scenario_is_supported(client):
    body = post(client, sales_change_pct=-20.0).json()
    assert body["consequences"]["extra_orders_per_month"] < 0


def test_ai_health_is_gone(client):
    assert client.get("/api/ai/health").status_code == 404
