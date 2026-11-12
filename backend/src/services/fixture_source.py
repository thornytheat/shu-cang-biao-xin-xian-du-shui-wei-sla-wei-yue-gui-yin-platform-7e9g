"""调度就绪事件 fixture：确定性生成每张表每日的"实际就绪时刻"。

设计约束：
1. 纯函数、无 random，同一 (表, 日期偏移) 永远得到同一个延迟 → seed 两次结果完全一致，
   探测运行（POST /api/probes/run）与 seed 的历史数据来自同一套口径。
2. 覆写表（DELAY_OVERRIDES / today_delay_min）用于制造确定的违约样本，
   不允许再叠加抖动，保证违约台账可复现。
3. 少量"早到"样本（约 4%）用于覆盖 early 状态（负延迟截 0）。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from scripts.demo_config import (
    MISSING_HISTORY,
    MISSING_TODAY,
    TABLE_BY_CODE,
    TABLES,
    TableSpec,
    history_overrides,
)
from src.constants.enums import ProbeStatus
from src.services.freshness_core import normalize_offset
from src.utils.timeutil import expected_ready_at

_TABLE_INDEX: dict[str, int] = {spec.code: index for index, spec in enumerate(TABLES)}
_MISSING_HISTORY_SET: frozenset[tuple[int, int]] = frozenset(MISSING_HISTORY)


@dataclass(frozen=True)
class ProbeValues:
    expected_ready_at: datetime
    actual_ready_at: datetime | None
    delay_seconds: int | None
    raw_offset_seconds: int | None
    is_early: bool
    status: str
    note: str


def _residue(index: int, day_offset: int, modulus: int) -> int:
    return (index * 13 + abs(day_offset) * 7) % modulus


def spec_of(code: str) -> TableSpec:
    spec = TABLE_BY_CODE.get(code)
    if spec is None:
        raise KeyError(f"unknown table code: {code}")
    return spec


def table_index(code: str) -> int:
    return _TABLE_INDEX.get(code, 0)


def is_missing(code: str, day_offset: int) -> bool:
    spec = TABLE_BY_CODE.get(code)
    if spec is None:
        return True
    if day_offset == 0:
        return spec.code in MISSING_TODAY or spec.today_delay_min is None
    return (table_index(code), day_offset) in _MISSING_HISTORY_SET


def planned_delay_seconds(spec: TableSpec, day_offset: int) -> int | None:
    """返回 None 表示该日探测缺失（整表不就绪）。"""
    index = _TABLE_INDEX.get(spec.code, 0)
    if day_offset == 0:
        if spec.code in MISSING_TODAY or spec.today_delay_min is None:
            return None
        return int(round(spec.today_delay_min * 60))

    if (index, day_offset) in _MISSING_HISTORY_SET:
        return None

    overrides = history_overrides(spec.code)
    if day_offset in overrides:
        return int(round(overrides[day_offset] * 60))

    scale = min(1.0, spec.base_delay_min / 12.0)
    variation = (_residue(index, day_offset, 19) - 9) * scale
    minutes = max(0.2, spec.base_delay_min + variation)
    return int(round(minutes * 60))


def planned_delay_seconds_for_code(code: str, day_offset: int) -> int | None:
    """按表 code + 日期偏移取 fixture 计划延迟（供归因/seed 复用同一口径）。"""
    spec = TABLE_BY_CODE.get(code)
    if spec is None:
        return None
    return planned_delay_seconds(spec, day_offset)


def _early_offset_seconds(spec: TableSpec, day_offset: int) -> int:
    """约 4% 的探测早到 1-4 分钟（负延迟，落库时截 0 并标 early）。"""
    if day_offset == 0 or history_overrides(spec.code).get(day_offset) is not None:
        return 0
    index = _TABLE_INDEX.get(spec.code, 0)
    if _residue(index, day_offset, 23) != 0:
        return 0
    return -(60 + (index % 4) * 60)


def build_probe_values(spec: TableSpec, probe_date: date, day_offset: int) -> ProbeValues:
    expected = expected_ready_at(probe_date, spec.ready_clock)
    delay_seconds = planned_delay_seconds(spec, day_offset)

    if delay_seconds is None:
        return ProbeValues(
            expected_ready_at=expected,
            actual_ready_at=None,
            delay_seconds=None,
            raw_offset_seconds=None,
            is_early=False,
            status=ProbeStatus.MISSING.value,
            note="未采到就绪事件（分区未产出）",
        )

    early_seconds = _early_offset_seconds(spec, day_offset)
    raw_offset = delay_seconds + early_seconds
    actual = expected + timedelta(seconds=raw_offset)
    # 口径归一（负值截 0、标 early、0=ok、正=late）集中在纯函数内核里，便于单测复核
    clamped, is_early, status = normalize_offset(raw_offset)

    return ProbeValues(
        expected_ready_at=expected,
        actual_ready_at=actual,
        delay_seconds=clamped,
        raw_offset_seconds=raw_offset,
        is_early=is_early,
        status=status,
        note="早到（负延迟截 0）" if is_early else "",
    )
