import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { breachesApi } from '../api/breaches';
import { tablesApi } from '../api/tables';
import { DelayCurve } from '../components/common/DelayCurve';
import { EmptyState, ErrorState, LoadingBlock } from '../components/common/EmptyState';
import { ConsecutiveTag, SeverityTag, StatusTag, TierTag, VoidedTag } from '../components/common/SeverityTag';
import { TierLamp } from '../components/common/TierLamp';
import { WaterBar } from '../components/common/WaterBar';
import { LAYER_LABELS, GRADE_LABELS, GRADE_HINTS, PROBE_STATUS_LABELS } from '../constants/enums';
import { can } from '../constants/roles';
import { useAsync } from '../hooks/useAsync';
import { useAuth } from '../hooks/useAuth';
import { useToasts } from '../hooks/useToast';
import { describeError, permissionHint } from '../utils/errorMessage';
import { formatMinutes, formatRatio, formatSize, shortDate, trimZero } from '../utils/format';

/** 表详情：近 30 天延迟曲线 + 分位 + 上游链 + 该表违约记录（链路第 2/3 段）。 */
export function TableDetail() {
  const { code = '' } = useParams();
  const { user } = useAuth();
  const { toast } = useToasts();
  const series = useAsync(() => tablesApi.series(code, 30), [code]);
  const breaches = useAsync(() => breachesApi.list({ q: code, includeVoided: true }), [code]);

  const [clock, setClock] = useState('');
  const [reports, setReports] = useState<number>(0);
  const [saving, setSaving] = useState(false);

  const [bfDate, setBfDate] = useState('');
  const [bfTime, setBfTime] = useState('');
  const [bfNote, setBfNote] = useState('');
  const [bfBusy, setBfBusy] = useState(false);

  useEffect(() => {
    if (series.data) {
      setClock(series.data.table.expected_ready_clock);
      setReports(series.data.table.report_count);
      setBfDate(series.data.evaluation.latest?.probe_date ?? '');
      setBfTime(series.data.table.expected_ready_clock);
    }
  }, [series.data]);

  const canEdit = can(user?.role, 'table:write');
  const canBackfill = can(user?.role, 'probe:run');

  async function onSave() {
    setSaving(true);
    try {
      await tablesApi.update(code, { expected_ready_clock: clock, report_count: reports });
      toast(`${code} 已更新：期望就绪 ${clock}、影响报表 ${reports} 张`, 'ok');
      series.reload();
    } catch (err) {
      toast(`${describeError(err)}｜${permissionHint('table:write')}`, 'error');
    } finally {
      setSaving(false);
    }
  }

  async function onBackfill() {
    if (!bfDate || !bfTime) {
      toast('请填写分区日期与实际就绪时间', 'error');
      return;
    }
    setBfBusy(true);
    try {
      const result = await tablesApi.backfill(code, {
        probe_date: bfDate,
        actual_ready_at: `${bfDate} ${bfTime}`,
        note: bfNote || undefined,
      });
      const before = result.before?.delay_minutes;
      const detection = result.breaches;
      toast(
        `已补录 ${result.probe_date}：延迟 ${before ?? '—'} → ${result.after.delay_minutes} 分钟` +
          (detection
            ? `；台账重算：作废 ${detection.voided} · 删除 ${detection.deleted} · 更新 ${detection.updated}`
            : ''),
        'ok',
      );
      setBfNote('');
      series.reload();
      breaches.reload();
    } catch (err) {
      toast(`${describeError(err)}｜${permissionHint('probe:run')}`, 'error');
    } finally {
      setBfBusy(false);
    }
  }

  if (series.error) {
    return (
      <ErrorState
        message={series.error}
        onRetry={series.reload}
        hint="表 code 区分大小写，例如 dwd.loan_repay；也可能是后端刚重启。"
      />
    );
  }

  if (series.loading && !series.data) {
    return (
      <section className="section">
        <LoadingBlock rows={7} />
      </section>
    );
  }

  const data = series.data;
  if (!data) {
    return <EmptyState title="没有拿到这张表的数据" body="返回看板重新点进来。" />;
  }

  const evaluation = data.evaluation;
  const stats = data.stats;
  const chain = data.chain;
  const breachItems = breaches.data?.items ?? [];
  const activeBreachCount = breachItems.filter((item) => !item.is_voided).length;
  const voidedBreachCount = breachItems.length - activeBreachCount;

  return (
    <>
      <section className="section">
        <div className="section-head">
          <Link to="/board" className="btn btn-ghost" style={{ padding: '4px 9px' }}>
            ← 看板
          </Link>
          <h2 className="num" style={{ fontSize: 18 }}>
            {data.table.code}
          </h2>
          <span style={{ color: 'var(--ink-300)', fontSize: 13 }}>{data.table.name}</span>
          <TierTag tier={data.table.tier} />
          <span className="tag">{LAYER_LABELS[data.table.layer]}</span>
          <TierLamp grade={evaluation.grade} showLabel />
          <span className="spacer" style={{ flex: 1 }} />
          <span className="num" style={{ fontSize: 12, color: 'var(--ink-400)' }}>
            cron `{data.table.schedule_cron}` · 期望 {data.table.expected_ready_clock} 就绪 · {formatSize(data.table.size_gb)}
          </span>
        </div>

        <div className="inline-actions" style={{ fontSize: 12, color: 'var(--ink-400)' }}>
          <span>责任人 {data.table.owner_team}</span>
          <span>·</span>
          <span>影响报表 {data.table.report_count} 张</span>
          <span>·</span>
          <span>上游 {data.table.upstream_code ?? '（无登记，延迟发生在表内）'}</span>
          {data.table.owner_note ? (
            <>
              <span>·</span>
              <span style={{ color: 'var(--ink-300)' }}>备注：{data.table.owner_note}</span>
            </>
          ) : null}
        </div>
      </section>

      <div className="detail-grid">
        <section className="section" style={{ gap: 12 }}>
          <div className="section-head">
            <h2>近 30 天延迟曲线</h2>
            <span className="count num">
              {stats.samples} 个有效样本 · 缺失 {stats.missing} 天 · 违约 {stats.breach_days} 天
            </span>
          </div>
          <div className="curve-wrap">
            <DelayCurve
              points={data.points}
              p50={evaluation.percentiles.p50}
              p90={evaluation.percentiles.p90}
              toleranceMinutes={evaluation.tolerance_minutes}
            />
            <div className="legend">
              <span>—— 实际延迟</span>
              <span style={{ color: 'var(--lamp-green)' }}>···· P50</span>
              <span style={{ color: 'var(--lamp-yellow)' }}>··· P90</span>
              <span style={{ color: 'var(--lamp-red)' }}>--- 容忍线 {evaluation.tolerance_minutes}m</span>
              <span style={{ marginLeft: 'auto' }}>
                均值 {formatMinutes(stats.avg_minutes)} · 中位 {formatMinutes(stats.median_minutes)} · 峰值{' '}
                {formatMinutes(stats.max_minutes)}
              </span>
            </div>
          </div>

          <div className="stat-grid">
            <div className="stat">
              <div className="k">最新延迟</div>
              <div className="v">
                {evaluation.latest?.delay_minutes === null || evaluation.latest === null
                  ? '—'
                  : trimZero(evaluation.latest.delay_minutes)}
                <small>分</small>
              </div>
            </div>
            <div className="stat">
              <div className="k">容忍 / 倍数</div>
              <div className="v">
                {evaluation.tolerance_minutes}
                <small>分 · {formatRatio(evaluation.latest?.ratio ?? null)}</small>
              </div>
            </div>
            <div className="stat">
              <div className="k">P50 / P90 / P95</div>
              <div className="v" style={{ fontSize: 17 }}>
                {fmtP(evaluation.percentiles.p50)} / {fmtP(evaluation.percentiles.p90)} /{' '}
                {fmtP(evaluation.percentiles.p95)}
                <small>分</small>
              </div>
            </div>
            <div className="stat">
              <div className="k">基线样本 / 准点率</div>
              <div className="v" style={{ fontSize: 17 }}>
                {evaluation.baseline_days}
                <small>
                  天 · {evaluation.on_time_rate === null ? '—' : `${(evaluation.on_time_rate * 100).toFixed(0)}%`}
                </small>
              </div>
            </div>
          </div>
        </section>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <section className="section">
            <div className="section-head">
              <h2>今日水位</h2>
              <TierLamp grade={evaluation.grade} showLabel />
            </div>
            <div style={{ fontSize: 12.5, color: 'var(--ink-300)', lineHeight: 1.7 }}>{evaluation.grade_reason}</div>
            <WaterBar
              ratio={evaluation.latest?.ratio ?? null}
              grade={evaluation.grade}
              toleranceMinutes={evaluation.tolerance_minutes}
              showScale
            />
            <div className="rail-kv">
              <span>探测日</span>
              <b>{evaluation.latest?.probe_date ?? '—'}</b>
            </div>
            <div className="rail-kv">
              <span>期望就绪</span>
              <b>{evaluation.latest?.expected_ready_at?.slice(5, 16) ?? '—'}</b>
            </div>
            <div className="rail-kv">
              <span>实际就绪</span>
              <b>{evaluation.latest?.actual_ready_at?.slice(5, 16) ?? '缺失'}</b>
            </div>
            <div className="rail-kv">
              <span>状态</span>
              <b>
                {evaluation.latest
                  ? `${PROBE_STATUS_LABELS[evaluation.latest.status]}${evaluation.latest.is_early ? '（负延迟截 0）' : ''}`
                  : '—'}
              </b>
            </div>
            <div className="rail-kv">
              <span>基线缺失</span>
              <b>{evaluation.missing_in_window} 天</b>
            </div>
            <div style={{ fontSize: 11, color: 'var(--ink-500)' }}>{GRADE_HINTS[evaluation.grade]}</div>
          </section>

          <section className="section">
            <div className="section-head">
              <h2>补录就绪时间</h2>
              <span className="count num">补采迟到对账</span>
            </div>
            <div style={{ fontSize: 12, color: 'var(--ink-400)', lineHeight: 1.6 }}>
              就绪事件补采迟到时，按分区补录实际就绪时间；保存后自动重算该日及后续连续违约——
              未处置的误违约删除，已认领/复盘的标作废并保留处置痕迹。
            </div>
            <div className="inline-actions">
              <div className="field">
                <label htmlFor="bf-date">分区日期</label>
                <input
                  id="bf-date"
                  type="date"
                  value={bfDate}
                  onChange={(event) => setBfDate(event.target.value)}
                  style={{ width: 142 }}
                />
              </div>
              <div className="field">
                <label htmlFor="bf-time">实际就绪</label>
                <input
                  id="bf-time"
                  type="time"
                  value={bfTime}
                  onChange={(event) => setBfTime(event.target.value)}
                  style={{ width: 96 }}
                />
              </div>
              <button type="button" className="btn" onClick={onBackfill} disabled={bfBusy}>
                {bfBusy ? '补录中…' : '补录并重算'}
              </button>
            </div>
            <div className="field">
              <label htmlFor="bf-note">备注（可选）</label>
              <input
                id="bf-note"
                type="text"
                value={bfNote}
                onChange={(event) => setBfNote(event.target.value)}
                placeholder="如：调度系统 03:30 就绪事件补采迟到"
              />
            </div>
            <div style={{ fontSize: 11, color: 'var(--ink-500)' }}>
              {canBackfill
                ? '幂等：重复提交不新增记录、不重复升级；巡检不会覆盖人工补录'
                : permissionHint('probe:run')}
            </div>
          </section>

          <section className="section">
            <div className="section-head">
              <h2>上游链</h2>
              <span className="count num">{chain.nodes.length} 跳</span>
            </div>
            <div className="chain">
              {chain.nodes.length <= 1 ? (
                <div style={{ fontSize: 12.5, color: 'var(--ink-400)' }}>
                  没有登记上游：这张表的延迟发生在表内计算（归因结论为 self）。
                </div>
              ) : null}
              {chain.nodes.map((node, index) => {
                const isSelf = node.code === data.table.code;
                const own = breaches.data?.items.find(
                  (item) => item.table_code === node.code && item.breach_date === chain.probe_date,
                );
                return (
                  <div className="chain-node" key={node.code}>
                    <span
                      className="rail-dot"
                      style={
                        isSelf
                          ? { background: 'var(--signal)', borderColor: 'var(--signal)' }
                          : undefined
                      }
                    />
                    <div className="meta">
                      <b className="num">
                        {node.code}
                        {isSelf ? <span style={{ color: 'var(--signal)', fontSize: 10 }}> · 本表</span> : null}
                      </b>
                      <span>
                        {node.name} · {LAYER_LABELS[node.layer]} · {PROBE_STATUS_LABELS[node.status as 'ok'] ?? node.status}
                        {typeof own?.cause_contribution_pct === 'number'
                          ? ` · 归因贡献 ${own.cause_contribution_pct}%`
                          : ''}
                      </span>
                    </div>
                    <div className="val">
                      {node.delay_minutes === null ? '缺失' : `${trimZero(node.delay_minutes)} 分`}
                      <small>报表 {node.report_count} 张</small>
                    </div>
                  </div>
                );
              })}
            </div>
            {chain.downstream.length > 0 ? (
              <div style={{ fontSize: 12, color: 'var(--ink-400)', marginTop: 6 }}>
                下游：{chain.downstream.map((item) => `${item.code}(${item.tier})`).join('、')}
              </div>
            ) : null}
          </section>

          <section className="section">
            <div className="section-head">
              <h2>{canEdit ? '维护表资产' : '表资产（只读）'}</h2>
            </div>
            <div className="inline-actions">
              <div className="field">
                <label htmlFor="clock">期望就绪</label>
                <input
                  id="clock"
                  type="text"
                  value={clock}
                  onChange={(event) => setClock(event.target.value)}
                  style={{ width: 84 }}
                  disabled={!canEdit}
                  placeholder="03:30"
                />
              </div>
              <div className="field">
                <label htmlFor="reports">影响报表数</label>
                <input
                  id="reports"
                  type="number"
                  min={0}
                  max={999}
                  value={reports}
                  onChange={(event) => setReports(Number(event.target.value))}
                  style={{ width: 96 }}
                  disabled={!canEdit}
                />
              </div>
              <button type="button" className="btn" onClick={onSave} disabled={!canEdit || saving}>
                {saving ? '保存中…' : '保存'}
              </button>
            </div>
            <div style={{ fontSize: 11, color: 'var(--ink-500)' }}>
              {canEdit ? '改动会影响判级基线之外的策略口径，保存后立即生效。' : permissionHint('table:write')}
            </div>
          </section>
        </div>
      </div>

      <section className="section">
        <div className="section-head">
          <h2>这张表的违约记录</h2>
          <span className="count num">
            {activeBreachCount} 起{voidedBreachCount > 0 ? ` · 已作废 ${voidedBreachCount} 起` : ''}
          </span>
          <span className="spacer" style={{ flex: 1 }} />
          <Link className="btn btn-ghost" to={`/breaches?q=${encodeURIComponent(code)}`}>
            在台账中打开 →
          </Link>
        </div>
        {breaches.loading && !breaches.data ? <LoadingBlock rows={3} /> : null}
        {breaches.data && breaches.data.items.length === 0 ? (
          <EmptyState
            title="近 30 天没有违约"
            body="延迟一直在容忍分钟内，或该表的探测存在缺失（缺失不参与判级）。"
          />
        ) : null}
        {breaches.data && breaches.data.items.length > 0 ? (
          <table className="ledger">
            <thead>
              <tr>
                <th>日期</th>
                <th>延迟 / 倍数</th>
                <th>严重度</th>
                <th>连续</th>
                <th>主因 / 贡献</th>
                <th>影响分</th>
                <th>处置</th>
              </tr>
            </thead>
            <tbody>
              {breaches.data.items.map((item) => (
                <tr key={item.id} className={item.is_voided ? 'is-voided' : ''}>
                  <td className="num">{shortDate(item.breach_date)}</td>
                  <td className="num">
                    {trimZero(item.delay_minutes)} 分 / {formatRatio(item.ratio)}
                  </td>
                  <td>
                    <SeverityTag severity={item.severity} />
                  </td>
                  <td>
                    <ConsecutiveTag count={item.consecutive_count} />
                  </td>
                  <td>
                    <span className="cause">{item.primary_cause}</span>
                    <span className="num" style={{ color: 'var(--ink-400)', marginLeft: 6 }}>
                      {item.cause_contribution_pct}%
                    </span>
                  </td>
                  <td className="num-cell">{item.impact_score.toFixed(1)}</td>
                  <td>
                    {item.is_voided ? (
                      <VoidedTag reason={item.void_reason} />
                    ) : (
                      <StatusTag status={item.handling_status} />
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
      </section>
    </>
  );
}

function fmtP(value: number | null): string {
  return value === null ? '—' : value.toFixed(1);
}
