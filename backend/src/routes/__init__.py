"""路由聚合：所有子路由挂在 /api 前缀下（Nginx 已剥掉 /api 并转发 /）。"""
from __future__ import annotations

from fastapi import APIRouter

from src.routes import auth, breaches, exports, health, policies, probes, tables

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(tables.router)
api_router.include_router(probes.router)
api_router.include_router(policies.router)
api_router.include_router(breaches.router)
api_router.include_router(exports.router)

__all__ = ["api_router"]
