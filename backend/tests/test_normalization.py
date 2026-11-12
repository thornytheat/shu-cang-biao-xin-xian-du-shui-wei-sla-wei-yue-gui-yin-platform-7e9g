"""解析 / 归一工具单测：原始偏移 → 落库口径、比值、水位、延迟分钟。"""
from __future__ import annotations

import pytest

from src.services.freshness_core import delay_minutes_of, normalize_offset, ratio_of, water_pct_of


def test_normalize_negative_offset_clamped_to_zero_early():
    """早到 90 秒：负延迟截 0，标记 early（不产生负水位）。"""
    clamped, is_early, status = normalize_offset(-90)
    assert clamped == 0
    assert is_early is True
    assert status == "early"


def test_normalize_zero_offset_is_ok():
    clamped, is_early, status = normalize_offset(0)
    assert clamped == 0
    assert is_early is False
    assert status == "ok"


def test_normalize_positive_offset_is_late():
    clamped, is_early, status = normalize_offset(5400)
    assert clamped == 5400
    assert is_early is False
    assert status == "late"


def test_normalize_none_offset_is_missing():
    assert normalize_offset(None) == (None, False, "missing")


def test_normalize_seconds_are_whole_seconds():
    """1800.4 秒按 int 截断为 1800（库里是秒整数）。"""
    assert normalize_offset(1800.4) == (1800, False, "late")


def test_ratio_of_two_decimal_rounding():
    # freshness_core.ratio_of 固定保留 2 位小数，容忍分钟换算成秒再除
    assert ratio_of(5400, 60) == pytest.approx(1.5)
    assert ratio_of(3600, 60) == pytest.approx(1.0)
    assert ratio_of(2160, 60) == pytest.approx(0.6)
    assert ratio_of(5400, 90) == pytest.approx(1.0)
    assert ratio_of(2880, 60) == pytest.approx(0.8)
    assert ratio_of(None, 60) is None


def test_water_pct_of_three_decimal_rounding():
    assert water_pct_of(96.0, 60) == pytest.approx(1.6)
    assert water_pct_of(30.0, 60) == pytest.approx(0.5)
    assert water_pct_of(None, 60) == pytest.approx(0.0)


def test_delay_minutes_of_conversion():
    assert delay_minutes_of(5760) == pytest.approx(96.0)
    assert delay_minutes_of(0) == pytest.approx(0.0)
    assert delay_minutes_of(None) is None
