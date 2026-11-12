/** 角色与权限点（前端只用于"可点/灰化 + 提示"，真正的拦截在后端 RBAC）。 */
import type { Role } from '../types/models';

export const ROLE_ORDER: Role[] = ['admin', 'ops', 'viewer'];

export const ROLE_SCOPE: Record<Role, string> = {
  admin: '表/策略/等级/导出全权，可改容忍值与升级阈值',
  ops: '跑探测、认领违约、写归因、导出复盘；不能改策略与表',
  viewer: '只读看板、表详情、策略与台账；不能运行探测或改任何数据',
};

export const ROLE_CAPABILITIES: Record<Role, string[]> = {
  admin: ['probe:run', 'policy:write', 'policy:preview', 'breach:detect', 'breach:claim', 'breach:resolve', 'export:read', 'audit:read', 'table:write'],
  ops: ['probe:run', 'policy:preview', 'breach:detect', 'breach:claim', 'breach:resolve', 'export:read'],
  viewer: [],
};

export function can(role: Role | undefined, capability: string): boolean {
  if (!role) return false;
  return ROLE_CAPABILITIES[role].includes(capability);
}
