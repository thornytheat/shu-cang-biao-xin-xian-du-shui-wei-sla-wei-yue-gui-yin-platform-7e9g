/** 认证 store：手写外部 store（无第三方状态库），配合 useSyncExternalStore。 */
import { authApi } from '../api/auth';
import type { User } from '../types/models';
import { readToken, readUserRaw, writeToken, writeUserRaw } from '../utils/storage';

export interface AuthState {
  user: User | null;
  status: 'idle' | 'loading' | 'ready' | 'error';
  error: string | null;
  bootstrapped: boolean;
}

const listeners = new Set<() => void>();

function loadCachedUser(): User | null {
  const raw = readUserRaw();
  if (!raw) return null;
  try {
    return JSON.parse(raw) as User;
  } catch {
    return null;
  }
}

let state: AuthState = {
  user: loadCachedUser(),
  status: readToken() ? 'idle' : 'ready',
  error: null,
  bootstrapped: false,
};

function setState(patch: Partial<AuthState>): void {
  state = { ...state, ...patch };
  listeners.forEach((listener) => listener());
}

function persist(user: User | null): void {
  writeUserRaw(user ? JSON.stringify(user) : null);
}

export const authStore = {
  subscribe(listener: () => void): () => void {
    listeners.add(listener);
    return () => listeners.delete(listener);
  },
  getState(): AuthState {
    return state;
  },
  get token(): string | null {
    return readToken();
  },
  async bootstrap(): Promise<void> {
    if (state.bootstrapped) return;
    if (!readToken()) {
      setState({ status: 'ready', bootstrapped: true, user: null });
      return;
    }
    setState({ status: 'loading' });
    try {
      const user = await authApi.me();
      persist(user);
      setState({ user, status: 'ready', error: null, bootstrapped: true });
    } catch (err) {
      writeToken(null);
      persist(null);
      setState({
        user: null,
        status: 'ready',
        error: err instanceof Error ? err.message : '登录态校验失败',
        bootstrapped: true,
      });
    }
  },
  async login(email: string, password: string): Promise<User> {
    setState({ status: 'loading', error: null });
    try {
      const payload = await authApi.login(email.trim(), password);
      writeToken(payload.access_token);
      persist(payload.user);
      setState({ user: payload.user, status: 'ready', error: null, bootstrapped: true });
      return payload.user;
    } catch (err) {
      const message = err instanceof Error ? err.message : '登录失败';
      setState({ status: 'error', error: message, user: null });
      throw err;
    }
  },
  logout(): void {
    writeToken(null);
    persist(null);
    setState({ user: null, status: 'ready', error: null });
  },
};
