"""探测路由：/api/probes/*"""
from __future__ import annotations

from fastapi import APIRouter

from src.controllers import probe_controller
from src.schemas.breach import ProbeRunResponse, ProbeStatusOut

router = APIRouter(prefix="/probes", tags=["probes"])

router.post("/run", response_model=ProbeRunResponse)(probe_controller.run_probes)
router.get("/status", response_model=ProbeStatusOut)(probe_controller.probe_status)
router.get("")(probe_controller.list_probes)
