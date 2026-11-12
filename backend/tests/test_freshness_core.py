"""算法 1（延迟分位 + 三色灯判级）单测。

口径：基线 = `[最新探测日-30, 最新探测日)` 的非缺失探测；
     green ≤ P50 < yellow ≤ P90 < red；缺失 / 无基线 → unknown。
所有期望值均为手算（或按 seed 覆写值手算），带 pytest.approx。
"""
from __future__ import annotations

import pytest

from src.services.freshness_core import (
    delay_minutes_of,
    evaluate,
    grade_of,
    is_usable,
    ratio_of,
    summarize_points,
    water_pct_of,
)


def _baseline(make_probe):
    """4 天基线延迟 [30,40,50,60] 分钟 -> P50=45.0 / P90=57.0 / P95=58.5。"""
    return [
        make_probe(-4, 30),
        make_probe(-3, 40),
        make_probe(-2, 50),
        make_probe(-1, 60),
    ]


# ---------- 算法 A 正常路径 ----------


def test_red_when_delay_above_p90(make_probe, base_date):
    probes = _baseline(make_probe) + [make_probe(0, 96)]
    result = evaluate(probes, tolerance_minutes=60, calibrate_days=30)

    assert result["grade"] == "red"
    assert result["grade_reason"] == "延迟超过 P90，已进入异常区"
    assert result["percentiles"]["p50"] == pytest.approx(45.0)
    assert result["percentiles"]["p90"] == pytest.approx(57.0)
    assert result["percentiles"]["p95"] == pytest.approx(58.5)
    assert result["latest"]["delay_minutes"] == pytest.approx(96.0)
    assert result["latest"]["ratio"] == pytest.approx(1.6)
    assert result["water_pct"] == pytest.approx(1.6)
    assert result["baseline_days"] == 4
    assert result["missing_in_window"] == 0
    assert result["on_time_rate"] == pytest.approx(1.0)
    assert result["latest"]["probe_date"] == base_date.isoformat()


def test_yellow_between_p50_and_p90(make_probe):
    probes = _baseline(make_probe) + [make_probe(0, 50)]
    result = evaluate(probes, 60, 30)

    assert result["grade"] == "yellow"
    assert result["grade_reason"] == "延迟在 P50 与 P90 之间，需关注"
    assert result["latest"]["ratio"] == pytest.approx(0.83)  # 50/60 -> 0.8333
    assert result["water_pct"] == pytest.approx(0.833)


def test_green_when_delay_equals_p50(make_probe):
    probes = _baseline(make_probe) + [make_probe(0, 45)]
    result = evaluate(probes, 60, 30)

    assert result["grade"] == "green"
    assert result["latest"]["delay_minutes"] == pytest.approx(45.0)
    assert result["percentiles"]["p50"] == pytest.approx(45.0)


# ---------- 算法 A 边界 ----------


def test_yellow_at_exact_p90_boundary(make_probe):
    """判级边界：delay == P90 仍为 yellow（只有 > P90 才转红）。"""
    probes = _baseline(make_probe) + [make_probe(0, 57)]
    result = evaluate(probes, 60, 30)

    assert result["grade"] == "yellow"
    assert result["latest"]["delay_minutes"] == pytest.approx(result["percentiles"]["p90"])


def test_missing_latest_is_unknown_but_keeps_baseline_percentiles(make_probe):
    probes = _baseline(make_probe) + [make_probe(0, None)]
    result = evaluate(probes, 60, 30)

    assert result["grade"] == "unknown"
    assert result["grade_reason"] == "今日探测缺失：分区未产出，不参与分位与判级"
    assert result["latest"]["is_missing"] is True
    assert result["latest"]["delay_seconds"] is None
    assert result["latest"]["ratio"] is None
    assert result["water_pct"] == pytest.approx(0.0)
    assert result["percentiles"]["p50"] == pytest.approx(45.0)
    assert result["baseline_days"] == 4


def test_no_baseline_at_all_is_unknown(make_probe):
    """只有当天一条探测：基线空 -> 分位 None -> unknown（不是 green）。"""
    probes = [make_probe(0, 96)]
    result = evaluate(probes, 60, 30)

    assert result["grade"] == "unknown"
    assert result["grade_reason"] == "基线样本不足（近 30 天无可用探测）"
    assert result["percentiles"] == {"p50": None, "p90": None, "p95": None}
    assert result["baseline_days"] == 0
    assert result["on_time_rate"] is None


