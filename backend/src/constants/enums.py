"""共享枚举（后端唯一来源）。前端镜像见 frontend/src/constants/enums.ts。"""
from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    """平台角色：admin 平台负责人 / ops 值班工程师 / viewer 报表 owner。"""

    ADMIN = "admin"
    OPS = "ops"
    VIEWER = "viewer"


class Layer(str, Enum):
    """数仓分层。"""

    ODS = "ods"
    DWD = "dwd"
    DWS = "dws"
    ADS = "ads"


class Tier(str, Enum):
    """SLA 等级。"""

    P0 = "P0"
    P1 = "P1"
    P2 = "P2"


class Grade(str, Enum):
    """新鲜度三色灯等级（由近 30 天延迟分位判定）。"""

    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"
    UNKNOWN = "unknown"


class ProbeStatus(str, Enum):
    """探测状态：ok 准点 / late 迟到 / early 早到（负延迟截 0）/ missing 缺失。"""

    OK = "ok"
    LATE = "late"
    EARLY = "early"
    MISSING = "missing"


class BreachSeverity(str, Enum):
    """违约严重度：warning 违约 / severe 严重 / escalated 连续升级（最高级）。"""

    WARNING = "warning"
    SEVERE = "severe"
    ESCALATED = "escalated"


class HandlingStatus(str, Enum):
    """违约处置态。"""

    OPEN = "open"
    CLAIMED = "claimed"
    RESOLVED = "resolved"


class AttributionCause(str, Enum):
    """归因结论的特殊值。"""

    SELF = "self"
    UNDETERMINED = "undetermined"


SEVERITY_LABELS: dict[str, str] = {
    BreachSeverity.WARNING.value: "违约",
    BreachSeverity.SEVERE.value: "严重",
    BreachSeverity.ESCALATED.value: "升级严重",
}

GRADE_LABELS: dict[str, str] = {
    Grade.GREEN.value: "绿 · 健康",
    Grade.YELLOW.value: "黄 · 关注",
    Grade.RED.value: "红 · 超标",
    Grade.UNKNOWN.value: "未知 · 探测缺失",
}

LAYER_LABELS: dict[str, str] = {
    Layer.ODS.value: "ODS 贴源",
    Layer.DWD.value: "DWD 明细",
    Layer.DWS.value: "DWS 汇总",
    Layer.ADS.value: "ADS 应用",
}

HANDLING_LABELS: dict[str, str] = {
    HandlingStatus.OPEN.value: "待认领",
    HandlingStatus.CLAIMED.value: "处置中",
    HandlingStatus.RESOLVED.value: "已复盘",
}
