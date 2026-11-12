"""SlaPolicy：按 P0/P1/P2 三档的容忍值与升级规则。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class SlaPolicy(Base):
    __tablename__ = "sla_policies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tier: Mapped[str] = mapped_column(String(4), unique=True, nullable=False, index=True, comment="P0/P1/P2")
    tolerance_minutes: Mapped[int] = mapped_column(Integer, nullable=False, comment="容忍分钟")
    escalate_after: Mapped[int] = mapped_column(Integer, nullable=False, default=3, comment="连续违约升级阈值 N")
    calibrate_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30, comment="分位基线窗口天数")
    report_owner_note: Mapped[str | None] = mapped_column(Text, nullable=True, comment="策略说明 / 通知口径")
    updated_by: Mapped[str | None] = mapped_column(String(160), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
