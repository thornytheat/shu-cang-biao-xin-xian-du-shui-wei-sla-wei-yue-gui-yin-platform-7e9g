"""ProbeRun：探测批次（新增/缺失/未知/红灯计数），支撑看板"今日是否已巡检"。"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class ProbeRun(Base):
    __tablename__ = "probe_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_date: Mapped[date] = mapped_column(Date, nullable=False, unique=True, index=True)
    triggered_by: Mapped[str] = mapped_column(String(160), nullable=False)
    trigger_source: Mapped[str] = mapped_column(String(16), nullable=False, default="api", comment="api/beat/seed")
    created_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    missing_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unknown_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    late_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    red_tables: Mapped[list | None] = mapped_column(JSON, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
