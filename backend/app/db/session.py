"""Database engine/session plus the tenant context used by PostgreSQL row-level security.

Every tenant-owned table has an RLS policy comparing `business_id` with the
session setting `app.business_id`. The setting is applied at the start of every
transaction (see `_apply_tenant`), so even a query that forgets its
`WHERE business_id = ...` clause cannot read another tenant's rows.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_settings = get_settings()
engine = create_engine(_settings.database_url, pool_pre_ping=True, pool_size=10, max_overflow=5,
                       future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

TENANT_KEY = "tenant_business_id"


@event.listens_for(Session, "after_begin")
def _apply_tenant(session: Session, transaction, connection) -> None:  # type: ignore[no-untyped-def]
    bid = session.info.get(TENANT_KEY)
    if bid is not None:
        connection.execute(text("SELECT set_config('app.business_id', :bid, true)"), {"bid": str(bid)})


def set_tenant(session: Session, business_id: UUID | None) -> None:
    """Bind the session to one business. Takes effect immediately and for every
    later transaction on this session."""
    session.info[TENANT_KEY] = business_id
    if business_id is not None and session.in_transaction():
        session.execute(text("SELECT set_config('app.business_id', :bid, true)"), {"bid": str(business_id)})


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def tenant_session(business_id: UUID) -> Iterator[Session]:
    """Session bound to one tenant, for scripts and background jobs."""
    db = SessionLocal()
    set_tenant(db, business_id)
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
