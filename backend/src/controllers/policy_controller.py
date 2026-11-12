"""控制器：SLA 策略读取/修改/试算。"""
from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.constants.roles import POLICY_PREVIEW_ROLES, POLICY_WRITE_ROLES
from src.middlewares.rbac import principal_of, require_roles
from src.schemas.policy import PolicyPreviewRequest, PolicyUpdateRequest
from src.services import audit_service, policy_service


def list_policies(db: Session = Depends(get_db), principal: dict = Depends(principal_of)):
    rows = policy_service.list_policies(db)
    return {
        "items": [policy_service.serialize(row) for row in rows],
        "can_edit": principal["role"] in POLICY_WRITE_ROLES,
        "can_preview": principal["role"] in POLICY_PREVIEW_ROLES,
    }


def update_policy(
    tier: str,
    payload: PolicyUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    principal: dict = Depends(require_roles(*POLICY_WRITE_ROLES)),
):
    row = policy_service.update_policy(
        db,
        tier,
        tolerance_minutes=payload.tolerance_minutes,
        escalate_after=payload.escalate_after,
        calibrate_days=payload.calibrate_days,
        note=payload.report_owner_note,
        actor_email=principal["email"],
    )
    audit_service.record(
        db,
        actor_email=principal["email"],
        actor_role=principal["role"],
        action="policy.update",
        entity="sla_policy",
        entity_id=row.tier,
        detail=policy_service.serialize(row),
        ip=request.client.host if request.client else None,
        message=f"更新 {row.tier} 策略：容忍 {row.tolerance_minutes} 分钟 / 连续 {row.escalate_after} 次",
    )
    db.commit()
    return policy_service.serialize(row)


def preview_policies(
    payload: PolicyPreviewRequest,
    request: Request,
    db: Session = Depends(get_db),
    principal: dict = Depends(require_roles(*POLICY_PREVIEW_ROLES)),
):
    result = policy_service.preview(
        db,
        tolerances={
            "P0": payload.p0_tolerance,
            "P1": payload.p1_tolerance,
            "P2": payload.p2_tolerance,
        },
        escalate_after=payload.escalate_after,
    )
    audit_service.record(
        db,
        actor_email=principal["email"],
        actor_role=principal["role"],
        action="policy.preview",
        entity="sla_policy",
        entity_id=None,
        detail={"params": result["params"], "totals": result["totals"]},
        ip=request.client.host if request.client else None,
        message=f"策略试算：预计 {result['totals']['breaches']} 起违约",
    )
    db.commit()
    return result
