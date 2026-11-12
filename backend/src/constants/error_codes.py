"""错误码与中文消息。"""

ERROR_CODES: dict[str, str] = {
    "AUTH_MISSING": "未登录或登录已过期",
    "AUTH_INVALID": "邮箱或密码不正确",
    "FORBIDDEN": "当前角色无权执行该操作",
    "NOT_FOUND": "对象不存在",
    "VALIDATION": "请求参数不合法",
    "RATE_LIMITED": "请求过于频繁，请稍后再试",
    "TABLE_EXISTS": "表已存在",
    "POLICY_INVALID": "策略参数超出允许区间",
    "PROBE_ALREADY_RUNNING": "今日探测正在运行，请稍候",
    "EXPORT_EMPTY": "当前筛选条件下没有可导出的违约记录",
    "INTERNAL": "服务内部错误",
}
