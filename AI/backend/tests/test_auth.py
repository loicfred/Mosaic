from __future__ import annotations

from conftest import PASSWORD, login
from fastapi.testclient import TestClient

CSRF = {"X-Requested-With": "Valora"}


def test_login_success_returns_short_lived_token_and_httponly_cookie(client: TestClient) -> None:
    r = client.post("/api/v1/auth/login", json={"email": "owner@coastal.demo", "password": PASSWORD})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer" and body["expires_in"] <= 3600
    cookie = r.headers["set-cookie"]
    assert "oos_refresh=" in cookie and "HttpOnly" in cookie and "SameSite=strict" in cookie
    assert "Path=/api/v1/auth" in cookie


def test_login_failure_is_generic(client: TestClient) -> None:
    r1 = client.post("/api/v1/auth/login", json={"email": "owner@coastal.demo", "password": "wrong-password"})
    r2 = client.post("/api/v1/auth/login", json={"email": "nobody@coastal.demo", "password": "wrong-password"})
    assert r1.status_code == r2.status_code == 401
    assert r1.json()["error"]["message"] == r2.json()["error"]["message"]


def test_me_requires_token(client: TestClient) -> None:
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not.a.jwt"}).status_code == 401


def test_me_returns_role_and_permissions(client: TestClient, viewer: dict) -> None:
    me = client.get("/api/v1/auth/me", headers=viewer).json()
    assert me["role"] == "viewer" and me["permissions"] == ["view"]
    assert me["business"]["data_label"] == "synthetic_demo"


def test_refresh_rotation_and_reuse_detection(client: TestClient) -> None:
    c = TestClient(client.app)
    login_resp = c.post("/api/v1/auth/login", json={"email": "accountant@coastal.demo", "password": PASSWORD})
    first = login_resp.cookies.get("oos_refresh")
    assert c.post("/api/v1/auth/refresh").status_code == 403  # missing CSRF header
    r = c.post("/api/v1/auth/refresh", headers=CSRF)
    assert r.status_code == 200
    second = r.cookies.get("oos_refresh")
    assert second and second != first
    # Replaying the first (rotated) token revokes the whole family...
    c.cookies.clear()
    c.cookies.set("oos_refresh", first, path="/api/v1/auth")
    assert c.post("/api/v1/auth/refresh", headers=CSRF).status_code == 401
    # ...including the newest token.
    c.cookies.clear()
    c.cookies.set("oos_refresh", second, path="/api/v1/auth")
    assert c.post("/api/v1/auth/refresh", headers=CSRF).status_code == 401


def test_logout_revokes_refresh_token(client: TestClient) -> None:
    c = TestClient(client.app)
    c.post("/api/v1/auth/login", json={"email": "viewer@coastal.demo", "password": PASSWORD})
    assert c.post("/api/v1/auth/logout", headers=CSRF).status_code == 204
    assert c.post("/api/v1/auth/refresh", headers=CSRF).status_code == 401


def test_login_rate_limit(client: TestClient) -> None:
    codes = [client.post("/api/v1/auth/login", json={"email": "ratelimit@coastal.demo", "password": "x" * 12})
             .status_code for _ in range(7)]
    assert codes[:5] == [401] * 5 and 429 in codes[5:]


def test_account_lockout_after_repeated_failures(client: TestClient) -> None:
    from app.security.rate_limit import limiter

    for _ in range(5):
        limiter.reset()
        client.post("/api/v1/auth/login", json={"email": "owner@tamarind.demo", "password": "wrong-password"})
    limiter.reset()
    r = client.post("/api/v1/auth/login", json={"email": "owner@tamarind.demo", "password": PASSWORD})
    assert r.status_code == 423
    # unlock for other tests
    from sqlalchemy import update

    from app.db.session import SessionLocal
    from app.models import User

    with SessionLocal() as db:
        db.execute(update(User).where(User.email == "owner@tamarind.demo").values(locked_until=None, failed_logins=0))
        db.commit()
    assert login(client, "owner@tamarind.demo")


def test_password_hash_is_argon2id() -> None:
    from sqlalchemy import select

    from app.db.session import SessionLocal
    from app.models import User

    with SessionLocal() as db:
        h = db.scalar(select(User.password_hash).where(User.email == "owner@coastal.demo"))
    assert h.startswith("$argon2id$") and PASSWORD not in h
