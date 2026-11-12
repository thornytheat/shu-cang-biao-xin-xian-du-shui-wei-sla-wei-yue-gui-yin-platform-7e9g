/** 展示格式化：全部为纯函数，方便 QA 核对口径。 */

export function formatMinutes(minutes: number | null | undefined): string {
  if (minutes === null || minutes === undefined || Number.isNaN(minutes)) return '—';
  if (minutes < 60) return `${trimZero(minutes)} 分`;
  const hours = Math.floor(minutes / 60);
  const rest = Math.round((minutes - hours * 60) * 10) / 10;
  return `${hours}h${rest > 0 ? `${trimZero(rest)}m` : ''}`;
}

export function formatDelaySeconds(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return '—';
  return formatMinutes(seconds / 60);
}

export function trimZero(value: number): string {
  const fixed = Math.round(value * 10) / 10;
  return Number.isInteger(fixed) ? String(fixed) : fixed.toFixed(1);
}

export function shortDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  return iso.slice(5, 10);
}

export function shortDateTime(value: string | null | undefined): string {
  if (!value) return '—';
  return value.replace('T', ' ').slice(5, 16);
}

export function formatRatio(ratio: number | null | undefined): string {
  if (ratio === null || ratio === undefined) return '—';
  return `${ratio.toFixed(2)}×`;
}

export function formatPercent(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined) return '—';
  return `${value.toFixed(digits)}%`;
}

export function formatSize(gb: number | null | undefined): string {
  if (gb === null || gb === undefined) return '—';
  if (gb < 1) return `${Math.round(gb * 1024)} MB`;
  if (gb < 1024) return `${trimZero(gb)} GB`;
  return `${(gb / 1024).toFixed(2)} TB`;
}

/** 水位文案：容忍倍数 + 是否越线 */
export function waterText(ratio: number | null, tolerance: number): string {
  if (ratio === null) return '缺失';
  const minutes = ratio * tolerance;
  if (ratio > 1) return `越线 ${(ratio - 1).toFixed(2)}×（${formatMinutes(minutes)}）`;
  return `容忍内（${formatMinutes(minutes)} / ${tolerance} 分）`;
}
