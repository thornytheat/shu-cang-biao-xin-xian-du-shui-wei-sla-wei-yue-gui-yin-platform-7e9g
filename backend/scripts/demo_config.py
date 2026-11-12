"""演示数据规格（fixture）：40 张核心表 + 30 天探测计划 + 3 条策略 + 账号。

这里只放"数据长什么样"，不含 ORM / 不含写库逻辑；
探测读取的"调度就绪事件 fixture"由 src/services/fixture_source.py 按本文件计算。
所有数值都是确定性公式（无 random），因此两次 seed 完全一致。
"""
from __future__ import annotations

from dataclasses import dataclass, field

DEMO_PASSWORD = "Demo@2026"
BRAND = "freshsla"
DOMAIN = "freshsla.io"

# (email, display_name, role, team)
DEMO_USERS: list[tuple[str, str, str, str]] = [
    ("admin@freshsla.io", "沈可（平台负责人）", "admin", "数据平台运营组"),
    ("ops@freshsla.io", "周航（值班工程师）", "ops", "数据平台运营组"),
    ("viewer@freshsla.io", "林岚（报表 owner）", "viewer", "经营分析室"),
]

HISTORY_DAYS = 30

# 策略：(tier, 容忍分钟, 连续升级阈值, 说明)
POLICY_SPECS: list[tuple[str, int, int, str]] = [
    ("P0", 60, 3, "核心还款/风险/监管链路：容忍 60 分钟，连续 4 次起升级为严重并电话通知"),
    ("P1", 90, 3, "经营分析与分行考核链路：容忍 90 分钟，连续 4 次起升级"),
    ("P2", 120, 4, "辅助与月度报表链路：容忍 120 分钟，连续 5 次起升级"),
]

# 今日探测缺失（→ unknown，不参与分位与判级）
MISSING_TODAY: set[str] = {"dwd.collection_daily", "dws.collection_eff"}

# 历史日延迟覆写（制造违约台账）：(code, day_offset) -> 分钟，offset 负数=历史
DELAY_OVERRIDES: dict[tuple[str, int], float] = {
    ("dwd.loan_repay", -1): 75.0,
    ("dwd.loan_repay", -2): 68.0,
    ("dwd.loan_repay", -3): 72.0,
    ("dws.branch_daily", -6): 210.0,
    ("ads.loan_risk_daily", -9): 130.0,
    ("dwd.member_daily", -13): 95.0,
    ("dwd.member_wide", -16): 72.0,
}


@dataclass(frozen=True)
class TableSpec:
    code: str
    name: str
    layer: str
    tier: str
    cron: str
    ready_clock: str
    upstream: str | None
    report_count: int
    owner_team: str
    size_gb: float
    base_delay_min: float
    today_delay_min: float | None
    note: str = field(default="")


