from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.session import get_db
from app.models import Role
from app.schemas.auth import ChangePasswordIn, LoginIn, MeOut, RegisterIn, SwitchBusinessIn, TokenOut
from app.security.deps import AuthContext, get_context
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])
COOKIE = "oos_refresh"
CSRF_HEADER = "x-requested-with"
CSRF_VALUE = "Valora"

PERMISSIONS = {
    Role.owner: ["view", "import_data", "approve_changes", "manage_opportunities", "save_scenarios", "view_audit",
                 "view_members"],
    Role.accountant: ["view", "import_data", "approve_changes", "manage_opportunities", "save_scenarios",
                      "view_audit"],
    Role.viewer: ["view"],
}


def _set_cookie(resp: Response, raw: str) -> None:
    s = get_settings()
    resp.set_cookie(COOKIE, raw, max_age=s.refresh_token_days * 86400, httponly=True, secure=s.secure_cookies,
                    samesite="strict", path=f"{s.api_prefix}/auth")


def _csrf(request: Request) -> None:
    # The refresh cookie is SameSite=Strict; this header adds a second CSRF barrier because
    # browsers do not let other sites set custom headers on cross-origin requests without CORS approval.
    if request.headers.get(CSRF_HEADER) != CSRF_VALUE:
        raise AppError(403, "csrf", "Missing request header.")


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)) -> TokenOut:
    access, expires, refresh, _, _ = auth_service.login(db, body.email, body.password, request)
    _set_cookie(response, refresh)
    return TokenOut(access_token=access, expires_in=expires)


@router.post("/register", response_model=TokenOut, status_code=201)
def register(body: RegisterIn, request: Request, response: Response, db: Session = Depends(get_db)) -> TokenOut:
    access, expires, refresh, _, _ = auth_service.register(
        db, full_name=body.full_name, email=body.email, password=body.password, business_name=body.business_name,
        sector=body.sector, opening_cash=body.opening_cash, opening_date=body.opening_date, request=request)
    _set_cookie(response, refresh)
    response.status_code = 201
    return TokenOut(access_token=access, expires_in=expires)


@router.post("/refresh", response_model=TokenOut)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)) -> TokenOut:
    _csrf(request)
    access, expires, raw, _ = auth_service.rotate(db, request.cookies.get(COOKIE), request)
    _set_cookie(response, raw)
    return TokenOut(access_token=access, expires_in=expires)


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> Response:
    _csrf(request)
    auth_service.logout(db, request.cookies.get(COOKIE), request)
    s = get_settings()
    response.delete_cookie(COOKIE, path=f"{s.api_prefix}/auth")
    response.status_code = 204
    return response


@router.get("/me", response_model=MeOut)
def me(ctx: AuthContext = Depends(get_context)) -> MeOut:
    b = ctx.business
    return MeOut(id=str(ctx.user.id), email=ctx.user.email, full_name=ctx.user.full_name, role=ctx.role.value,
                 business={"id": str(b.id), "name": b.name, "sector": b.sector, "currency": b.currency,
                           "data_label": b.data_label},
                 memberships=auth_service.memberships(ctx.db, ctx.user.id),
                 permissions=PERMISSIONS[ctx.role])


@router.post("/switch-business", response_model=TokenOut)
def switch_business(body: SwitchBusinessIn, request: Request, response: Response,
                    ctx: AuthContext = Depends(get_context)) -> TokenOut:
    access, expires, raw = auth_service.switch_business(ctx.db, ctx.user, body.business_id, request)
    _set_cookie(response, raw)
    return TokenOut(access_token=access, expires_in=expires)


@router.post("/change-password", status_code=204)
def change_password(body: ChangePasswordIn, request: Request, response: Response,
                    ctx: AuthContext = Depends(get_context)) -> Response:
    auth_service.change_password(ctx.db, ctx.user, body.current_password, body.new_password, request)
    response.status_code = 204
    return response
