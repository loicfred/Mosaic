import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(datasets_dir, tmp_path):
    with TestClient(create_app(datasets_dir=datasets_dir, models_dir=tmp_path / "models")) as c:
        yield c


def test_buying_times_cover_every_slot_even_empty_ones(client):
    week = client.get("/api/breakdowns/buying-times?by=weekday").json()["slots"]
    hours = client.get("/api/breakdowns/buying-times?by=hour").json()["slots"]
    assert [s["slot"] for s in week][:2] == ["Monday", "Tuesday"] and len(week) == 7 and len(hours) == 24
    # every fixture order is bought at 10:00, and an empty hour is 0 orders, not missing
    assert next(s for s in hours if s["slot"] == "10:00")["share_of_orders"] == pytest.approx(1.0)
    assert hours[0]["orders"] == 0
    assert client.get("/api/breakdowns/buying-times?by=minute").status_code == 422


def test_customer_states_leave_small_rates_empty(client):
    states = {s["state"]: s for s in client.get("/api/breakdowns/customer-states?min_orders=5").json()["states"]}
    # RJ's order b is late in even months: 6 of 12 delivered
    assert states["RJ"]["late_rate"] == pytest.approx(0.5)
    tiny = {s["state"]: s for s in client.get("/api/breakdowns/customer-states?min_orders=100").json()["states"]}
    assert tiny["RJ"]["late_rate"] is None and tiny["RJ"]["orders"] == 12


def test_review_scores_count_every_star(client):
    scores = client.get("/api/breakdowns/review-scores").json()["scores"]
    assert [s["score"] for s in scores] == [1, 2, 3, 4, 5]
    assert scores[2]["orders"] == 0 and sum(s["share"] for s in scores) == pytest.approx(1.0)
