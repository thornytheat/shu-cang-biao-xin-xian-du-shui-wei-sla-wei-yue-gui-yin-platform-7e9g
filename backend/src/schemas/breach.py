"""违约与探测批次相关模型。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class BreachOut(BaseModel):
    id: int
    table_code: str
    table_name: str
    tier: str
    layer: str
    breach_date: str
    delay_seconds: int
    delay_minutes: float
    tolerance_minutes: int
    ratio: float
    severity: str
    severity_label: str
    consecutive_count: int
    primary_cause: str
    cause_contribution_pct: float
    impacted_reports: int
    impact_score: float
    suggested_action: str
    attribution_detail: dict | None = None
    handling_status: str
    claimed_by: str | None = None
    claimed_at: str | None = None
    resolved_at: str | None = None
    root_note: str | None = None
    is_voided: bool = False
    voided_at: str | None = None
    void_reason: str | None = None
    report_count: int
    expected_ready_clock: str


class BreachListOut(BaseModel):
    items: list[BreachOut]
    summary: dict


class BreachActionRequest(BaseModel):
    note: str | None = Field(default=None, max_length=600)


class DetectRequest(BaseModel):
    days: int = Field(default=30, ge=7, le=90)
    include_planned: bool = False


class DetectResponse(BaseModel):
    scanned: int
    created: int
    updated: int
    voided: int = 0
    deleted: int = 0
    revived: int = 0
    total: int
    budget: dict
    window_days: int
    summary: dict


class ProbeRunResponse(BaseModel):
    run_date: str
    created: int
    updated: int
    total: int
    missing: int
    unknown: int
    late: int
    early: int
    ok: int
    backfilled: int = 0
    red_tables: list[str]
    red_count: int
    duration_ms: int
    waterline: str
    breaches: dict | None = None


class ProbeRowOut(BaseModel):
    id: int
    table_code: str
    table_name: str
    tier: str
    probe_date: str
    partition_dt: str
    expected_ready_at: str
    actual_ready_at: str | None = None
    delay_minutes: float | None = None
    status: str
    is_early: bool


class ProbeStatusOut(BaseModel):
    today: str
    probed_today: bool
    run: dict | None = None
    latest: dict | None = None
