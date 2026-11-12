"""表资产服务：查询、详情、上游链解析、写入。"""
from __future__ import annotations

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session

from src.constants.enums import Layer, Tier
from src.models.table_asset import TableAsset
from src.utils.errors import AppError

MAX_CHAIN_DEPTH = 6


def base_query() -> Select:
    return select(TableAsset).where(TableAsset.is_active.is_(True))


def list_tables(
    db: Session,
    *,
    layer: str | None = None,
    tier: str | None = None,
    keyword: str | None = None,
) -> list[TableAsset]:
    stmt = base_query()
    if layer:
        stmt = stmt.where(TableAsset.layer == layer)
    if tier:
        stmt = stmt.where(TableAsset.tier == tier)
    if keyword:
        like = f"%{keyword.strip()}%"
        stmt = stmt.where(or_(TableAsset.code.like(like), TableAsset.name.like(like)))
    stmt = stmt.order_by(TableAsset.layer, TableAsset.code)
    return list(db.scalars(stmt))


def get_by_code(db: Session, code: str) -> TableAsset:
    table = db.scalar(select(TableAsset).where(TableAsset.code == code))
    if table is None:
        raise AppError("NOT_FOUND", 404, detail={"code": code})
    return table


def get_by_id(db: Session, table_id: int) -> TableAsset:
    table = db.get(TableAsset, table_id)
    if table is None:
        raise AppError("NOT_FOUND", 404, detail={"table_id": table_id})
    return table


def upstream_chain(db: Session, table: TableAsset) -> list[TableAsset]:
    """按链路顺序（上游 → 直接上游）返回上游表，防环、限深。"""
    chain: list[TableAsset] = []
    seen = {table.code}
    current = table
    while current.upstream_code and len(chain) < MAX_CHAIN_DEPTH:
        upstream = db.scalar(select(TableAsset).where(TableAsset.code == current.upstream_code))
        if upstream is None or upstream.code in seen:
            break
        chain.append(upstream)
        seen.add(upstream.code)
        current = upstream
    return chain


def downstream_tables(db: Session, table: TableAsset) -> list[TableAsset]:
    stmt = select(TableAsset).where(TableAsset.upstream_code == table.code).order_by(TableAsset.code)
    return list(db.scalars(stmt))


def full_path(db: Session, table: TableAsset) -> list[TableAsset]:
    """根 → 目标 的完整链路（含目标），用于详情页横向展示。"""
    chain = upstream_chain(db, table)
    return list(reversed(chain)) + [table]


def update_table(
    db: Session,
    table: TableAsset,
    *,
    tier: str | None = None,
    expected_ready_clock: str | None = None,
    report_count: int | None = None,
    owner_team: str | None = None,
    owner_note: str | None = None,
) -> TableAsset:
    if tier is not None:
        if tier not in {item.value for item in Tier}:
            raise AppError("VALIDATION", 422, detail={"tier": tier})
        table.tier = tier
    if expected_ready_clock is not None:
        _validate_clock(expected_ready_clock)
        table.expected_ready_clock = expected_ready_clock
    if report_count is not None:
        if report_count < 0 or report_count > 999:
            raise AppError("VALIDATION", 422, detail={"report_count": report_count})
        table.report_count = report_count
    if owner_team is not None:
        table.owner_team = owner_team.strip()[:64]
    if owner_note is not None:
        table.owner_note = owner_note.strip() or None
    db.flush()
    return table


def _validate_clock(value: str) -> None:
    parts = value.split(":")
    if len(parts) != 2:
        raise AppError("VALIDATION", 422, detail={"expected_ready_clock": value})
    try:
        hour, minute = int(parts[0]), int(parts[1])
    except ValueError as exc:
        raise AppError("VALIDATION", 422, detail={"expected_ready_clock": value}) from exc
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise AppError("VALIDATION", 422, detail={"expected_ready_clock": value})


def layer_options() -> list[dict]:
    return [{"value": item.value, "label": item.value.upper()} for item in Layer]


def summarize(table: TableAsset) -> dict:
    return {
        "code": table.code,
        "name": table.name,
        "layer": table.layer,
        "tier": table.tier,
        "schedule_cron": table.schedule_cron,
        "expected_ready_clock": table.expected_ready_clock,
        "upstream_code": table.upstream_code,
        "report_count": table.report_count,
        "owner_team": table.owner_team,
        "size_gb": round(table.size_gb, 2),
        "owner_note": table.owner_note,
    }