def test_zero_variance_all_equal_delays(make_probe):
    """全相同零方差：P50=P90=P95=40，当天 40 -> green（≤P50）。"""
    probes = [make_probe(-3, 40), make_probe(-2, 40), make_probe(-1, 40), make_probe(0, 40)]
    result = evaluate(probes, 60, 30)

    assert result["percentiles"]["p50"] == pytest.approx(40.0)
    assert result["percentiles"]["p90"] == pytest.approx(40.0)
    assert result["percentiles"]["p95"] == pytest.approx(40.0)
    assert result["grade"] == "green"
    assert result["water_pct"] == pytest.approx(0.667)


def test_empty_probe_list_is_unknown():
    result = evaluate([], 60, 30)

    assert result["latest"] is None
    assert result["grade"] == "unknown"
    assert result["grade_reason"] == "该表还没有任何探测记录"
    assert result["percentiles"]["p50"] is None
    assert result["baseline_days"] == 0
    assert result["water_pct"] == pytest.approx(0.0)
    assert result["on_time_rate"] is None


def test_early_probe_clamped_zero_grade_green(make_probe):
    """早到样本：delay=0 / status=early 参与基线，当天 0 分钟 -> green。"""
    probes = [make_probe(-3, 30), make_probe(-2, 40), make_probe(-1, 50), make_probe(0, 0, status="early")]
    result = evaluate(probes, 60, 30)

    assert result["latest"]["is_early"] is True
    assert result["latest"]["is_missing"] is False
    assert result["latest"]["delay_minutes"] == pytest.approx(0.0)
    assert result["latest"]["ratio"] == pytest.approx(0.0)
    assert result["water_pct"] == pytest.approx(0.0)
    assert result["percentiles"]["p50"] == pytest.approx(40.0)
    assert result["grade"] == "green"


# ---------- 基线窗口 / 缺失计数 ----------


def test_baseline_excludes_latest_probe_date(make_probe):
    """当天异常不进自己的基线：96 分钟不抬高 P90。"""
    probes = _baseline(make_probe) + [make_probe(0, 96)]
    result = evaluate(probes, 60, 30)

    assert result["percentiles"]["p90"] == pytest.approx(57.0)
    assert result["baseline_days"] == 4
    assert result["latest"]["delay_minutes"] == pytest.approx(96.0)


def test_window_cutoff_drops_old_probe(make_probe):
    """最新日 -31 天的探测在 30 天窗口外，不参与分位。"""
    probes = [make_probe(-31, 600), make_probe(-2, 10), make_probe(-1, 20), make_probe(0, 30)]
    result = evaluate(probes, 60, 30)

    assert result["baseline_days"] == 2
    assert result["percentiles"]["p50"] == pytest.approx(15.0)
    assert result["percentiles"]["p95"] == pytest.approx(19.5)
    assert result["grade"] == "red"  # 30 > P90=19.0


def test_missing_probes_counted_in_window_not_in_percentiles(make_probe):
    probes = [make_probe(-3, 10), make_probe(-2, None), make_probe(-1, 20), make_probe(0, 30)]
    result = evaluate(probes, 60, 30)

    assert result["baseline_days"] == 2
    assert result["missing_in_window"] == 1
    assert result["percentiles"]["p50"] == pytest.approx(15.0)
    # 计数守恒：可用 + 缺失 == 窗口内总探测数
    window_size = 3  # -3, -2, -1 三天（当天不进基线）
    assert result["baseline_days"] + result["missing_in_window"] == window_size


def test_custom_calibration_days_changes_window(make_probe):
    probes = [make_probe(-10, 600), make_probe(-2, 10), make_probe(-1, 20), make_probe(0, 30)]

    narrow = evaluate(probes, 60, calibrate_days=7)
    wide = evaluate(probes, 60, calibrate_days=30)

    assert narrow["baseline_days"] == 2
    assert narrow["percentiles"]["p50"] == pytest.approx(15.0)
    assert wide["baseline_days"] == 3
    assert wide["percentiles"]["p50"] == pytest.approx(20.0)


# ---------- 归一 / 水位 / 比值 ----------


