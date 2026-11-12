import { readToken, writeToken } from '../utils/storage';

export class ApiError extends Error {
  status: number;
  code: string;
  detail: unknown;

  constructor(status: number, code: string, message: string, detail?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.detail = detail;
  }
}

function redirectToLogin(): void {
  writeToken(null);
  if (window.location.pathname !== '/login') {
    window.location.assign('/login');
  }
}

async function parseError(res: Response): Promise<ApiError> {
  let code = `HTTP_${res.status}`;
  let message = `请求失败（${res.status}）`;
  let detail: unknown = null;
  try {
    const body = await res.json();
    if (body && typeof body === 'object') {
      code = body.code ?? code;
      message = body.message ?? message;
      detail = body.detail ?? null;
    }
  } catch {
    /* 非 JSON 响应（例如 nginx 502） */
  }
  return new ApiError(res.status, code, message, detail);
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers ?? {});
  if (!headers.has('Content-Type') && init.body) headers.set('Content-Type', 'application/json');
  const token = readToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);

  let res: Response;
  try {
    res = await fetch(path, { ...init, headers });
  } catch {
    throw new ApiError(0, 'NETWORK', '网络不可达：请确认后端容器已就绪');
  }

  if (res.status === 401) {
    const err = await parseError(res);
    redirectToLogin();
    throw err;
  }
  if (!res.ok) throw await parseError(res);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export async function requestBlob(
  path: string,
  init: RequestInit = {},
): Promise<{ blob: Blob; filename: string }> {
  const headers = new Headers(init.headers ?? {});
  const token = readToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);
  let res: Response;
  try {
    res = await fetch(path, { ...init, headers });
  } catch {
    throw new ApiError(0, 'NETWORK', '网络不可达：导出失败');
  }
  if (!res.ok) {
    if (res.status === 401) redirectToLogin();
    throw await parseError(res);
  }
  const disposition = res.headers.get('Content-Disposition') ?? '';
  const match = /filename\*=UTF-8''([^;]+)/.exec(disposition);
  const filename = match ? decodeURIComponent(match[1]) : 'freshsla-export.csv';
  return { blob: await res.blob(), filename };
}

export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'PATCH', body: JSON.stringify(body) }),
};
