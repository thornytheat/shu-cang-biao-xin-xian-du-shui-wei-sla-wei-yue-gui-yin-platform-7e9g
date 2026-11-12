/** UI 常量：导航、班次、页面文案。 */
export const NAV_ITEMS = [
  { to: '/board', index: '01', label: '表健康看板', hint: 'P0/P1/P2 分栏 + 水位条' },
  { to: '/policies', index: '02', label: 'SLA 策略', hint: '容忍值 / 升级规则 / 试算' },
  { to: '/breaches', index: '03', label: '违约台账', hint: '筛选 / 归因 / 认领 / 导出' },
];

export const SHIFT = {
  name: '早班 07:00 - 15:00',
  operator: '周航',
  phone: '内线 8821',
  review: '月度复盘：每月 1 日 10:00',
};

export const BRAND = 'freshsla';
export const BRAND_CN = '数仓新鲜度水位台';
export const DOMAIN = 'freshsla.io';

export const PAGE_TITLES: Record<string, string> = {
  '/board': '表健康看板',
  '/policies': 'SLA 策略管理',
  '/breaches': 'SLA 违约台账',
};

export const DEMO_ACCOUNTS = [
  { email: 'admin@freshsla.io', role: 'admin', label: '平台负责人 · 沈可' },
  { email: 'ops@freshsla.io', role: 'ops', label: '值班工程师 · 周航' },
  { email: 'viewer@freshsla.io', role: 'viewer', label: '报表 owner · 林岚' },
];

export const DEMO_PASSWORD = 'Demo@2026';
