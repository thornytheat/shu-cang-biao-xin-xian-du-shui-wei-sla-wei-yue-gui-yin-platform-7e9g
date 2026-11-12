"""业务时间工具：所有就绪时刻按 UTC+8 的朴素 datetime 处理。

容器内 TZ=Asia/Shanghai，DB 会话时区 +08:00，因此这里统一用
"本地朴素时间"，避免 naive/aware 混用带来的 8 小时漂移。
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta

from src.config.settings import settings


def business_today() -> date:
    """当前业务日（UTC+8 的今天）。"""
    offset = timedelta(minutes=settings.app_timezone_offset_minutes)
    return (datetime.utcnow() + offset).date()


def business_now() -> datetime:
    offset = timedelta(minutes=settings.app_timezone_offset_minutes)
    return datetime.utcnow() + offset


def clock_to_time(clock: str) -> time:
    """'03:30' -> time(3, 30)。"""
    hour, minute = clock.split(":")[:2]
    return time(int(hour), int(minute))


def expected_ready_at(probe_date: date, clock: str) -> datetime:
    return datetime.combine(probe_date, clock_to_time(clock))


def minutes_to_seconds(minutes: float) -> int:
    return int(round(minutes * 60))


def seconds_to_minutes(seconds: int | None) -> float:
    if seconds is None:
        return 0.0
    return round(seconds / 60.0, 1)


def format_minutes(seconds: int | None) -> str:
    """96 分钟 / 1 小时 36 分 的统一展示。"""
    if seconds is None:
        return "—"
    minutes = seconds / 60.0
    if minutes < 60:
        return f"{round(minutes, 1)} 分钟"
    hours = int(minutes // 60)
    rest = round(minutes - hours * 60, 1)
    return f"{hours} 小时 {rest} 分"


def day_range(end: date, days: int) -> list[date]:
    """返回 [end-days+1, end] 的连续日期升序列表。"""
    return [end - timedelta(days=offset) for offset in range(days - 1, -1, -1)]


def iso(value: date | datetime | None) -> str | None:
    return value.isoformat() if value is not None else None
