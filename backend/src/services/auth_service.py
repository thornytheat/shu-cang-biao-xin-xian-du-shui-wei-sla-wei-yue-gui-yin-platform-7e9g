"""认证服务：登录、用户列表、令牌签发。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.constants.enums import Role
from src.constants.roles import PERMISSIONS, ROLE_LABELS
from src.models.user import User
from src.utils.errors import AppError
from src.utils.security import create_access_token, verify_password


def authenticate(db: Session, email: str, password: str) -> tuple[User, str, int]:
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None or not verify_password(password, user.password_hash):
        raise AppError("AUTH_INVALID", 401)
    token, expires_in = create_access_token(user.email, user.role)
    user.last_login_at = datetime.utcnow()
    return user, token, expires_in


def get_user(db: Session, email: str) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        raise AppError("NOT_FOUND", 404, detail={"email": email})
    return user


def list_users(db: Session) -> list[User]:
    return list(db.scalars(select(User).order_by(User.id)))


def serialize(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
        "role_label": ROLE_LABELS.get(user.role, user.role),
        "team": user.team,
        "permissions": sorted(PERMISSIONS.get(user.role, set())),
    }


def role_catalog() -> list[dict]:
    return [
        {
            "role": role.value,
            "label": ROLE_LABELS.get(role.value, role.value),
            "permissions": sorted(PERMISSIONS.get(role.value, set())),
        }
        for role in Role
    ]