# 40 张核心表：P0 12 / P1 18 / P2 10；ODS 14 / DWD 13 / DWS 8 / ADS 5
TABLES: list[TableSpec] = [
    # ---- ODS 贴源层（14）----
    TableSpec("ods.loan_event", "贷款事件流", "ods", "P1", "0 1 * * *", "02:00", None, 4,
              "数据平台运营组", 820.5, 8.0, 59.5, "Kafka 落仓 + 01:00 批次，延迟直接传导至 dwd.loan_repay"),
    TableSpec("ods.loan_apply", "贷款申请流水", "ods", "P1", "10 2 * * *", "02:10", None, 3,
              "数据平台运营组", 412.0, 6.0, 6.0, ""),
    TableSpec("ods.repay_plan", "还款计划快照", "ods", "P1", "20 2 * * *", "02:20", None, 3,
              "数据平台运营组", 286.4, 7.0, 11.0, "月初批量重算，易受上游核心系统影响"),
    TableSpec("ods.member_profile", "会员主档", "ods", "P1", "30 2 * * *", "02:30", None, 5,
              "数据平台运营组", 198.2, 5.0, 5.0, ""),
    TableSpec("ods.card_txn", "卡交易明细", "ods", "P0", "0 2 * * *", "02:40", None, 6,
              "数据平台运营组", 1240.0, 9.0, 8.0, "消费流水主源，P0 必须 03:00 前就绪"),
    TableSpec("ods.branch_open", "网点营业日开", "ods", "P2", "0 3 * * *", "03:00", None, 1,
              "渠道运营部", 12.6, 4.0, 4.0, ""),
    TableSpec("ods.collateral", "押品台账", "ods", "P2", "10 3 * * *", "03:10", None, 1,
              "风险管理部", 88.0, 3.0, 3.0, ""),
    TableSpec("ods.risk_blacklist", "风险名单", "ods", "P1", "20 3 * * *", "03:20", None, 3,
              "风险管理部", 41.5, 6.0, 6.0, ""),
    TableSpec("ods.collection_call", "催收通话记录", "ods", "P2", "30 3 * * *", "03:30", None, 1,
              "资产保全部", 33.8, 5.0, 5.0, ""),
    TableSpec("ods.fund_flow", "资金流水", "ods", "P1", "40 3 * * *", "03:40", None, 3,
              "财务部", 512.7, 10.0, 10.0, ""),
    TableSpec("ods.product_dim", "产品维表", "ods", "P2", "0 4 * * *", "04:00", None, 1,
              "数据平台运营组", 2.4, 2.0, 2.0, ""),
    TableSpec("ods.org_dim", "机构维表", "ods", "P2", "0 4 * * *", "04:00", None, 1,
              "数据平台运营组", 1.8, 2.0, 2.0, ""),
    TableSpec("ods.calendar_dim", "日历维表", "ods", "P2", "0 4 * * *", "04:00", None, 1,
              "数据平台运营组", 0.6, 1.5, 1.5, ""),
    TableSpec("ods.rate_snapshot", "利率快照", "ods", "P1", "10 4 * * *", "04:10", None, 3,
              "财务部", 6.2, 7.0, 7.0, ""),
    # ---- DWD 明细层（13）----
    TableSpec("dwd.loan_repay", "还款事实明细", "dwd", "P0", "0 3 * * *", "03:30", "ods.loan_event", 7,
              "数据平台运营组", 640.3, 30.0, 96.0, "月度结息日延迟放大，直接影响 7 张报表"),
    TableSpec("dwd.loan_apply_daily", "贷款申请日汇总", "dwd", "P0", "40 3 * * *", "03:40", "ods.loan_apply", 6,
              "数据平台运营组", 210.9, 18.0, 17.0, ""),
    TableSpec("dwd.member_wide", "会员宽表", "dwd", "P0", "50 3 * * *", "03:50", "ods.member_profile", 9,
              "数据平台运营组", 380.1, 14.0, 18.0, "标签回溯任务偶发排队"),
    TableSpec("dwd.card_txn_detail", "卡交易事实", "dwd", "P0", "0 4 * * *", "04:00", "ods.card_txn", 8,
              "数据平台运营组", 980.6, 22.0, 21.0, ""),
    TableSpec("dwd.repay_plan_detail", "还款计划明细", "dwd", "P1", "10 4 * * *", "04:10", "ods.repay_plan", 5,
              "数据平台运营组", 320.4, 12.0, 12.0, ""),
    TableSpec("dwd.branch_perf_daily", "网点日业绩", "dwd", "P1", "20 4 * * *", "04:20", "ods.branch_open", 4,
              "渠道运营部", 45.2, 15.0, 15.0, ""),
    TableSpec("dwd.collateral_detail", "押品明细", "dwd", "P2", "30 4 * * *", "04:30", "ods.collateral", 2,
              "风险管理部", 120.8, 9.0, 9.0, ""),
    TableSpec("dwd.risk_event", "风险事件流", "dwd", "P1", "40 4 * * *", "04:40", "ods.risk_blacklist", 3,
              "风险管理部", 66.1, 11.0, 11.0, ""),
    TableSpec("dwd.collection_daily", "催收日汇总", "dwd", "P2", "50 4 * * *", "04:50", "ods.collection_call", 2,
              "资产保全部", 28.4, 8.0, None, "上游通话记录归集失败时整表不就绪"),
    TableSpec("dwd.fund_flow_detail", "资金流水明细", "dwd", "P1", "0 5 * * *", "05:00", "ods.fund_flow", 3,
              "财务部", 410.3, 13.0, 13.0, ""),
    TableSpec("dwd.member_daily", "会员日活", "dwd", "P1", "10 5 * * *", "05:10", "dwd.member_wide", 4,
              "数据平台运营组", 92.7, 16.0, 16.0, ""),
    TableSpec("dwd.loan_status_snap", "贷款状态快照", "dwd", "P1", "20 5 * * *", "05:20", "dwd.loan_apply_daily", 3,
              "数据平台运营组", 150.6, 10.0, 10.0, ""),
    TableSpec("dwd.repay_overdue", "逾期明细", "dwd", "P1", "30 5 * * *", "05:30", "dwd.repay_plan_detail", 4,
              "资产保全部", 180.2, 14.0, 14.0, ""),
    # ---- DWS 汇总层（8）----
    TableSpec("dws.branch_daily", "网点经营日汇总", "dws", "P1", "0 6 * * *", "06:00", "dwd.branch_perf_daily", 5,
              "渠道运营部", 76.3, 40.0, 150.0, "季末考核批量重跑，历史多次迟到"),
    TableSpec("dws.loan_portfolio", "贷款组合", "dws", "P0", "10 6 * * *", "06:10", "dwd.loan_repay", 11,
              "风险管理部", 240.8, 25.0, 24.0, ""),
    TableSpec("dws.member_value", "会员价值", "dws", "P0", "20 6 * * *", "06:20", "dwd.member_wide", 10,
              "零售业务部", 130.5, 20.0, 19.0, ""),
    TableSpec("dws.card_risk_daily", "卡风险日汇总", "dws", "P0", "30 6 * * *", "06:30", "dwd.card_txn_detail", 7,
              "风险管理部", 118.9, 28.0, 27.0, ""),
    TableSpec("dws.repay_health", "还款健康度", "dws", "P0", "40 6 * * *", "06:40", "dwd.repay_overdue", 6,
              "资产管理部", 96.4, 24.0, 23.0, ""),
    TableSpec("dws.collection_eff", "催收效能", "dws", "P2", "50 6 * * *", "06:50", "dwd.collection_daily", 2,
              "资产保全部", 22.1, 18.0, None, "上游整表缺失时联动 unknown"),
    TableSpec("dws.fund_liquidity", "资金流动性", "dws", "P1", "0 7 * * *", "07:00", "dwd.fund_flow_detail", 3,
              "财务部", 88.6, 30.0, 30.0, ""),
    TableSpec("dws.risk_exposure", "风险敞口", "dws", "P1", "10 7 * * *", "07:10", "dwd.risk_event", 4,
              "风险管理部", 104.2, 26.0, 26.0, ""),
    # ---- ADS 应用层（5）----
    TableSpec("ads.loan_risk_daily", "贷款风险日报", "ads", "P0", "0 7 * * *", "07:30", "dws.card_risk_daily", 12,
              "风险管理部", 18.4, 12.0, 42.0, "07:30 前必须出数，供 08:00 风险晨会"),
    TableSpec("ads.exec_dashboard", "高管驾驶舱", "ads", "P0", "40 7 * * *", "07:40", "dws.loan_portfolio", 15,
              "经营分析室", 12.8, 35.0, 34.0, ""),
    TableSpec("ads.regulatory_report", "监管报送宽表", "ads", "P0", "50 7 * * *", "07:50", "dws.repay_health", 8,
              "合规部", 8.6, 45.0, 49.0, "报送窗口固定，晚于 08:30 需报备"),
    TableSpec("ads.branch_scorecard", "网点考核表", "ads", "P1", "0 8 * * *", "08:00", "dws.branch_daily", 6,
              "渠道运营部", 6.3, 20.0, 20.0, ""),
    TableSpec("ads.month_end_growth", "月末增长报表", "ads", "P2", "10 8 * * *", "08:10", "dws.member_value", 3,
              "零售业务部", 3.1, 55.0, 54.0, ""),
]

TABLE_BY_CODE: dict[str, TableSpec] = {spec.code: spec for spec in TABLES}


def history_overrides(code: str) -> dict[int, float]:
    return {offset: minutes for (c, offset), minutes in DELAY_OVERRIDES.items() if c == code}


def missing_history_pairs() -> list[tuple[int, int]]:
    """24 条历史缺失探测：确定性分布，保证 (表下标, day_offset) 唯一。"""
    pairs: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    k = 0
    while len(pairs) < 24:
        table_index = (k * 7 + 3) % len(TABLES)
        offset = -1 - (k % (HISTORY_DAYS - 1))
        key = (table_index, offset)
        if key not in seen:
            seen.add(key)
            pairs.append(key)
        k += 1
    return pairs


MISSING_HISTORY: list[tuple[int, int]] = missing_history_pairs()
