import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { EmptyState } from '../components/common/EmptyState';

/** 路由守卫：未登录跳 /login（带 redirect 参数），首次进入时校验 token。 */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { user, bootstrapped, status } = useAuth();
  const location = useLocation();

  if (!bootstrapped && status === 'loading') {
    return (
      <div style={{ padding: 40 }}>
        <EmptyState title="正在校验登录态…" body="读取本地令牌并向 /api/auth/me 校验角色。" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to={`/login?redirect=${encodeURIComponent(location.pathname)}`} replace />;
  }

  return <>{children}</>;
}
