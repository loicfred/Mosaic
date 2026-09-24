"""Authentication/authorisation dependencies.

Every protected route depends on `get_context`, which:
  * validates the bearer access token,
  * re-checks from the database that the user is active and still a member of
    the business named in the token (so revoking access takes effect at once),
  * binds the DB session to that business for PostgreSQL row-level security.
Role checks use `require_roles`.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db, set_tenant
from app.models import Business, Membership, Role, User
from app.security.rate_limit import limiter
from app.security.tokens import TokenError, decode_access_token
from app.services import audit_service

bearer = HTTPBearer(auto_error=False)


@dataclass
class AuthContext:
    user: User
    business: Business
    role: Role
    db: Session

    @property
    def business_id(self) -> uuid.UUID:
        return self.business.id


def get_context(request: Request, creds: HTTPAuthorizationCredentials | None = Depends(bearer),
                db: Session = Depends(get_db)) -> AuthContext:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(401, "Authentication required.", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = decode_access_token(creds.credentials)
        user_id, business_id = uuid.UUID(payload["sub"]), uuid.UUID(payload["bid"])
    except (TokenError, ValueError, KeyError):
        raise HTTPException(401, "Session expired or invalid.", headers={"WWW-Authenticate": "Bearer"}) from None

    s = get_settings()
    allowed, retry = limiter.hit(f"api:{user_id}", s.api_rate_limit, s.api_rate_window_seconds)
    if not allowed:
        raise HTTPException(429, "Too many requests. Please slow down.", headers={"Retry-After": str(retry)})

    row = db.execute(
        select(User, Membership, Business)
        .join(Membership, Membership.user_id == User.id)
        .join(Business, Business.id == Membership.business_id)
        .where(User.id == user_id, Membership.business_id == business_id)
    ).first()
    if row is None or not row[0].is_active:
        audit_service.record("authz.membership_denied", "access", "denied", request=request, user_id=user_id,
                             business_id=business_id, details={"path": request.url.path})
        raise HTTPException(401, "Session is no longer valid.")
    user, membership, business = row
    set_tenant(db, business.id)
    request.state.user_id = user.id
    return AuthContext(user=user, business=business, role=membership.role, db=db)


def require_roles(*roles: Role) -> Callable[..., AuthContext]:
    def dep(request: Request, ctx: AuthContext = Depends(get_context)) -> AuthContext:
        if ctx.role not in roles:
            audit_service.record("authz.role_denied", "access", "denied", request=request, user_id=ctx.user.id,
                                 actor=ctx.user.email, business_id=ctx.business_id,
                                 details={"path": request.url.path, "method": request.method,
                                          "role": ctx.role.value, "required": [r.value for r in roles]})
            raise HTTPException(403, "Your role does not allow this action.")
        return ctx

    return dep


ANY_ROLE = (Role.owner, Role.accountant, Role.viewer)
EDITORS = (Role.owner, Role.accountant)
OWNER_ONLY = (Role.owner,)
