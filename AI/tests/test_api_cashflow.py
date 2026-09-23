import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.models.train_cashflow import train
from tests.conftest import CASHFLOW_SPLIT_MONTH, write_fixture_csvs


@pytest.fixture
def models_dir(tmp_path):
    return tmp_path / "models"


def client_for(datasets_dir, models_dir):
    return TestClient(create_app(datasets_dir=datasets_dir, models_dir=models_dir))


def test_cashflow_summary_is_observed_data_even_without_model(datasets_dir, models_dir):
    with client_for(datasets_dir, models_dir) as client:
        body = client.get("/api/risk/cashflow/summary").json()
    assert body["available"] is True
    assert body["model"] is None
    assert body["unit"] == "usd"
    by_sector = {row["sector"]: row for row in body["by_sector"]}
    assert by_sector["Retail"]["records"] == 24
    assert by_sector["Retail"]["stressed"] == 12
    assert by_sector["Retail"]["stress_rate"] == pytest.approx(0.5)
    june = next(m for m in body["monthly"] if m["month"] == "2024-06")
    assert june == {"month": "2024-06", "records": 4, "stressed": 2, "stress_rate": 0.5}


def test_cashflow_records_needs_model(datasets_dir, models_dir):
    with client_for(datasets_dir, models_dir) as client:
        response = client.get("/api/risk/cashflow/records")
    assert response.status_code == 503
    assert "train_cashflow" in response.json()["detail"]


def test_cashflow_records_scored_after_training_and_stale_artifact_rejected(datasets_dir, models_dir):
    train(datasets_dir, models_dir, split_month=CASHFLOW_SPLIT_MONTH)
    with client_for(datasets_dir, models_dir) as client:
        health = client.get("/api/health").json()
        body = client.get("/api/risk/cashflow/records?limit=5").json()
        assert client.get("/api/risk/cashflow/records?limit=0").status_code == 422
    assert health["models"]["cashflow_stress"] is True
    assert body["prediction_time"] == "at_snapshot"
    assert len(body["records"]) == 5
    assert all(0.0 <= r["risk"] <= 1.0 for r in body["records"])

    with open(datasets_dir / "small_business_cashflow.csv", "a", encoding="utf-8") as f:
        f.write(
            "F-new,Retail,10,2024-07,10000,9000,10,10,1000,0,0\n"
        )
    with client_for(datasets_dir, models_dir) as client:
        assert client.get("/api/risk/cashflow/records").status_code == 409


def test_api_starts_without_the_cashflow_file(tmp_path, models_dir):
    """Startup auto-training must skip the cash-flow model, not crash, when its CSV is absent."""
    datasets_dir = tmp_path / "datasets"
    datasets_dir.mkdir()
    write_fixture_csvs(datasets_dir, include_cashflow=False)
    with TestClient(create_app(datasets_dir=datasets_dir, models_dir=models_dir, auto_train=True)) as client:
        health = client.get("/api/health").json()
        summary = client.get("/api/risk/cashflow/summary").json()
        records_response = client.get("/api/risk/cashflow/records")
    assert health["status"] == "ok"
    assert health["models"]["cashflow_stress"] is False
    assert summary == {
        "unit": "usd", "available": False, "reason": "dataset_not_present", "by_sector": [], "monthly": [], "model": None,
    }
    assert records_response.status_code == 503
