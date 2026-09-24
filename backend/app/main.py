"""Valora API - FastAPI application factory."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core import errors
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.middleware import SecurityMiddleware
from app.db.session import SessionLocal
from app.ml.registry import anomaly_model, cash_pressure_model, categoriser_model


def create_app() -> FastAPI:
    s = get_settings()
    configure_logging()
    app = FastAPI(
        title="Valora API",
        version="1.0.0",
        description="Evidence-backed financial opportunities for SMEs. All financial facts are computed by a "
                    "deterministic engine; ML adds a 30-day cash-pressure prediction, anomaly flags and "
                    "category suggestions.",
        docs_url=None if s.is_production else "/docs",
        redoc_url=None,
        openapi_url=None if s.is_production else "/openapi.json",
    )
    app.add_middleware(SecurityMiddleware)
    app.add_middleware(CORSMiddleware, allow_origins=s.cors_origins, allow_credentials=True,
                       allow_methods=["GET", "POST", "PATCH", "DELETE"],
                       allow_headers=["Authorization", "Content-Type", "X-Requested-With"], max_age=600)
    errors.install(app)
    app.include_router(api_router, prefix=s.api_prefix)

    @app.get(f"{s.api_prefix}/health", tags=["health"])
    def health() -> dict[str, Any]:
        db_ok = True
        try:
            with SessionLocal() as db:
                db.execute(text("SELECT 1"))
        except Exception:
            db_ok = False
        return {"status": "ok" if db_ok else "degraded", "database": "ok" if db_ok else "unavailable",
                "models": {"cash_pressure": cash_pressure_model().status, "anomaly": anomaly_model().status,
                           "categoriser": categoriser_model().status}}

    return app


app = create_app()
