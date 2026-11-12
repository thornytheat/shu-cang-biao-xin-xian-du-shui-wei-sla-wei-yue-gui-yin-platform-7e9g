"""认证相关模型。"""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)


class UserOut(BaseModel):
    id: int
    email: str
    display_name: str
    role: str
    role_label: str
    team: str
    permissions: list[str]


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class RoleCatalogOut(BaseModel):
    role: str
    label: str
    permissions: list[str]
