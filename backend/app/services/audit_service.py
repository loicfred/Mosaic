"""Audit logging. Written in its own short transaction so that a failure in the
calling request (for example a rejected login) is still recorded."""

from __future__ import annotations

import hashlib
import logging
import uuid
from typing import Any

from fastapi import Request

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import AuditEvent

log = logging.getLogger("opportunityos.audit")

FORBIDDEN_KEYS = {"password", "token", "access_token", "refresh_token", "secret", "authorization"}


def client_ip_hash(request: Request | None) -> str | None:
    if request is None or request.client is None:
        return None
    salt = get_settings().audit_ip_salt
    return hashlib.sha256(f"{salt}{request.client.host}".encode()).hexdigest()[:16]


def _clean(details: dict[str, Any] | None) -> dict[str, Any]:
    if not details:
        return {}
    return {k: v for k, v in details.items() if k.lower() not in FORBIDDEN_KEYS}


def record(event_type: str, category: str, outcome: str = "success", *, request: Request | None = None,
           user_id: uuid.UUID | None = None, actor: str | None = None, business_id: uuid.UUID | None = None,
           resource_type: str | None = None, resource_id: str | None = None,
           details: dict[str, Any] | None = None) -> None:
    db = SessionLocal()
    try:
        db.add(AuditEvent(event_type=event_type, category=category, outcome=outcome, user_id=user_id,
                          actor=actor, business_id=business_id, resource_type=resource_type,
                          resource_id=resource_id, ip_hash=client_ip_hash(request), details=_clean(details)))
        db.commit()
    except Exception:  # pragma: no cover - audit must never break the request
        db.rollback()
        log.exception("failed to write audit event %s", event_type)
    finally:
        db.close()
