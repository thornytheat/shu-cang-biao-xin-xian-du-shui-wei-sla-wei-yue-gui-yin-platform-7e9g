import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { BRAND_CN, DEMO_ACCOUNTS, DEMO_PASSWORD } from '../constants/ui';
import { ROLE_LABELS } from '../constants/enums';
import { useAuth } from '../hooks/useAuth';
import { useClock } from '../hooks/useClock';
import { TierLamp } from '../components/common/TierLamp';
import { Toasts } from '../components/common/Toasts';
import { describeError } from '../utils/errorMessage';

const SAMPLE_LAMPS = [
  { grade: 'red' as const, text: 'dwd.loan_repay · 96 分' },
  { grade: 'yellow' as const, text: 'dwd.member_wide · 18 分' },
  { grade: 'green' as const, text: 'dws.loan_portfolio · 24 分' },
  { grade: 'unknown' as const, text: 'dws.collection_eff · 缺失' },
];

/** 登录页：左侧值班挂板，右侧登录表单（三个演示账号可一键填入）。 */
export function Login() {
  const { login, user, status } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const redirect = params.get('redirect') || '/board';
  const [email, setEmail] = useState('admin@freshsla.io');
  const [password, setPassword] = useState(DEMO_PASSWORD);
  const [error, setError] = useState<string | null>(null);
  const { clock, date } = useClock(1000);

  useEffect(() => {
    if (user) navigate(redirect, { replace: true });
  }, [user, navigate, redirect]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await login(email, password);
      navigate(redirect, { replace: true });
    } catch (err) {
      setError(describeError(err));
    }
  }

  const busy = status === 'loading';

  return (
    <div className="login">
      <section className="login-board">
        <div className="brand" style={{ gap: 2 }}>
          <div className="brand-mark" style={{ fontSize: 15, letterSpacing: '0.28em' }}>
            FRESH<span>SLA</span>
          </div>
          <div className="mono-label">澜河银行 · 数据平台运营组 · 值班挂板</div>
        </div>

        <h1 className="login-title">
          谁延迟、延迟多久、<br />
          影响哪些报表——<em>一块挂板说清</em>。
        </h1>

        <p className="login-lede">
          380 张表里挑出 40 张核心表：每天 08:10 自动跑一次新鲜度巡检，
          用近 30 天分位判定三色灯；超过容忍分钟即进违约台账，按上游链路归因到具体那张表。
        </p>

        <div className="login-clock">
          {clock}
          <small>{date} · 早班</small>
        </div>

        <div className="login-facts">
          <div>
            <div className="k">核心表</div>
            <div className="v num">40</div>
          </div>
          <div>
            <div className="k">近 30 天探测</div>
            <div className="v num">1,200</div>
          </div>
          <div>
            <div className="k">违约台账</div>
            <div className="v num">9</div>
          </div>
        </div>

        <div className="login-lamps">
          {SAMPLE_LAMPS.map((item) => (
            <span key={item.text} className="inline-actions">
              <TierLamp grade={item.grade} />
              <span className="num" style={{ fontSize: 11, color: 'var(--ink-400)' }}>
                {item.text}
              </span>
            </span>
          ))}
        </div>

        <div className="legend" style={{ marginTop: 'auto' }}>
          <span>{BRAND_CN}</span>
          <span>·</span>
          <span>绿 ≤ P50 / 黄 ≤ P90 / 红 &gt; P90</span>
          <span>·</span>
          <span>探测缺失 → unknown 不参与判级</span>
        </div>
      </section>

      <section className="login-form-side">
        <div className="mono-label">值班登录 · {DEMO_PASSWORD}</div>
        <h2 style={{ color: 'var(--paper-50)' }}>进入新鲜度挂板</h2>

        <form className="login-form" onSubmit={onSubmit}>
          <div className="field">
            <label htmlFor="email">邮箱</label>
            <input
              id="email"
              type="email"
              autoComplete="username"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="admin@freshsla.io"
              required
            />
          </div>
          <div className="field">
            <label htmlFor="password">密码</label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder={DEMO_PASSWORD}
              required
            />
          </div>

          {error ? (
            <div className="state error" role="alert" style={{ padding: '10px 12px' }}>
              <div className="state-body" style={{ color: 'var(--paper-100)' }}>
                {error}
              </div>
            </div>
          ) : null}

          <button type="submit" className="btn btn-primary" disabled={busy}>
            {busy ? '校验中…' : '登录'}
          </button>
        </form>

        <div className="field" style={{ gap: 6 }}>
          <span className="label">演示账号（点击填入）</span>
          <div className="account-list">
            {DEMO_ACCOUNTS.map((account) => (
              <button
                key={account.email}
                type="button"
                className="account-chip"
                onClick={() => {
                  setEmail(account.email);
                  setPassword(DEMO_PASSWORD);
                  setError(null);
                }}
              >
                <span>{account.email}</span>
                <span className="role">
                  {account.label.split(' · ')[1]} · {ROLE_LABELS[account.role as 'admin']}
                </span>
              </button>
            ))}
          </div>
        </div>

        <p className="hint">
          viewer 登录后只能看：看板、表详情、策略与台账都是只读；
          试试点"运行今日探测"或改容忍值，后端会真的返回 403。
        </p>
      </section>
      <Toasts />
    </div>
  );
}
