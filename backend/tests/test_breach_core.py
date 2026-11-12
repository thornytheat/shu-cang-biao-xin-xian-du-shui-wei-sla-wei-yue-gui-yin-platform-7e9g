"""算法 2（违约分级 / 连续升级 / 上游归因 / 影响分）单测。

口径：ratio=延迟/容忍；>1 违约、>2 严重；连续次数 > N 升一级；
     影响分 = 0.45×贡献% + 0.35×min(100,报表数×10) + 0.20×min(100,ratio/2×100)。
期望值按 seed 契约手算：贡献 62.0% / 7 张报表 / ratio 1.6 -> 68.4。
"""
from __future__ import annotations

from datetime import date

import pytest

from src.services.breach_core import (
    build_action,
    compute_impact,
    contribution_pct,
    is_breach,
    is_severe,
    next_streak,
    ratio_of,
    resolve_primary,
    severity_for,
)


# ---------- 算法 B 正常路径 ----------


def test_severity_by_ratio():
    assert severity_for(1.6, consecutive=1, escalate_after=3) == "warning"
    assert severity_for(2.5, consecutive=1, escalate_after=3) == "severe"
    assert severity_for(4.0, consecutive=1, escalate_after=3) == "severe"  # 最高基础级就是 severe


def test_consecutive_escalation():
    """连续次数 > escalate_after 才升一级（4 次触发，3 次不触发）。"""
    assert severity_for(1.6, consecutive=4, escalate_after=3) == "severe"
    assert severity_for(2.5, consecutive=4, escalate_after=3) == "escalated"
    assert severity_for(2.5, consecutive=5, escalate_after=3) == "escalated"  # 封顶


def test_impact_score_seed_contract():
    """seed 主流程契约：贡献 62.0% / 7 张报表 / ratio 1.6 -> 68.4。"""
    score = compute_impact(62.0, reports=7, ratio=1.6)
    # 0.45*62 + 0.35*70 + 0.20*80 = 27.9 + 24.5 + 16.0
    assert score == pytest.approx(68.4)


def test_impact_score_bounds():
    assert compute_impact(0.0, reports=0, ratio=0.0) == pytest.approx(0.0)
    assert compute_impact(100.0, reports=10, ratio=2.0) == pytest.approx(100.0)
    assert compute_impact(100.0, reports=999, ratio=9.0) == pytest.approx(100.0)  # 两个归一化项都封顶 100


# ---------- 算法 B 边界 ----------


def test_ratio_breach_boundary():
    assert is_breach(1.0) is False
    assert is_severe(1.0) is False
    assert is_breach(1.01) is True
    assert is_severe(1.01) is False


def test_ratio_severe_boundary():
    assert is_severe(2.0) is False  # 恰好 2 倍仍只是 warning
    assert severity_for(2.0, 1, 3) == "warning"
    assert is_severe(2.01) is True
    assert severity_for(2.01, 1, 3) == "severe"


def test_consecutive_exactly_threshold_no_escalation():
    assert severity_for(1.6, consecutive=3, escalate_after=3) == "warning"
    assert severity_for(2.5, consecutive=3, escalate_after=3) == "severe"
    assert severity_for(1.6, consecutive=4, escalate_after=3) == "severe"


def test_ratio_of_rounding_and_zero_tolerance_floor():
    assert ratio_of(5400, 60) == pytest.approx(1.5)
    assert ratio_of(3420, 60, digits=2) == pytest.approx(0.95)
    assert ratio_of(5700, 60, digits=2) == pytest.approx(1.58)
    # 容忍 0 时用 1 秒下限，避免 ZeroDivisionError（降级可预测，不是静默脏值）
    assert ratio_of(2, 0) == pytest.approx(2.0)


# ---------- 归因 ----------


def test_contribution_matches_seed_numbers():
    """ods.loan_event 晚 59.5 分钟 / dwd.loan_repay 晚 96 分钟 -> 62.0%。"""
    assert contribution_pct(3570, 5760) == pytest.approx(62.0)


def test_contribution_clamped_and_degraded():
    assert contribution_pct(200, 100) == pytest.approx(100.0)  # 上限 100%
    assert contribution_pct(None, 5760) == pytest.approx(0.0)  # 上游无就绪事件
    assert contribution_pct(100, 0) == pytest.approx(0.0)  # 本表无延迟
    assert contribution_pct(0, 5760) == pytest.approx(0.0)


