import pytest
from fastapi.testclient import TestClient

from app.forecast.train import train
from app.main import create_app
from tests.conftest import FIXTURE_MONTHLY_SALES


@pytest.fixture
def models_dir(tmp_path):
    return tmp_path / "models"


def client_for(datasets_dir, models_dir):
    return TestClient(create_app(datasets_dir=datasets_dir, models_dir=models_dir))


def test_health_reports_model_not_loaded_before_training(datasets_dir, models_dir):
    with client_for(datasets_dir, models_dir) as client:
        body = client.get("/api/health").json()
    assert body["status"] == "ok" and body["model_loaded"] is False
    assert body["models"] == {"sales_forecast": False, "late_delivery": False, "low_review": False}


def test_history_returns_monthly_series_and_exclusions(datasets_dir, models_dir):
    with client_for(datasets_dir, models_dir) as client:
        body = client.get("/api/sales/history").json()
    assert body["unit"] == "BRL"
    assert body["measure"] == "gross_item_sales"
    assert body["range"] == {"start": "2017-01", "end": "2017-12"}
    assert len(body["months"]) == 12
    assert sum(m["sales"] for m in body["months"]) == FIXTURE_MONTHLY_SALES * 12
    assert body["months"][0] == {"month": "2017-01", "orders": 2, "sales": 350.0, "freight": 30.0}
    assert body["exclusions"]["statuses"] == {"canceled": 1, "unavailable": 1}
    assert body["exclusions"]["months_outside_range"] == {"2016-10": 1, "2018-09": 1}


def test_forecast_without_artifact_is_503(datasets_dir, models_dir):
    with client_for(datasets_dir, models_dir) as client:
        response = client.get("/api/sales/forecast")
    assert response.status_code == 503
    assert "train" in response.json()["detail"].lower()


def test_forecast_after_training(datasets_dir, models_dir):
    train(datasets_dir, models_dir)
    with client_for(datasets_dir, models_dir) as client:
        assert client.get("/api/health").json()["model_loaded"] is True
        body = client.get("/api/sales/forecast").json()
    assert body["horizon"] == 3
    assert body["model_version"] == "sales-ridge-v1"
    assert [f["month"] for f in body["forecast"]] == ["2018-01", "2018-02", "2018-03"]
    for point in body["forecast"]:
        assert point["lower"] <= point["sales"] <= point["upper"]
    assert body["baselines"]["naive_last"] == [
        {"month": "2018-01", "sales": 350.0},
        {"month": "2018-02", "sales": 350.0},
        {"month": "2018-03", "sales": 350.0},
    ]
    assert body["baselines"]["mean_last_3"][0]["sales"] == 350.0
    assert set(body["evaluation"]) == {"model", "naive_last", "mean_last_3"}
    assert len(body["evaluation"]["model"]["points"]) == 6
    assert body["evaluation"]["model"]["points"][0]["month"] == "2017-07"
    assert body["limitations"]


def test_forecast_horizon_is_validated(datasets_dir, models_dir):
    train(datasets_dir, models_dir)
    with client_for(datasets_dir, models_dir) as client:
        assert client.get("/api/sales/forecast?horizon=7").status_code == 422
        assert client.get("/api/sales/forecast?horizon=0").status_code == 422
        assert len(client.get("/api/sales/forecast?horizon=6").json()["forecast"]) == 6


def test_forecast_with_stale_artifact_is_409(datasets_dir, models_dir):
    train(datasets_dir, models_dir)
    with open(datasets_dir / "olist_orders_dataset.csv", "a", encoding="utf-8") as f:
        f.write("late,c,delivered,2017-12-20 00:00:00,,,,\n")
    with client_for(datasets_dir, models_dir) as client:
        response = client.get("/api/sales/forecast")
    assert response.status_code == 409
    assert "retrain" in response.json()["detail"].lower()
