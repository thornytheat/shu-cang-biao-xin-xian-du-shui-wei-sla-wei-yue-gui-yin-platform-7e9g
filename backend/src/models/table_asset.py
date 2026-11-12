"""TableAsset：数仓表资产（分层 / 调度 / 期望就绪 / 上游 / 影响报表数）。"""
from __future__ import annotations

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class TableAsset(Base, TimestampMixin):
    __tablename__ = "table_assets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True, comment="如 dwd.loan_repay")
    name: Mapped[str] = mapped_column(String(80), nullable=False, comment="表中文名")
    layer: Mapped[str] = mapped_column(String(8), nullable=False, index=True, comment="ods/dwd/dws/ads")
    tier: Mapped[str] = mapped_column(String(4), nullable=False, index=True, comment="P0/P1/P2")
    schedule_cron: Mapped[str] = mapped_column(String(48), nullable=False, comment="调度 cron")
    expected_ready_clock: Mapped[str] = mapped_column(String(5), nullable=False, comment="期望就绪时刻 HH:MM")
    upstream_code: Mapped[str | None] = mapped_column(String(80), nullable=True, comment="直接上游表 code")
    report_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="受影响报表数")
    owner_team: Mapped[str] = mapped_column(String(64), nullable=False, default="数据平台运营组")
    size_gb: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    owner_note: Mapped[str | None] = mapped_column(Text, nullable=True, comment="值班备注 / 处理约定")
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