def test_resolve_primary_self_when_no_upstream():
    assert resolve_primary([]) == {
        "primary_cause": "self",
        "cause_contribution_pct": pytest.approx(100.0),
        "basis": "self",
    }


def test_resolve_primary_undetermined_when_all_upstream_missing():
    nodes = [
        {"code": "ods.a", "contribution_pct": 0.0, "available": False, "basis": "missing"},
        {"code": "ods.b", "contribution_pct": 0.0, "available": False, "basis": "missing"},
    ]
    assert resolve_primary(nodes) == {
        "primary_cause": "undetermined",
        "cause_contribution_pct": pytest.approx(0.0),
        "basis": "missing",
    }


def test_resolve_primary_picks_max_contribution():
    nodes = [
        {"code": "ods.root", "contribution_pct": 20.0, "available": True, "basis": "probe"},
        {"code": "ods.loan_event", "contribution_pct": 62.0, "available": True, "basis": "probe"},
        {"code": "ods.direct", "contribution_pct": 40.0, "available": True, "basis": "fixture"},
    ]
    assert resolve_primary(nodes) == {
        "primary_cause": "ods.loan_event",
        "cause_contribution_pct": pytest.approx(62.0),
        "basis": "probe",
    }


def test_resolve_primary_tie_takes_first_in_chain():
    nodes = [
        {"code": "ods.first", "contribution_pct": 50.0, "available": True, "basis": "probe"},
        {"code": "ods.second", "contribution_pct": 50.0, "available": True, "basis": "probe"},
    ]
    assert resolve_primary(nodes)["primary_cause"] == "ods.first"


# ---------- 连续次数状态机 ----------


def test_next_streak_consecutive_days_increment():
    assert next_streak(date(2026, 11, 11), date(2026, 11, 12), 3) == 4


def test_next_streak_gap_resets():
    assert next_streak(date(2026, 11, 9), date(2026, 11, 12), 3) == 1
    assert next_streak(None, date(2026, 11, 12), 0) == 1


# ---------- 建议动作 ----------


def test_build_action_self():
    text = build_action("dwd.loan_repay", "03:30", "self", 100.0, 7, 5760)
    assert "核对表内计算任务 dwd.loan_repay" in text
    assert "7 张报表顺延约 96.0 分钟" in text


def test_build_action_undetermined():
    text = build_action("dwd.loan_repay", "03:30", "undetermined", 0.0, 7, 5760)
    assert "上游链路无就绪事件" in text
    assert "通知 7 张报表 owner" in text


def test_build_action_upstream():
    text = build_action("dwd.loan_repay", "03:30", "ods.loan_event", 62.0, 7, 5760)
    assert "联系上游 ods.loan_event" in text
    assert "核对 03:30 批次（贡献 62.0%）" in text
    assert "7 张报表顺延约 96.0 分钟" in text


# ---------- 异常输入 ----------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"contribution_pct": -1.0, "reports": 7, "ratio": 1.6},
        {"contribution_pct": 62.0, "reports": -1, "ratio": 1.6},
        {"contribution_pct": 62.0, "reports": 7, "ratio": -0.1},
    ],
)
def test_compute_impact_rejects_negative_inputs(kwargs):
    with pytest.raises(ValueError, match="non-negative"):
        compute_impact(**kwargs)


# ---------- 不变量 / 性质 ----------


def test_severity_monotonic_in_ratio_and_streak():
    rank = {"warning": 0, "severe": 1, "escalated": 2}
    by_ratio = [severity_for(ratio, 1, 3) for ratio in (1.01, 2.01)]
    assert [rank[item] for item in by_ratio] == [0, 1]
    # 同一 ratio 下连续次数越多，等级不降
    for ratio in (1.01, 2.01):
        ranks = [rank[severity_for(ratio, consecutive, 3)] for consecutive in (1, 4)]
        assert ranks == sorted(ranks)
    # ratio 已到严重时，连续 4 次再升一级
    assert severity_for(2.5, 4, 3) == "escalated"


def test_impact_monotonic_in_contribution():
    low = compute_impact(20.0, 7, 1.6)
    high = compute_impact(62.0, 7, 1.6)
    assert high > low
    assert high - low == pytest.approx(0.45 * 42.0)  # 只有贡献项变化


def test_deterministic_same_inputs():
    assert compute_impact(62.0, 7, 1.6) == compute_impact(62.0, 7, 1.6)
    assert severity_for(2.5, 4, 3) == severity_for(2.5, 4, 3)
    assert contribution_pct(3570, 5760) == contribution_pct(3570, 5760)
