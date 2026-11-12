"""算法 1：延迟分位与三色灯判级。

口径（README / TESTING 同步，QA 可复核）：
  delay = 实际就绪 − 期望就绪（秒）；负值截 0 并标 early。
  基线 = 最近一次探测之前、连续 CALIBRATION_DAYS(30) 天内的非缺失探测。
  分位 = 基线延迟的线性插值分位（P50 / P90 / P95，等价 Excel PERCENTILE.INC）。
  判级 = green  delay ≤ P50
         yellow P50 < delay ≤ P90
         red    delay > P90
         探测缺失 / 无基线 → unknown（不参与分位与判级）
"""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config.settings import settings
from src.constants.enums import Grade, ProbeStatus, Tier
from src.constants.limits import DEFAULT_TOLERANCE
from src.models.freshness_probe import FreshnessProbe
from src.models.sla_policy import SlaPolicy
from src.models.table_asset import TableAsset
from src.services import freshness_core, table_service


def policy_map(db: Session) -> dict[str, int]:
    rows = list(db.scalars(select(SlaPolicy)))
    mapping = {row.tier: row.tolerance_minutes for row in rows}
    for tier in Tier:
        mapping.setdefault(tier.value, DEFAULT_TOLERANCE[tier.value])
    return mapping


def load_probes(
    db: Session,
    *,
    table_ids: list[int] | None = None,
    start=None,
    end=None,
) -> dict[int, list[FreshnessProbe]]:
    stmt = select(FreshnessProbe)
    if table_ids is not None:
        stmt = stmt.where(FreshnessProbe.table_id.in_(table_ids))
    if start is not None:
        stmt = stmt.where(FreshnessProbe.probe_date >= start)
    if end is not None:
        stmt = stmt.where(FreshnessProbe.probe_date <= end)
    stmt = stmt.order_by(FreshnessProbe.table_id, FreshnessProbe.probe_date)
    grouped: dict[int, list[FreshnessProbe]] = {}
    for probe in db.scalars(stmt):
        grouped.setdefault(probe.table_id, []).append(probe)
    return grouped


def probes_for_table(db: Session, table_id: int, days: int | None = None) -> list[FreshnessProbe]:
    calibrate = days or settings.calibration_days
    stmt = (
        select(FreshnessProbe)
        .where(FreshnessProbe.table_id == table_id)
        .order_by(FreshnessProbe.probe_date)
    )
    rows = list(db.scalars(stmt))
    if not rows:
        return []
    cutoff = rows[-1].probe_date - timedelta(days=calibrate + 1)
    return [row for row in rows if row.probe_date >= cutoff]


def _probe_row(probe: FreshnessProbe) -> dict:
    """ORM -> 纯函数内核需要的普通 dict（不把 Session 传进算法层）。"""
    return {
        "probe_date": probe.probe_date,
        "partition_dt": probe.partition_dt,
        "expected_ready_at": probe.expected_ready_at,
        "actual_ready_at": probe.actual_ready_at,
        "delay_seconds": probe.delay_seconds,
        "status": probe.status,
        "is_early": probe.is_early,
    }


def grade_of(delay_minutes: float | None, p50: float | None, p90: float | None) -> str:
    return freshness_core.grade_of(delay_minutes, p50, p90)


def evaluate(probes: list[FreshnessProbe], tolerance_minutes: int, calibrate_days: int | None = None) -> dict:
    """取数包装：把 ORM 探测行转成 dict 后交给纯函数内核计算。"""
    calibrate = calibrate_days or settings.calibration_days
    return freshness_core.evaluate(
        [_probe_row(probe) for probe in probes],
        tolerance_minutes,
        calibrate,
    )


def describe(db: Session, table: TableAsset, tolerances: dict[str, int] | None = None) -> dict:
    tolerances = tolerances or policy_map(db)
    probes = probes_for_table(db, table.id)
    payload = evaluate(probes, tolerances.get(table.tier, DEFAULT_TOLERANCE[table.tier]))
    return {**table_service.summarize(table), **payload}


