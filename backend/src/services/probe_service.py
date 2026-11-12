"""探测服务：执行一次"新鲜度巡检"，把 fixture 就绪事件落成 FreshnessProbe。"""
from __future__ import annotations

import time
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.freshness_probe import FreshnessProbe
from src.models.probe_run import ProbeRun
from src.models.table_asset import TableAsset
from src.constants.enums import Grade, ProbeStatus
from src.services import fixture_source
from src.utils.logger import get_logger
from src.utils.timeutil import business_today

logger = get_logger("probe")


def run(db: Session, *, actor_email: str, run_date: date | None = None, trigger_source: str = "api") -> dict:
    started = time.time()
    target = run_date or business_today()
    tables = list(db.scalars(select(TableAsset).where(TableAsset.is_active.is_(True)).order_by(TableAsset.code)))
    today = business_today()
    offset = (target - today).days

    created = updated = 0
    missing = late = early = ok = 0
    for table in tables:
        values = fixture_source.build_probe_values(fixture_source.spec_of(table.code), target, offset)
        existing = db.scalar(
            select(FreshnessProbe).where(
                FreshnessProbe.table_id == table.id,
                FreshnessProbe.probe_date == target,
            )
        )
        payload = {
            "expected_ready_at": values.expected_ready_at,
            "actual_ready_at": values.actual_ready_at,
            "delay_seconds": values.delay_seconds,
            "raw_offset_seconds": values.raw_offset_seconds,
            "is_early": values.is_early,
            "status": values.status,
            "note": values.note,
        }
        if existing is None:
            db.add(
                FreshnessProbe(
                    table_id=table.id,
                    probe_date=target,
                    partition_dt=target.isoformat(),
                    source="probe",
                    **payload,
                )
            )
            created += 1
        else:
            for key, value in payload.items():
                setattr(existing, key, value)
            existing.source = "probe"
            updated += 1

        if values.status == ProbeStatus.MISSING.value:
            missing += 1
        elif values.status == ProbeStatus.LATE.value:
            late += 1
        elif values.status == ProbeStatus.EARLY.value:
            early += 1
        else:
            ok += 1

    db.flush()

    red_tables = _red_tables(db, tables, target)
    duration_ms = int((time.time() - started) * 1000)
    run_row = db.scalar(select(ProbeRun).where(ProbeRun.run_date == target))
    if run_row is None:
        run_row = ProbeRun(run_date=target, triggered_by=actor_email, trigger_source=trigger_source)
        db.add(run_row)
    run_row.triggered_by = actor_email
    run_row.trigger_source = trigger_source
    run_row.created_count = created
    run_row.missing_count = missing
    run_row.unknown_count = missing
    run_row.late_count = late
    run_row.red_tables = red_tables
    run_row.duration_ms = duration_ms
    db.flush()

    logger.info(
        "[PROBE] date=%s created=%s missing=%s late=%s red=%s in %sms",
        target, created, missing, late, len(red_tables), duration_ms,
    )
    return {
        "run_date": target.isoformat(),
        "created": created,
        "updated": updated,
        "total": created + updated,
        "missing": missing,
        "unknown": missing,
        "late": late,
        "early": early,
        "ok": ok,
        "red_tables": red_tables,
        "red_count": len(red_tables),
        "duration_ms": duration_ms,
        "waterline": target.isoformat(),
    }


def _red_tables(db: Session, tables: list[TableAsset], target: date) -> list[str]:
    """运行后即时判级：只针对本次巡检日，取当日延迟与该表基线分位比较。"""
    from src.services import freshness_service

    tolerances = freshness_service.policy_map(db)
    reds: list[str] = []
    for table in tables:
        probes = freshness_service.probes_for_table(db, table.id)
        probes = [probe for probe in probes if probe.probe_date <= target]
        payload = freshness_service.evaluate(probes, tolerances.get(table.tier, 60))
        if payload["grade"] == Grade.RED.value:
            reds.append(table.code)
    return sorted(reds)


def latest_run(db: Session) -> ProbeRun | None:
    return db.scalar(select(ProbeRun).order_by(ProbeRun.run_date.desc()).limit(1))


def serialize_run(run_row: ProbeRun | None) -> dict | None:
    if run_row is None:
        return None
    return {
        "run_date": run_row.run_date.isoformat(),
        "triggered_by": run_row.triggered_by,
        "trigger_source": run_row.trigger_source,
        "created_count": run_row.created_count,
        "missing_count": run_row.missing_count,
        "unknown_count": run_row.unknown_count,
        "late_count": run_row.late_count,
        "red_tables": run_row.red_tables or [],
        "duration_ms": run_row.duration_ms,
        "created_at": run_row.created_at.isoformat(sep=" ") if run_row.created_at else None,
    }


def recent_probes(db: Session, *, table_code: str | None = None, days: int = 14) -> list[dict]:
    stmt = (
        select(FreshnessProbe, TableAsset)
        .join(TableAsset, TableAsset.id == FreshnessProbe.table_id)
        .order_by(FreshnessProbe.probe_date.desc(), TableAsset.code)
    )
    if table_code:
        stmt = stmt.where(TableAsset.code == table_code)
    today = business_today()
    stmt = stmt.where(FreshnessProbe.probe_date >= today - timedelta(days=days))
    rows = []
    for probe, table in db.execute(stmt.limit(200)).all():
        rows.append(
            {
                "id": probe.id,
                "table_code": table.code,
                "table_name": table.name,
                "tier": table.tier,
                "probe_date": probe.probe_date.isoformat(),
                "partition_dt": probe.partition_dt,
                "expected_ready_at": probe.expected_ready_at.isoformat(sep=" "),
                "actual_ready_at": probe.actual_ready_at.isoformat(sep=" ") if probe.actual_ready_at else None,
                "delay_minutes": round(probe.delay_seconds / 60.0, 1) if probe.delay_seconds is not None else None,
                "status": probe.status,
                "is_early": probe.is_early,
            }
        )
    return rows


def status(db: Session) -> dict:
    today = business_today()
    run_row = db.scalar(select(ProbeRun).where(ProbeRun.run_date == today))
    return {
        "today": today.isoformat(),
        "probed_today": run_row is not None,
        "run": serialize_run(run_row),
        "latest": serialize_run(latest_run(db)),
    }
