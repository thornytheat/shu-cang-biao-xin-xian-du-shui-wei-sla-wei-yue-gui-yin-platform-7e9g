"""算法 2：违约检测与归因。

口径（README / TESTING 同步，QA 可复核）：
  ratio = 延迟秒数 / (容忍分钟 × 60)
  ratio > 1.0 → 违约(warning)；ratio > 2.0 → 严重(severe)
  连续违约：同一张表按自然日连续命中，第 n 天 consecutive = n；
            consecutive > escalate_after(默认 3) 时升级一级（warning→severe→escalated）
  归因：沿上游链逐跳取当日延迟，contribution = 上游延迟 / 本表延迟（上限 100%），
        取贡献最大的上游表为 primary_cause；无上游 → self；全链路无就绪事件 → undetermined
  影响分 impact_score = 0.45×贡献% + 0.35×min(100, 影响报表数×10) + 0.20×min(100, ratio/2×100)
        示例：贡献 62.0% / 7 张报表 / ratio 1.6 → 68.4
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.constants.enums import BreachSeverity, HandlingStatus, ProbeStatus, Tier
from src.constants.limits import (
    BREACH_SCAN_DAYS,
    DEFAULT_ESCALATE_AFTER,
    DEFAULT_TOLERANCE,
    IMPACT_WEIGHT_CONTRIBUTION,
    IMPACT_WEIGHT_REPORTS,
    IMPACT_WEIGHT_SEVERITY,
)
from src.models.freshness_probe import FreshnessProbe
from src.models.sla_breach import SlaBreach
from src.models.sla_policy import SlaPolicy
from src.models.table_asset import TableAsset
from src.services import breach_core, fixture_source, table_service
from src.utils.timeutil import business_now, business_today

SEVERITY_ORDER = breach_core.SEVERITY_ORDER
SEVERITY_LABELS = breach_core.SEVERITY_LABELS


@dataclass
class Candidate:
    table: TableAsset
    breach_date: date
    delay_seconds: int
    tolerance_minutes: int
    ratio: float
    consecutive: int
    probe_id: int | None
    source: str


def policies(db: Session) -> dict[str, SlaPolicy]:
    rows = list(db.scalars(select(SlaPolicy)))
    return {row.tier: row for row in rows}


def severity_for(ratio: float, consecutive: int, escalate_after: int) -> str:
    """兼容包装：实现在纯函数内核 `breach_core.severity_for`。"""
    return breach_core.severity_for(ratio, consecutive, escalate_after)


def compute_impact(contribution_pct: float, reports: int, ratio: float) -> float:
    """兼容包装：实现在纯函数内核 `breach_core.compute_impact`。"""
    return breach_core.compute_impact(contribution_pct, reports, ratio)


def _probe_on(db: Session, table_id: int, probe_date: date) -> FreshnessProbe | None:
    return db.scalar(
        select(FreshnessProbe).where(
            FreshnessProbe.table_id == table_id,
            FreshnessProbe.probe_date == probe_date,
        )
    )


def _node_delay_seconds(db: Session, table: TableAsset, probe_date: date, today: date) -> tuple[int | None, str]:
    probe = _probe_on(db, table.id, probe_date)
    if probe is not None and probe.delay_seconds is not None:
        return probe.delay_seconds, "probe"
    offset = (probe_date - today).days
    planned = fixture_source.planned_delay_seconds_for_code(table.code, offset)
    if planned is None:
        return None, "missing"
    return planned, "fixture"


def attribute(db: Session, table: TableAsset, breach_date: date, delay_seconds: int, impacted_reports: int) -> dict:
    """沿上游链归因，返回 primary_cause / 贡献 / 逐跳明细 / 影响分。"""
    today = business_today()
    upstream = table_service.upstream_chain(db, table)
    chain_nodes: list[dict] = []
    primary_inputs: list[dict] = []

    for node in reversed(upstream):  # 根 → 直接上游
        node_delay, basis = _node_delay_seconds(db, node, breach_date, today)
        contribution = breach_core.contribution_pct(node_delay, delay_seconds)
        primary_inputs.append(
            {
                "code": node.code,
                "contribution_pct": contribution,
                "available": node_delay is not None and delay_seconds > 0,
                "basis": basis,
            }
        )
        chain_nodes.append(
            {
                "code": node.code,
                "name": node.name,
                "layer": node.layer,
                "tier": node.tier,
                "report_count": node.report_count,
                "delay_minutes": round(node_delay / 60.0, 1) if node_delay is not None else None,
                "contribution_pct": contribution,
                "basis": basis,
            }
        )

    resolution = breach_core.resolve_primary(primary_inputs)
    primary = resolution["primary_cause"]
    contribution_pct = resolution["cause_contribution_pct"]
    basis = resolution["basis"]

    ratio = breach_core.ratio_of(delay_seconds, _tolerance_of(db, table), 2)
    score = compute_impact(contribution_pct, impacted_reports, ratio)
    return {
        "primary_cause": primary,
        "cause_contribution_pct": contribution_pct,
        "impact_score": score,
        "suggested_action": build_action(table, primary, contribution_pct, impacted_reports, delay_seconds),
        "detail": {
            "chain": chain_nodes,
            "basis": basis,
            "impact": {
                "contribution_pct": contribution_pct,
                "reports": impacted_reports,
                "ratio": ratio,
                "score": score,
                "weights": {
                    "contribution": IMPACT_WEIGHT_CONTRIBUTION,
                    "reports": IMPACT_WEIGHT_REPORTS,
                    "severity": IMPACT_WEIGHT_SEVERITY,
                },
            },
        },
    }


def _tolerance_of(db: Session, table: TableAsset) -> int:
    policy = db.scalar(select(SlaPolicy).where(SlaPolicy.tier == table.tier))
    if policy is None:
        return DEFAULT_TOLERANCE.get(table.tier, 60)
    return policy.tolerance_minutes


def build_action(
    table: TableAsset,
    primary: str,
    contribution_pct: float,
    reports: int,
    delay_seconds: int,
) -> str:
    """兼容包装：实现在纯函数内核 `breach_core.build_action`。"""
    return breach_core.build_action(
        table.code,
        table.expected_ready_clock,
        primary,
        contribution_pct,
        reports,
        delay_seconds,
    )


def scan(
    db: Session,
    *,
    days: int = BREACH_SCAN_DAYS,
    include_planned: bool = False,
    tolerances: dict[str, int] | None = None,
    escalate_after_override: int | None = None,
) -> list[Candidate]:
    """扫描窗口内的违约候选（按 (表, 日期) 去重，含连续次数）。

    tolerances / escalate_after_override 仅用于"策略试算"，不落库。
    """
    today = business_today()
    policy_rows = policies(db)
    tables = table_service.list_tables(db)
    table_by_id = {table.id: table for table in tables}

    all_probes = list(
        db.scalars(select(FreshnessProbe).order_by(FreshnessProbe.table_id, FreshnessProbe.probe_date))
    )
    latest_date = max((probe.probe_date for probe in all_probes), default=today)
    end = max(latest_date, today) if include_planned else latest_date
    start = end - timedelta(days=days - 1)

    grouped: dict[int, list[FreshnessProbe]] = {}
    for probe in all_probes:
        if start <= probe.probe_date <= end:
            grouped.setdefault(probe.table_id, []).append(probe)

    candidates: list[Candidate] = []
    for table_id, table in table_by_id.items():
        policy = policy_rows.get(table.tier)
        tolerance = policy.tolerance_minutes if policy else DEFAULT_TOLERANCE.get(table.tier, 60)
        if tolerances and table.tier in tolerances:
            tolerance = int(tolerances[table.tier])
        escalate_after = policy.escalate_after if policy else DEFAULT_ESCALATE_AFTER
        if escalate_after_override is not None:
            escalate_after = escalate_after_override
        rows = sorted(grouped.get(table_id, []), key=lambda item: item.probe_date)

        streak = 0
        previous: date | None = None
        seen_dates: set[date] = set()
        for probe in rows:
            seen_dates.add(probe.probe_date)
            if probe.status == ProbeStatus.MISSING.value or probe.delay_seconds is None:
                streak = 0
                previous = probe.probe_date
                continue
            ratio = breach_core.ratio_of(probe.delay_seconds, tolerance)
            if breach_core.is_breach(ratio):
                streak = breach_core.next_streak(previous, probe.probe_date, streak)
                candidates.append(
                    Candidate(
                        table=table,
                        breach_date=probe.probe_date,
                        delay_seconds=probe.delay_seconds,
                        tolerance_minutes=tolerance,
                        ratio=round(ratio, 2),
                        consecutive=streak,
                        probe_id=probe.id,
                        source="probe",
                    )
                )
            else:
                streak = 0
            previous = probe.probe_date

        if include_planned and today not in seen_dates:
            planned = fixture_source.planned_delay_seconds_for_code(table.code, 0)
            if planned is not None:
                ratio = breach_core.ratio_of(planned, tolerance)
                if breach_core.is_breach(ratio):
                    streak = breach_core.next_streak(previous, today, streak)
                    candidates.append(
                        Candidate(
                            table=table,
                            breach_date=today,
                            delay_seconds=planned,
                            tolerance_minutes=tolerance,
                            ratio=round(ratio, 2),
                            consecutive=streak,
                            probe_id=None,
                            source="fixture",
                        )
                    )

    candidates.sort(key=lambda item: (item.breach_date, item.table.code))
    return candidates


def detect(db: Session, *, days: int = BREACH_SCAN_DAYS, include_planned: bool = False) -> dict:
    """检测 + upsert（自然键 table_id + breach_date），保留人工处置字段。"""
    policy_rows = policies(db)
    candidates = scan(db, days=days, include_planned=include_planned)
    created = updated = 0
    severe = escalated = warning = 0

    for candidate in candidates:
        policy = policy_rows.get(candidate.table.tier)
        escalate_after = policy.escalate_after if policy else DEFAULT_ESCALATE_AFTER
        severity = severity_for(candidate.ratio, candidate.consecutive, escalate_after)
        attribution = attribute(
            db,
            candidate.table,
            candidate.breach_date,
            candidate.delay_seconds,
            candidate.table.report_count,
        )

        if severity == BreachSeverity.SEVERE.value:
            severe += 1
        elif severity == BreachSeverity.ESCALATED.value:
            escalated += 1
        else:
            warning += 1

        existing = db.scalar(
            select(SlaBreach).where(
                SlaBreach.table_id == candidate.table.id,
                SlaBreach.breach_date == candidate.breach_date,
            )
        )
        payload = {
            "delay_seconds": candidate.delay_seconds,
            "tolerance_minutes": candidate.tolerance_minutes,
            "ratio": candidate.ratio,
            "severity": severity,
            "consecutive_count": candidate.consecutive,
            "primary_cause": attribution["primary_cause"],
            "cause_contribution_pct": attribution["cause_contribution_pct"],
            "impacted_reports": candidate.table.report_count,
            "impact_score": attribution["impact_score"],
            "suggested_action": attribution["suggested_action"],
            "attribution_detail": attribution["detail"],
            "probe_id": candidate.probe_id,
        }
        if existing is None:
            db.add(SlaBreach(table_id=candidate.table.id, breach_date=candidate.breach_date, **payload))
            created += 1
        else:
            for key, value in payload.items():
                if key == "probe_id" and existing.probe_id is not None:
                    continue
                setattr(existing, key, value)
            updated += 1

    db.flush()
    return {
        "scanned": len(candidates),
        "created": created,
        "updated": updated,
        "total": created + updated,
        "budget": {"warning": warning, "severe": severe, "escalated": escalated},
        "window_days": days,
    }


def query(
    db: Session,
    *,
    severity: str | None = None,
    status: str | None = None,
    tier: str | None = None,
    keyword: str | None = None,
    limit: int = 200,
) -> list[tuple[SlaBreach, TableAsset]]:
    stmt = (
        select(SlaBreach, TableAsset)
        .join(TableAsset, TableAsset.id == SlaBreach.table_id)
        .order_by(SlaBreach.breach_date.desc(), SlaBreach.impact_score.desc())
        .limit(limit)
    )
    if severity:
        stmt = stmt.where(SlaBreach.severity == severity)
    if status:
        stmt = stmt.where(SlaBreach.handling_status == status)
    if tier:
        stmt = stmt.where(TableAsset.tier == tier)
    if keyword:
        like = f"%{keyword.strip()}%"
        stmt = stmt.where(TableAsset.code.like(like) | TableAsset.name.like(like) | SlaBreach.primary_cause.like(like))
    return [(breach, table) for breach, table in db.execute(stmt).all()]


def get(db: Session, breach_id: int) -> tuple[SlaBreach, TableAsset]:
    row = db.execute(
        select(SlaBreach, TableAsset).join(TableAsset, TableAsset.id == SlaBreach.table_id).where(SlaBreach.id == breach_id)
    ).first()
    if row is None:
        from src.utils.errors import AppError

        raise AppError("NOT_FOUND", 404, detail={"breach_id": breach_id})
    return row[0], row[1]


def claim(db: Session, breach: SlaBreach, actor_email: str) -> SlaBreach:
    breach.handling_status = HandlingStatus.CLAIMED.value
    breach.claimed_by = actor_email
    breach.claimed_at = business_now()
    db.flush()
    return breach


def resolve(db: Session, breach: SlaBreach, actor_email: str, note: str | None) -> SlaBreach:
    breach.handling_status = HandlingStatus.RESOLVED.value
    breach.claimed_by = breach.claimed_by or actor_email
    breach.claimed_at = breach.claimed_at or business_now()
    breach.resolved_at = business_now()
    if note:
        breach.root_note = note.strip()
    db.flush()
    return breach


def summary(db: Session) -> dict:
    rows = list(db.scalars(select(SlaBreach)))
    counters = {item.value: 0 for item in BreachSeverity}
    statuses = {item.value: 0 for item in HandlingStatus}
    for row in rows:
        counters[row.severity] = counters.get(row.severity, 0) + 1
        statuses[row.handling_status] = statuses.get(row.handling_status, 0) + 1
    top = max(rows, key=lambda row: row.impact_score) if rows else None
    top_code = None
    if top is not None:
        top_table = db.get(TableAsset, top.table_id)
        top_code = top_table.code if top_table else None
    return {
        "total": len(rows),
        "by_severity": counters,
        "by_status": statuses,
        "severe_total": counters.get(BreachSeverity.SEVERE.value, 0) + counters.get(BreachSeverity.ESCALATED.value, 0),
        "top_impact": top_code,
    }


def serialize(breach: SlaBreach, table: TableAsset | None) -> dict:
    return {
        "id": breach.id,
        "table_code": table.code if table else "",
        "table_name": table.name if table else "",
        "tier": table.tier if table else "",
        "layer": table.layer if table else "",
        "breach_date": breach.breach_date.isoformat(),
        "delay_seconds": breach.delay_seconds,
        "delay_minutes": round(breach.delay_seconds / 60.0, 1),
        "tolerance_minutes": breach.tolerance_minutes,
        "ratio": breach.ratio,
        "severity": breach.severity,
        "severity_label": SEVERITY_LABELS.get(breach.severity, breach.severity),
        "consecutive_count": breach.consecutive_count,
        "primary_cause": breach.primary_cause,
        "cause_contribution_pct": breach.cause_contribution_pct,
        "impacted_reports": breach.impacted_reports,
        "impact_score": breach.impact_score,
        "suggested_action": breach.suggested_action,
        "attribution_detail": breach.attribution_detail,
        "handling_status": breach.handling_status,
        "claimed_by": breach.claimed_by,
        "claimed_at": breach.claimed_at.isoformat(sep=" ") if breach.claimed_at else None,
        "resolved_at": breach.resolved_at.isoformat(sep=" ") if breach.resolved_at else None,
        "root_note": breach.root_note,
        "report_count": table.report_count if table else 0,
        "expected_ready_clock": table.expected_ready_clock if table else "",
    }
