from __future__ import annotations

from datetime import date, timedelta

from conftest import login
from fastapi.testclient import TestClient

NEW = {
    "full_name": "Asha Ramdin",
    "email": "Asha@Example.com",
    "password": "Harbour-Lights-2026",
    "business_name": "Harbour Test Kitchen",
    "sector": "Food & beverage",
    "opening_cash": "85000.00",
    "opening_date": "2026-01-01",
}


def test_register_creates_owner_of_an_empty_business_and_signs_in(client: TestClient) -> None:
    c = TestClient(client.app)
    r = c.post("/api/v1/auth/register", json=NEW)
    assert r.status_code == 201, r.text
    assert "oos_refresh=" in r.headers["set-cookie"] and "HttpOnly" in r.headers["set-cookie"]
    auth = {"Authorization": f"Bearer {r.json()['access_token']}"}
    me = c.get("/api/v1/auth/me", headers=auth).json()
    assert me["email"] == "asha@example.com" and me["role"] == "owner"
    assert me["business"]["name"] == "Harbour Test Kitchen"
    assert me["business"]["data_label"] == "user_data" and me["business"]["currency"] == "MUR"
    # A brand-new business starts with no records at all (nothing is generated for it) ...
    assert c.get("/api/v1/transactions", headers=auth).json()["total"] == 0
    assert c.get("/api/v1/opportunities", headers=auth).json() == []
    # ... and cannot see any other tenant's data.
    assert "Coastal" not in str(c.get("/api/v1/business", headers=auth).json())
    # The same credentials work for a normal sign-in.
    login(c, "asha@example.com", NEW["password"])


def test_register_rejects_duplicate_email_weak_password_and_future_date(client: TestClient) -> None:
    dup = {**NEW, "email": "owner@coastal.demo"}
    assert client.post("/api/v1/auth/register", json=dup).status_code == 409
    weak = {**NEW, "email": "weak@example.com", "password": "aaaaaaaaaaaa"}
    assert client.post("/api/v1/auth/register", json=weak).status_code == 422
    future = {**NEW, "email": "future@example.com", "opening_date": str(date.today() + timedelta(days=3))}
    assert client.post("/api/v1/auth/register", json=future).status_code == 422
    extra = {**NEW, "email": "extra@example.com", "role": "admin"}
    assert client.post("/api/v1/auth/register", json=extra).status_code == 422  # unknown fields refused


def test_register_is_rate_limited_per_ip(client: TestClient) -> None:
    codes = [client.post("/api/v1/auth/register", json={**NEW, "email": f"burst{i}@example.com"}).status_code
             for i in range(7)]
    assert codes[:5] == [201] * 5 and codes[5] == 429
