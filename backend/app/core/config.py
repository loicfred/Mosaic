"""Application settings, loaded from environment variables / backend/.env.

No secret has a usable default: JWT_SECRET must be provided (scripts/bootstrap.py
writes a random one into backend/.env for local demos).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8",
                                      extra="ignore")

    app_name: str = "Valora"
    app_env: str = Field(default="development", pattern="^(development|production|test)$")
    api_prefix: str = "/api/v1"

    database_url: str = Field(..., description="postgresql+psycopg://user:pass@host:5432/db")

    jwt_secret: str = Field(..., min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "opportunityos"
    access_token_minutes: int = Field(default=15, ge=1, le=60)
    refresh_token_days: int = Field(default=7, ge=1, le=30)

    # NoDecode: read "a,b" as a comma-separated list instead of trying to parse JSON.
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    cookie_secure: bool = False  # set true behind HTTPS (forced true in production)

    max_upload_bytes: int = 5 * 1024 * 1024
    max_import_rows: int = 20_000

    login_rate_limit: int = 5  # attempts per window per IP+email
    login_rate_window_seconds: int = 60
    api_rate_limit: int = 300  # requests per window per user
    api_rate_window_seconds: int = 60
    # Self-service sign-up (POST /auth/register). Creates an owner account and an empty business.
    registration_enabled: bool = True
    register_rate_limit: int = 5  # new accounts per window per IP
    register_rate_window_seconds: int = 3600
    lockout_threshold: int = 5
    lockout_minutes: int = 15

    models_dir: Path = ROOT_DIR / "models"
    audit_ip_salt: str = Field(default="", description="salt for hashing client IPs in audit logs")

    # Valora Insight ("Ask Valora") answers with a Groq-hosted LLM when GROQ_API_KEY is set. Only a compact
    # summary of already-computed figures is sent; see docs/SECURITY.md "AI assistant".
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    llm_timeout_seconds: float = Field(default=20.0, gt=0, le=120)
    llm_rate_limit: int = 20  # questions per window per user
    llm_rate_window_seconds: int = 60

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, v: object) -> object:
        if isinstance(v, str):
            if v.strip().startswith("["):
                return json.loads(v)
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def secure_cookies(self) -> bool:
        return self.cookie_secure or self.is_production

    @property
    def external_ai_enabled(self) -> bool:
        return bool(self.groq_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
