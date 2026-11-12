"""控制器：探测运行与探测记录。"""
from __future__ import annotations

from fastapi import Depends, Query, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.constants.roles import PROBE_RUN_ROLES
from src.middlewares.rbac import principal_of, require_roles
from src.services import audit_service, breach_service, probe_service


def run_probes(
    request: Request,
    db: Session = Depends(get_db),
    principal: dict = Depends(require_roles(*PROBE_RUN_ROLES)),
):
    result = probe_service.run(db, actor_email=principal["email"], trigger_source="api")
    detection = breach_service.detect(db)
    summary = breach_service.summary(db)
    audit_service.record(
        db,
        actor_email=principal["email"],
        actor_role=principal["role"],
        action="probe.run",
        entity="freshness_probe",
        entity_id=result["run_date"],
        detail={
            "created": result["created"],
            "missing": result["missing"],
            "backfilled": result["backfilled"],
            "red_tables": result["red_tables"],
            "breaches_created": detection["created"],
            "breaches_updated": detection["updated"],
            "breaches_voided": detection["voided"],
            "breaches_deleted": detection["deleted"],
        },
        ip=request.client.host if request.client else None,
        message=f"巡检 {result['run_date']}：新增 {result['created']} 条探测，缺失 {result['missing']} 条",
    )
    db.commit()
    return {**result, "breaches": {**detection, "summary": summary}}


def probe_status(db: Session = Depends(get_db), principal: dict = Depends(principal_of)):
    return probe_service.status(db)


def list_probes(
    table: str | None = Query(default=None, max_length=80),
    days: int = Query(default=14, ge=1, le=60),
    db: Session = Depends(get_db),
    principal: dict = Depends(principal_of),
):
    rows = probe_service.recent_probes(db, table_code=table, days=days)
    return {"items": rows, "total": len(rows)}
