from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.db.session import SessionLocal, set_tenant
from app.models import Business, Transaction


def _ids(client: TestClient, headers: dict) -> tuple[str, str]:
    tx = client.get("/api/v1/transactions?page_size=1", headers=headers).json()["items"][0]["id"]
    opp = client.get("/api/v1/opportunities", headers=headers).json()[0]["id"]
    return tx, opp


def test_other_tenant_cannot_read_records_by_id(client: TestClient, owner: dict, other_tenant: dict) -> None:
    tx, opp = _ids(client, owner)
    assert client.get(f"/api/v1/transactions/{tx}", headers=other_tenant).status_code == 404
    assert client.get(f"/api/v1/opportunities/{opp}", headers=other_tenant).status_code == 404
    r = client.patch(f"/api/v1/opportunities/{opp}/status", json={"status": "reviewed"}, headers=other_tenant)
    assert r.status_code == 404


def test_lookup_only_returns_own_records(client: TestClient, owner: dict, other_tenant: dict) -> None:
    tx, _ = _ids(client, owner)
    assert client.post("/api/v1/transactions/lookup", json=[tx], headers=other_tenant).json() == []
    assert len(client.post("/api/v1/transactions/lookup", json=[tx], headers=owner).json()) == 1


def test_lists_are_scoped(client: TestClient, owner: dict, other_tenant: dict) -> None:
    a = client.get("/api/v1/business", headers=owner).json()
    b = client.get("/api/v1/business", headers=other_tenant).json()
    assert a["id"] != b["id"]
    names = {o["title"] for o in client.get("/api/v1/opportunities", headers=other_tenant).json()}
    assert not any("Coral Crest" in n for n in names)


def test_switching_to_a_business_without_membership_is_denied(client: TestClient, other_tenant: dict,
                                                              owner: dict) -> None:
    coastal_id = client.get("/api/v1/business", headers=owner).json()["id"]
    r = client.post("/api/v1/auth/switch-business", json={"business_id": coastal_id}, headers=other_tenant)
    assert r.status_code == 403


def test_forged_token_for_foreign_business_is_rejected(client: TestClient, owner: dict, other_tenant: dict) -> None:
    from app.security.tokens import create_access_token, decode_access_token

    tamarind_user = decode_access_token(other_tenant["Authorization"].split()[1])["sub"]
    coastal_id = client.get("/api/v1/business", headers=owner).json()["id"]
    forged, _ = create_access_token(uuid.UUID(tamarind_user), uuid.UUID(coastal_id))
    r = client.get("/api/v1/transactions", headers={"Authorization": f"Bearer {forged}"})
    assert r.status_code == 401


def test_row_level_security_blocks_queries_without_where_clause() -> None:
    with SessionLocal() as db:
        # The two seeded demo tenants (other tests may register extra, empty businesses).
        biz = db.scalars(select(Business).where(Business.data_label == "synthetic_demo")).all()
        assert len(biz) == 2
        # No tenant bound: RLS returns nothing at all (fail closed).
        assert db.scalar(text("SELECT count(*) FROM transactions")) == 0
    with SessionLocal() as db:
        a, b = biz
        set_tenant(db, a.id)
        rows = db.scalars(select(Transaction.business_id).distinct()).all()  # deliberately no WHERE
        assert rows == [a.id]
        # Writing a row for another tenant is rejected by the policy's WITH CHECK.
        from sqlalchemy.exc import ProgrammingError

        try:
            db.execute(text("INSERT INTO transactions (id, business_id, txn_date, direction, amount, category, "
                            "description, source, is_anomaly, excluded, created_at, updated_at) VALUES "
                            "(gen_random_uuid(), :b, now(), 'outflow', 1, 'Other expenses', 'x', 'manual', false, "
                            "false, now(), now())"), {"b": b.id})
            raised = False
        except ProgrammingError:
            raised = True
        db.rollback()
        assert raised
