"""控制器：登录 / 当前用户 / 角色目录。"""
from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.middlewares.rbac import principal_of
from src.schemas.auth import LoginRequest
from src.services import audit_service, auth_service


def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user, token, expires_in = auth_service.authenticate(db, payload.email, payload.password)
    audit_service.record(
        db,
        actor_email=user.email,
        actor_role=user.role,
        action="auth.login",
        entity="user",
        entity_id=user.id,
        detail={"role": user.role},
        ip=request.client.host if request.client else None,
        message=f"{user.display_name} 登录",
    )
    db.commit()
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": expires_in,
        "user": auth_service.serialize(user),
    }


def me(db: Session = Depends(get_db), principal: dict = Depends(principal_of)):
    user = auth_service.get_user(db, principal["email"])
    return auth_service.serialize(user)


def users(db: Session = Depends(get_db), principal: dict = Depends(principal_of)):
    return {"items": [auth_service.serialize(user) for user in auth_service.list_users(db)]}


def roles():
    return {"items": auth_service.role_catalog()}
