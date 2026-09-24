from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select, text

from app.core.config import get_settings
from app.ml.registry import anomaly_model, cash_pressure_model, categoriser_model
from app.models import AuditEvent
from app.security.deps import EDITORS, AuthContext, get_context, require_roles

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/events")
def events(ctx: AuthContext = Depends(require_roles(*EDITORS)),
           category: Literal["auth", "access", "data", "opportunity", "security"] | None = None,
           outcome: Literal["success", "failure", "denied"] | None = None,
           limit: int = Query(100, ge=1, le=500)) -> list[dict[str, Any]]:
    # Business events for this tenant, plus this user's own sign-in events (which may have no business).
    q = select(AuditEvent).where(or_(AuditEvent.business_id == ctx.business_id,
                                     (AuditEvent.business_id.is_(None)) & (AuditEvent.user_id == ctx.user.id)))
    if category:
        q = q.where(AuditEvent.category == category)
    if outcome:
        q = q.where(AuditEvent.outcome == outcome)
    rows = ctx.db.scalars(q.order_by(AuditEvent.id.desc()).limit(limit)).all()
    return [{"id": e.id, "at": e.created_at.isoformat(), "event": e.event_type, "category": e.category,
             "outcome": e.outcome, "actor": e.actor, "resource_type": e.resource_type,
             "resource_id": e.resource_id, "details": e.details, "ip_hash": e.ip_hash} for e in rows]


@router.get("/security-summary")
def security_summary(ctx: AuthContext = Depends(get_context)) -> dict[str, Any]:
    """Only controls that are implemented and verifiable at runtime are reported."""
    s = get_settings()
    db = ctx.db
    role = db.execute(text("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user")).one()
    rls = db.execute(text("SELECT count(*) FILTER (WHERE relrowsecurity AND relforcerowsecurity), count(*) "
                          "FROM pg_class WHERE relname = ANY(:t)"),
                     {"t": ["transactions", "invoices", "import_batches", "import_rows", "proposed_changes",
                            "opportunities", "opportunity_events", "scenarios", "predictions"]}).one()
    rls_effective = bool(rls[0] == rls[1] and not role[0] and not role[1])
    counts = dict(db.execute(select(AuditEvent.outcome, func.count()).where(
        AuditEvent.business_id == ctx.business_id,
        AuditEvent.created_at > func.now() - text("interval '7 days'")).group_by(AuditEvent.outcome)).all())
    return {
        "authentication": {"password_hashing": "Argon2id (64 MiB, t=3, p=2)",
                           "access_token_minutes": s.access_token_minutes,
                           "refresh_token": f"httpOnly SameSite=Strict cookie, rotated on every use, "
                                            f"reuse revokes the session family, {s.refresh_token_days}-day expiry",
                           "lockout": f"{s.lockout_threshold} failures -> {s.lockout_minutes} min lock",
                           "login_rate_limit": f"{s.login_rate_limit} per {s.login_rate_window_seconds}s per IP+email"},
        "authorization": {"model": "RBAC", "roles": ["owner", "accountant", "viewer"], "your_role": ctx.role.value,
                          "enforced_in": "every API route (server-side), re-checked against the database per request"},
        "tenant_isolation": {"app_layer": "every query filtered by business_id from the verified token",
                             "database_layer": "PostgreSQL row-level security (FORCE) on tenant tables",
                             "rls_tables_protected": f"{rls[0]}/{rls[1]}",
                             "rls_effective_for_app_role": rls_effective,
                             "note": None if rls_effective else
                             "The database role is a superuser or has BYPASSRLS, so RLS is not enforced. "
                             "Use the dedicated application role from the README."},
        "input_validation": {"api": "Pydantic schemas (unknown fields rejected)",
                             "csv": f"size <= {s.max_upload_bytes // 1048576} MB, <= {s.max_import_rows:,} rows, "
                                    "encoding + column checks, formula-injection stripping",
                             "sql": "SQLAlchemy parameterised queries only"},
        "api": {"versioned_prefix": s.api_prefix, "cors_origins": s.cors_origins,
                "security_headers": ["Content-Security-Policy", "X-Content-Type-Options", "X-Frame-Options",
                                     "Referrer-Policy", "Permissions-Policy", "Cache-Control: no-store",
                                     "HSTS (production)"],
                "api_rate_limit": f"{s.api_rate_limit} requests per {s.api_rate_window_seconds}s per user",
                "errors": "generic messages with request id; no stack traces"},
        "data_protection": {"stored_secrets": "refresh tokens stored as SHA-256 hashes; no card or bank numbers stored",
                            "audit_ip": "client IPs stored only as salted hashes",
                            "external_ai": "disabled - explanations are generated locally from verified figures"
                            if not s.external_ai_enabled else "enabled (structured findings only)",
                            "https": "HSTS and Secure cookies enforced when APP_ENV=production",
                            "at_rest": "Use disk/volume encryption for the PostgreSQL host (deployment responsibility)"},
        "audit": {"append_only": "database trigger rejects UPDATE/DELETE on audit_events",
                  "events_last_7_days": counts},
        "models": {"cash_pressure": cash_pressure_model().status, "anomaly": anomaly_model().status,
                   "categoriser": categoriser_model().status},
        "environment": s.app_env,
    }
