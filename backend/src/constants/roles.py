"""角色 -> 权限点映射。README 与前端 constants/roles.ts 同步。"""
from __future__ import annotations

from src.constants.enums import Role

ROLE_LABELS: dict[str, str] = {
    Role.ADMIN.value: "平台负责人",
    Role.OPS.value: "值班工程师",
    Role.VIEWER.value: "报表 owner（只读）",
}

PERMISSIONS: dict[str, set[str]] = {
    Role.ADMIN.value: {
        "table:read", "table:write",
        "probe:read", "probe:run",
        "policy:read", "policy:write", "policy:preview",
        "breach:read", "breach:detect", "breach:claim", "breach:resolve", "breach:attribution",
        "export:read", "audit:read",
    },
    Role.OPS.value: {
        "table:read",
        "probe:read", "probe:run",
        "policy:read", "policy:preview",
        "breach:read", "breach:detect", "breach:claim", "breach:resolve",
        "export:read",
    },
    Role.VIEWER.value: {
        "table:read", "probe:read", "policy:read", "breach:read",
    },
}

# route/controller 层直接使用的角色白名单
TABLE_WRITE_ROLES = (Role.ADMIN.value,)
POLICY_WRITE_ROLES = (Role.ADMIN.value,)
POLICY_PREVIEW_ROLES = (Role.ADMIN.value, Role.OPS.value)
PROBE_RUN_ROLES = (Role.ADMIN.value, Role.OPS.value)
BREACH_ACTION_ROLES = (Role.ADMIN.value, Role.OPS.value)
EXPORT_ROLES = (Role.ADMIN.value, Role.OPS.value)
AUDIT_ROLES = (Role.ADMIN.value,)
READ_ROLES = (Role.ADMIN.value, Role.OPS.value, Role.VIEWER.value)


def has_permission(role: str, permission: str) -> bool:
    return permission in PERMISSIONS.get(role, set())
