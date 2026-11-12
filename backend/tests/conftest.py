"""pytest 配置：把 backend 根目录放进 sys.path（容器内 /app 已由 PYTHONPATH 提供）。

单测全部是纯函数，不连 MySQL / Redis / 网络，也不 mock 算法本身。
"""
from __future__ import annotations

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

BASE_DATE = date(2026, 11, 12)


@pytest.fixture
def base_date() -> date:
    return BASE_DATE


@pytest.fixture
def make_probe():
    """构造算法 1 的探测 dict（字段与 freshness_service._probe_row 一致）。"""

    def _make(day_offset: int, delay_minutes: float | None, status: str | None = None) -> dict:
        probe_date = BASE_DATE + timedelta(days=day_offset)
        if status is None:
            status = "missing" if delay_minutes is None else ("ok" if delay_minutes == 0 else "late")
        delay_seconds = None if delay_minutes is None else int(round(delay_minutes * 60))
        expected = datetime(probe_date.year, probe_date.month, probe_date.day, 3, 30)
        actual = expected + timedelta(seconds=delay_seconds) if delay_seconds is not None else None
        return {
            "probe_date": probe_date,
            "partition_dt": probe_date.isoformat(),
            "expected_ready_at": expected,
            "actual_ready_at": actual,
            "delay_seconds": delay_seconds,
            "status": status,
            "is_early": status == "early",
        }

    return _make
