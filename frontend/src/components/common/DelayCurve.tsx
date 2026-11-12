import { useMemo } from 'react';
import type { ProbePoint } from '../../types/models';
import { shortDate } from '../../utils/format';

interface Props {
  points: ProbePoint[];
  p50: number | null;
  p90: number | null;
  toleranceMinutes: number;
  height?: number;
}

const W = 880;

/** 把 y 轴上限取到"好看"的刻度：步长从 5 起，最多 5 格。 */
function niceScale(rawMax: number): { max: number; step: number } {
  const steps = [5, 10, 15, 20, 25, 30, 40, 50, 60, 80, 100, 120, 150, 200, 250, 300, 400];
  for (const step of steps) {
    if (rawMax / step <= 5) return { max: Math.ceil(rawMax / step) * step, step };
  }
  const step = Math.ceil(rawMax / 5 / 100) * 100;
  return { max: Math.ceil(rawMax / step) * step, step };
}
const PAD_L = 46;
const PAD_R = 18;
const PAD_T = 16;
const PAD_B = 28;

/** 近 30 天延迟曲线（纯 SVG 手绘，无图表库）：面积 + 分位虚线 + 违约点 + 缺失断点。 */
export function DelayCurve({ points, p50, p90, toleranceMinutes, height = 268 }: Props) {
  const geometry = useMemo(() => {
    const usable = points.filter((point) => point.delay_minutes !== null);
    const maxDelay = usable.reduce((max, point) => Math.max(max, point.delay_minutes ?? 0), 0);
    const rawMax = Math.max(10, maxDelay * 1.1, (p90 ?? 0) * 1.15, toleranceMinutes * 1.05);
    const { max: yMax, step } = niceScale(rawMax);
    const count = Math.max(points.length, 2);
    const innerW = W - PAD_L - PAD_R;
    const innerH = height - PAD_T - PAD_B;
    const x = (index: number) => PAD_L + (innerW * index) / (count - 1);
    const y = (value: number) => PAD_T + innerH - (innerH * Math.min(value, yMax)) / yMax;

    const segments: { x: number; y: number; point: ProbePoint }[][] = [];
    let current: { x: number; y: number; point: ProbePoint }[] = [];
    points.forEach((point, index) => {
      if (point.delay_minutes === null) {
        if (current.length > 0) segments.push(current);
        current = [];
        return;
      }
      current.push({ x: x(index), y: y(point.delay_minutes), point });
    });
    if (current.length > 0) segments.push(current);

    const ticks = [];
    for (let value = 0; value <= yMax + 0.001; value += step) {
      ticks.push({ value, y: PAD_T + innerH - (innerH * value) / yMax });
    }
    return { yMax, x, y, segments, innerH, innerW, ticks };
  }, [points, p50, p90, toleranceMinutes, height]);

  if (points.length === 0) {
    return (
      <div className="state" role="status">
        <div className="state-title">还没有 30 天延迟序列</div>
        <div className="state-body">这张表尚未采集到探测记录，先到看板点"运行今日探测"。</div>
      </div>
    );
  }

  const { y, segments, innerH, ticks } = geometry;

  return (
    <svg viewBox={`0 0 ${W} ${height}`} role="img" aria-label="近 30 天延迟曲线">
      <defs>
        <clipPath id="curve-clip">
          <rect x={PAD_L} y={PAD_T - 6} width={W - PAD_L - PAD_R} height={innerH + 12} />
        </clipPath>
      </defs>

      {/* 网格与 y 轴刻度 */}
      {ticks.map((tick) => (
        <g key={tick.y}>
          <line
            x1={PAD_L}
            x2={W - PAD_R}
            y1={tick.y}
            y2={tick.y}
            stroke="oklch(0.386 0.011 250 / 0.34)"
            strokeWidth={1}
          />
          <text
            x={PAD_L - 8}
            y={tick.y + 3}
            textAnchor="end"
            fontSize={10}
            fill="oklch(0.556 0.010 250)"
            fontFamily="Sora, sans-serif"
          >
            {Math.round(tick.value)}
          </text>
        </g>
      ))}

      {/* 容忍线（红）与分位线（黄/绿） */}
      <line
        x1={PAD_L}
        x2={W - PAD_R}
        y1={y(toleranceMinutes)}
        y2={y(toleranceMinutes)}
        stroke="oklch(0.638 0.148 27 / 0.55)"
        strokeWidth={1.4}
        strokeDasharray="7 4"
      />
      <text
        x={W - PAD_R}
        y={y(toleranceMinutes) - 5}
        textAnchor="end"
        fontSize={10}
        fill="oklch(0.638 0.148 27 / 0.9)"
        fontFamily="Sora, sans-serif"
      >
        容忍 {toleranceMinutes}m
      </text>

      {p90 !== null ? (
        <>
          <line
            x1={PAD_L}
            x2={W - PAD_R}
            y1={y(p90)}
            y2={y(p90)}
            stroke="oklch(0.822 0.098 92 / 0.42)"
            strokeWidth={1}
            strokeDasharray="3 5"
          />
          <text
            x={PAD_L + 4}
            y={y(p90) - 4}
            fontSize={10}
            fill="oklch(0.822 0.098 92 / 0.85)"
            fontFamily="Sora, sans-serif"
          >
            P90 {p90.toFixed(1)}m
          </text>
        </>
      ) : null}

      {p50 !== null ? (
        <>
          <line
            x1={PAD_L}
            x2={W - PAD_R}
            y1={y(p50)}
            y2={y(p50)}
            stroke="oklch(0.742 0.088 154 / 0.4)"
            strokeWidth={1}
            strokeDasharray="2 6"
          />
          <text
            x={PAD_L + 4}
            y={y(p50) - 4}
            fontSize={10}
            fill="oklch(0.742 0.088 154 / 0.85)"
            fontFamily="Sora, sans-serif"
          >
            P50 {p50.toFixed(1)}m
          </text>
        </>
      ) : null}

      <g clipPath="url(#curve-clip)">
        {segments.map((segment, index) => {
          const line = segment.map((item, i) => `${i === 0 ? 'M' : 'L'}${item.x.toFixed(1)} ${item.y.toFixed(1)}`).join(' ');
          const area = `${line} L${segment[segment.length - 1].x.toFixed(1)} ${PAD_T + innerH} L${segment[0].x.toFixed(1)} ${PAD_T + innerH} Z`;
          return (
            <g key={index}>
              <path d={area} fill="oklch(0.788 0.062 205 / 0.09)" stroke="none" />
              <path
                d={line}
                fill="none"
                stroke="oklch(0.788 0.062 205 / 0.85)"
                strokeWidth={1.6}
                strokeLinejoin="round"
              />
            </g>
          );
        })}

        {points.map((point, index) => {
          if (point.delay_minutes === null) return null;
          const cx = geometry.x(index);
          const cy = y(point.delay_minutes);
          if (point.is_breach) {
            return <circle key={point.probe_date} cx={cx} cy={cy} r={3.6} fill="oklch(0.638 0.148 27)" />;
          }
          if (point.is_early) {
            return (
              <circle
                key={point.probe_date}
                cx={cx}
                cy={cy}
                r={2.8}
                fill="none"
                stroke="oklch(0.742 0.088 154)"
                strokeWidth={1.4}
              />
            );
          }
          if (index === points.length - 1) {
            return (
              <circle
                key={point.probe_date}
                cx={cx}
                cy={cy}
                r={3.4}
                fill="oklch(0.938 0.005 245)"
                stroke="oklch(0.195 0.011 250)"
                strokeWidth={1}
              />
            );
          }
          return null;
        })}
      </g>

      {/* x 轴：首 / 中 / 末日期 */}
      {[0, Math.floor((points.length - 1) / 2), points.length - 1].map((index) => (
        <text
          key={index}
          x={geometry.x(index)}
          y={height - 8}
          textAnchor={index === 0 ? 'start' : index === points.length - 1 ? 'end' : 'middle'}
          fontSize={10}
          fill="oklch(0.556 0.010 250)"
          fontFamily="Sora, sans-serif"
        >
          {shortDate(points[index]?.probe_date)}
        </text>
      ))}

      {points.some((point) => point.is_missing) ? (
        <text
          x={W - PAD_R}
          y={height - 8}
          textAnchor="end"
          fontSize={10}
          fill="oklch(0.638 0.148 27 / 0.8)"
          fontFamily="Sora, sans-serif"
        >
          断点 = 探测缺失
        </text>
      ) : null}
    </svg>
  );
}
