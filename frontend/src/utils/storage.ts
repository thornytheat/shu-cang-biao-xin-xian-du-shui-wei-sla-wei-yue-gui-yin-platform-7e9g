/** 令牌存取（单独抽出，避免 api/client 与 stores/authStore 循环依赖）。 */
const TOKEN_KEY = 'freshsla.token';
const USER_KEY = 'freshsla.user';

export function readToken(): string | null {
  try {
    return window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function writeToken(token: string | null): void {
  try {
    if (token) window.localStorage.setItem(TOKEN_KEY, token);
    else window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* 隐私模式下忽略 */
  }
}

export function readUserRaw(): string | null {
  try {
    return window.localStorage.getItem(USER_KEY);
  } catch {
    return null;
  }
}

export function writeUserRaw(value: string | null): void {
  try {
    if (value) window.localStorage.setItem(USER_KEY, value);
    else window.localStorage.removeItem(USER_KEY);
  } catch {
    /* ignore */
  }
}
