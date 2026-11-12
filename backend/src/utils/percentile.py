"""分位数（线性插值，等价 Excel PERCENTILE.INC / numpy linear）。

不依赖 numpy：数据量小（单表 ≤ 30 点），纯 Python 足够且可复现。
"""
from __future__ import annotations

import math
from collections.abc import Iterable


def percentile(values: Iterable[float], p: float) -> float | None:
    """p 取 0-100；空集返回 None（调用方据此判 unknown）。

    越界分位点显式报错：静默返回首/尾值会让"样本不足"看起来像正常结果。
    """
    p = float(p)
    if not 0.0 <= p <= 100.0:
        raise ValueError(f"percentile p must be within [0, 100], got {p!r}")
    data = sorted(float(v) for v in values)
    n = len(data)
    if n == 0:
        return None
    if n == 1:
        return data[0]
    rank = (p / 100.0) * (n - 1)
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return data[int(rank)]
    weight = rank - low
    return data[low] + (data[high] - data[low]) * weight


def percentile_bundle(values: Iterable[float], points: Iterable[int] = (50, 90, 95)) -> dict[str, float | None]:
    data = list(values)
    return {f"p{int(point)}": percentile(data, float(point)) for point in points}


def median(values: Iterable[float]) -> float | None:
    return percentile(values, 50.0)
