import { GRADE_LABELS } from '../../constants/enums';
import type { Grade } from '../../types/models';

interface Props {
  grade: Grade;
  showLabel?: boolean;
  compact?: boolean;
}

/** 三色灯：低饱和红/黄/绿 + 缺失虚线灯。看板与详情页共用。 */
export function TierLamp({ grade, showLabel = false, compact = false }: Props) {
  const label = GRADE_LABELS[grade] ?? grade;
  return (
    <span className={`lamp ${grade}`} title={label} aria-label={label}>
      <span className="dot" aria-hidden="true" />
      {showLabel ? <span>{compact ? label.split(' ')[0] : label}</span> : null}
    </span>
  );
}
