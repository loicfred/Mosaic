import pytest
from fastapi.testclient import TestClient

from app.main import create_app

MEASURES = ("delivery", "reviews", "sellers")


@pytest.fixture
def client(datasets_dir, tmp_path):
    # no trained model is needed: every trend route is observed data only
    with TestClient(create_app(datasets_dir=datasets_dir, models_dir=tmp_path / "models")) as client:
        yield client


@pytest.mark.parametrize("measure", MEASURES)
def test_trend_routes_answer_from_observed_data(client, measure):
    trend = client.get(f"/api/{measure}/trend").json()
    assert trend["measure"] == measure
    assert {"label", "unit", "good_direction", "trend", "monthly", "rules", "limitations"} <= set(trend)
    assert len(trend["monthly"]) == 12 and trend["trend"]["recent_months"] == ["2017-10", "2017-11", "2017-12"]
    # nothing improves in the fixture: late "b" orders fall in two of the last three months
    found = client.get(f"/api/{measure}/opportunities").json()
    assert found["candidates"] == [] and found["reason"] == "not_improving"
    assert {"group_label", "trend", "business_rates", "rules", "limitations"} <= set(found)
    caveats = client.get(f"/api/{measure}/caveats").json()
    assert caveats["checks"] and caveats["triggered"] == sum(check["triggered"] for check in caveats["checks"])
    assert {check["kind"] for check in caveats["checks"]} <= {"change", "groups", "gap"}


def test_openapi_lists_every_trend_route_with_a_summary(client):
    paths = client.get("/openapi.json").json()["paths"]
    for measure in MEASURES:
        for kind in ("trend", "opportunities", "caveats"):
            assert paths[f"/api/{measure}/{kind}"]["get"]["summary"]
