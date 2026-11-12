"""SLA 策略服务：读取、修改、试算（试算为后端真算，不落库）。"""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.constants.enums import BreachSeverity, Tier
from src.constants.limits import (
    DEFAULT_ESCALATE_AFTER,
    DEFAULT_TOLERANCE,
    ESCALATE_AFTER_MAX,
    ESCALATE_AFTER_MIN,
    RATIO_SEVERE,
    TOLERANCE_MAX,
    TOLERANCE_MIN,
)
from src.models.freshness_probe import FreshnessProbe
from src.models.sla_policy import SlaPolicy
from src.services import breach_service
from src.utils.errors import AppError
from src.utils.timeutil import business_now, business_today

TIER_LABELS = {
    Tier.P0.value: "P0 · 核心链路",
    Tier.P1.value: "P1 · 经营分析",
    Tier.P2.value: "P2 · 辅助报表",
}


def ensure_defaults(db: Session) -> list[SlaPolicy]:
    rows = list(db.scalars(select(SlaPolicy).order_by(SlaPolicy.tier)))
    existing = {row.tier for row in rows}
    for index, tier in enumerate(Tier):
        if tier.value in existing:
            continue
        row = SlaPolicy(
            tier=tier.value,
            tolerance_minutes=DEFAULT_TOLERANCE[tier.value],
            escalate_after=DEFAULT_ESCALATE_AFTER if index < 2 else 4,
            calibrate_days=30,
            report_owner_note="",
        )
        db.add(row)
        rows.append(row)
    db.flush()
    return sorted(rows, key=lambda row: row.tier)


def list_policies(db: Session) -> list[SlaPolicy]:
    rows = list(db.scalars(select(SlaPolicy).order_by(SlaPolicy.tier)))
    return rows or ensure_defaults(db)


def get_policy(db: Session, tier: str) -> SlaPolicy:
    row = db.scalar(select(SlaPolicy).where(SlaPolicy.tier == tier))
    if row is None:
        raise AppError("NOT_FOUND", 404, detail={"tier": tier})
    return row


def update_policy(
    db: Session,
    tier: str,
    *,
    tolerance_minutes: int | None,
    escalate_after: int | None,
    calibrate_days: int | None,
    note: str | None,
    actor_email: str,
) -> SlaPolicy:
    row = get_policy(db, tier)
    if tolerance_minutes is not None:
        if not (TOLERANCE_MIN <= tolerance_minutes <= TOLERANCE_MAX):
            raise AppError(
                "POLICY_INVALID",
                422,
                detail={"tolerance_minutes": f"允许区间 {TOLERANCE_MIN}-{TOLERANCE_MAX}"},
            )
        row.tolerance_minutes = tolerance_minutes
    if escalate_after is not None:
        if not (ESCALATE_AFTER_MIN <= escalate_after <= ESCALATE_AFTER_MAX):
            raise AppError(
                "POLICY_INVALID",
                422,
                detail={"escalate_after": f"允许区间 {ESCALATE_AFTER_MIN}-{ESCALATE_AFTER_MAX}"},
            )
        row.escalate_after = escalate_after
    if calibrate_days is not None:
        if not (7 <= calibrate_days <= 90):
            raise AppError("POLICY_INVALID", 422, detail={"calibrate_days": "允许区间 7-90"})
        row.calibrate_days = calibrate_days
    if note is not None:
        row.report_owner_note = note.strip() or None
    row.updated_by = actor_email
    row.updated_at = business_now()
    db.flush()
    return row


def preview(
    db: Session,
    *,
    tolerances: dict[str, int],
    escalate_after: int | None = None,
) -> dict:
    """试算：用给定的三档容忍值/升级阈值重算近 30 天违约，不写库。"""
    for tier, value in tolerances.items():
        if tier not in {item.value for item in Tier}:
            raise AppError("POLICY_INVALID", 422, detail={"tier": tier})
        if not (TOLERANCE_MIN <= int(value) <= TOLERANCE_MAX):
            raise AppError(
                "POLICY_INVALID",
                422,
                detail={"tolerance_minutes": f"{tier} 允许区间 {TOLERANCE_MIN}-{TOLERANCE_MAX}"},
            )
    if escalate_after is not None and not (ESCALATE_AFTER_MIN <= escalate_after <= ESCALATE_AFTER_MAX):
        raise AppError("POLICY_INVALID", 422, detail={"escalate_after": "超出允许区间"})

    candidates = breach_service.scan(
        db,
        tolerances={tier: int(value) for tier, value in tolerances.items()},
        escalate_after_override=escalate_after,
    )
    policy_rows = breach_service.policies(db)
    tiers: dict[str, dict] = {}
    for tier in Tier:
        tiers[tier.value] = {
            "tier": tier.value,
            "label": TIER_LABELS[tier.value],
            "tolerance_minutes": int(tolerances.get(tier.value, DEFAULT_TOLERANCE[tier.value])),
            "breaches": 0,
            "severe": 0,
            "tables": [],
        }

    sample = []
    for candidate in candidates:
        policy = policy_rows.get(candidate.table.tier)
        threshold = escalate_after if escalate_after is not None else (policy.escalate_after if policy else 3)
        severity = breach_service.severity_for(candidate.ratio, candidate.consecutive, threshold)
        bucket = tiers[candidate.table.tier]
        bucket["breaches"] += 1
        if severity in {BreachSeverity.SEVERE.value, BreachSeverity.ESCALATED.value}:
            bucket["severe"] += 1
        if candidate.table.code not in bucket["tables"]:
            bucket["tables"].append(candidate.table.code)
        sample.append(
            {
                "table_code": candidate.table.code,
                "breach_date": candidate.breach_date.isoformat(),
                "tier": candidate.table.tier,
                "delay_minutes": round(candidate.delay_seconds / 60.0, 1),
                "tolerance_minutes": candidate.tolerance_minutes,
                "ratio": candidate.ratio,
                "consecutive": candidate.consecutive,
                "severity": severity,
            }
        )

    today = business_today()
    probe_count = db.scalar(
        select(func.count(FreshnessProbe.id)).where(FreshnessProbe.probe_date >= today - timedelta(days=30))
    )
    severe_total = sum(bucket["severe"] for bucket in tiers.values())
    return {
        "params": {
            "tolerances": {tier.value: int(tolerances.get(tier.value, DEFAULT_TOLERANCE[tier.value])) for tier in Tier},
            "escalate_after": escalate_after,
        },
        "tiers": [tiers[tier.value] for tier in Tier],
        "totals": {
            "breaches": len(candidates),
            "severe": severe_total,
            "warning": len(candidates) - severe_total,
            "affected_tables": len({item["table_code"] for item in sample}),
        },
        "sample": sorted(sample, key=lambda item: (-item["ratio"], item["breach_date"]))[:6],
        "baseline": {"probe_rows": probe_count, "window_days": 30, "critical_ratio": RATIO_SEVERE},
    }


def serialize(row: SlaPolicy) -> dict:
    return {
        "id": row.id,
        "tier": row.tier,
        "label": TIER_LABELS.get(row.tier, row.tier),
        "tolerance_minutes": row.tolerance_minutes,
        "escalate_after": row.escalate_after,
        "calibrate_days": row.calibrate_days,
        "report_owner_note": row.report_owner_note,
        "updated_by": row.updated_by,
        "updated_at": row.updated_at.isoformat(sep=" ") if row.updated_at else None,
    }
