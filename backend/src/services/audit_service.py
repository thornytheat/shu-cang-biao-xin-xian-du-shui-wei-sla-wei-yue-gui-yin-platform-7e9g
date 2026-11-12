"""审计日志写入：HTTP 层（中间件）与领域动作（controller）共用。"""
from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from src.models.audit import AuditLog


def record(
    db: Session,
    *,
    actor_email: str,
    actor_role: str,
    action: str,
    entity: str,
    entity_id: str | int | None = None,
    detail: dict | None = None,
    layer: str = "domain",
    ip: str | None = None,
    message: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_email=actor_email,
        actor_role=actor_role,
        action=action,
        entity=entity,
        entity_id=None if entity_id is None else str(entity_id),
        layer=layer,
        detail=detail,
        ip=ip,
        message=message,
    )
    db.add(entry)
    return entry


def list_recent(db: Session, limit: int = 40, layer: str | None = None) -> list[AuditLog]:
    stmt = select(AuditLog).order_by(desc(AuditLog.id)).limit(limit)
    if layer:
        stmt = select(AuditLog).where(AuditLog.layer == layer).order_by(desc(AuditLog.id)).limit(limit)
    return list(db.scalars(stmt))


def serialize(entry: AuditLog) -> dict:
    return {
        "id": entry.id,
        "actor_email": entry.actor_email,
        "actor_role": entry.actor_role,
        "action": entry.action,
        "entity": entry.entity,
        "entity_id": entry.entity_id,
        "layer": entry.layer,
        "detail": entry.detail,
        "message": entry.message,
        "created_at": entry.created_at.isoformat(sep=" ") if entry.created_at else None,
    }
