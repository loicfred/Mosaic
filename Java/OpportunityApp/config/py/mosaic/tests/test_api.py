import json

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


def test_api_rejects_untrusted_host(datasets_dir, models_dir):
    with client_for(datasets_dir, models_dir) as client:
        assert client.get("/api/health", headers={"Host": "127.0.0.1:8000"}).status_code == 200
        response = client.get("/api/health", headers={"Host": "attacker.example"})
    assert response.status_code == 400
    assert "models" not in response.text


def test_health_reports_model_not_loaded_before_training(datasets_dir, models_dir):
    with client_for(datasets_dir, models_dir) as client:
        body = client.get("/api/health").json()
    assert body["status"] == "ok" and body["model_loaded"] is False
    assert body["models"] == {
        "sales_forecast": False, "late_delivery": False, "low_review": False, "cashflow_stress": False,
    }


def test_datasets_list_every_file_read_with_its_columns(datasets_dir, models_dir):
    with client_for(datasets_dir, models_dir) as client:
        files = {f["file"]: f["columns"] for f in client.get("/api/datasets").json()["files"]}
    assert "order_purchase_timestamp" in files["olist_orders_dataset.csv"]
    assert "price" in files["olist_order_items_dataset.csv"]


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


def test_forecast_with_stale_artifact_is_409(datasets_dir, models_dir):
    train(datasets_dir, models_dir)
    with open(datasets_dir / "olist_orders_dataset.csv", "a", encoding="utf-8") as f:
        f.write("late,c,delivered,2017-12-20 00:00:00,,,,\n")
    with client_for(datasets_dir, models_dir) as client:
        response = client.get("/api/sales/forecast")
    assert response.status_code == 409
    assert "retrain" in response.json()["detail"].lower()


def test_forecast_uses_better_baseline_when_model_loses_backtest(datasets_dir, models_dir):
    train(datasets_dir, models_dir)
    path = models_dir / "sales_forecast.json"
    metadata = json.loads(path.read_text(encoding="utf-8"))
    metadata["evaluation"]["model"]["mae"] = 1000.0
    metadata["evaluation"]["naive_last"]["mae"] = 10.0
    metadata["evaluation"]["mean_last_3"]["mae"] = 50.0
    path.write_text(json.dumps(metadata), encoding="utf-8")

    with client_for(datasets_dir, models_dir) as client:
        body = client.get("/api/sales/forecast").json()
        advice = client.get("/api/sales/opportunities").json()

    assert body["forecast_method"] == "naive_last"
    assert [point["sales"] for point in body["forecast"]] == [350.0] * 3
    assert advice["forecast_method"] == "naive_last"
    assert advice["trend"]["forecast_monthly_mean"] == 350.0
