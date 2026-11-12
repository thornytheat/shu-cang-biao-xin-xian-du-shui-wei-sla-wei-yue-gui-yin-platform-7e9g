import { HANDLING_LABELS, SEVERITY_LABELS } from '../../constants/enums';
import type { BreachSeverity, HandlingStatus } from '../../types/models';

/** 违约严重度标签：warning 违约 / severe 严重 / escalated 升级严重。 */
export function SeverityTag({ severity }: { severity: BreachSeverity }) {
  return <span className={`tag sev-${severity}`}>{SEVERITY_LABELS[severity] ?? severity}</span>;
}

/** 处置态标签：待认领 / 处置中 / 已复盘。 */
export function StatusTag({ status }: { status: HandlingStatus }) {
  return <span className={`tag status-${status}`}>{HANDLING_LABELS[status] ?? status}</span>;
}

/** 等级标签：P0/P1/P2。 */
export function TierTag({ tier }: { tier: string }) {
  return <span className={`tag tier-${tier}`}>{tier}</span>;
}

/** 连续违约标记：连续 ≥3 次时高亮（升级规则的可见化）。 */
export function ConsecutiveTag({ count }: { count: number }) {
  if (count <= 1) return <span className="num" style={{ color: 'var(--ink-500)' }}>{count}</span>;
  const hot = count >= 3;
  return (
    <span
      className="num"
      style={{ color: hot ? 'var(--lamp-red)' : 'var(--ink-300)' }}
      title={hot ? `连续 ${count} 次违约，已触发升级规则` : `连续 ${count} 次违约`}
    >
      {count}
      {hot ? ' ↑' : ''}
    </span>
  );
}
