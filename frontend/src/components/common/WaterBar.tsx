import { waterWidth } from '../../constants/enums';
import type { Grade } from '../../types/models';
import { formatMinutes, formatRatio } from '../../utils/format';

interface Props {
  ratio: number | null;
  grade: Grade;
  toleranceMinutes: number;
  showScale?: boolean;
}

/** 条带水位条：0 → 2 倍容忍，刻度线标出"容忍线"（50% 处）。看板与台账共用。 */
export function WaterBar({ ratio, grade, toleranceMinutes, showScale = false }: Props) {
  const width = waterWidth(ratio);
  const title =
    ratio === null
      ? `探测缺失（容忍 ${toleranceMinutes} 分）`
      : `延迟 ${formatMinutes(ratio * toleranceMinutes)} / 容忍 ${toleranceMinutes} 分 = ${formatRatio(ratio)}`;
  return (
    <div className="waterbar-wrap" title={title}>
      <div className={`waterbar ${grade}`} role="img" aria-label={title}>
        <div className="fill" style={{ width: `${width}%` }} />
        <div className="sla-mark" style={{ left: '50%' }} />
      </div>
      {showScale ? (
        <div
          className="num"
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            fontSize: 10,
            color: 'var(--ink-500)',
            marginTop: 2,
          }}
        >
          <span>0</span>
          <span>容忍 {toleranceMinutes} 分</span>
          <span>2×</span>
        </div>
      ) : null}
    </div>
  );
}
