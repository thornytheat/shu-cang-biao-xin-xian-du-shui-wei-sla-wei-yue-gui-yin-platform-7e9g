import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { breachesApi } from '../api/breaches';
import { probesApi } from '../api/probes';
import { tablesApi } from '../api/tables';
import { EmptyState, ErrorState, LoadingBlock } from '../components/common/EmptyState';
import { TierLamp } from '../components/common/TierLamp';
import { WaterBar } from '../components/common/WaterBar';
import { GRADE_HINTS, LAYER_LABELS, TIER_LABELS, TIER_ORDER } from '../constants/enums';
import { can } from '../constants/roles';
import { useAsync } from '../hooks/useAsync';
import { useAuth } from '../hooks/useAuth';
import { useToasts } from '../hooks/useToast';
import type { BoardRow, Grade, ProbeRunResult } from '../types/models';
import { describeError, permissionHint } from '../utils/errorMessage';
import { formatMinutes, formatRatio, trimZero } from '../utils/format';

const GRADE_ORDER: Grade[] = ['red', 'yellow', 'green', 'unknown'];

/** 表健康看板：P0/P1/P2 三栏 + 水位条 + 三色灯；顶部可运行今日探测。 */
export function Board() {
  const { user } = useAuth();
  const { toast } = useToasts();
  const [layer, setLayer] = useState('');
  const [keyword, setKeyword] = useState('');
  const [runResult, setRunResult] = useState<ProbeRunResult | null>(null);
  const [running, setRunning] = useState(false);

  const boardState = useAsync(() => tablesApi.board({ layer: layer || undefined, q: keyword || undefined }), [layer, keyword]);
  const summaryState = useAsync(() => breachesApi.summary(), []);
  const statusState = useAsync(() => probesApi.status(), []);

  const board = boardState.data;
  const canRun = can(user?.role, 'probe:run');

  const totals = board?.totals;
  const breachSummary = summaryState.data;

  const runLabel = useMemo(() => (running ? '巡检中…' : '运行今日探测'), [running]);

  async function onRun() {
    setRunning(true);
    try {
      const result = await probesApi.run();
      setRunResult(result);
      toast(
        `巡检完成：新增 ${result.created} 条、缺失 ${result.missing} 条、红灯 ${result.red_count} 张`,
        'ok',
      );
      boardState.reload();
      summaryState.reload();
      statusState.reload();
    } catch (err) {
      toast(`${describeError(err)}｜${permissionHint('probe:run')}`, 'error');
    } finally {
      setRunning(false);
    }
  }

  return (
    <>
      <section className="section">
        <div className="section-head">
          <h2>今日巡检</h2>
          <span className="count num">
            {statusState.data?.today ?? '—'} · {statusState.data?.probed_today ? '已巡检' : '未巡检'}
          </span>
          <span className="spacer" style={{ flex: 1 }} />
          <div className="inline-actions">
            <select value={layer} onChange={(event) => setLayer(event.target.value)} aria-label="按分层筛选">
              <option value="">全部层（ODS/DWD/DWS/ADS）</option>
              {Object.entries(LAYER_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
            <input
              type="text"
              placeholder="搜表名 / 中文名"
              value={keyword}
              onChange={(event) => setKeyword(event.target.value)}
              style={{ width: 190 }}
              aria-label="搜索表"
            />
            <button
              type="button"
              className={canRun ? 'btn btn-primary' : 'btn'}
              onClick={onRun}
              disabled={running}
              title={canRun ? '跑一次 40 张表的巡检并自动检测违约' : `${permissionHint('probe:run')}（点击可验证后端 403）`}
            >
              {runLabel}
            </button>
          </div>
        </div>

        <div className="inline-actions" style={{ fontSize: 12, color: 'var(--ink-400)' }}>
          <span className="num">水线 {board?.waterline ?? '—'}</span>
          <span>·</span>
          <span>分位基线窗口 {board?.calibration_days ?? 30} 天</span>
          <span>·</span>
          <span>违约 {breachSummary?.total ?? '—'} 起（严重 {breachSummary?.severe_total ?? '—'} 起）</span>
          <span>·</span>
          <span>红灯 {totals?.red ?? '—'} 张 / 待认领 {breachSummary?.by_status?.open ?? '—'} 起</span>
          {!canRun ? (
            <span className="tag" style={{ color: 'var(--lamp-yellow)' }}>
              当前角色只读：探测由 admin/ops 触发
            </span>
          ) : null}
        </div>

        {runResult ? (
          <div
            className="section"
            style={{ borderColor: 'oklch(0.742 0.088 154 / 0.35)', background: 'oklch(0.742 0.088 154 / 0.06)' }}
          >
            <div className="section-head">
              <h3 style={{ color: 'var(--lamp-green)' }}>巡检结果 · {runResult.run_date}</h3>
              <span className="count num">{runResult.duration_ms} ms</span>
            </div>
            <div className="inline-actions" style={{ fontSize: 12.5 }}>
              <span>
                新增 <b className="num">{runResult.created}</b> 条
              </span>
              <span>
                缺失 <b className="num" style={{ color: 'var(--lamp-yellow)' }}>{runResult.missing}</b> 条 → unknown
              </span>
              <span>
                迟到 <b className="num">{runResult.late}</b> 条
              </span>
              <span>
                早到 <b className="num">{runResult.early}</b> 条
              </span>
              <span>
                红灯 <b className="num" style={{ color: 'var(--lamp-red)' }}>{runResult.red_count}</b> 张
              </span>
              {runResult.red_tables.length > 0 ? (
                <span className="num" style={{ color: 'var(--ink-400)' }}>
                  {runResult.red_tables.join(' / ')}
                </span>
              ) : null}
              {runResult.breaches ? (
                <span>
                  违约检测：扫描 {runResult.breaches.scanned} · 新增 {runResult.breaches.created} · 更新{' '}
                  {runResult.breaches.updated}
                </span>
              ) : null}
            </div>
          </div>
        ) : null}
      </section>

      {boardState.error ? (
        <ErrorState
          message={boardState.error}
          onRetry={boardState.reload}
          hint="若刚启动容器，等 backend healthy 后再刷新；也可直接点重试。"
        />
      ) : null}

      {boardState.loading && !board ? (
        <section className="section">
          <LoadingBlock rows={6} />
        </section>
      ) : null}

      {board ? (
        <>
          <section className="section" style={{ gap: 10 }}>
            <div className="stat-grid five">
              <div className="stat">
                <div className="k">核心表</div>
                <div className="v">{totals?.tables ?? 0}</div>
              </div>
              <div className="stat">
                <div className="k">红灯（&gt; P90）</div>
                <div className="v" style={{ color: 'var(--lamp-red)' }}>
                  {totals?.red ?? 0}
                </div>
              </div>
              <div className="stat">
                <div className="k">黄灯</div>
                <div className="v" style={{ color: 'var(--lamp-yellow)' }}>
                  {totals?.yellow ?? 0}
                </div>
              </div>
              <div className="stat">
                <div className="k">绿灯</div>
                <div className="v" style={{ color: 'var(--lamp-green)' }}>
                  {totals?.green ?? 0}
                </div>
              </div>
              <div className="stat">
                <div className="k">缺失（unknown）</div>
                <div className="v" style={{ color: 'var(--ink-300)' }}>
                  {totals?.unknown ?? 0}
                </div>
              </div>
            </div>
          </section>

          <div className="board-grid">
            {TIER_ORDER.map((tier) => {
              const column = board.tiers[tier];
              if (!column) return null;
              return (
                <section className="tier-col" key={tier}>
                  <header className="tier-col-head">
                    <span className="tier-name">{TIER_LABELS[tier].split(' · ')[0]}</span>
                    <span className="tier-sub">{TIER_LABELS[tier].split(' · ')[1]} · 容忍 {column.tolerance_minutes}m</span>
                    <span className="counters num">
                      {GRADE_ORDER.map((grade) => (
                        <span key={grade} style={{ color: gradeColor(grade) }}>
                          {countersText(grade)} {column.counters[grade] ?? 0}
                        </span>
                      ))}
                    </span>
                  </header>
                  <div className="rowlist">
                    {column.rows.length === 0 ? (
                      <div style={{ padding: 14 }}>
                        <EmptyState title="这一栏没有命中记录" body="换个分层或清空搜索词再看。" />
                      </div>
                    ) : (
                      column.rows.map((row) => <BoardRowItem key={row.code} row={row} />)
                    )}
                  </div>
                </section>
              );
            })}
          </div>

          <div className="legend">
            {GRADE_ORDER.map((grade) => (
              <span key={grade} className="inline-actions">
                <TierLamp grade={grade} />
                <span>{GRADE_HINTS[grade]}</span>
              </span>
            ))}
            <span style={{ marginLeft: 'auto' }}>水位条满格 = 延迟达到容忍值的 2 倍；竖线 = 容忍线</span>
          </div>
        </>
      ) : null}

      {board && totals?.tables === 0 ? (
        <EmptyState
          title="没有匹配的表"
          body="当前筛选条件下 40 张核心表都没命中。清空搜索词或把分层切回“全部层”。"
          action={
            <button
              type="button"
              className="btn"
              onClick={() => {
                setLayer('');
                setKeyword('');
              }}
            >
              清空筛选
            </button>
          }
        />
      ) : null}
    </>
  );
}

function BoardRowItem({ row }: { row: BoardRow }) {
  const delayText =
    row.delay_minutes === null ? '缺失' : `${trimZero(row.delay_minutes)}`;
  return (
    <div className={`trow ${row.grade}`}>
      <TierLamp grade={row.grade} />
      <div style={{ minWidth: 0 }}>
        <div className="code">
          {row.code}
          {row.is_early ? <span style={{ color: 'var(--lamp-green)', fontSize: 10, marginLeft: 6 }}>early</span> : null}
        </div>
        <div className="name">
          {row.name} · {row.report_count} 张报表 · {row.expected_ready_clock} 应就绪
        </div>
        <WaterBar ratio={row.ratio} grade={row.grade} toleranceMinutes={row.tolerance_minutes} />
      </div>
      <div className="delay">
        {delayText}
        <small>
          {row.ratio === null ? '探测缺失' : `${formatRatio(row.ratio)} / ${row.tolerance_minutes}m`}
        </small>
        <small style={{ color: 'var(--ink-600)' }}>
          {row.delay_minutes === null ? '—' : formatMinutes(row.delay_minutes)}
        </small>
      </div>
      <Link className="rowlink" to={`/tables/${encodeURIComponent(row.code)}`} aria-label={`查看 ${row.code} 详情`} />
    </div>
  );
}

function gradeColor(grade: Grade): string {
  if (grade === 'red') return 'var(--lamp-red)';
  if (grade === 'yellow') return 'var(--lamp-yellow)';
  if (grade === 'green') return 'var(--lamp-green)';
  return 'var(--ink-400)';
}

function countersText(grade: Grade): string {
  return { red: '红', yellow: '黄', green: '绿', unknown: '缺' }[grade];
}
