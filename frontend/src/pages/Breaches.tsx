import { Fragment, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { breachesApi } from '../api/breaches';
import { EmptyState, ErrorState, LoadingBlock } from '../components/common/EmptyState';
import { ConsecutiveTag, SeverityTag, StatusTag, TierTag } from '../components/common/SeverityTag';
import { HANDLING_LABELS, SEVERITY_LABELS, SEVERITY_ORDER } from '../constants/enums';
import { can } from '../constants/roles';
import { useAsync } from '../hooks/useAsync';
import { useAuth } from '../hooks/useAuth';
import { useToasts } from '../hooks/useToast';
import type { Breach, BreachSeverity, HandlingStatus, Tier } from '../types/models';
import { describeError, permissionHint } from '../utils/errorMessage';
import { formatPercent, formatRatio, shortDate, shortDateTime, trimZero } from '../utils/format';

/** SLA 违约台账：筛选 → 归因 → 认领 → 复盘 → 导出 CSV（链路第 4/5 段）。 */
export function Breaches() {
  const { user } = useAuth();
  const { toast } = useToasts();
  const [searchParams] = useSearchParams();

  const [severity, setSeverity] = useState<BreachSeverity | ''>('');
  const [status, setStatus] = useState<HandlingStatus | ''>('');
  const [tier, setTier] = useState<Tier | ''>('');
  const [keyword, setKeyword] = useState(searchParams.get('q') ?? '');
  const [expanded, setExpanded] = useState<number | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [note, setNote] = useState('');

  const state = useAsync(
    () =>
      breachesApi.list({
        severity: severity || undefined,
        status: status || undefined,
        tier: tier || undefined,
        q: keyword || undefined,
      }),
    [severity, status, tier, keyword],
  );

  const canAct = can(user?.role, 'breach:claim');
  const canExport = can(user?.role, 'export:read');
  const items = state.data?.items ?? [];
  const summary = state.data?.summary;

  async function onDetect() {
    setBusy('detect');
    try {
      const result = await breachesApi.detect(30, false);
      toast(`检测完成：扫描 ${result.scanned} 起，新增 ${result.created} 起，更新 ${result.updated} 起`, 'ok');
      state.reload();
    } catch (err) {
      toast(`${describeError(err)}｜${permissionHint('breach:claim')}`, 'error');
    } finally {
      setBusy(null);
    }
  }

  async function onClaim(item: Breach) {
    setBusy(`claim-${item.id}`);
    try {
      await breachesApi.claim(item.id);
      toast(`已认领 ${item.table_code} ${item.breach_date}`, 'ok');
      state.reload();
    } catch (err) {
      toast(`${describeError(err)}｜${permissionHint('breach:claim')}`, 'error');
    } finally {
      setBusy(null);
    }
  }

  async function onResolve(item: Breach) {
    setBusy(`resolve-${item.id}`);
    try {
      await breachesApi.resolve(item.id, note || '上游批次延迟，已与上游对齐并通知报表 owner 顺延');
      toast(`已复盘 ${item.table_code} ${item.breach_date}`, 'ok');
      setNote('');
      state.reload();
    } catch (err) {
      toast(`${describeError(err)}｜${permissionHint('breach:resolve')}`, 'error');
    } finally {
      setBusy(null);
    }
  }

  async function onExport(kind: 'csv' | 'md') {
    setBusy(`export-${kind}`);
    try {
      const filename =
        kind === 'csv'
          ? await breachesApi.exportCsv({
              severity: severity || undefined,
              status: status || undefined,
              tier: tier || undefined,
              q: keyword || undefined,
            })
          : await breachesApi.exportMarkdown();
      toast(`已下载 ${filename}`, 'ok');
    } catch (err) {
      toast(`${describeError(err)}｜${permissionHint('export:read')}`, 'error');
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      <section className="section">
        <div className="section-head">
          <h2>违约台账</h2>
          <span className="count num">
            {summary?.total ?? '—'} 起 · 严重 {summary?.severe_total ?? '—'} 起 · 待认领{' '}
            {summary?.by_status?.open ?? '—'} 起
          </span>
          <span className="spacer" style={{ flex: 1 }} />
          <div className="inline-actions">
            <button type="button" className="btn" onClick={onDetect} disabled={busy === 'detect'}>
              {busy === 'detect' ? '检测中…' : '检测违约'}
            </button>
            <button type="button" className="btn btn-primary" onClick={() => onExport('csv')} disabled={busy === 'export-csv'}>
              {busy === 'export-csv' ? '导出中…' : '导出复盘 CSV'}
            </button>
            <button type="button" className="btn btn-ghost" onClick={() => onExport('md')} disabled={busy === 'export-md'}>
              复盘 MD
            </button>
          </div>
        </div>

        <div className="filters">
          <div className="field">
            <label htmlFor="sev">严重度</label>
            <select id="sev" value={severity} onChange={(event) => setSeverity(event.target.value as BreachSeverity | '')}>
              <option value="">全部</option>
              {SEVERITY_ORDER.map((value) => (
                <option key={value} value={value}>
                  {SEVERITY_LABELS[value]}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="status">处置态</label>
            <select id="status" value={status} onChange={(event) => setStatus(event.target.value as HandlingStatus | '')}>
              <option value="">全部</option>
              {Object.entries(HANDLING_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="tier">等级</label>
            <select id="tier" value={tier} onChange={(event) => setTier(event.target.value as Tier | '')}>
              <option value="">全部</option>
              <option value="P0">P0</option>
              <option value="P1">P1</option>
              <option value="P2">P2</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="kw">表 / 主因</label>
            <input
              id="kw"
              type="text"
              value={keyword}
              onChange={(event) => setKeyword(event.target.value)}
              placeholder="如 loan_repay"
              style={{ width: 180 }}
            />
          </div>
          <button
            type="button"
            className="btn btn-ghost"
            onClick={() => {
              setSeverity('');
              setStatus('');
              setTier('');
              setKeyword('');
            }}
          >
            清空筛选
          </button>
        </div>

        {!canAct ? (
          <div className="inline-actions" style={{ fontSize: 12, color: 'var(--ink-400)' }}>
            <span className="tag" style={{ color: 'var(--lamp-yellow)' }}>
              {permissionHint('breach:claim')}
            </span>
            <span>按钮仍可点击，用于验证后端真实 403（不是前端隐藏）。</span>
          </div>
        ) : null}
        {!canExport ? (
          <div style={{ fontSize: 12, color: 'var(--ink-500)' }}>{permissionHint('export:read')}</div>
        ) : null}
      </section>

      {state.error ? <ErrorState message={state.error} onRetry={state.reload} /> : null}
      {state.loading && !state.data ? (
        <section className="section">
          <LoadingBlock rows={6} />
        </section>
      ) : null}

      {state.data ? (
        <section className="section" style={{ padding: 0, gap: 0 }}>
          <div style={{ padding: '12px 14px', borderBottom: '1px solid var(--line)' }} className="inline-actions">
            <span className="mono-label">台账明细</span>
            <span className="num" style={{ fontSize: 12, color: 'var(--ink-400)' }}>
              {items.length} 行（告警 → 认领 → 复盘；点击行展开上游链路）
            </span>
            <span className="spacer" style={{ flex: 1 }} />
            <span className="num" style={{ fontSize: 11, color: 'var(--ink-500)' }}>
              主因最多：{summary?.top_impact ?? '—'}
            </span>
          </div>

          {items.length === 0 ? (
            <div style={{ padding: 16 }}>
              <EmptyState
                title="当前筛选下没有违约记录"
                body="把严重度/处置态切回“全部”，或点“检测违约”用近 30 天探测重算一次。"
                action={
                  <button
                    type="button"
                    className="btn"
                    onClick={() => {
                      setSeverity('');
                      setStatus('');
                      setTier('');
                      setKeyword('');
                    }}
                  >
                    清空筛选
                  </button>
                }
              />
            </div>
          ) : (
            <table className="ledger">
              <thead>
                <tr>
                  <th>日期</th>
                  <th>表</th>
                  <th>等级</th>
                  <th style={{ textAlign: 'right' }}>延迟</th>
                  <th style={{ textAlign: 'right' }}>倍数</th>
                  <th>严重度</th>
                  <th>连续</th>
                  <th>主因 / 贡献</th>
                  <th style={{ textAlign: 'right' }}>影响分</th>
                  <th>处置</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => {
                  const isOpen = expanded === item.id;
                  return (
                    <Fragment key={item.id}>
                      <tr
                        className={item.handling_status === 'open' ? 'is-open' : ''}
                        onClick={() => setExpanded(isOpen ? null : item.id)}
                        style={{ cursor: 'pointer' }}
                      >
                        <td className="num">{shortDate(item.breach_date)}</td>
                        <td>
                          <div className="num" style={{ fontSize: 12.5 }}>{item.table_code}</div>
                          <div style={{ fontSize: 11, color: 'var(--ink-500)' }}>{item.table_name}</div>
                        </td>
                        <td>
                          <TierTag tier={item.tier} />
                        </td>
                        <td className="num-cell">{trimZero(item.delay_minutes)} 分</td>
                        <td className="num-cell" style={{ color: item.ratio > 1 ? 'var(--lamp-red)' : undefined }}>
                          {formatRatio(item.ratio)}
                        </td>
                        <td>
                          <SeverityTag severity={item.severity} />
                        </td>
                        <td>
                          <ConsecutiveTag count={item.consecutive_count} />
                        </td>
                        <td>
                          <span className="cause">{item.primary_cause}</span>
                          <div className="num" style={{ fontSize: 11, color: 'var(--ink-500)' }}>
                            贡献 {formatPercent(item.cause_contribution_pct)} · 报表 {item.impacted_reports} 张
                          </div>
                        </td>
                        <td className="num-cell" style={{ fontSize: 14 }}>
                          {item.impact_score.toFixed(1)}
                        </td>
                        <td>
                          <StatusTag status={item.handling_status} />
                          {item.claimed_by ? (
                            <div style={{ fontSize: 10.5, color: 'var(--ink-500)' }}>
                              {item.claimed_by.split('@')[0]}
                            </div>
                          ) : null}
                        </td>
                        <td onClick={(event) => event.stopPropagation()}>
                          <div className="inline-actions">
                            <button
                              type="button"
                              className="btn btn-ghost"
                              style={{ padding: '3px 8px', fontSize: 11.5 }}
                              onClick={() => onClaim(item)}
                              disabled={busy === `claim-${item.id}` || item.handling_status !== 'open'}
                            >
                              {busy === `claim-${item.id}` ? '…' : '认领'}
                            </button>
                            <button
                              type="button"
                              className="btn btn-ghost"
                              style={{ padding: '3px 8px', fontSize: 11.5 }}
                              onClick={() => setExpanded(item.id)}
                            >
                              {isOpen ? '收起' : '归因'}
                            </button>
                          </div>
                        </td>
                      </tr>
                      {isOpen ? (
                        <tr>
                          <td colSpan={11} style={{ background: 'oklch(0.214 0.012 250 / 0.6)', padding: 14 }}>
                            <div className="detail-grid" style={{ gridTemplateColumns: 'minmax(0,1fr) minmax(0,1fr)' }}>
                              <div>
                                <div className="mono-label" style={{ marginBottom: 6 }}>
                                  上游链路（按链路顺序取最大贡献）
                                </div>
                                <div className="chain">
                                  {(item.attribution_detail?.chain ?? []).map((node) => (
                                    <div className="chain-node" key={node.code}>
                                      <span className="rail-dot" />
                                      <div className="meta">
                                        <b className="num">{node.code}</b>
                                        <span>
                                          {node.name} · {node.tier} · 依据 {node.basis}
                                        </span>
                                      </div>
                                      <div className="val">
                                        {node.delay_minutes === null ? '缺失' : `${node.delay_minutes} 分`}
                                        <small>贡献 {node.contribution_pct}%</small>
                                      </div>
                                    </div>
                                  ))}
                                  {(item.attribution_detail?.chain ?? []).length === 0 ? (
                                    <div style={{ fontSize: 12, color: 'var(--ink-400)' }}>
                                      该表无上游登记 → 归因为 self（表内计算）。
                                    </div>
                                  ) : null}
                                </div>
                                <div style={{ marginTop: 8, fontSize: 12, color: 'var(--ink-300)' }}>
                                  影响分 = 0.45×贡献 {item.cause_contribution_pct}% + 0.35×报表覆盖（
                                  {item.impacted_reports} 张）+ 0.20×超时倍数（{item.ratio.toFixed(2)}×）= {' '}
                                  <b className="num" style={{ color: 'var(--signal)' }}>{item.impact_score.toFixed(1)}</b>
                                </div>
                              </div>
                              <div>
                                <div className="mono-label" style={{ marginBottom: 6 }}>
                                  建议动作
                                </div>
                                <div style={{ fontSize: 12.5, color: 'var(--paper-100)', lineHeight: 1.7 }}>
                                  {item.suggested_action}
                                </div>
                                <div className="rail-kv">
                                  <span>认领人</span>
                                  <b>{item.claimed_by ?? '未认领'}</b>
                                </div>
                                <div className="rail-kv">
                                  <span>认领时间</span>
                                  <b>{shortDateTime(item.claimed_at)}</b>
                                </div>
                                <div className="rail-kv">
                                  <span>复盘时间</span>
                                  <b>{shortDateTime(item.resolved_at)}</b>
                                </div>
                                {item.root_note ? (
                                  <div style={{ fontSize: 12, color: 'var(--ink-300)', marginTop: 4 }}>
                                    复盘结论：{item.root_note}
                                  </div>
                                ) : null}
                                <div className="field" style={{ marginTop: 10 }}>
                                  <label htmlFor={`note-${item.id}`}>复盘结论</label>
                                  <textarea
                                    id={`note-${item.id}`}
                                    rows={2}
                                    value={note}
                                    onChange={(event) => setNote(event.target.value)}
                                    placeholder="如：上游 ods.loan_event 01:00 批次因核心系统批量延迟 59.5 分钟"
                                  />
                                </div>
                                <button
                                  type="button"
                                  className="btn"
                                  onClick={() => onResolve(item)}
                                  disabled={busy === `resolve-${item.id}` || item.handling_status === 'resolved'}
                                >
                                  {busy === `resolve-${item.id}` ? '提交中…' : '提交复盘'}
                                </button>
                              </div>
                            </div>
                          </td>
                        </tr>
                      ) : null}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          )}
        </section>
      ) : null}

      <div className="legend">
        <span>主因 = 上游链路上当日延迟贡献最大的表</span>
        <span>· 全链路无就绪事件 → undetermined</span>
        <span>· 导出 CSV 含 {items.length} 行</span>
        <span style={{ marginLeft: 'auto' }}>GET /api/exports/breaches.csv（admin / ops）</span>
      </div>
    </>
  );
}
