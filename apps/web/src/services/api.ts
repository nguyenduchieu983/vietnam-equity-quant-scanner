import type { Envelope } from '@quant/contracts';
import { ref } from 'vue';
// Bearer token stays in memory; refresh requires login. No cookie CSRF surface.
export const token = ref('');
export async function api<T>(path: string, body?: unknown): Promise<Envelope<T>> {
  const response = await fetch(`/api/v1/${path}`, {
    method: body === undefined ? 'GET' : 'POST',
    headers: { 'Content-Type': 'application/json', ...(token.value ? { Authorization: `Bearer ${token.value}` } : {}) },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.timeout(10000)
  });
  const result: Envelope<T> = await response.json();
  if (response.status === 401) token.value = '';
  if (!response.ok || result.error) throw new Error(result.error?.message ?? `HTTP ${response.status}`);
  return result;
}
