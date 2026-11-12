"""算法 2（违约分级 + 连续升级 + 上游归因）的纯函数内核。

第二轮测试补齐时从 `breach_service.py` 抽出，约束：
- 只吃数字 / list[dict] / 字符串，不 import ORM、Session、数据库配置；
- 口径与 README / TESTING 一致：ratio>1 违约、ratio>2 严重、连续次数 > N 升一级、
  贡献 = 上游延迟 / 本表延迟（上限 100%）、影响分三项加权；
- 与 `breach_service.py` 行为逐字一致（原 smoke 的 9 起 / 3 严重 / 68.4 不变）。
"""
from __future__ import annotations

from datetime import date

from src.constants.enums import AttributionCause, BreachSeverity
from src.constants.limits import (
    DEFAULT_ESCALATE_AFTER,
    IMPACT_WEIGHT_CONTRIBUTION,
    IMPACT_WEIGHT_REPORTS,
    IMPACT_WEIGHT_SEVERITY,
    RATIO_BREACH,
    RATIO_SEVERE,
    REPORTS_SCALE,
    SEVERITY_SCALE,
)

SEVERITY_ORDER: dict[str, int] = {
    BreachSeverity.WARNING.value: 0,
    BreachSeverity.SEVERE.value: 1,
    BreachSeverity.ESCALATED.value: 2,
}
SEVERITY_LABELS: dict[str, str] = {
    BreachSeverity.WARNING.value: "违约",
    BreachSeverity.SEVERE.value: "严重",
    BreachSeverity.ESCALATED.value: "升级严重",
}


def ratio_of(delay_seconds: int | float, tolerance_minutes: int, digits: int | None = None) -> float:
    """超时倍数 = 延迟秒数 / max(1, 容忍分钟 × 60)；digits 为 None 时不取整。"""
    value = float(delay_seconds) / max(1, int(tolerance_minutes) * 60)
    return round(value, digits) if digits is not None else value


def is_breach(ratio: float) -> bool:
    return ratio > RATIO_BREACH


def is_severe(ratio: float) -> bool:
    return ratio > RATIO_SEVERE


def severity_for(ratio: float, consecutive: int, escalate_after: int = DEFAULT_ESCALATE_AFTER) -> str:
    """先按 ratio 定基础级，再看连续次数是否 > escalate_after 升一级（最高 escalated）。"""
    level = BreachSeverity.SEVERE.value if is_severe(ratio) else BreachSeverity.WARNING.value
    if consecutive > escalate_after:
        index = min(SEVERITY_ORDER[level] + 1, len(SEVERITY_ORDER) - 1)
        level = [name for name, rank in SEVERITY_ORDER.items() if rank == index][0]
    return level


def compute_impact(contribution_pct: float, reports: int, ratio: float) -> float:
    """影响分 = 0.45×贡献% + 0.35×min(100, 报表数×10) + 0.20×min(100, ratio/2×100)。

    负值属于非法输入（会让影响分静默变小），显式报错而不是返回脏值。
    """
    if contribution_pct < 0 or reports < 0 or ratio < 0:
        raise ValueError(
            "impact inputs must be non-negative: "
            f"contribution_pct={contribution_pct!r} reports={reports!r} ratio={ratio!r}"
        )
    report_norm = min(100.0, reports * REPORTS_SCALE)
    severity_norm = min(100.0, (ratio / SEVERITY_SCALE) * 100.0)
    score = (
        IMPACT_WEIGHT_CONTRIBUTION * contribution_pct
        + IMPACT_WEIGHT_REPORTS * report_norm
        + IMPACT_WEIGHT_SEVERITY * severity_norm
    )
    return round(score, 1)


def contribution_pct(node_delay_seconds: int | None, table_delay_seconds: int) -> float:
    """上游归因贡献 = min(1, 上游延迟 / 本表延迟) × 100，保留 1 位小数。

    上游无就绪事件（None）或本表延迟非正 → 0.0（不参与主因竞争）。
    """
    if node_delay_seconds is None or table_delay_seconds <= 0:
        return 0.0
    return round(min(1.0, node_delay_seconds / table_delay_seconds) * 100.0, 1)


def next_streak(previous_date: date | None, current_date: date, streak: int) -> int:
    """自然日连续：前一天也违约则 +1，否则从 1 重新计数。"""
    if previous_date is not None and (current_date - previous_date).days == 1:
        return streak + 1
    return 1


def resolve_primary(nodes: list[dict]) -> dict:
    """从上游链逐跳贡献里选主因。

    nodes: [{"code": str, "contribution_pct": float, "available": bool, "basis": str}]
    - 无上游 → self / 100% / basis=self
    - 有上游但全无就绪事件 → undetermined / 0% / basis=missing
    - 否则取贡献最大者（并列取链上靠前者，与 max 语义一致）
    """
    if not nodes:
        return {
            "primary_cause": AttributionCause.SELF.value,
            "cause_contribution_pct": 100.0,
            "basis": "self",
        }
    available = [node for node in nodes if node.get("available")]
    if not available:
        return {
            "primary_cause": AttributionCause.UNDETERMINED.value,
            "cause_contribution_pct": 0.0,
            "basis": "missing",
        }
    best = max(nodes, key=lambda item: item["contribution_pct"])
    return {
        "primary_cause": best["code"],
        "cause_contribution_pct": best["contribution_pct"],
        "basis": best.get("basis", "missing"),
    }


def build_action(
    table_code: str,
    expected_ready_clock: str,
    primary: str,
    contribution_pct: float,
    reports: int,
    delay_seconds: int,
) -> str:
    """建议动作：按 self / undetermined / 上游三类给出可执行话术。"""
    delay_minutes = round(delay_seconds / 60.0, 1)
    if primary == AttributionCause.SELF.value:
        return f"核对表内计算任务 {table_code} 的资源队列与 SQL 耗时；{reports} 张报表顺延约 {delay_minutes} 分钟"
    if primary == AttributionCause.UNDETERMINED.value:
        return (
            f"{table_code} 上游链路无就绪事件：先补采探测再定位，暂按值班升级处理并通知 {reports} 张报表 owner"
        )
    return (
        f"联系上游 {primary} 值班核对 {expected_ready_clock} 批次（贡献 {contribution_pct}%）；"
        f"{reports} 张报表顺延约 {delay_minutes} 分钟，通知报表 owner"
    )
