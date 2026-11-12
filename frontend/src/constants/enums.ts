/** 共享枚举（前端镜像）。后端唯一来源：backend/src/constants/enums.py */
import type { BreachSeverity, Grade, HandlingStatus, Layer, ProbeStatus, Role, Tier } from '../types/models';

export const ROLE_LABELS: Record<Role, string> = {
  admin: '平台负责人',
  ops: '值班工程师',
  viewer: '报表 owner（只读）',
};

export const LAYER_LABELS: Record<Layer, string> = {
  ods: 'ODS 贴源',
  dwd: 'DWD 明细',
  dws: 'DWS 汇总',
  ads: 'ADS 应用',
};

export const TIER_LABELS: Record<Tier, string> = {
  P0: 'P0 · 核心链路',
  P1: 'P1 · 经营分析',
  P2: 'P2 · 辅助报表',
};

export const TIER_ORDER: Tier[] = ['P0', 'P1', 'P2'];

export const GRADE_LABELS: Record<Grade, string> = {
  green: '绿 · 健康',
  yellow: '黄 · 关注',
  red: '红 · 超标',
  unknown: '未知 · 缺失',
};

export const GRADE_HINTS: Record<Grade, string> = {
  green: '延迟 ≤ P50',
  yellow: 'P50 < 延迟 ≤ P90',
  red: '延迟 > P90',
  unknown: '探测缺失，不参与判级',
};

export const PROBE_STATUS_LABELS: Record<ProbeStatus, string> = {
  ok: '准点',
  late: '迟到',
  early: '早到',
  missing: '缺失',
};

export const SEVERITY_LABELS: Record<BreachSeverity, string> = {
  warning: '违约',
  severe: '严重',
  escalated: '升级严重',
};

export const SEVERITY_ORDER: BreachSeverity[] = ['warning', 'severe', 'escalated'];

export const HANDLING_LABELS: Record<HandlingStatus, string> = {
  open: '待认领',
  claimed: '处置中',
  resolved: '已复盘',
};

/** 三色灯 → CSS 类名 */
export function lampClass(grade: Grade): string {
  return `lamp ${grade}`;
}

/** 水位条宽度：ratio 2.0（两倍容忍）作为满格，便于横向比较 */
export function waterWidth(ratio: number | null): number {
  if (ratio === null || Number.isNaN(ratio)) return 0;
  return Math.max(0, Math.min(100, ratio * 50));
}
