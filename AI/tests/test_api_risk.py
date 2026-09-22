import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.models.train_risk import train_all
from tests.conftest import FIXTURE_MONTHS, LATE_B_MONTHS

FIXTURE_SPLIT = "2017-10-01"


@pytest.fixture
def models_dir(tmp_path):
    return tmp_path / "models"


def client_for(datasets_dir, models_dir):
    return TestClient(create_app(datasets_dir=datasets_dir, models_dir=models_dir))


def test_delivery_summary_is_observed_data_even_without_model(datasets_dir, models_dir):
    with client_for(datasets_dir, models_dir) as client:
        body = client.get("/api/risk/delivery/summary").json()
    assert body["model"] is None
    assert [m["month"] for m in body["monthly"]] == FIXTURE_MONTHS
    february = next(m for m in body["monthly"] if m["month"] == "2017-02")
    assert february == {"month": "2017-02", "delivered": 2, "late": 1, "late_rate": 0.5}
    march = next(m for m in body["monthly"] if m["month"] == "2017-03")
    assert march["delivered"] == 3 and march["late"] == 0  # includes the order without items
    assert body["exclusions"]["orders_without_items"] == 1


def test_open_orders_needs_model(datasets_dir, models_dir):
    with client_for(datasets_dir, models_dir) as client:
        response = client.get("/api/risk/delivery/open-orders")
    assert response.status_code == 503
    assert "train_risk" in response.json()["detail"]


def test_open_orders_are_scored_after_training(datasets_dir, models_dir):
    train_all(datasets_dir, models_dir, split_date=FIXTURE_SPLIT)
    with client_for(datasets_dir, models_dir) as client:
        health = client.get("/api/health").json()
        body = client.get("/api/risk/delivery/open-orders?limit=10").json()
        assert client.get("/api/risk/delivery/open-orders?limit=0").status_code == 422
    assert health["models"] == {"sales_forecast": False, "late_delivery": True, "low_review": True}
    assert body["prediction_time"] == "at_purchase"
    assert len(body["orders"]) == 1
    order = body["orders"][0]
    assert order["order_id"] == "open-1" and order["order_status"] == "shipped"
    assert 0.0 <= order["risk"] <= 1.0
    assert order["days_since_purchase"] == 0
    assert order["purchase_ts"] == "2018-09-15T10:00:00"


def test_sellers_table_observed_rates(datasets_dir, models_dir):
    with client_for(datasets_dir, models_dir) as client:
        body = client.get("/api/risk/delivery/sellers?min_orders=1").json()
        assert client.get("/api/risk/delivery/sellers?min_orders=0").status_code == 422
        default = client.get("/api/risk/delivery/sellers").json()
    sellers = {s["seller_id"]: s for s in body["sellers"]}
    assert list(sellers) == ["s2", "s1"]  # worst first
    s2 = sellers["s2"]
    assert s2["orders"] == 12 and s2["late"] == len(LATE_B_MONTHS) and s2["late_rate"] == 0.5
    assert s2["handover_late"] == 6 and s2["handover_late_rate"] == 0.5
    # Recent window = Oct-Dec: Oct and Dec are late -> 2/3; earlier = 4/9.
    assert s2["recent_late_rate"] == pytest.approx(2 / 3)
    assert s2["earlier_late_rate"] == pytest.approx(4 / 9)
    assert sellers["s1"]["late_rate"] == 0.0
    assert default["sellers"] == []  # nobody has 30 orders in the fixture


def test_reviews_summary(datasets_dir, models_dir):
    with client_for(datasets_dir, models_dir) as client:
        body = client.get("/api/risk/reviews/summary").json()
    assert body["model"] is None
    assert body["by_lateness"]["late"] == {"reviewed": 6, "low": 6, "low_rate": 1.0}
    assert body["by_lateness"]["on_time"] == {"reviewed": 17, "low": 0, "low_rate": 0.0}
    may = next(m for m in body["monthly"] if m["month"] == "2017-05")
    assert may == {"month": "2017-05", "reviewed": 1, "low": 0, "low_rate": 0.0}


def test_unreviewed_orders_scored_and_stale_artifact_rejected(datasets_dir, models_dir):
    train_all(datasets_dir, models_dir, split_date=FIXTURE_SPLIT)
    with client_for(datasets_dir, models_dir) as client:
        body = client.get("/api/risk/reviews/unreviewed").json()
        summary = client.get("/api/risk/reviews/summary").json()
    assert body["prediction_time"] == "after_delivery"
    assert sorted(o["order_id"] for o in body["orders"]) == ["2017-05-b", "no-items-1", "out-of-range-1"]
    assert all(0.0 <= o["risk"] <= 1.0 for o in body["orders"])
    assert summary["model"]["evaluation"]["n_test"] > 0
    assert "days_late" in {i["feature"] for i in summary["model"]["importances"]} or summary["model"]["importances"] == []

    with open(datasets_dir / "olist_order_reviews_dataset.csv", "a", encoding="utf-8") as f:
        f.write("r-new,2017-05-b,3,,,2017-06-01 00:00:00,2017-06-01 00:00:00\n")
    with client_for(datasets_dir, models_dir) as client:
        assert client.get("/api/risk/reviews/unreviewed").status_code == 409
        assert client.get("/api/risk/delivery/open-orders").status_code == 409
