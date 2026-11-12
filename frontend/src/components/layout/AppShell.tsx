import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { probesApi } from '../../api/probes';
import { ROLE_LABELS } from '../../constants/enums';
import { NAV_ITEMS, PAGE_TITLES, SHIFT } from '../../constants/ui';
import { useAsync } from '../../hooks/useAsync';
import { useAuth } from '../../hooks/useAuth';
import { useClock } from '../../hooks/useClock';
import { Toasts } from '../common/Toasts';
import { shortDateTime } from '../../utils/format';

/** 外壳：左侧值班栏 + 顶部挂板条 + 内容区。所有业务页共用。 */
export function AppShell() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const { clock, date } = useClock();
  const status = useAsync(() => probesApi.status(), []);

  const title =
    PAGE_TITLES[location.pathname] ??
    (location.pathname.startsWith('/tables/') ? '表详情 · 延迟曲线与上游链' : 'FRESHSLA');

  const todayProbed = status.data?.probed_today ?? false;
  const waterline = String(status.data?.latest?.run_date ?? status.data?.today ?? '—');

  return (
    <div className="shell">
      <aside className="rail">
        <div className="brand">
          <div className="brand-mark">
            FRESH<span>SLA</span>
          </div>
          <div className="brand-sub">
            澜河银行 · 数据平台运营组
            <br />
            40 张核心表新鲜度水位挂板
          </div>
        </div>

        <nav className="nav" aria-label="主导航">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              data-index={item.index}
              className={({ isActive }) => (isActive ? 'active' : '')}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="rail-block">
          <div className="mono-label" style={{ marginBottom: 6 }}>
            当前班次
          </div>
          <div className="rail-kv">
            <span>班次</span>
            <b>{SHIFT.name}</b>
          </div>
          <div className="rail-kv">
            <span>值班员</span>
            <b>{SHIFT.operator}</b>
          </div>
          <div className="rail-kv">
            <span>时钟</span>
            <b>{clock}</b>
          </div>
          <div className="rail-kv">
            <span>日期</span>
            <b>{date}</b>
          </div>
        </div>

        <div className="rail-block">
          <div className="mono-label" style={{ marginBottom: 6 }}>
            三色灯口径
          </div>
          <div className="rail-kv">
            <span>绿</span>
            <b>延迟 ≤ P50</b>
          </div>
          <div className="rail-kv">
            <span>黄</span>
            <b>≤ P90</b>
          </div>
          <div className="rail-kv">
            <span>红</span>
            <b>&gt; P90</b>
          </div>
          <div className="rail-kv">
            <span>未知</span>
            <b>探测缺失</b>
          </div>
        </div>

        <div className="rail-foot">
          最近巡检：{waterline}
          <br />
          复盘会：{SHIFT.review}
        </div>
      </aside>

      <div className="main">
        <header className="topstrip">
          <h1>{title}</h1>
          <span className="spacer" />
          <div className="waterline">
            <span className="mono-label">水位</span>
            <b>{waterline}</b>
            <span
              className="tag"
              style={{
                color: todayProbed ? 'var(--lamp-green)' : 'var(--lamp-yellow)',
                borderColor: todayProbed
                  ? 'oklch(0.742 0.088 154 / 0.45)'
                  : 'oklch(0.822 0.098 92 / 0.45)',
              }}
            >
              {todayProbed ? '今日已巡检' : '今日未巡检'}
            </span>
            {status.data?.run ? (
              <span className="num" style={{ color: 'var(--ink-500)', fontSize: 11 }}>
                {shortDateTime(status.data.run.created_at)} · {status.data.run.duration_ms}ms
              </span>
            ) : null}
          </div>
          <span className="spacer" />
          {user ? (
            <div className="inline-actions">
              <span className="tag" title={user.email}>
                {user.display_name.split('（')[0]} · {ROLE_LABELS[user.role]}
              </span>
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => {
                  logout();
                  navigate('/login');
                }}
              >
                退出
              </button>
            </div>
          ) : null}
        </header>

        <main className="page">
          <Outlet />
        </main>
      </div>
      <Toasts />
    </div>
  );
}
