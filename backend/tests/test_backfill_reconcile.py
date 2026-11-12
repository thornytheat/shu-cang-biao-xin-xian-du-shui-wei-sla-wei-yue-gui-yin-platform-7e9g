"""补采迟到对账的端到端回归测试（SQLite 内存库，不连 MySQL / Redis / 网络）。

场景还原需求原文：
  还款事实明细(dwd.loan_repay, P0/容忍 60 分/期望 03:30) 先按 96 分钟延迟判成违约，
  后来才收到 03:30 的就绪事件；补录后重跑检测——
  · 未处置(open)的误违约从待办消失（删除）；
  · 已认领/已复盘的保留处置痕迹并标作废（voided_at + void_reason）；
  · 该日及后续连续天数重算；重复运行不新增记录、不重复升级；
  · 看板/详情/导出与台账同口径（active），作废记录可带痕迹查询。
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from src.models.base import Base
from src.models.audit import AuditLog  # noqa: F401  (注册 mapper)
from src.models.freshness_probe import FreshnessProbe
from src.models.probe_run import ProbeRun  # noqa: F401
from src.models.sla_breach import SlaBreach
from src.models.sla_policy import SlaPolicy
from src.models.table_asset import TableAsset
from src.models.user import User  # noqa: F401
from src.services import breach_service, probe_service
from src.services.export_service import review_markdown
from src.utils.timeutil import business_today, expected_ready_at


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    yield session
    session.close()


@pytest.fixture
def tables(db):
    for tier, tol, esc in (("P0", 60, 3), ("P1", 90, 3), ("P2", 120, 4)):
        db.add(SlaPolicy(tier=tier, tolerance_minutes=tol, escalate_after=esc, calibrate_days=30))
    upstream = TableAsset(
        code="ods.loan_event", name="贷款事件流", layer="ods", tier="P1", schedule_cron="0 1 * * *",
        expected_ready_clock="02:00", upstream_code=None, report_count=4,
        owner_team="数据平台运营组", size_gb=820.5, is_active=True,
    )
    table = TableAsset(
        code="dwd.loan_repay", name="还款事实明细", layer="dwd", tier="P0", schedule_cron="0 3 * * *",
        expected_ready_clock="03:30", upstream_code="ods.loan_event", report_count=7,
        owner_team="数据平台运营组", size_gb=640.3, is_active=True,
    )
    db.add_all([upstream, table])
    db.flush()
    return {"table": table, "upstream": upstream}


def _add_probe(db, tbl, day, delay_min):
    expected = expected_ready_at(day, tbl.expected_ready_clock)
    db.add(FreshnessProbe(
        table_id=tbl.id, probe_date=day, partition_dt=day.isoformat(),
        expected_ready_at=expected,
        actual_ready_at=expected + timedelta(minutes=delay_min),
        delay_seconds=int(delay_min * 60), raw_offset_seconds=int(delay_min * 60),
        is_early=False, status="late" if delay_min > 0 else "ok", source="probe",
    ))


def _ledger(db, table_id):
    return {
        row.breach_date: row
        for row in db.scalars(select(SlaBreach).where(SlaBreach.table_id == table_id))
    }


def _at(day, hour, minute):
    return datetime.combine(day, datetime.min.time()).replace(hour=hour, minute=minute)


@pytest.fixture
def breached(db, tables):
    """-3/-2/-1 天 72/68/75 分 + 今天 96 分（误报），初始检测后 -1 天被认领。"""
    today = business_today()
    table = tables["table"]
    for offset, mins in ((-3, 72), (-2, 68), (-1, 75), (0, 96)):
        _add_probe(db, table, today + timedelta(days=offset), mins)
    _add_probe(db, tables["upstream"], today, 59.5)
    db.flush()
    result = breach_service.detect(db)
    assert result["created"] == 4
    rows = _ledger(db, table.id)
    assert rows[today].consecutive_count == 4
    assert rows[today].severity == "severe"  # 连续 4 天 > escalate_after 3，升一级
    breach_service.claim(db, rows[today - timedelta(days=1)], "ops@freshsla.io")
    return {"today": today, "result": result}


def test_open_false_breach_disappears_after_backfill(db, tables, breached):
    """补录今天 03:30（准点）→ 未处置的误违约从待办删除，历史连续天数不变。"""
    today = breached["today"]
    table = tables["table"]
    res = probe_service.backfill(db, table=table, probe_date=today, actual_ready_at=_at(today, 3, 30))
    assert res["before"]["delay_minutes"] == 96.0
    assert res["after"]["delay_minutes"] == 0.0

    result = breach_service.detect(db)
    assert result["deleted"] == 1 and result["voided"] == 0
    rows = _ledger(db, table.id)
    assert today not in rows  # 待办里已消失
    assert len(rows) == 3
    assert rows[today - timedelta(days=1)].consecutive_count == 3  # 历史连续天数不受今天影响


def test_claimed_false_breach_is_voided_with_traces(db, tables, breached):
    """补录 -1 天准点 → 已认领的误违约标作废，认领痕迹保留，汇总/查询口径一致。"""
    today = breached["today"]
    day_m1 = today - timedelta(days=1)
    table = tables["table"]
    probe_service.backfill(db, table=table, probe_date=day_m1, actual_ready_at=_at(day_m1, 3, 30))
    result = breach_service.detect(db)
    assert result["voided"] == 1 and result["deleted"] == 0

    row = _ledger(db, table.id)[day_m1]
    assert row.voided_at is not None
    assert "75.0" in (row.void_reason or "")  # 作废原因保留原延迟
    assert row.handling_status == "claimed" and row.claimed_by == "ops@freshsla.io"  # 处置痕迹保留

    summary = breach_service.summary(db)
    assert summary["total"] == 3 and summary["voided"] == 1  # 看板口径：只算有效违约
    assert len(breach_service.query(db)) == 3  # 台账默认不含作废
    assert len(breach_service.query(db, include_voided=True)) == 4  # 作废记录可带痕迹查询

    md, count, _ = review_markdown(db)
    assert count == 3  # 导出与台账一致（只含有效违约）
    assert "已作废" in md


def test_repeated_detect_is_idempotent(db, tables, breached):
    """重复运行：不新增记录、不重复作废、不重复升级。"""
    today = breached["today"]
    day_m1 = today - timedelta(days=1)
    table = tables["table"]
    probe_service.backfill(db, table=table, probe_date=today, actual_ready_at=_at(today, 3, 30))
    probe_service.backfill(db, table=table, probe_date=day_m1, actual_ready_at=_at(day_m1, 3, 30))
    breach_service.detect(db)
    stamp = _ledger(db, table.id)[day_m1].voided_at

    again = breach_service.detect(db)
    assert again["created"] == 0
    assert again["voided"] == 0 and again["deleted"] == 0 and again["revived"] == 0
    assert _ledger(db, table.id)[day_m1].voided_at == stamp  # 不重复作废
    severities = [row.severity for row in _ledger(db, table.id).values()]
    assert severities == ["warning"] * len(severities)  # 不重复升级


def test_voided_record_revives_when_breach_returns(db, tables, breached):
    """作废后补录值又被修正回迟到 → 记录复活，连续天数重算。"""
    today = breached["today"]
    day_m1 = today - timedelta(days=1)
    table = tables["table"]
    probe_service.backfill(db, table=table, probe_date=day_m1, actual_ready_at=_at(day_m1, 3, 30))
    breach_service.detect(db)
    assert _ledger(db, table.id)[day_m1].voided_at is not None

    probe_service.backfill(db, table=table, probe_date=day_m1, actual_ready_at=_at(day_m1, 4, 45))
    result = breach_service.detect(db)
    assert result["revived"] == 1
    row = _ledger(db, table.id)[day_m1]
    assert row.voided_at is None and row.void_reason is None
    assert row.consecutive_count == 3 and row.delay_seconds == 75 * 60


def test_probe_run_does_not_overwrite_manual_backfill(db, tables, breached):
    """巡检保留人工补录：重复跑探测不把补录值冲掉，也不重新判违约。"""
    today = breached["today"]
    table = tables["table"]
    probe_service.backfill(db, table=table, probe_date=today, actual_ready_at=_at(today, 3, 30))
    breach_service.detect(db)

    run = probe_service.run(db, actor_email="ops@freshsla.io")
    assert run["backfilled"] == 1
    probe = db.scalar(
        select(FreshnessProbe).where(
            FreshnessProbe.table_id == table.id, FreshnessProbe.probe_date == today
        )
    )
    assert probe.source == "backfill" and probe.delay_seconds == 0
    result = breach_service.detect(db)
    assert result["created"] == 0
    assert today not in _ledger(db, table.id)


def test_backfill_rejects_future_partition_and_huge_offset(db, tables):
    """防呆：未来分区 / 与期望就绪相差超过 48 小时的补录被拒绝。"""
    from src.utils.errors import AppError

    today = business_today()
    table = tables["table"]
    with pytest.raises(AppError):
        probe_service.backfill(
            db, table=table, probe_date=today + timedelta(days=1), actual_ready_at=_at(today, 3, 30)
        )
    with pytest.raises(AppError):
        probe_service.backfill(
            db, table=table, probe_date=today, actual_ready_at=_at(today, 3, 30) + timedelta(hours=49)
        )
