import { useSyncExternalStore } from 'react';
import { uiStore } from '../stores/uiStore';

/** 提示条：全局唯一实例挂在 AppShell / Login 上。 */
export function useToasts() {
  const state = useSyncExternalStore(uiStore.subscribe, uiStore.getState, uiStore.getState);
  return {
    toasts: state.toasts,
    toast: (text: string, kind: 'ok' | 'error' = 'ok') => uiStore.toast(text, kind),
    dismiss: (id: number) => uiStore.dismiss(id),
  };
}
