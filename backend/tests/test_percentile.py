"""分位数（线性插值）单测：手算期望值 + 边界 / 空集 / 零方差 / 乱序 / 越界。"""
from __future__ import annotations

import pytest

from src.utils.percentile import median, percentile, percentile_bundle


def test_percentile_interpolation_hand_computed():
    """[10,20,30,40] 的 P50/P90/P95 线性插值（等价 Excel PERCENTILE.INC）。"""
    data = [10, 20, 30, 40]
    # rank(50%)=(4-1)*0.5=1.5 -> 20 + (30-20)*0.5
    assert percentile(data, 50) == pytest.approx(25.0)
    # rank(90%)=2.7 -> 30 + (40-30)*0.7
    assert percentile(data, 90) == pytest.approx(37.0)
    # rank(95%)=2.85 -> 30 + (40-30)*0.85
    assert percentile(data, 95) == pytest.approx(38.5)


def test_percentile_seed_delays_three_points():
    """真实 seed 中 dwd.loan_repay 的历史覆写 75/68/72 分钟 -> 手算分位。"""
    data = [75.0, 68.0, 72.0]  # sorted: 68, 72, 75
    assert percentile(data, 50) == pytest.approx(72.0)  # rank=1 命中整点
    assert percentile(data, 90) == pytest.approx(74.4)  # 72 + 3*0.8
    assert percentile(data, 95) == pytest.approx(74.7)  # rank=(3-1)*0.95=1.9 -> 72 + 3*0.9


def test_percentile_empty_returns_none():
    assert percentile([], 50) is None
    assert percentile([], 95) is None


def test_percentile_single_value_returns_itself():
    assert percentile([42.5], 0) == pytest.approx(42.5)
    assert percentile([42.5], 50) == pytest.approx(42.5)
    assert percentile([42.5], 100) == pytest.approx(42.5)


def test_percentile_all_equal_zero_variance():
    bundle = percentile_bundle([7.5, 7.5, 7.5, 7.5], (50, 90, 95))
    assert bundle == {"p50": pytest.approx(7.5), "p90": pytest.approx(7.5), "p95": pytest.approx(7.5)}


def test_percentile_unsorted_input_is_equivalent():
    values = [40, 10, 30, 20]
    assert percentile(values, 50) == pytest.approx(percentile(sorted(values), 50))
    assert percentile(values, 90) == pytest.approx(37.0)
    assert percentile(values, 95) == pytest.approx(38.5)


def test_percentile_endpoints_are_min_and_max():
    data = [40, 10, 30, 20]
    assert percentile(data, 0) == pytest.approx(10.0)
    assert percentile(data, 100) == pytest.approx(40.0)


def test_median_equals_p50():
    assert median([10, 20, 30, 40]) == pytest.approx(25.0)
    assert median([3]) == pytest.approx(3.0)


def test_percentile_bundle_has_exactly_three_named_keys():
    bundle = percentile_bundle([1, 2, 3, 4])
    assert list(bundle) == ["p50", "p90", "p95"]
    assert bundle["p90"] == pytest.approx(3.7)


def test_percentile_is_deterministic():
    data = [12, 5, 33, 8, 21]
    first = percentile_bundle(data)
    second = percentile_bundle(data)
    assert first == second


@pytest.mark.parametrize("bad_p", [-1, -0.1, 100.1, 101])
def test_percentile_rejects_out_of_range_point(bad_p):
    """越界分位点必须显式报错，不能静默返回首/尾值冒充分位。"""
    with pytest.raises(ValueError, match=r"percentile p must be within \[0, 100\]"):
        percentile([1, 2, 3], bad_p)
