import { useEffect, useState } from 'react';
import { policiesApi } from '../api/policies';
import { EmptyState, ErrorState, LoadingBlock } from '../components/common/EmptyState';
import { TierLamp } from '../components/common/TierLamp';
import { TierTag } from '../components/common/SeverityTag';
import { TIER_LABELS, TIER_ORDER } from '../constants/enums';
import { can } from '../constants/roles';
import { useAsync } from '../hooks/useAsync';
import { useAuth } from '../hooks/useAuth';
import { useToasts } from '../hooks/useToast';
import type { Policy, PolicyPreview, Tier } from '../types/models';
import { describeError, permissionHint } from '../utils/errorMessage';

type Draft = Record<Tier, { tolerance: number; escalate: number; note: string }>;

const EMPTY_DRAFT: Draft = {
  P0: { tolerance: 60, escalate: 3, note: '' },
  P1: { tolerance: 90, escalate: 3, note: '' },
  P2: { tolerance: 120, escalate: 4, note: '' },
};

/** SLA 策略管理：三档容忍值 / 升级阈值 / 试算（试算走后端真算）。 */
export function Policies() {
  const { user } = useAuth();
  const { toast } = useToasts();
  const state = useAsync(() => policiesApi.list(), []);
  const [draft, setDraft] = useState<Draft>(EMPTY_DRAFT);
  const [preview, setPreview] = useState<PolicyPreview | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [saving, setSaving] = useState<Tier | null>(null);

  useEffect(() => {
    if (!state.data) return;
    const next: Draft = { ...EMPTY_DRAFT };
    state.data.items.forEach((policy) => {
      next[policy.tier] = {
        tolerance: policy.tolerance_minutes,
        escalate: policy.escalate_after,
        note: policy.report_owner_note ?? '',
      };
    });
    setDraft(next);
  }, [state.data]);

  const canWrite = can(user?.role, 'policy:write');
  const canPreview = can(user?.role, 'policy:preview');

  async function onSave(tier: Tier) {
    setSaving(tier);
    try {
      await policiesApi.update(tier, {
        tolerance_minutes: draft[tier].tolerance,
        escalate_after: draft[tier].escalate,
        report_owner_note: draft[tier].note,
      });
      toast(`${tier} 策略已保存：容忍 ${draft[tier].tolerance} 分钟 / 连续 ${draft[tier].escalate} 次升级`, 'ok');
      state.reload();
    } catch (err) {
      toast(`${describeError(err)}｜${permissionHint('policy:write')}`, 'error');
    } finally {
      setSaving(null);
    }
  }

  async function onPreview() {
    setPreviewing(true);
    try {
      const result = await policiesApi.preview({
        p0_tolerance: draft.P0.tolerance,
        p1_tolerance: draft.P1.tolerance,
        p2_tolerance: draft.P2.tolerance,
        escalate_after: draft.P0.escalate,
      });
      setPreview(result);
      toast(
        `试算完成：预计 ${result.totals.breaches} 起违约（严重 ${result.totals.severe} 起，涉及 ${result.totals.affected_tables} 张表）`,
        'ok',
      );
    } catch (err) {
      toast(`${describeError(err)}｜${permissionHint('policy:preview')}`, 'error');
    } finally {
      setPreviewing(false);
    }
  }

  return (
    <>
      <section className="section">
        <div className="section-head">
          <h2>三档 SLA 策略</h2>
          <span className="count num">
            {state.data?.items.length ?? 0} 条 · 改完记得逐档保存
          </span>
          <span className="spacer" style={{ flex: 1 }} />
          {!canWrite ? (
            <span className="tag" style={{ color: 'var(--lamp-yellow)' }}>
              {permissionHint('policy:write')}
            </span>
          ) : null}
        </div>
        <div style={{ fontSize: 12, color: 'var(--ink-400)' }}>
          判级口径固定：延迟 ≤ P50 绿、≤ P90 黄、&gt; P90 红；策略只控制「容忍分钟」与「连续违约升级阈值」。
          连续次数 <b>超过</b> 阈值时升级一级（默认 3 → 第 4 次起升级）。
        </div>
      </section>

      {state.error ? <ErrorState message={state.error} onRetry={state.reload} /> : null}
      {state.loading && !state.data ? (
        <section className="section">
          <LoadingBlock rows={5} />
        </section>
      ) : null}

      {state.data ? (
        <div className="board-grid">
          {TIER_ORDER.map((tier) => {
            const policy: Policy | undefined = state.data?.items.find((item) => item.tier === tier);
            const local = draft[tier];
            return (
              <section className="tier-col" key={tier}>
                <header className="tier-col-head">
                  <TierTag tier={tier} />
                  <span className="tier-sub">{TIER_LABELS[tier].split(' · ')[1]}</span>
                  <span className="counters num">
                    <span style={{ color: 'var(--ink-400)' }}>{policy?.updated_by ?? '未更新'}</span>
                  </span>
                </header>
                <div style={{ padding: 12, display: 'flex', flexDirection: 'column', gap: 10 }}>
                  <div className="inline-actions">
                    <div className="field">
                      <label htmlFor={`tol-${tier}`}>容忍分钟</label>
                      <input
                        id={`tol-${tier}`}
                        type="number"
                        min={10}
                        max={240}
                        value={local.tolerance}
                        disabled={!canWrite}
                        onChange={(event) =>
                          setDraft((prev) => ({
                            ...prev,
                            [tier]: { ...prev[tier], tolerance: Number(event.target.value) },
                          }))
                        }
                        style={{ width: 90 }}
                      />
                    </div>
                    <div className="field">
                      <label htmlFor={`esc-${tier}`}>连续升级 N</label>
                      <input
                        id={`esc-${tier}`}
                        type="number"
                        min={2}
                        max={7}
                        value={local.escalate}
                        disabled={!canWrite}
                        onChange={(event) =>
                          setDraft((prev) => ({
                            ...prev,
                            [tier]: { ...prev[tier], escalate: Number(event.target.value) },
                          }))
                        }
                        style={{ width: 90 }}
                      />
                    </div>
                  </div>
                  <div className="field">
                    <label htmlFor={`note-${tier}`}>通知口径 / 说明</label>
                    <textarea
                      id={`note-${tier}`}
                      rows={3}
                      value={local.note}
                      disabled={!canWrite}
                      onChange={(event) =>
                        setDraft((prev) => ({
                          ...prev,
                          [tier]: { ...prev[tier], note: event.target.value },
                        }))
                      }
                    />
                  </div>
                  <div className="inline-actions">
                    <button
                      type="button"
                      className="btn"
                      onClick={() => onSave(tier)}
                      disabled={!canWrite || saving === tier}
                    >
                      {saving === tier ? '保存中…' : '保存该档'}
                    </button>
                    <span className="num" style={{ fontSize: 11, color: 'var(--ink-500)' }}>
                      基线窗口 {policy?.calibrate_days ?? 30} 天 · {policy?.updated_at?.slice(0, 16) ?? '—'}
                    </span>
                  </div>
                </div>
              </section>
            );
          })}
        </div>
      ) : null}

      <section className="section">
        <div className="section-head">
          <h2>策略试算</h2>
          <span className="count">用近 30 天真实探测回放，不写库</span>
          <span className="spacer" style={{ flex: 1 }} />
          <button type="button" className="btn btn-primary" onClick={onPreview} disabled={previewing}>
            {previewing ? '试算中…' : '用当前输入试算'}
          </button>
        </div>

        <div className="inline-actions" style={{ fontSize: 12, color: 'var(--ink-400)' }}>
          输入：P0 {draft.P0.tolerance}m / P1 {draft.P1.tolerance}m / P2 {draft.P2.tolerance}m，连续 &gt;{' '}
          {draft.P0.escalate} 次升级。试算会按新的容忍值重算 9 起台账的命中情况。
        </div>

        {!canPreview ? (
          <EmptyState title="当前角色不能试算" body={permissionHint('policy:preview')} hint="viewer 只读；可让值班工程师或负责人操作。" />
        ) : null}

        {preview ? (
          <>
            <div className="stat-grid four">
              <div className="stat">
                <div className="k">预计违约</div>
                <div className="v" style={{ color: 'var(--lamp-yellow)' }}>
                  {preview.totals.breaches}
                </div>
              </div>
              <div className="stat">
                <div className="k">其中严重</div>
                <div className="v" style={{ color: 'var(--lamp-red)' }}>
                  {preview.totals.severe}
                </div>
              </div>
              <div className="stat">
                <div className="k">涉及表</div>
                <div className="v">{preview.totals.affected_tables}</div>
              </div>
              <div className="stat">
                <div className="k">回放样本</div>
                <div className="v" style={{ fontSize: 18 }}>
                  {preview.baseline.probe_rows}
                  <small>条探测 / {preview.baseline.window_days} 天</small>
                </div>
              </div>
            </div>

            <table className="ledger">
              <thead>
                <tr>
                  <th>档位</th>
                  <th>容忍</th>
                  <th>违约</th>
                  <th>严重</th>
                  <th>命中的表</th>
                </tr>
              </thead>
              <tbody>
                {preview.tiers.map((tier) => (
                  <tr key={tier.tier}>
                    <td>
                      <TierTag tier={tier.tier} />{' '}
                      <span style={{ color: 'var(--ink-400)' }}>{tier.label.replace(`${tier.tier} · `, '')}</span>
                    </td>
                    <td className="num">{tier.tolerance_minutes} 分</td>
                    <td className="num-cell">{tier.breaches}</td>
                    <td className="num-cell" style={{ color: tier.severe > 0 ? 'var(--lamp-red)' : undefined }}>
                      {tier.severe}
                    </td>
                    <td className="num" style={{ fontSize: 11.5 }}>
                      {tier.tables.length > 0 ? tier.tables.join(' · ') : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {preview.sample.length > 0 ? (
              <div style={{ fontSize: 12, color: 'var(--ink-400)' }}>
                最接近/超出容忍的样本：
                {preview.sample.slice(0, 4).map((item) => (
                  <span key={`${item.table_code}-${item.breach_date}`} style={{ marginLeft: 10 }}>
                    <span className="num">{item.table_code}</span> {item.delay_minutes}m / {item.tolerance_minutes}m ={' '}
                    <b style={{ color: item.ratio > 1 ? 'var(--lamp-red)' : 'var(--ink-300)' }}>
                      {item.ratio.toFixed(2)}×
                    </b>
                  </span>
                ))}
              </div>
            ) : (
              <EmptyState title="这个参数下没有表违约" body="把容忍值调小一点，或者点试算重新回放一次。" />
            )}
          </>
        ) : null}
      </section>

      <div className="legend">
        <span className="inline-actions">
          <TierLamp grade="red" /> 超过容忍即进台账
        </span>
        <span>· 严重：倍数 &gt; 2</span>
        <span>· 升级：连续违约超过阈值升一级</span>
        <span style={{ marginLeft: 'auto' }}>试算接口 POST /api/policies/preview（admin / ops）</span>
      </div>
    </>
  );
}
