import assert from 'node:assert/strict';
import { login, call, finish } from './research-helper.mjs';
const token=await login();
const datasets=await call(token,'datasets');
const datasetId=datasets.find(d=>d.status==='COMPLETE').id;
const body={datasetId,session:'2026-10-16'};
const first=await finish(token,await call(token,'scans',body));
const second=await finish(token,await call(token,'scans',body));
assert.equal(first.scanId,second.scanId);
for(const strategy of ['S1','S2','S3','S4']){
  const results=await call(token,`scans/${first.scanId}/results?strategy=${strategy}&limit=2`);
  assert.equal(results.items.length,2);
  assert.equal(results.total,7);
  assert.ok(results.items.every(r=>r.sub_scores_json.evidence.source_date==='2026-10-16'));
}
const bars=await call(token,`instruments/SIM00/bars?datasetId=${datasetId}&limit=30`);
assert.equal(bars.length,30);
assert.equal((await call(token,'instruments/SIM00/features')).features_json.source_date,'2026-10-16');
console.log('PASS M2 scan idempotency, S1–S4 persisted explanations, pagination, symbol history/features.');
