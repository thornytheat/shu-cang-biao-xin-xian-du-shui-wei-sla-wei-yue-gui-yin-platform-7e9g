"""模型注册表：create_all 与 seed 通过这里拿到全部表。"""
from __future__ import annotations

from src.models.audit import AuditLog
from src.models.base import Base, TimestampMixin
from src.models.freshness_probe import FreshnessProbe
from src.models.probe_run import ProbeRun
from src.models.sla_breach import SlaBreach
from src.models.sla_policy import SlaPolicy
from src.models.table_asset import TableAsset
from src.models.user import User

__all__ = [
    "Base",
    "TimestampMixin",
    "AuditLog",
    "FreshnessProbe",
    "ProbeRun",
    "SlaBreach",
    "SlaPolicy",
    "TableAsset",
    "User",
]