def board(db: Session, *, layer: str | None = None, keyword: str | None = None) -> dict:
    """看板：一次取全量探测，按 P0/P1/P2 分栏汇总。"""
    tolerances = policy_map(db)
    tables = table_service.list_tables(db, layer=layer, keyword=keyword)
    grouped = load_probes(db, table_ids=[table.id for table in tables])

    rows: list[dict] = []
    for table in tables:
        payload = evaluate(grouped.get(table.id, []), tolerances.get(table.tier, DEFAULT_TOLERANCE[table.tier]))
        rows.append(
            {
                **table_service.summarize(table),
                "code": table.code,
                "tolerance_minutes": payload["tolerance_minutes"],
                "grade": payload["grade"],
                "grade_reason": payload["grade_reason"],
                "delay_minutes": payload["latest"]["delay_minutes"] if payload["latest"] else None,
                "delay_seconds": payload["latest"]["delay_seconds"] if payload["latest"] else None,
                "ratio": payload["latest"]["ratio"] if payload["latest"] else None,
                "probe_date": payload["latest"]["probe_date"] if payload["latest"] else None,
                "status": payload["latest"]["status"] if payload["latest"] else None,
                "is_early": payload["latest"]["is_early"] if payload["latest"] else False,
                "water_pct": payload["water_pct"],
                "percentiles": payload["percentiles"],
                "baseline_days": payload["baseline_days"],
                "missing_in_window": payload["missing_in_window"],
                "on_time_rate": payload["on_time_rate"],
            }
        )

    tiers: dict[str, dict] = {}
    for tier in Tier:
        tier_rows = [row for row in rows if row["tier"] == tier.value]
        counters = {grade.value: 0 for grade in Grade}
        for row in tier_rows:
            counters[row["grade"]] = counters.get(row["grade"], 0) + 1
        tiers[tier.value] = {
            "tier": tier.value,
            "tolerance_minutes": tolerances.get(tier.value, DEFAULT_TOLERANCE[tier.value]),
            "total": len(tier_rows),
            "counters": counters,
            "red_tables": [row["code"] for row in tier_rows if row["grade"] == Grade.RED.value],
            "rows": sorted(tier_rows, key=lambda row: (-(row["water_pct"] or 0), row["code"])),
        }

    latest_dates = sorted({row["probe_date"] for row in rows if row["probe_date"]})
    return {
        "tiers": tiers,
        "totals": {
            "tables": len(rows),
            "red": sum(1 for row in rows if row["grade"] == Grade.RED.value),
            "yellow": sum(1 for row in rows if row["grade"] == Grade.YELLOW.value),
            "green": sum(1 for row in rows if row["grade"] == Grade.GREEN.value),
            "unknown": sum(1 for row in rows if row["grade"] == Grade.UNKNOWN.value),
        },
        "waterline": latest_dates[-1] if latest_dates else None,
        "calibration_days": settings.calibration_days,
    }


def series(db: Session, table: TableAsset, days: int | None = None) -> dict:
    """详情页：近 30 天 + 今日的延迟序列、分位与违约日标记。"""
    calibrate = days or settings.calibration_days
    tolerances = policy_map(db)
    tolerance = tolerances.get(table.tier, DEFAULT_TOLERANCE[table.tier])
    probes = _probes_window(db, table.id, calibrate)
    evaluated = evaluate(probes, tolerance)
    ordered = sorted(probes, key=lambda row: row.probe_date)
    points = []
    for probe in ordered[-calibrate - 1 :]:
        delay_minutes = probe.delay_seconds / 60.0 if probe.delay_seconds is not None else None
        points.append(
            {
                "probe_date": probe.probe_date.isoformat(),
                "partition_dt": probe.partition_dt,
                "delay_minutes": delay_minutes,
                "status": probe.status,
                "is_early": probe.is_early,
                "is_missing": probe.status == ProbeStatus.MISSING.value,
                "is_breach": delay_minutes is not None and delay_minutes * 60 > tolerance * 60,
                "expected_ready_at": probe.expected_ready_at.isoformat(sep=" "),
                "actual_ready_at": probe.actual_ready_at.isoformat(sep=" ") if probe.actual_ready_at else None,
            }
        )
    return {
        "table": table_service.summarize(table),
        "evaluation": evaluated,
        "points": points,
        "stats": freshness_core.summarize_points(points, tolerance),
        "chain": _chain_payload(db, table, probes, tolerance),
    }


def _probes_window(db: Session, table_id: int, days: int) -> list[FreshnessProbe]:
    stmt = (
        select(FreshnessProbe)
        .where(FreshnessProbe.table_id == table_id)
        .order_by(FreshnessProbe.probe_date)
    )
    rows = list(db.scalars(stmt))
    if not rows:
        return []
    cutoff = rows[-1].probe_date - timedelta(days=days)
    return [row for row in rows if row.probe_date >= cutoff]


def _chain_payload(db: Session, table: TableAsset, probes: list[FreshnessProbe], tolerance: int) -> dict:
    by_date = {probe.probe_date: probe for probe in probes}
    latest_date = max(by_date) if by_date else None
    upstream = table_service.upstream_chain(db, table)
    nodes = []
    for node in reversed(upstream):
        own = _probe_for(db, node, latest_date)
        nodes.append(
            {
                "code": node.code,
                "name": node.name,
                "layer": node.layer,
                "tier": node.tier,
                "report_count": node.report_count,
                "delay_minutes": (own.delay_seconds / 60.0) if own and own.delay_seconds is not None else None,
                "status": own.status if own else "unknown",
            }
        )
    nodes.append(
        {
            "code": table.code,
            "name": table.name,
            "layer": table.layer,
            "tier": table.tier,
            "report_count": table.report_count,
            "delay_minutes": (probes[-1].delay_seconds / 60.0) if probes and probes[-1].delay_seconds is not None else None,
            "status": probes[-1].status if probes else "unknown",
        }
    )
    downstream = table_service.downstream_tables(db, table)
    return {
        "nodes": nodes,
        "downstream": [{"code": item.code, "name": item.name, "tier": item.tier} for item in downstream],
        "tolerance_minutes": tolerance,
        "probe_date": latest_date.isoformat() if latest_date else None,
    }


def _probe_for(db: Session, table: TableAsset, probe_date) -> FreshnessProbe | None:
    if probe_date is None:
        return None
    return db.scalar(
        select(FreshnessProbe).where(
            FreshnessProbe.table_id == table.id,
            FreshnessProbe.probe_date == probe_date,
        )
    )
