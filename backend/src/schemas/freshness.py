"""新鲜度（算法 1）相关模型。"""
from __future__ import annotations

from pydantic import BaseModel


class LatestProbeOut(BaseModel):
    probe_date: str
    partition_dt: str
    expected_ready_at: str
    actual_ready_at: str | None = None
    delay_seconds: int | None = None
    delay_minutes: float | None = None
    ratio: float | None = None
    status: str
    is_early: bool
    is_missing: bool


class PercentilesOut(BaseModel):
    p50: float | None = None
    p90: float | None = None
    p95: float | None = None


class EvaluationOut(BaseModel):
    latest: LatestProbeOut | None = None
    grade: str
    grade_reason: str
    percentiles: PercentilesOut
    baseline_days: int
    missing_in_window: int
    tolerance_minutes: int
    water_pct: float
    on_time_rate: float | None = None


class BoardRowOut(BaseModel):
    code: str
    name: str
    layer: str
    tier: str
    schedule_cron: str
    expected_ready_clock: str
    upstream_code: str | None = None
    report_count: int
    owner_team: str
    size_gb: float
    owner_note: str | None = None
    tolerance_minutes: int
    grade: str
    grade_reason: str
    delay_minutes: float | None = None
    delay_seconds: int | None = None
    ratio: float | None = None
    probe_date: str | None = None
    status: str | None = None
    is_early: bool = False
    water_pct: float
    percentiles: PercentilesOut
    baseline_days: int
    missing_in_window: int
    on_time_rate: float | None = None


class BoardTierOut(BaseModel):
    tier: str
    tolerance_minutes: int
    total: int
    counters: dict[str, int]
    red_tables: list[str]
    rows: list[BoardRowOut]


class BoardTotalsOut(BaseModel):
    tables: int
    red: int
    yellow: int
    green: int
    unknown: int


class BoardOut(BaseModel):
    tiers: dict[str, BoardTierOut]
    totals: BoardTotalsOut
    waterline: str | None = None
    calibration_days: int


class ProbePointOut(BaseModel):
    probe_date: str
    partition_dt: str
    delay_minutes: float | None = None
    status: str
    is_early: bool
    is_missing: bool
    is_breach: bool
    expected_ready_at: str
    actual_ready_at: str | None = None


class SeriesStatsOut(BaseModel):
    avg_minutes: float | None = None
    max_minutes: float | None = None
    median_minutes: float | None = None
    samples: int
    missing: int
    breach_days: int


class TableFreshnessOut(BaseModel):
    table: dict
    evaluation: EvaluationOut
    points: list[ProbePointOut]
    stats: SeriesStatsOut
    chain: dict