def test_ratio_and_on_time_rate_use_tolerance(make_probe):
    """容忍 60 分钟：基线 70/80 全超时 -> on_time_rate=0；当天 90 -> ratio 1.5。"""
    probes = [make_probe(-2, 70), make_probe(-1, 80), make_probe(0, 90)]
    result = evaluate(probes, 60, 30)

    assert result["latest"]["ratio"] == pytest.approx(1.5)
    assert result["water_pct"] == pytest.approx(1.5)
    assert result["on_time_rate"] == pytest.approx(0.0)
    assert result["grade"] == "red"


def test_water_and_ratio_are_consistent(make_probe):
    probes = _baseline(make_probe) + [make_probe(0, 96)]
    result = evaluate(probes, 60, 30)

    assert result["water_pct"] == pytest.approx(result["latest"]["ratio"], abs=1e-9)


def test_grade_of_unknown_when_missing_inputs():
    assert grade_of(None, 45.0, 57.0) == "unknown"
    assert grade_of(96.0, None, 57.0) == "unknown"
    assert grade_of(96.0, 45.0, None) == "red"  # 无 P90 时降级为 P50 上界


# ---------- 不变量 / 性质 ----------


@pytest.mark.parametrize("dataset", [[1, 2], [10, 20, 30, 40, 50], [0, 0, 0, 100], [12.5]])
def test_percentiles_are_monotonic(dataset):
    from src.utils.percentile import percentile_bundle

    bundle = percentile_bundle(dataset)
    assert bundle["p50"] <= bundle["p90"] <= bundle["p95"]


def test_order_independence(make_probe):
    probes = _baseline(make_probe) + [make_probe(0, 96)]
    forward = evaluate(probes, 60, 30)
    backward = evaluate(list(reversed(probes)), 60, 30)

    assert forward == backward


def test_deterministic_same_input_twice(make_probe):
    probes = _baseline(make_probe) + [make_probe(0, 96)]
    assert evaluate(probes, 60, 30) == evaluate(probes, 60, 30)


def test_grade_monotonic_in_delay(make_probe):
    """延迟越大判级不降：green < yellow < red。"""
    rank = {"green": 0, "yellow": 1, "red": 2}
    baseline = _baseline(make_probe)
    grades = [evaluate(baseline + [make_probe(0, delay)], 60, 30)["grade"] for delay in (10, 50, 60)]

    assert grades == ["green", "yellow", "red"]
    assert [rank[item] for item in grades] == sorted(rank[item] for item in grades)


def test_on_time_rate_within_zero_one(make_probe):
    probes = [make_probe(-3, 10), make_probe(-2, 70), make_probe(-1, 20), make_probe(0, 90)]
    result = evaluate(probes, 60, 30)

    assert 0.0 <= result["on_time_rate"] <= 1.0
    assert result["on_time_rate"] == pytest.approx(0.667)  # 2/3 命中
    assert result["baseline_days"] == 3


# ---------- 详情页序列统计 ----------


def test_summarize_points_hand_computed():
    points = [
        {"delay_minutes": 10.0, "is_missing": False},
        {"delay_minutes": 20.0, "is_missing": False},
        {"delay_minutes": None, "is_missing": True},
        {"delay_minutes": 90.0, "is_missing": False},
    ]
    stats = summarize_points(points, tolerance_minutes=60)

    assert stats["avg_minutes"] == pytest.approx(40.0)  # (10+20+90)/3
    assert stats["max_minutes"] == pytest.approx(90.0)
    assert stats["median_minutes"] == pytest.approx(20.0)
    assert stats["samples"] == 3
    assert stats["missing"] == 1
    assert stats["breach_days"] == 1  # 只有 90 分钟 > 60


def test_summarize_points_empty_returns_none_stats():
    stats = summarize_points([], 60)
    assert stats == {"avg_minutes": None, "max_minutes": None, "median_minutes": None, "samples": 0, "missing": 0, "breach_days": 0}


def test_helpers_are_pure_scalars():
    assert delay_minutes_of(5400) == pytest.approx(90.0)
    assert delay_minutes_of(None) is None
    assert ratio_of(5400, 60) == pytest.approx(1.5)
    assert ratio_of(None, 60) is None
    assert water_pct_of(90.0, 60) == pytest.approx(1.5)
    assert water_pct_of(None, 60) == pytest.approx(0.0)


def test_is_usable_rules(make_probe):
    assert is_usable(make_probe(-1, 10)) is True
    assert is_usable(make_probe(-1, 0, status="early")) is True
    assert is_usable(make_probe(-1, None)) is False
    assert is_usable({**make_probe(-1, 10), "status": "missing"}) is False
