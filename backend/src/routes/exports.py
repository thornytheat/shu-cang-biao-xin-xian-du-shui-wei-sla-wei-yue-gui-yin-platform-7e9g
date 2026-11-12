"""导出与审计路由：/api/exports/*、/api/audit"""
from __future__ import annotations

from fastapi import APIRouter

from src.controllers import export_controller

router = APIRouter(tags=["exports"])

router.get("/exports/breaches.csv")(export_controller.export_breaches_csv)
router.get("/exports/review.md")(export_controller.export_review_markdown)
router.get("/audit")(export_controller.list_audit)
