import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import FIXTURE_MONTHS


@pytest.fixture
def client(datasets_dir, tmp_path):
    with TestClient(create_app(datasets_dir=datasets_dir, models_dir=tmp_path / "models")) as client:
        yield client


def test_category_list_sorted_without_series(client):
    body = client.get("/api/sales/categories").json()
    assert body["recent_months"] == 3 and body["count"] == 2
    assert body["total_change_pct"] == 0.0
    assert [c["category"] for c in body["categories"]] == ["category_b", "category_a"]
    top = body["categories"][0]
    assert "series" not in top
    assert top["recent"] == 750.0 and top["previous"] == 750.0 and top["change_pct"] == 0.0
    assert top["share_recent"] == pytest.approx(250 / 350)
    assert top["flags"] == {"underperforming_total": False, "latest_month_anomaly": False}
    assert top["forecast"] is not None and len(top["forecast"]) == 3


def test_category_list_limit_and_flag_filter(client):
    assert len(client.get("/api/sales/categories?limit=1").json()["categories"]) == 1
    flagged = client.get("/api/sales/categories?flag=underperforming_total").json()
    assert flagged["count"] == 0 and flagged["categories"] == []
    assert client.get("/api/sales/categories?flag=nonsense").status_code == 422
    assert client.get("/api/sales/categories?limit=0").status_code == 422


def test_category_detail_includes_series_and_404(client):
    body = client.get("/api/sales/categories/category_a").json()
    assert [p["month"] for p in body["series"]] == FIXTURE_MONTHS
    assert all(p["sales"] == 100.0 for p in body["series"])
    assert "evidence" in body and "underperforming_total" in body["evidence"]
    assert client.get("/api/sales/categories/does_not_exist").status_code == 404
