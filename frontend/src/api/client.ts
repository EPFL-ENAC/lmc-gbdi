// The one way the frontend talks to the backend: same-origin /api, JSON, and a thrown
// Error carrying the backend's message when the answer is not 2xx.
export async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`/api${path}`, { headers: { Accept: 'application/json' } });
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    const detail = body !== null && typeof body === 'object' && 'detail' in body ? String(body.detail) : '';
    throw new Error(`${response.status} ${response.statusText}${detail ? `: ${detail}` : ''}`);
  }
  return (await response.json()) as T;
}
