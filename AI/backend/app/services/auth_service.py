"""Login, refresh-token rotation, logout and password changes."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import Request
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.models import Business, Membership, RefreshToken, Role, User
from app.security.passwords import hash_password, needs_rehash, password_problems, verify_password
from app.security.rate_limit import limiter
from app.security.tokens import create_access_token, hash_refresh_token, new_refresh_token
from app.services import audit_service

UTC = timezone.utc  # datetime.UTC needs Python 3.11+

GENERIC_LOGIN_ERROR = "Email or password is incorrect."


def _issue(db: Session, user: User, business_id: uuid.UUID, family: uuid.UUID | None = None) -> tuple[str, int, str]:
    s = get_settings()
    access, expires_in = create_access_token(user.id, business_id)
    raw, digest = new_refresh_token()
    db.add(RefreshToken(user_id=user.id, business_id=business_id, token_hash=digest,
                        family_id=family or uuid.uuid4(),
                        expires_at=datetime.now(UTC) + timedelta(days=s.refresh_token_days)))
    return access, expires_in, raw


def login(db: Session, email: str, password: str, request: Request) -> tuple[str, int, str, User, uuid.UUID]:
    s = get_settings()
    email = email.strip().lower()
    ip = request.client.host if request.client else "unknown"
    ok, retry = limiter.hit(f"login:{ip}:{email}", s.login_rate_limit, s.login_rate_window_seconds)
    ok_ip, retry_ip = limiter.hit(f"login-ip:{ip}", s.login_rate_limit * 4, s.login_rate_window_seconds)
    if not ok or not ok_ip:
        audit_service.record("auth.login_rate_limited", "auth", "denied", request=request, actor=email)
        raise AppError(429, "rate_limited", "Too many login attempts. Try again shortly.",
                       {"retry_after_seconds": max(retry, retry_ip)})

    user = db.scalar(select(User).where(User.email == email))
    now = datetime.now(UTC)
    if user and user.locked_until and user.locked_until > now:
        verify_password(password, None)  # constant-ish time
        audit_service.record("auth.login_locked", "auth", "denied", request=request, user_id=user.id, actor=email)
        raise AppError(423, "account_locked", "Account temporarily locked after repeated failures. "
                                              "Try again later.")
    if user is None or not user.is_active or not verify_password(password, user.password_hash if user else None):
        if user:
            user.failed_logins += 1
            if user.failed_logins >= s.lockout_threshold:
                user.locked_until = now + timedelta(minutes=s.lockout_minutes)
                user.failed_logins = 0
                audit_service.record("auth.account_locked", "security", "success", request=request,
                                     user_id=user.id, actor=email, details={"minutes": s.lockout_minutes})
            db.commit()
        audit_service.record("auth.login_failed", "auth", "failure", request=request,
                             user_id=user.id if user else None, actor=email)
        raise AppError(401, "invalid_credentials", GENERIC_LOGIN_ERROR)

    membership = db.scalar(select(Membership).where(Membership.user_id == user.id)
                           .order_by(Membership.created_at))
    if membership is None:
        raise AppError(403, "no_business", "This account is not linked to a business.")
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    user.failed_logins, user.locked_until, user.last_login_at = 0, None, now
    access, expires_in, refresh = _issue(db, user, membership.business_id)
    db.commit()
    audit_service.record("auth.login_success", "auth", request=request, user_id=user.id, actor=email,
                         business_id=membership.business_id)
    return access, expires_in, refresh, user, membership.business_id


def register(db: Session, *, full_name: str, email: str, password: str, business_name: str, sector: str,
             opening_cash: Decimal, opening_date: date, request: Request) -> tuple[str, int, str, User, uuid.UUID]:
    """Create an owner account, its business (empty, labelled user_data) and the owner
    membership in one transaction, then sign the new owner in."""
    s = get_settings()
    if not s.registration_enabled:
        raise AppError(403, "registration_disabled", "New accounts cannot be created on this server.")
    email = email.strip().lower()
    ip = request.client.host if request.client else "unknown"
    ok, retry = limiter.hit(f"register-ip:{ip}", s.register_rate_limit, s.register_rate_window_seconds)
    if not ok:
        audit_service.record("auth.register_rate_limited", "auth", "denied", request=request, actor=email)
        raise AppError(429, "rate_limited", "Too many new accounts from this network. Try again later.",
                       {"retry_after_seconds": retry})
    if opening_date > date.today():
        raise AppError(422, "invalid_opening_date", "The opening balance date cannot be in the future.")
    problems = password_problems(password, email)
    if problems:
        raise AppError(422, "weak_password", " ".join(problems))
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        audit_service.record("auth.register_duplicate", "auth", "denied", request=request, actor=email)
        raise AppError(409, "email_taken", "An account with this email already exists. Sign in instead.")

    user = User(email=email, full_name=full_name, password_hash=hash_password(password),
                password_changed_at=datetime.now(UTC), last_login_at=datetime.now(UTC))
    business = Business(name=business_name, sector=sector, currency="MUR", opening_cash=opening_cash,
                        opening_date=opening_date, data_label="user_data")
    db.add_all([user, business])
    db.flush()
    db.add(Membership(user_id=user.id, business_id=business.id, role=Role.owner))
    access, expires_in, refresh = _issue(db, user, business.id)
    db.commit()
    audit_service.record("auth.register", "auth", request=request, user_id=user.id, actor=email,
                         business_id=business.id, resource_type="business", resource_id=str(business.id))
    return access, expires_in, refresh, user, business.id


def rotate(db: Session, raw: str | None, request: Request) -> tuple[str, int, str, uuid.UUID]:
    if not raw:
        raise AppError(401, "no_session", "Not signed in.")
    now = datetime.now(UTC)
    tok = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw)))
    if tok is None:
        raise AppError(401, "invalid_session", "Session expired. Please sign in again.")
    if tok.revoked_at is not None:
        # A rotated token was presented again: likely theft. Revoke the whole family.
        db.execute(update(RefreshToken).where(RefreshToken.family_id == tok.family_id,
                                              RefreshToken.revoked_at.is_(None)).values(revoked_at=now))
        db.commit()
        audit_service.record("auth.refresh_reuse_detected", "security", "denied", request=request,
                             user_id=tok.user_id, business_id=tok.business_id)
        raise AppError(401, "invalid_session", "Session expired. Please sign in again.")
    if tok.expires_at < now:
        raise AppError(401, "invalid_session", "Session expired. Please sign in again.")
    user = db.get(User, tok.user_id)
    member = db.scalar(select(Membership).where(Membership.user_id == tok.user_id,
                                                Membership.business_id == tok.business_id))
    if user is None or not user.is_active or member is None:
        raise AppError(401, "invalid_session", "Session expired. Please sign in again.")
    access, expires_in, new_raw = _issue(db, user, tok.business_id, tok.family_id)
    tok.revoked_at = now
    db.flush()
    tok.replaced_by = db.scalar(select(RefreshToken.id).where(RefreshToken.token_hash == hash_refresh_token(new_raw)))
    db.commit()
    return access, expires_in, new_raw, tok.business_id


def logout(db: Session, raw: str | None, request: Request) -> None:
    if not raw:
        return
    tok = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw)))
    if tok:
        db.execute(update(RefreshToken).where(RefreshToken.family_id == tok.family_id,
                                              RefreshToken.revoked_at.is_(None))
                   .values(revoked_at=datetime.now(UTC)))
        db.commit()
        audit_service.record("auth.logout", "auth", request=request, user_id=tok.user_id,
                             business_id=tok.business_id)


def switch_business(db: Session, user: User, business_id: uuid.UUID, request: Request) -> tuple[str, int, str]:
    member = db.scalar(select(Membership).where(Membership.user_id == user.id,
                                                Membership.business_id == business_id))
    if member is None:
        audit_service.record("authz.switch_business_denied", "access", "denied", request=request,
                             user_id=user.id, actor=user.email, business_id=business_id)
        raise AppError(403, "forbidden", "You do not have access to that business.")
    access, expires_in, refresh = _issue(db, user, business_id)
    db.commit()
    audit_service.record("auth.switch_business", "auth", request=request, user_id=user.id, actor=user.email,
                         business_id=business_id)
    return access, expires_in, refresh


def change_password(db: Session, user: User, current: str, new: str, request: Request) -> None:
    if not verify_password(current, user.password_hash):
        audit_service.record("auth.password_change_failed", "security", "failure", request=request,
                             user_id=user.id, actor=user.email)
        raise AppError(400, "invalid_password", "Current password is incorrect.")
    problems = password_problems(new, user.email)
    if problems:
        raise AppError(422, "weak_password", " ".join(problems))
    user.password_hash = hash_password(new)
    user.password_changed_at = datetime.now(UTC)
    # Sign out every other session.
    db.execute(update(RefreshToken).where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
               .values(revoked_at=datetime.now(UTC)))
    db.commit()
    audit_service.record("auth.password_changed", "security", request=request, user_id=user.id, actor=user.email)


def memberships(db: Session, user_id: uuid.UUID) -> list[dict[str, str]]:
    rows = db.execute(select(Membership, Business).join(Business, Business.id == Membership.business_id)
                      .where(Membership.user_id == user_id)).all()
    return [{"business_id": str(b.id), "business_name": b.name, "role": m.role.value} for m, b in rows]
