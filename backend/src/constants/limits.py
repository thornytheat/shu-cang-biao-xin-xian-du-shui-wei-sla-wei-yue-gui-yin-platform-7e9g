"""限额与算法常量（算法口径集中在此，便于复核）。"""

# 延迟分位基线窗口（天），与 settings.calibration_days 一致
DEFAULT_CALIBRATION_DAYS = 30

# 违约检测扫描窗口（天）
BREACH_SCAN_DAYS = 30

# ratio = 延迟 / 容忍；>1 违约，>2 严重
RATIO_BREACH = 1.0
RATIO_SEVERE = 2.0

# 连续违约升级：连续次数 > escalate_after 时升级一级
DEFAULT_ESCALATE_AFTER = 3

# 默认容忍分钟（P0/P1/P2），seed 会写入 SlaPolicy
DEFAULT_TOLERANCE: dict[str, int] = {"P0": 60, "P1": 90, "P2": 120}

# 影响分权重（contribution / 报表覆盖 / 超时倍数）
IMPACT_WEIGHT_CONTRIBUTION = 0.45
IMPACT_WEIGHT_REPORTS = 0.35
IMPACT_WEIGHT_SEVERITY = 0.20
# 报表覆盖归一化：report_count * REPORTS_SCALE 封顶 100
REPORTS_SCALE = 10.0
# 超时倍数归一化：ratio / SEVERITY_SCALE * 100 封顶 100
SEVERITY_SCALE = 2.0

# 分位点
PERCENTILES = (50, 90, 95)

# 策略参数允许区间
TOLERANCE_MIN = 10
TOLERANCE_MAX = 240
ESCALATE_AFTER_MIN = 2
ESCALATE_AFTER_MAX = 7

# 限流固定窗口
RATE_WINDOW_SECONDS = 60
