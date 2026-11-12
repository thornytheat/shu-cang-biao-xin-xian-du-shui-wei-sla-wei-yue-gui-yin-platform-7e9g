"""控制器：表资产 + 看板（页面 2/3 的数据来源）。"""
from __future__ import annotations

from fastapi import Depends, Query, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.middlewares.rbac import principal_of, require_roles
from src.services import audit_service, freshness_service, table_service
from src.constants.roles import TABLE_WRITE_ROLES
from src.schemas.table import TableUpdateRequest


def list_tables(
    request: Request,
    layer: str | None = Query(default=None, pattern="^(ods|dwd|dws|ads)$"),
    tier: str | None = Query(default=None, pattern="^(P0|P1|P2)$"),
    q: str | None = Query(default=None, max_length=64),
    db: Session = Depends(get_db),
    principal: dict = Depends(principal_of),
):
    tables = table_service.list_tables(db, layer=layer, tier=tier, keyword=q)
    tolerances = freshness_service.policy_map(db)
    return {
        "items": [
            {
                **table_service.summarize(table),
                "tolerance_minutes": tolerances.get(table.tier, 60),
            }
            for table in tables
        ],
        "total": len(tables),
        "filters": {"layer": layer, "tier": tier, "q": q},
    }


def get_table(
    code: str,
    db: Session = Depends(get_db),
    principal: dict = Depends(principal_of),
):
    table = table_service.get_by_code(db, code)
    payload = freshness_service.describe(db, table)
    return payload


def table_freshness(
    code: str,
    days: int = Query(default=30, ge=7, le=90),
    db: Session = Depends(get_db),
    principal: dict = Depends(principal_of),
):
    table = table_service.get_by_code(db, code)
    return freshness_service.series(db, table, days)


def update_table(
    code: str,
    payload: TableUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    principal: dict = Depends(require_roles(*TABLE_WRITE_ROLES)),
):
    table = table_service.get_by_code(db, code)
    before = table_service.summarize(table)
    table_service.update_table(
        db,
        table,
        tier=payload.tier,
        expected_ready_clock=payload.expected_ready_clock,
        report_count=payload.report_count,
        owner_team=payload.owner_team,
        owner_note=payload.owner_note,
    )
    audit_service.record(
        db,
        actor_email=principal["email"],
        actor_role=principal["role"],
        action="table.update",
        entity="table_asset",
        entity_id=table.code,
        detail={"before": before, "after": table_service.summarize(table)},
        ip=request.client.host if request.client else None,
    )
    db.commit()
    return freshness_service.describe(db, table)


def board(
    layer: str | None = Query(default=None, pattern="^(ods|dwd|dws|ads)$"),
    q: str | None = Query(default=None, max_length=64),
    db: Session = Depends(get_db),
    principal: dict = Depends(principal_of),
):
    return freshness_service.board(db, layer=layer, keyword=q)


def upstream_hint(db: Session, code: str) -> dict:
    table = table_service.get_by_code(db, code)
    return {
        "chain": [
            {"code": node.code, "name": node.name, "tier": node.tier}
            for node in table_service.full_path(db, table)
        ]
    }
