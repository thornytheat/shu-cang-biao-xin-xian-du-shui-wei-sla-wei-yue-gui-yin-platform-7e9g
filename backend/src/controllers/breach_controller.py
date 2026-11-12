"""控制器：违约台账、检测、认领、复盘。"""
from __future__ import annotations

from fastapi import Depends, Query, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.constants.roles import BREACH_ACTION_ROLES

# 归因重算只允许平台负责人（保守口径）
BREACH_ADMIN_ROLES = ("admin",)
from src.middlewares.rbac import principal_of, require_roles
from src.schemas.breach import BreachActionRequest, DetectRequest
from src.services import audit_service, breach_service


def list_breaches(
    severity: str | None = Query(default=None, pattern="^(warning|severe|escalated)$"),
    status: str | None = Query(default=None, pattern="^(open|claimed|resolved)$"),
    tier: str | None = Query(default=None, pattern="^(P0|P1|P2)$"),
    q: str | None = Query(default=None, max_length=64),
    limit: int = Query(default=100, ge=1, le=300),
    db: Session = Depends(get_db),
    principal: dict = Depends(principal_of),
):
    rows = breach_service.query(db, severity=severity, status=status, tier=tier, keyword=q, limit=limit)
    return {
        "items": [breach_service.serialize(breach, table) for breach, table in rows],
        "summary": breach_service.summary(db),
        "filters": {"severity": severity, "status": status, "tier": tier, "q": q},
    }


def get_breach(
    breach_id: int,
    db: Session = Depends(get_db),
    principal: dict = Depends(principal_of),
):
    breach, table = breach_service.get(db, breach_id)
    payload = breach_service.serialize(breach, table)
    payload["chain"] = breach.attribution_detail or {}
    return payload


def detect_breaches(
    request: Request,
    payload: DetectRequest,
    db: Session = Depends(get_db),
    principal: dict = Depends(require_roles(*BREACH_ACTION_ROLES)),
):
    result = breach_service.detect(
        db, days=payload.days, include_planned=payload.include_planned
    )
    summary = breach_service.summary(db)
    audit_service.record(
        db,
        actor_email=principal["email"],
        actor_role=principal["role"],
        action="breach.detect",
        entity="sla_breach",
        entity_id=None,
        detail={"window_days": payload.days, **{k: result[k] for k in ("scanned", "created", "updated")}},
        ip=request.client.host if request.client else None,
        message=f"违约检测：扫描 {result['scanned']} 起，新增 {result['created']} 起",
    )
    db.commit()
    return {**result, "summary": summary}


def claim_breach(
    breach_id: int,
    request: Request,
    payload: BreachActionRequest | None = None,
    db: Session = Depends(get_db),
    principal: dict = Depends(require_roles(*BREACH_ACTION_ROLES)),
):
    breach, table = breach_service.get(db, breach_id)
    breach_service.claim(db, breach, principal["email"])
    if payload and payload.note:
        breach.root_note = payload.note.strip()
    audit_service.record(
        db,
        actor_email=principal["email"],
        actor_role=principal["role"],
        action="breach.claim",
        entity="sla_breach",
        entity_id=breach.id,
        detail={"table": table.code, "breach_date": breach.breach_date.isoformat()},
        ip=request.client.host if request.client else None,
        message=f"认领违约：{table.code} {breach.breach_date}",
    )
    db.commit()
    return breach_service.serialize(breach, table)


def resolve_breach(
    breach_id: int,
    request: Request,
    payload: BreachActionRequest,
    db: Session = Depends(get_db),
    principal: dict = Depends(require_roles(*BREACH_ACTION_ROLES)),
):
    breach, table = breach_service.get(db, breach_id)
    breach_service.resolve(db, breach, principal["email"], payload.note)
    audit_service.record(
        db,
        actor_email=principal["email"],
        actor_role=principal["role"],
        action="breach.resolve",
        entity="sla_breach",
        entity_id=breach.id,
        detail={
            "table": table.code,
            "breach_date": breach.breach_date.isoformat(),
            "note": payload.note,
        },
        ip=request.client.host if request.client else None,
        message=f"复盘完成：{table.code} {breach.breach_date}",
    )
    db.commit()
    return breach_service.serialize(breach, table)


def recompute_attribution(
    breach_id: int,
    request: Request,
    db: Session = Depends(get_db),
    principal: dict = Depends(require_roles(*BREACH_ADMIN_ROLES)),
):
    breach, table = breach_service.get(db, breach_id)
    attribution = breach_service.attribute(
        db, table, breach.breach_date, breach.delay_seconds, table.report_count
    )
    breach.primary_cause = attribution["primary_cause"]
    breach.cause_contribution_pct = attribution["cause_contribution_pct"]
    breach.impact_score = attribution["impact_score"]
    breach.suggested_action = attribution["suggested_action"]
    breach.attribution_detail = attribution["detail"]
    audit_service.record(
        db,
        actor_email=principal["email"],
        actor_role=principal["role"],
        action="breach.attribution",
        entity="sla_breach",
        entity_id=breach.id,
        detail={"primary_cause": breach.primary_cause, "impact_score": breach.impact_score},
        ip=request.client.host if request.client else None,
    )
    db.commit()
    return breach_service.serialize(breach, table)


def summary(db: Session = Depends(get_db), principal: dict = Depends(principal_of)):
    return breach_service.summary(db)

