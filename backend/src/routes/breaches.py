"""违约路由：/api/breaches/*"""
from __future__ import annotations

from fastapi import APIRouter

from src.controllers import breach_controller
from src.schemas.breach import BreachActionRequest, BreachListOut, BreachOut, DetectRequest, DetectResponse

router = APIRouter(prefix="/breaches", tags=["breaches"])

router.get("", response_model=BreachListOut)(breach_controller.list_breaches)
router.get("/summary")(breach_controller.summary)
router.post("/detect", response_model=DetectResponse)(breach_controller.detect_breaches)
router.get("/{breach_id}")(breach_controller.get_breach)
router.post("/{breach_id}/claim", response_model=BreachOut)(breach_controller.claim_breach)
router.post("/{breach_id}/resolve", response_model=BreachOut)(breach_controller.resolve_breach)
router.post("/{breach_id}/attribution", response_model=BreachOut)(breach_controller.recompute_attribution)
