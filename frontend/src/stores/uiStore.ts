/** 全局 UI store：提示条（toast）+ 看板筛选条件（跨页保持）。 */
export interface Toast {
  id: number;
  kind: 'ok' | 'error';
  text: string;
}

interface UIState {
  toasts: Toast[];
  boardFilter: { layer: string; q: string };
}

const listeners = new Set<() => void>();
let seq = 0;

let state: UIState = {
  toasts: [],
  boardFilter: { layer: '', q: '' },
};

function emit(): void {
  listeners.forEach((listener) => listener());
}

export const uiStore = {
  subscribe(listener: () => void): () => void {
    listeners.add(listener);
    return () => listeners.delete(listener);
  },
  getState(): UIState {
    return state;
  },
  toast(text: string, kind: 'ok' | 'error' = 'ok', ttl = 4200): number {
    const id = ++seq;
    state = { ...state, toasts: [...state.toasts, { id, kind, text }] };
    emit();
    window.setTimeout(() => uiStore.dismiss(id), ttl);
    return id;
  },
  dismiss(id: number): void {
    state = { ...state, toasts: state.toasts.filter((item) => item.id !== id) };
    emit();
  },
  setBoardFilter(patch: Partial<UIState['boardFilter']>): void {
    state = { ...state, boardFilter: { ...state.boardFilter, ...patch } };
    emit();
  },
};
