"""Short-lived JWT access tokens and opaque, rotating refresh tokens."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app.core.config import get_settings

UTC = timezone.utc  # datetime.UTC needs Python 3.11+


class TokenError(Exception):
    pass


def create_access_token(user_id: uuid.UUID, business_id: uuid.UUID) -> tuple[str, int]:
    s = get_settings()
    now = datetime.now(UTC)
    exp = now + timedelta(minutes=s.access_token_minutes)
    payload = {"sub": str(user_id), "bid": str(business_id), "iat": int(now.timestamp()),
               "nbf": int(now.timestamp()), "exp": int(exp.timestamp()), "iss": s.jwt_issuer,
               "typ": "access", "jti": uuid.uuid4().hex}
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm), s.access_token_minutes * 60


def decode_access_token(token: str) -> dict[str, Any]:
    s = get_settings()
    try:
        payload = jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm], issuer=s.jwt_issuer,
                             options={"require": ["exp", "iat", "sub", "bid", "iss"]})
    except jwt.PyJWTError as exc:
        raise TokenError("invalid token") from exc
    if payload.get("typ") != "access":
        raise TokenError("wrong token type")
    return payload


def new_refresh_token() -> tuple[str, str]:
    """Returns (raw token for the cookie, sha256 hash for the database)."""
    raw = secrets.token_urlsafe(48)
    return raw, hash_refresh_token(raw)


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()
