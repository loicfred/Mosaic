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
    assert {k: body["scenario"][k] for k in ("horizon", "sales_change_pct", "recent_months", "category")} == {
        "horizon": 3, "sales_change_pct": 20.0, "recent_months": 3, "category": None}
    consequences = body["consequences"]
    assert consequences["projected_monthly_orders"] == pytest.approx(
        body["baseline"]["monthly_orders"] * 1.2
    )
    assert consequences["late"]["rate_held"]["expected_late_per_month"] >= 0
    assert "sellers_at_capacity" in consequences
    assert body["assumptions"] and body["limitations"]
    assert body["evidence"]["aov"] > 0
