import { ApiError } from '../api/client';

/** 把后端 {code,message,detail} 转成值班员能看懂的一句话。 */
export function describeError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 403) return `${error.message}（角色权限不足，已由后端拦截）`;
    if (error.status === 0) return error.message;
    if (error.status === 429) return '触发限流：一分钟内请求过多，请稍后再试';
    if (error.status === 422 && error.detail) {
      const detail = error.detail as { msg?: string }[] | Record<string, string>;
      if (Array.isArray(detail) && detail.length > 0) {
        return `${error.message}：${detail[0]?.msg ?? ''}`;
      }
      if (typeof detail === 'object' && detail !== null) {
        const first = Object.entries(detail)[0];
        if (first) return `${error.message}：${first[0]} ${String(first[1])}`;
      }
    }
    return error.message;
  }
  if (error instanceof Error) return error.message;
  return '未知错误';
}

/** 403 时给出"谁可以操作"的提示（不修改后端行为，仅 UX）。 */
export function permissionHint(capability: string): string {
  const map: Record<string, string> = {
    'probe:run': '运行探测需要 admin 或 ops 角色',
    'policy:write': '修改 SLA 策略需要 admin（平台负责人）角色',
    'breach:claim': '认领违约需要 admin 或 ops 角色',
    'breach:resolve': '写复盘结论需要 admin 或 ops 角色',
    'export:read': '导出复盘需要 admin 或 ops 角色',
    'table:write': '修改表资产需要 admin 角色',
  };
  return map[capability] ?? '当前角色无权执行该操作';
}
