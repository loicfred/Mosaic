from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

DEMO_CSV = Path(__file__).resolve().parents[2] / "data" / "demo" / "coastal_petty_cash_sep2026.csv"


def test_viewer_can_read_but_not_change(client: TestClient, viewer: dict) -> None:
    assert client.get("/api/v1/analytics/overview", headers=viewer).status_code == 200
    opp = client.get("/api/v1/opportunities", headers=viewer).json()[0]
    r = client.patch(f"/api/v1/opportunities/{opp['id']}/status", json={"status": "reviewed"}, headers=viewer)
    assert r.status_code == 403
    with DEMO_CSV.open("rb") as f:
        r = client.post("/api/v1/data-quality/imports", files={"file": ("x.csv", f, "text/csv")}, headers=viewer)
    assert r.status_code == 403
    assert client.get("/api/v1/audit/events", headers=viewer).status_code == 403
    assert client.post("/api/v1/scenarios", json={"name": "x", "assumptions": {}}, headers=viewer).status_code == 403


def test_viewer_can_simulate_without_saving(client: TestClient, viewer: dict) -> None:
    r = client.post("/api/v1/scenarios/simulate", json={"assumptions": {"supplier_cost_pct": -10}}, headers=viewer)
    assert r.status_code == 200


def test_members_list_is_owner_only(client: TestClient, owner: dict, accountant: dict) -> None:
    assert client.get("/api/v1/business/members", headers=owner).status_code == 200
    assert client.get("/api/v1/business/members", headers=accountant).status_code == 403


def test_authorization_failures_are_audited(client: TestClient, viewer: dict, owner: dict) -> None:
    client.get("/api/v1/audit/events", headers=viewer)
    events = client.get("/api/v1/audit/events?category=access&outcome=denied", headers=owner).json()
    assert any(e["event"] == "authz.role_denied" for e in events)
