"""FreshnessProbe：每表每日一条探测记录。"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class FreshnessProbe(Base):
    __tablename__ = "freshness_probes"
    __table_args__ = (
        UniqueConstraint("table_id", "probe_date", name="uq_probe_table_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    table_id: Mapped[int] = mapped_column(ForeignKey("table_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    probe_date: Mapped[date] = mapped_column(Date, nullable=False, index=True, comment="业务日期（数据分区）")
    partition_dt: Mapped[str] = mapped_column(String(16), nullable=False, comment="分区 dt")
    expected_ready_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="期望就绪时刻")
    actual_ready_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="实际就绪时刻，NULL=缺失")
    delay_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="延迟秒数，负值截 0")
    raw_offset_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="未截断的原始偏移")
    is_early: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="实际早于期望")
    status: Mapped[str] = mapped_column(String(12), nullable=False, index=True, comment="ok/late/early/missing")
    source: Mapped[str] = mapped_column(String(12), nullable=False, default="probe", comment="seed/probe/fixture")
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
