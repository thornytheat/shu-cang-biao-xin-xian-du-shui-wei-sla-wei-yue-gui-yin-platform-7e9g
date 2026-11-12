"""导出服务：违约复盘 CSV（供月度 SLA 复盘会）与复盘 Markdown。"""
from __future__ import annotations

import csv
import io
from datetime import datetime

from sqlalchemy.orm import Session

from src.constants.enums import BreachSeverity, HandlingStatus
from src.services import breach_service
from src.utils.errors import AppError
from src.utils.timeutil import business_now

CSV_HEADER = [
    "违约日期",
    "表名",
    "中文名",
    "等级",
    "延迟分钟",
    "容忍分钟",
    "超时倍数",
    "严重度",
    "连续次数",
    "主因表",
    "贡献占比%",
    "影响报表数",
    "影响分",
    "处置态",
    "认领人",
    "建议动作",
    "复盘结论",
]

SEVERITY_CSV = {
    BreachSeverity.WARNING.value: "违约",
    BreachSeverity.SEVERE.value: "严重",
    BreachSeverity.ESCALATED.value: "升级严重",
}
STATUS_CSV = {
    HandlingStatus.OPEN.value: "待认领",
    HandlingStatus.CLAIMED.value: "处置中",
    HandlingStatus.RESOLVED.value: "已复盘",
}


def breaches_csv(
    db: Session,
    *,
    severity: str | None = None,
    status: str | None = None,
    tier: str | None = None,
    keyword: str | None = None,
    actor_email: str = "",
) -> tuple[str, int, str]:
    rows = breach_service.query(
        db, severity=severity, status=status, tier=tier, keyword=keyword, limit=500
    )
    if not rows:
        raise AppError("EXPORT_EMPTY", 422, detail={"filters": {"severity": severity, "status": status}})

    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(CSV_HEADER)
    for breach, table in rows:
        writer.writerow(
            [
                breach.breach_date.isoformat(),
                table.code,
                table.name,
                table.tier,
                f"{breach.delay_seconds / 60.0:.1f}",
                breach.tolerance_minutes,
                f"{breach.ratio:.2f}",
                SEVERITY_CSV.get(breach.severity, breach.severity),
                breach.consecutive_count,
                breach.primary_cause,
                f"{breach.cause_contribution_pct:.1f}",
                breach.impacted_reports,
                f"{breach.impact_score:.1f}",
                STATUS_CSV.get(breach.handling_status, breach.handling_status),
                breach.claimed_by or "",
                breach.suggested_action or "",
                (breach.root_note or "").replace("\n", " "),
            ]
        )
    stamp = business_now().strftime("%Y%m%d-%H%M")
    filename = f"freshsla-sla-breach-review-{stamp}.csv"
    # BOM 让 Excel 正确识别中文
    return "\ufeff" + buffer.getvalue(), len(rows), filename


def review_markdown(db: Session, *, days: int = 30) -> tuple[str, int, str]:
    rows = breach_service.query(db, limit=500)
    if not rows:
        raise AppError("EXPORT_EMPTY", 422, detail={"scope": "breaches"})

    severe = [item for item in rows if item[0].severity in {BreachSeverity.SEVERE.value, BreachSeverity.ESCALATED.value}]
    lines = [
        "# SLA 违约复盘 · 澜河银行数据平台运营组",
        "",
        f"- 生成时间：{business_now().strftime('%Y-%m-%d %H:%M')}",
        f"- 统计窗口：近 {days} 天",
        f"- 违约总数：**{len(rows)}** 起（严重 {len(severe)} 起）",
        "",
        "## 一、违约明细",
        "",
        "| 日期 | 表 | 等级 | 延迟(分) | 容忍(分) | 倍数 | 严重度 | 连续 | 主因 | 贡献% | 影响分 | 处置 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for breach, table in rows:
        lines.append(
            "| {date} | `{code}` | {tier} | {delay:.1f} | {tol} | {ratio:.2f} | {sev} | {consec} | `{cause}` | "
            "{contrib:.1f} | {score:.1f} | {status} |".format(
                date=breach.breach_date.isoformat(),
                code=table.code,
                tier=table.tier,
                delay=breach.delay_seconds / 60.0,
                tol=breach.tolerance_minutes,
                ratio=breach.ratio,
                sev=SEVERITY_CSV.get(breach.severity, breach.severity),
                consec=breach.consecutive_count,
                cause=breach.primary_cause,
                contrib=breach.cause_contribution_pct,
                score=breach.impact_score,
                status=STATUS_CSV.get(breach.handling_status, breach.handling_status),
            )
        )

    lines += ["", "## 二、主因分布", ""]
    buckets: dict[str, list] = {}
    for breach, _table in rows:
        buckets.setdefault(breach.primary_cause, []).append(breach)
    for cause, items in sorted(buckets.items(), key=lambda pair: -len(pair[1])):
        avg = sum(item.impact_score for item in items) / len(items)
        lines.append(f"- `{cause}`：{len(items)} 起，平均影响分 {avg:.1f}")
    lines += [
        "",
        "## 三、改进项",
        "",
        "1. 对连续违约的表（连续 > 3 次）在调度侧加前置依赖检查，避免整表等上游。",
        "2. 对贡献 > 60% 的上游表补二次探测（02:30 / 03:30），缩短定位时间。",
        "3. 报表 owner 通知改为自动：违约即推送影响报表清单，不再人工群里追问。",
        "",
    ]
    stamp = business_now().strftime("%Y%m%d-%H%M")
    return "\n".join(lines), len(rows), f"freshsla-sla-review-{stamp}.md"


def bundle_meta(row_count: int, generated_at: datetime | None = None) -> dict:
    return {
        "rows": row_count,
        "generated_at": (generated_at or business_now()).isoformat(sep=" "),
    }
