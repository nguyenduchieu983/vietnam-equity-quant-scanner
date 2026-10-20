import assert from 'node:assert/strict';
const base = process.env.API_URL ?? 'http://127.0.0.1:3000';
const password = process.env.SMOKE_ADMIN_PASSWORD;
assert.ok(password, 'SMOKE_ADMIN_PASSWORD required; never use a committed password');
async function request(path, token, body) {
  return fetch(`${base}/api/v1/${path}`, {
    method: body ? 'POST' : 'GET',
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: body ? JSON.stringify(body) : undefined, signal: AbortSignal.timeout(10000)
  });
}
assert.equal((await request('system/status')).status, 401);
const login = await request('auth/login', null, { password });
assert.equal(login.status, 201);
const token = (await login.json()).data.accessToken;
const status = await (await request('system/status', token)).json();
assert.equal(status.meta.isDemo, true);
assert.ok(status.data.bars >= 3);
assert.equal(status.data.worker, true);
assert.equal((await request('scans?limit=1000', token)).status, 400);
const key = `smoke-${Date.now()}`;
const body = { provider: 'fixture', idempotencyKey: key };
const job = await (await request('ingestion/runs', token, body)).json();
const duplicate = await (await request('ingestion/runs', token, body)).json();
assert.equal(job.data.id, duplicate.data.id);
let complete = false;
for (let attempt = 0; attempt < 20; attempt++) {
  const poll = await (await request(`jobs/${job.data.id}`, token)).json();
  if (poll.data.status === 'COMPLETE') { complete = true; break; }
  assert.notEqual(poll.data.status, 'FAILED');
  await new Promise(resolve => setTimeout(resolve, 1000));
}
assert.ok(complete, 'Worker must complete durable ingestion job');
const scans = await (await request('scans', token)).json();
assert.deepEqual(scans.data, [], 'M0 must not fabricate computed scans');
const regime = await (await request('market/regime', token)).json();
assert.equal(regime.data.regime, 'UNKNOWN');
console.log('PASS M0 API smoke (not browser E2E, not M1–M4 acceptance)');
