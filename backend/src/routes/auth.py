"""认证路由：/api/auth/*"""
from __future__ import annotations

from fastapi import APIRouter

from src.controllers import auth_controller
from src.schemas.auth import LoginRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

router.post("/login", response_model=TokenResponse)(auth_controller.login)
router.get("/me", response_model=UserOut)(auth_controller.me)
router.get("/users")(auth_controller.users)
router.get("/roles")(auth_controller.roles)
