"""表资产与看板路由：/api/tables/*、/api/dashboard/*"""
from __future__ import annotations

from fastapi import APIRouter

from src.controllers import table_controller
from src.schemas.freshness import BoardOut, TableFreshnessOut

router = APIRouter(tags=["tables"])

router.get("/tables")(table_controller.list_tables)
router.get("/tables/{code}")(table_controller.get_table)
router.get("/tables/{code}/freshness", response_model=TableFreshnessOut)(table_controller.table_freshness)
router.patch("/tables/{code}")(table_controller.update_table)
router.get("/dashboard/health", response_model=BoardOut)(table_controller.board)
