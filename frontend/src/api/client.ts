// The one way the frontend talks to the backend: same-origin /api, JSON, and a thrown
// ApiError carrying the backend's message (and body) when the answer is not 2xx.
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly body: unknown,
    statusText: string,
  ) {
    const detail = body !== null && typeof body === 'object' && 'detail' in body ? String(body.detail) : '';
    super(`${status} ${statusText}${detail ? `: ${detail}` : ''}`);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, { ...init, headers: { Accept: 'application/json' } });
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    throw new ApiError(response.status, body, response.statusText);
  }
  return (response.status === 204 ? undefined : await response.json()) as T;
}

export const getJson = <T>(path: string) => request<T>(path);
export const postForm = <T>(path: string, form: FormData) => request<T>(path, { method: 'POST', body: form });
export const deleteJson = (path: string) => request<void>(path, { method: 'DELETE' });
