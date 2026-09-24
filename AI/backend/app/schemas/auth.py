from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import StrictModel


class LoginIn(StrictModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RegisterIn(StrictModel):
    """A new owner account and the business it owns. Only what the engine needs:
    the opening cash balance and the date it applies from anchor every cash figure."""

    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    business_name: str = Field(min_length=2, max_length=160)
    sector: str = Field(min_length=2, max_length=80)
    opening_cash: Decimal = Field(ge=0, le=Decimal("1000000000000"), max_digits=14, decimal_places=2)
    opening_date: date


class SwitchBusinessIn(StrictModel):
    business_id: uuid.UUID


class ChangePasswordIn(StrictModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)


class MembershipOut(BaseModel):
    business_id: str
    business_name: str
    role: str


class MeOut(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    business: dict
    memberships: list[MembershipOut]
    permissions: list[str]


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105
    expires_in: int
