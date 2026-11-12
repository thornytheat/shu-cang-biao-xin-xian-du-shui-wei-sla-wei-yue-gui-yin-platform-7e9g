"""表资产相关模型。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class TableOut(BaseModel):
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


class TableUpdateRequest(BaseModel):
    tier: str | None = Field(default=None, pattern="^(P0|P1|P2)$")
    expected_ready_clock: str | None = Field(default=None, pattern="^\\d{2}:\\d{2}$")
    report_count: int | None = Field(default=None, ge=0, le=999)
    owner_team: str | None = Field(default=None, max_length=64)
    owner_note: str | None = Field(default=None, max_length=400)


class ChainNodeOut(BaseModel):
    code: str
    name: str
    layer: str
    tier: str
    report_count: int
    delay_minutes: float | None = None
    status: str
    contribution_pct: float | None = None
    basis: str | None = None


class TableChainOut(BaseModel):
    nodes: list[ChainNodeOut]
    downstream: list[dict]
    tolerance_minutes: int
    probe_date: str | None = None
