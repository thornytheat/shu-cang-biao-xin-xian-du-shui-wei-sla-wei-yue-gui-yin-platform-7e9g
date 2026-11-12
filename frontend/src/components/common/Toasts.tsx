import { useToasts } from '../../hooks/useToast';

/** 提示条宿主：全局唯一，挂在需要的位置（外壳 / 登录页）。 */
export function Toasts() {
  const { toasts, dismiss } = useToasts();
  if (toasts.length === 0) return null;
  return (
    <div className="toasts" role="status" aria-live="polite">
      {toasts.map((item) => (
        <div
          key={item.id}
          className={`toast ${item.kind === 'error' ? 'error' : ''}`}
          onClick={() => dismiss(item.id)}
          style={{ cursor: 'pointer' }}
        >
          {item.text}
        </div>
      ))}
    </div>
  );
}
