"""Users, businesses (tenants), role memberships and refresh tokens."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_col, uuid_pk


class Role(str, enum.Enum):
    owner = "owner"
    accountant = "accountant"
    viewer = "viewer"


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = uuid_pk()
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    failed_logins: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at_col()


class Business(Base):
    __tablename__ = "businesses"
    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(160))
    sector: Mapped[str] = mapped_column(String(80))
    currency: Mapped[str] = mapped_column(String(3), default="MUR")
    opening_cash: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    opening_date: Mapped[date] = mapped_column(Date)
    # 'synthetic_demo' for seeded demo tenants, 'user_data' for real imports.
    data_label: Mapped[str] = mapped_column(String(32), default="user_data")
    created_at: Mapped[datetime] = created_at_col()


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("user_id", "business_id"),)
    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
                                               index=True)
    business_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True),
                                                   ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    role: Mapped[Role] = mapped_column(Enum(Role, name="role"))
    created_at: Mapped[datetime] = created_at_col()


class RefreshToken(Base):
    """Only a SHA-256 hash of the token is stored. Tokens rotate on every use;
    re-use of a rotated token revokes the whole family (theft detection)."""

    __tablename__ = "refresh_tokens"
    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
                                               index=True)
    business_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True),
                                                   ForeignKey("businesses.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    family_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replaced_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True))
    created_at: Mapped[datetime] = created_at_col()
