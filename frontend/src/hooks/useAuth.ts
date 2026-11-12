import { useSyncExternalStore } from 'react';
import { authStore } from '../stores/authStore';

/** 认证 hook：登录态 + 角色能力判断。 */
export function useAuth() {
  const state = useSyncExternalStore(authStore.subscribe, authStore.getState, authStore.getState);
  return {
    ...state,
    login: authStore.login.bind(authStore),
    logout: authStore.logout.bind(authStore),
    bootstrap: authStore.bootstrap.bind(authStore),
  };
}
