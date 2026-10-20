import 'dotenv/config';
import assert from 'node:assert/strict';
const base = process.env.API_URL ?? 'http://127.0.0.1:5173';
export async function login() {
  const response = await fetch(`${base}/api/v1/auth/login`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({password:process.env.SMOKE_ADMIN_PASSWORD}) });
  assert.equal(response.status, 201);
  return (await response.json()).data.accessToken;
}
export async function call(token, path, body, method = body ? 'POST' : 'GET') {
  const response = await fetch(`${base}/api/v1/${path}`, { method, headers:{'Content-Type':'application/json',Authorization:`Bearer ${token}`}, body:body ? JSON.stringify(body) : undefined, signal:AbortSignal.timeout(15000) });
  const data = await response.json();
  assert.ok(response.ok, `${path}: ${JSON.stringify(data)}`);
  return data.data;
}
export async function finish(token, job) {
  for (let i=0;i<150;i++) {
    const value = await call(token, `jobs/${job.id}`);
    if (value.status === 'COMPLETE') return value.result_json;
    assert.notEqual(value.status,'FAILED',JSON.stringify(value));
    await new Promise(resolve=>setTimeout(resolve,2000));
  }
  throw new Error('Job timeout');
}
