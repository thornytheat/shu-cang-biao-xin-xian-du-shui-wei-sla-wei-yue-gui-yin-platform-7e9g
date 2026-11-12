"""幂等 seed：3 账号 / 40 张核心表 / 30 天 × 40 条探测 / 3 条 SLA 策略 / 9 起违约。

自然键：
  users.email
  sla_policies.tier
  table_assets.code
  freshness_probes(table_id, probe_date)
  sla_breaches(table_id, breach_date)

重复执行不新增、不覆盖用户改过的数据（策略/表/处置态只在缺失时写入）。
所有数值来自 fixture_source 的确定性公式，不使用 random，因此两次 seed 完全一致。
"""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from scripts.demo_config import (
    BRAND,
    DEMO_PASSWORD,
    DEMO_USERS,
    HISTORY_DAYS,
    POLICY_SPECS,
    TABLES,
)
from src.config.database import session_scope
from src.models.audit import AuditLog
from src.models.freshness_probe import FreshnessProbe
from src.models.sla_breach import SlaBreach
from src.models.sla_policy import SlaPolicy
from src.models.table_asset import TableAsset
from src.models.user import User
from src.services import breach_service, fixture_source
from src.utils.security import hash_password
from src.utils.timeutil import business_now, business_today


def ensure_users(db: Session) -> dict[str, User]:
    users: dict[str, User] = {}
    for email, display_name, role, team in DEMO_USERS:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                email=email,
                password_hash=hash_password(DEMO_PASSWORD),
                display_name=display_name,
                role=role,
                team=team,
            )
            db.add(user)
            db.flush()
        users[email] = user
    return users


def ensure_policies(db: Session) -> int:
    for tier, tolerance, escalate_after, note in POLICY_SPECS:
        policy = db.scalar(select(SlaPolicy).where(SlaPolicy.tier == tier))
        if policy is None:
            db.add(
                SlaPolicy(
                    tier=tier,
                    tolerance_minutes=tolerance,
                    escalate_after=escalate_after,
                    calibrate_days=30,
                    report_owner_note=note,
                    updated_by="seed@freshsla.io",
                )
            )
    db.flush()
    return int(db.scalar(select(func.count(SlaPolicy.id))) or 0)


def ensure_tables(db: Session) -> dict[str, TableAsset]:
    tables: dict[str, TableAsset] = {}
    for spec in TABLES:
        table = db.scalar(select(TableAsset).where(TableAsset.code == spec.code))
        if table is None:
            table = TableAsset(
                code=spec.code,
                name=spec.name,
                layer=spec.layer,
                tier=spec.tier,
                schedule_cron=spec.cron,
                expected_ready_clock=spec.ready_clock,
                upstream_code=spec.upstream,
                report_count=spec.report_count,
                owner_team=spec.owner_team,
                size_gb=spec.size_gb,
                owner_note=spec.note or None,
                is_active=True,
            )
            db.add(table)
            db.flush()
        tables[spec.code] = table
    return tables


def ensure_probes(db: Session, tables: dict[str, TableAsset]) -> int:
    """近 30 天（不含今天）的历史探测：40 表 × 30 天 = 1200 条，其中 24 条缺失。"""
    today = business_today()
    existing_keys: set[tuple[int, object]] = set()
    for row in db.execute(
        select(FreshnessProbe.table_id, FreshnessProbe.probe_date).where(
            FreshnessProbe.probe_date >= today - timedelta(days=HISTORY_DAYS)
        )
    ).all():
        existing_keys.add((row[0], row[1]))

    created = 0
    for spec in TABLES:
        table = tables[spec.code]
        for offset in range(-HISTORY_DAYS, 0):
            probe_date = today + timedelta(days=offset)
            if (table.id, probe_date) in existing_keys:
                continue
            values = fixture_source.build_probe_values(spec, probe_date, offset)
            db.add(
                FreshnessProbe(
                    table_id=table.id,
                    probe_date=probe_date,
                    partition_dt=probe_date.isoformat(),
                    expected_ready_at=values.expected_ready_at,
                    actual_ready_at=values.actual_ready_at,
                    delay_seconds=values.delay_seconds,
                    raw_offset_seconds=values.raw_offset_seconds,
                    is_early=values.is_early,
                    status=values.status,
                    source="seed",
                    note=values.note or None,
                )
            )
            created += 1
    db.flush()
    return created


def ensure_breaches(db: Session) -> int:
    """用同一套检测算法建立初始台账（含今天的计划值，探测未跑时用 fixture 计划）。"""
    breach_service.detect(db, days=30, include_planned=True)
    return int(db.scalar(select(func.count(SlaBreach.id))) or 0)


SEED_AUDIT = [
    ("seed:audit:1", "admin@freshsla.io", "admin", "probe.run", "freshness_probe",
     "首次巡检（种子）", {"created": 40, "missing": 2, "source": "seed"}),
    ("seed:audit:2", "ops@freshsla.io", "ops", "breach.detect", "sla_breach",
     "初始违约台账（种子）", {"scanned": 9, "created": 9}),
    ("seed:audit:3", "admin@freshsla.io", "admin", "policy.update", "sla_policy",
     "写入三档 SLA 策略（种子）", {"tiers": ["P0", "P1", "P2"]}),
]


def ensure_audit(db: Session) -> None:
    for key, email, role, action, entity, message, detail in SEED_AUDIT:
        exists = db.scalar(
            select(AuditLog).where(AuditLog.action == action, AuditLog.layer == "domain").limit(1)
        )
        if exists is not None:
            continue
        db.add(
            AuditLog(
                actor_email=email,
                actor_role=role,
                action=action,
                entity=entity,
                entity_id=key,
                layer="domain",
                detail=detail,
                message=message,
                created_at=business_now(),
            )
        )
    db.flush()


def collect_counts(db: Session) -> dict[str, int]:
    return {
        "tables": int(db.scalar(select(func.count(TableAsset.id))) or 0),
        "probes": int(
            db.scalar(select(func.count(FreshnessProbe.id)).where(FreshnessProbe.source == "seed")) or 0
        ),
        "policies": int(db.scalar(select(func.count(SlaPolicy.id))) or 0),
        "breaches": int(db.scalar(select(func.count(SlaBreach.id))) or 0),
        "users": int(db.scalar(select(func.count(User.id))) or 0),
    }


def seed_all(verbose: bool = True) -> dict[str, int]:
    with session_scope() as db:
        ensure_users(db)
        ensure_policies(db)
        tables = ensure_tables(db)
        created_probes = ensure_probes(db, tables)
        ensure_breaches(db)
        ensure_audit(db)
        db.flush()
        counts = collect_counts(db)

    if verbose:
        print(f"[SEED] brand={BRAND} probe rows inserted this run: {created_probes}", flush=True)
        print(
            "[SEED] demo accounts: admin@freshsla.io / ops@freshsla.io / viewer@freshsla.io"
            f" password={DEMO_PASSWORD}",
            flush=True,
        )
        print(
            f"SEED_SUMMARY brand={BRAND} "
            f"tables={counts['tables']} "
            f"probes={counts['probes']} "
            f"policies={counts['policies']} "
            f"breaches={counts['breaches']} "
            f"users={counts['users']}",
            flush=True,
        )
    return counts


if __name__ == "__main__":  # pragma: no cover
    seed_all()
