import type { ReactNode } from 'react';

interface EmptyProps {
  title: string;
  body?: string;
  action?: ReactNode;
  hint?: string;
}

/** 空态：教值班员"下一步做什么"，而不是干瘪的"暂无数据"。 */
export function EmptyState({ title, body, action, hint }: EmptyProps) {
  return (
    <div className="state" role="status">
      <div className="state-title">{title}</div>
      {body ? <div className="state-body">{body}</div> : null}
      {hint ? (
        <div className="state-body num" style={{ color: 'var(--ink-500)', fontSize: 11 }}>
          {hint}
        </div>
      ) : null}
      {action}
    </div>
  );
}

interface ErrorProps {
  message: string;
  onRetry?: () => void;
  hint?: string;
}

/** 错误态：始终可恢复（重试按钮 + 具体原因）。 */
export function ErrorState({ message, onRetry, hint }: ErrorProps) {
  return (
    <div className="state error" role="alert">
      <div className="state-title">数据没取回来</div>
      <div className="state-body">{message}</div>
      {hint ? (
        <div className="state-body" style={{ color: 'var(--ink-500)', fontSize: 11 }}>
          {hint}
        </div>
      ) : null}
      {onRetry ? (
        <button type="button" className="btn" onClick={onRetry}>
          重试
        </button>
      ) : null}
    </div>
  );
}

/** 加载骨架：保持版面高度，避免跳动。 */
export function LoadingBlock({ rows = 4 }: { rows?: number }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }} aria-busy="true">
      {Array.from({ length: rows }).map((_, index) => (
        <div
          key={index}
          className="skeleton"
          style={{ width: `${88 - index * 9}%`, height: index === 0 ? 14 : 12 }}
        />
      ))}
    </div>
  );
}
