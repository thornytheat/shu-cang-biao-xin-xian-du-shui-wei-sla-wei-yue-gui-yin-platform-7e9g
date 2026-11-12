"""SLA 策略路由：/api/policies/*"""
from __future__ import annotations

from fastapi import APIRouter

from src.controllers import policy_controller
from src.schemas.policy import PolicyOut, PolicyPreviewOut, PolicyPreviewRequest, PolicyUpdateRequest

router = APIRouter(prefix="/policies", tags=["policies"])

router.get("")(policy_controller.list_policies)
router.post("/preview", response_model=PolicyPreviewOut)(policy_controller.preview_policies)
router.patch("/{tier}", response_model=PolicyOut)(policy_controller.update_policy)
