"""SlaBreach：违约事件台账（含归因、影响分、处置态）。"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class SlaBreach(Base):
    __tablename__ = "sla_breaches"
    __table_args__ = (
        UniqueConstraint("table_id", "breach_date", name="uq_breach_table_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    table_id: Mapped[int] = mapped_column(ForeignKey("table_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    probe_id: Mapped[int | None] = mapped_column(
        ForeignKey("freshness_probes.id", ondelete="SET NULL"), nullable=True
    )
    breach_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    delay_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tolerance_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, comment="延迟/容忍")
    severity: Mapped[str] = mapped_column(String(12), nullable=False, index=True, comment="warning/severe/escalated")
    consecutive_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    primary_cause: Mapped[str] = mapped_column(
        String(80), nullable=False, default="undetermined", comment="上游表 code / self / undetermined"
    )
    cause_contribution_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    impacted_reports: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    impact_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    suggested_action: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    attribution_detail: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="链路逐跳贡献")
    handling_status: Mapped[str] = mapped_column(String(12), nullable=False, default="open", index=True)
    claimed_by: Mapped[str | None] = mapped_column(String(160), nullable=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    root_note: Mapped[str | None] = mapped_column(Text, nullable=True, comment="复盘结论")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
