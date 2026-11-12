"""算法 1（延迟分位 + 三色灯判级）的纯函数内核。

第二轮测试补齐时从 `freshness_service.py` 抽出的纯计算层，约束：
- 只吃 dict / list / 基本类型，不 import ORM、Session、数据库配置；
- 与 `freshness_service.py` 的分工：这里做计算与口径归一，那里只做取数 + ORM -> dict；
- 行为（含取整、判定边界、字段名）与原实现逐字一致，原 smoke / API 数值不变。

探测输入 dict 的字段（由 `freshness_service._probe_row` 提供）：
    probe_date        date
    partition_dt      str
    expected_ready_at datetime
    actual_ready_at   datetime | None
    delay_seconds     int | None
    status            "ok" | "late" | "early" | "missing"
    is_early          bool
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from src.constants.enums import Grade, ProbeStatus
from src.constants.limits import PERCENTILES
from src.utils.percentile import median, percentile_bundle


def normalize_offset(raw_offset_seconds: int | None) -> tuple[int | None, bool, str]:
    """把「实际就绪 − 期望就绪」的原始秒数归一成落库口径。

    None -> (None, False, "missing")；
    负值 -> 截 0、is_early=True、status="early"（负延迟不参与水位）；
    0    -> status="ok"；正值 -> status="late"。
    """
    if raw_offset_seconds is None:
        return None, False, ProbeStatus.MISSING.value
    raw = int(raw_offset_seconds)
    clamped = max(0, raw)
    if raw < 0:
        return clamped, True, ProbeStatus.EARLY.value
    if clamped == 0:
        return clamped, False, ProbeStatus.OK.value
    return clamped, False, ProbeStatus.LATE.value


def is_usable(probe: dict) -> bool:
    """缺失探测与无延迟样本不参与分位 / 判级。"""
    return probe.get("status") != ProbeStatus.MISSING.value and probe.get("delay_seconds") is not None


def delay_minutes_of(delay_seconds: float | None) -> float | None:
    if delay_seconds is None:
        return None
    return delay_seconds / 60.0


def ratio_of(delay_seconds: int | None, tolerance_minutes: int) -> float | None:
    """超时倍数 = 延迟秒数 / (容忍分钟 × 60)，保留 2 位小数。"""
    if delay_seconds is None:
        return None
    tolerance_seconds = max(1, int(tolerance_minutes) * 60)
    return round(delay_seconds / tolerance_seconds, 2)


def water_pct_of(delay_minutes: float | None, tolerance_minutes: int) -> float:
    """水位 = 当前延迟 / 容忍，保留 3 位小数；无延迟记 0。"""
    tolerance_seconds = max(1, int(tolerance_minutes) * 60)
    return round((delay_minutes or 0) * 60 / tolerance_seconds, 3)


def grade_of(delay_minutes: float | None, p50: float | None, p90: float | None) -> str:
    """green ≤ P50；yellow ≤ P90；red > P90；无延迟或无基线 → unknown。"""
    if delay_minutes is None or p50 is None:
        return Grade.UNKNOWN.value
    if delay_minutes <= p50:
        return Grade.GREEN.value
    upper = p90 if p90 is not None else p50
    if delay_minutes <= upper:
        return Grade.YELLOW.value
    return Grade.RED.value


def evaluate(
    probes: list[dict],
    tolerance_minutes: int,
    calibrate_days: int,
) -> dict:
    """纯计算：给定一张表的探测序列（可乱序），返回最新状态 + 分位 + 判级。

    基线口径：`[latest_date - calibrate_days, latest_date)` 内的非缺失探测。
    当天（最新一条）不进入自己的基线，避免异常把自己 P90 抬高。
    """
    ordered = sorted(probes, key=lambda row: row["probe_date"])
    tolerance_seconds = max(1, int(tolerance_minutes) * 60)

    if not ordered:
        return {
            "latest": None,
            "grade": Grade.UNKNOWN.value,
            "grade_reason": "该表还没有任何探测记录",
            "percentiles": {"p50": None, "p90": None, "p95": None},
            "baseline_days": 0,
            "missing_in_window": 0,
            "tolerance_minutes": tolerance_minutes,
            "water_pct": 0.0,
            "on_time_rate": None,
        }

    latest = ordered[-1]
    latest_date: date = latest["probe_date"]
    window_start = latest_date - timedelta(days=calibrate_days)
    window = [row for row in ordered if window_start <= row["probe_date"] < latest_date]
    baseline = [row for row in window if is_usable(row)]
    delays_minutes = [row["delay_seconds"] / 60.0 for row in baseline]
    bundle = percentile_bundle(delays_minutes, PERCENTILES)
    missing_in_window = len(window) - len(baseline)

    delay_minutes = None
    ratio = None
    if is_usable(latest):
        delay_minutes = latest["delay_seconds"] / 60.0
        ratio = ratio_of(latest["delay_seconds"], tolerance_minutes)

    if not is_usable(latest):
        grade = Grade.UNKNOWN.value
        reason = "今日探测缺失：分区未产出，不参与分位与判级"
    elif bundle["p50"] is None:
        grade = Grade.UNKNOWN.value
        reason = "基线样本不足（近 30 天无可用探测）"
    else:
        grade = grade_of(delay_minutes, bundle["p50"], bundle["p90"])
        reason = {
            Grade.GREEN.value: "延迟 ≤ P50，链路健康",
            Grade.YELLOW.value: "延迟在 P50 与 P90 之间，需关注",
            Grade.RED.value: "延迟超过 P90，已进入异常区",
        }.get(grade, "")

    on_time_rate = None
    if baseline:
        on_time = sum(1 for row in baseline if (row["delay_seconds"] or 0) <= tolerance_seconds)
        on_time_rate = round(on_time / len(baseline), 3)

    expected_ready_at: datetime = latest["expected_ready_at"]
    actual_ready_at: datetime | None = latest.get("actual_ready_at")
    return {
        "latest": {
            "probe_date": latest_date.isoformat(),
            "partition_dt": latest["partition_dt"],
            "expected_ready_at": expected_ready_at.isoformat(sep=" "),
            "actual_ready_at": actual_ready_at.isoformat(sep=" ") if actual_ready_at else None,
            "delay_seconds": latest["delay_seconds"],
            "delay_minutes": delay_minutes,
            "ratio": ratio,
            "status": latest["status"],
            "is_early": bool(latest.get("is_early", False)),
            "is_missing": latest["status"] == ProbeStatus.MISSING.value,
        },
        "grade": grade,
        "grade_reason": reason,
        "percentiles": bundle,
        "baseline_days": len(baseline),
        "missing_in_window": missing_in_window,
        "tolerance_minutes": tolerance_minutes,
        "water_pct": water_pct_of(delay_minutes, tolerance_minutes),
        "on_time_rate": on_time_rate,
    }


def summarize_points(points: list[dict], tolerance_minutes: int) -> dict:
    """详情页序列统计：均值 / 最大 / 中位 / 样本数 / 缺失数 / 违约天数。

    `points` 只要求 `delay_minutes`（None=缺失）与 `is_missing` 两个字段。
    """
    usable = [point["delay_minutes"] for point in points if point.get("delay_minutes") is not None]
    tolerance_seconds = max(1, int(tolerance_minutes) * 60)
    return {
        "avg_minutes": round(sum(usable) / len(usable), 1) if usable else None,
        "max_minutes": round(max(usable), 1) if usable else None,
        "median_minutes": round(median(usable), 1) if usable else None,
        "samples": len(usable),
        "missing": sum(1 for point in points if point.get("is_missing")),
        "breach_days": sum(
            1
            for point in points
            if point.get("delay_minutes") is not None and point["delay_minutes"] * 60 > tolerance_seconds
        ),
    }
