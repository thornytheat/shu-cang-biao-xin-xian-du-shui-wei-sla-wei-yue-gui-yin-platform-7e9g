"""控制器：违约复盘导出（CSV / Markdown）与审计查询。"""
from __future__ import annotations

from urllib.parse import quote

from fastapi import Depends, Query, Request, Response
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.constants.roles import AUDIT_ROLES, EXPORT_ROLES
from src.middlewares.rbac import principal_of, require_roles
from src.services import audit_service, export_service


def _download(content: str, filename: str, media_type: str) -> Response:
    encoded = quote(filename)
    return Response(
        content=content.encode("utf-8"),
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded}",
            "X-Export-Filename": encoded,
        },
    )


def export_breaches_csv(
    request: Request,
    severity: str | None = Query(default=None, pattern="^(warning|severe|escalated)$"),
    status: str | None = Query(default=None, pattern="^(open|claimed|resolved)$"),
    tier: str | None = Query(default=None, pattern="^(P0|P1|P2)$"),
    q: str | None = Query(default=None, max_length=64),
    db: Session = Depends(get_db),
    principal: dict = Depends(require_roles(*EXPORT_ROLES)),
):
    content, rows, filename = export_service.breaches_csv(
        db,
        severity=severity,
        status=status,
        tier=tier,
        keyword=q,
        actor_email=principal["email"],
    )
    audit_service.record(
        db,
        actor_email=principal["email"],
        actor_role=principal["role"],
        action="export.breaches_csv",
        entity="sla_breach",
        entity_id=None,
        detail={"rows": rows, "filename": filename, "filters": {"severity": severity, "status": status}},
        ip=request.client.host if request.client else None,
        message=f"导出违约复盘 CSV：{rows} 行",
    )
    db.commit()
    return _download(content, filename, "text/csv; charset=utf-8")


def export_review_markdown(
    request: Request,
    db: Session = Depends(get_db),
    principal: dict = Depends(require_roles(*EXPORT_ROLES)),
):
    content, rows, filename = export_service.review_markdown(db)
    audit_service.record(
        db,
        actor_email=principal["email"],
        actor_role=principal["role"],
        action="export.review_md",
        entity="sla_breach",
        entity_id=None,
        detail={"rows": rows, "filename": filename},
        ip=request.client.host if request.client else None,
        message=f"导出月度复盘 Markdown：{rows} 行",
    )
    db.commit()
    return _download(content, filename, "text/markdown; charset=utf-8")


def list_audit(
    limit: int = Query(default=40, ge=1, le=200),
    layer: str | None = Query(default=None, pattern="^(http|domain)$"),
    db: Session = Depends(get_db),
    principal: dict = Depends(require_roles(*AUDIT_ROLES)),
):
    rows = audit_service.list_recent(db, limit=limit, layer=layer)
    return {"items": [audit_service.serialize(row) for row in rows], "total": len(rows)}
