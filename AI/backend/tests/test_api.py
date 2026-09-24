from __future__ import annotations

from fastapi.testclient import TestClient


def test_security_headers(client: TestClient, owner: dict) -> None:
    r = client.get("/api/v1/analytics/overview", headers=owner)
    for h in ("content-security-policy", "x-content-type-options", "x-frame-options", "referrer-policy",
              "x-request-id"):
        assert h in r.headers
    assert r.headers["cache-control"] == "no-store"


def test_errors_are_structured_and_do_not_echo_input(client: TestClient, owner: dict) -> None:
    r = client.get("/api/v1/transactions/00000000-0000-0000-0000-000000000000", headers=owner)
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"
    r = client.post("/api/v1/auth/login", json={"email": "not-an-email", "password": "secret-value-123"})
    assert r.status_code == 422
    assert "secret-value-123" not in r.text and "Traceback" not in r.text


def test_unknown_fields_are_rejected(client: TestClient, owner: dict) -> None:
    r = client.post("/api/v1/scenarios/simulate", json={"assumptions": {}, "is_admin": True}, headers=owner)
    assert r.status_code == 422


def test_health_endpoint(client: TestClient) -> None:
    r = client.get("/api/v1/health").json()
    assert r["status"] == "ok" and r["models"]["cash_pressure"] == "loaded"


def test_overview_and_insights_shapes(client: TestClient, owner: dict) -> None:
    o = client.get("/api/v1/analytics/overview", headers=owner).json()
    assert o["as_of"] == "2026-09-22" and o["cash"]["balance"] > 0 and o["prediction"]["band"] == "HIGH"
    i = client.get("/api/v1/insights", headers=owner).json()
    assert i["collections"]["has_invoices"] and i["customer_concentration"]["top"]
