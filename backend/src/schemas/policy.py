"""策略相关模型。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class PolicyOut(BaseModel):
    id: int
    tier: str
    label: str
    tolerance_minutes: int
    escalate_after: int
    calibrate_days: int
    report_owner_note: str | None = None
    updated_by: str | None = None
    updated_at: str | None = None


class PolicyUpdateRequest(BaseModel):
    tolerance_minutes: int | None = Field(default=None, ge=10, le=240)
    escalate_after: int | None = Field(default=None, ge=2, le=7)
    calibrate_days: int | None = Field(default=None, ge=7, le=90)
    report_owner_note: str | None = Field(default=None, max_length=400)


class PolicyPreviewRequest(BaseModel):
    p0_tolerance: int = Field(ge=10, le=240)
    p1_tolerance: int = Field(ge=10, le=240)
    p2_tolerance: int = Field(ge=10, le=240)
    escalate_after: int | None = Field(default=None, ge=2, le=7)


class PreviewTierOut(BaseModel):
    tier: str
    label: str
    tolerance_minutes: int
    breaches: int
    severe: int
    tables: list[str]


class PreviewSampleOut(BaseModel):
    table_code: str
    breach_date: str
    tier: str
    delay_minutes: float
    tolerance_minutes: int
    ratio: float
    consecutive: int
    severity: str


class PolicyPreviewOut(BaseModel):
    params: dict
    tiers: list[PreviewTierOut]
    totals: dict
    sample: list[PreviewSampleOut]
    baseline: dict
