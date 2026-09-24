"""Test configuration: runs against a separate PostgreSQL database (opportunityos_test).

Set TEST_DATABASE_URL to override. The schema is migrated with Alembic and the
synthetic demo tenants are seeded once per test session.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://opportunityos:devpassword@localhost:5432/opportunityos_test")
os.environ.setdefault("JWT_SECRET", "test-secret-" + "x" * 40)
os.environ["APP_ENV"] = "test"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "backend"))

from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from alembic import command  # noqa: E402

PASSWORD = "Coastal-Demo-2026!"


@pytest.fixture(scope="session", autouse=True)
def database() -> None:
    from sqlalchemy import create_engine, text

    eng = create_engine(os.environ["DATABASE_URL"])
    with eng.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
    eng.dispose()
    cfg = Config(str(ROOT / "backend" / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "backend" / "alembic"))
    command.upgrade(cfg, "head")
    import seed_demo

    seed_demo.main()


@pytest.fixture(autouse=True)
def reset_limits() -> None:
    from app.security.rate_limit import limiter

    limiter.reset()


@pytest.fixture(scope="session")
def client(database: None) -> TestClient:
    from app.main import app

    return TestClient(app)


def login(client: TestClient, email: str, password: str = PASSWORD) -> dict[str, str]:
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def owner(client: TestClient) -> dict[str, str]:
    return login(client, "owner@coastal.demo")


@pytest.fixture()
def accountant(client: TestClient) -> dict[str, str]:
    return login(client, "accountant@coastal.demo")


@pytest.fixture()
def viewer(client: TestClient) -> dict[str, str]:
    return login(client, "viewer@coastal.demo")


@pytest.fixture()
def other_tenant(client: TestClient) -> dict[str, str]:
    return login(client, "owner@tamarind.demo")
