from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

DEMO_CSV = Path(__file__).resolve().parents[2] / "data" / "demo" / "coastal_petty_cash_sep2026.csv"


def upload(client: TestClient, headers: dict, name: str, data: bytes):
    return client.post("/api/v1/data-quality/imports", files={"file": (name, data, "text/csv")}, headers=headers)


def test_malformed_files_are_rejected(client: TestClient, accountant: dict) -> None:
    assert upload(client, accountant, "x.csv", b"\x00\x01\x02binary").status_code == 400
    assert upload(client, accountant, "x.csv", b"foo,bar\n1,2\n").status_code == 400
    assert upload(client, accountant, "x.exe", b"date,description,amount\n").status_code == 415
    big = b"date,description,amount\n" + b"2026-01-01,x,1\n" * 400_000
    assert upload(client, accountant, "big.csv", big).status_code == 413


def test_demo_import_flow_requires_approval(client: TestClient, accountant: dict) -> None:
    before = client.get("/api/v1/transactions?page_size=1", headers=accountant).json()["total"]
    r = upload(client, accountant, "coastal_petty_cash_sep2026.csv", DEMO_CSV.read_bytes())
    assert r.status_code == 200, r.text
    batch = r.json()
    assert batch["row_count"] == 22 and batch["error_count"] == 4 and batch["duplicate_count"] == 2
    assert 0 < batch["health"]["score"] < 100
    detail = client.get(f"/api/v1/data-quality/imports/{batch['id']}", headers=accountant).json()
    # Formula characters were stripped from the stored description.
    assert not any(r["parsed"].get("description", "").startswith("=") for r in detail["rows"])
    # Nothing was written yet.
    assert client.get("/api/v1/transactions?page_size=1", headers=accountant).json()["total"] == before
    # Commit is blocked until every duplicate has a decision.
    assert client.post(f"/api/v1/data-quality/imports/{batch['id']}/commit", headers=accountant).status_code == 409
    dups = [p for p in detail["proposals"] if p["change_type"] == "exclude_duplicate"]
    for p in dups:
        d = client.post(f"/api/v1/data-quality/proposals/{p['id']}/decision", json={"decision": "approve"},
                        headers=accountant)
        assert d.status_code == 200
    cats = [p for p in detail["proposals"] if p["change_type"] == "set_category"]
    client.post(f"/api/v1/data-quality/proposals/{cats[0]['id']}/decision",
                json={"decision": "approve", "new_value": "Other expenses"}, headers=accountant)
    c = client.post(f"/api/v1/data-quality/imports/{batch['id']}/commit", headers=accountant)
    assert c.status_code == 200
    after = client.get("/api/v1/transactions?page_size=1", headers=accountant).json()["total"]
    assert after == before + 22 - 4 - 2  # errors and approved duplicates excluded
    events = client.get("/api/v1/audit/events?category=data", headers=accountant).json()
    kinds = {e["event"] for e in events}
    assert {"data.import_staged", "data.change_approved", "data.import_committed"} <= kinds
    approved = next(e for e in events if e["event"] == "data.change_approved" and e["details"]["field"] == "category")
    assert approved["details"]["after"] == "Other expenses"


def test_ledger_health_reports_checks(client: TestClient, owner: dict) -> None:
    h = client.get("/api/v1/data-quality/health", headers=owner).json()
    assert 0 <= h["score"] <= 100
    assert {c["key"] for c in h["checks"]} >= {"valid", "coverage", "duplicates", "payees", "suspicious"}


def test_sql_injection_attempts_are_inert(client: TestClient, owner: dict) -> None:
    for q in ["' OR 1=1 --", "'; DROP TABLE transactions; --", "%' UNION SELECT * FROM users --"]:
        r = client.get("/api/v1/transactions", params={"q": q}, headers=owner)
        assert r.status_code == 200 and r.json()["total"] == 0
    assert client.get("/api/v1/transactions?page_size=1", headers=owner).json()["total"] > 1000
    r = client.get("/api/v1/transactions", params={"sort": "amount_desc; DROP TABLE users"}, headers=owner)
    assert r.status_code == 422
