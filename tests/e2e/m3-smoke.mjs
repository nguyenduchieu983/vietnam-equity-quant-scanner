import assert from 'node:assert/strict';
import { writeFileSync } from 'node:fs';
import { login, call, finish } from './research-helper.mjs';
const token=await login();
const dataset=(await call(token,'datasets')).find(d=>d.status==='COMPLETE');
const config={datasetId:dataset.id,strategy:'S1',capital:50000000,trainStart:'2022-01-03',trainEnd:'2023-12-29',validationStart:'2024-02-15',validationEnd:'2024-06-28',testStart:'2024-09-02',testEnd:'2026-10-16',maxHold:30,embargoSessions:30,minLiquidity:5e9,buyFee:.0015,sellFee:.0015,sellTax:.001,slippage:.001};
const reports=[];
for(const strategy of ['S1','S2','S3','S4','S1']){
  const start=Date.now();
  const run=await call(token,'backtests',{...config,strategy,maxHold:strategy==='S4'?5:strategy==='S1'?30:20});
  await finish(token,{id:run.job_id});
  const result=await call(token,`backtests/${run.id}`);
  assert.equal(result.status,'COMPLETE');
  assert.ok(result.equity.length>500);
  assert.equal(result.artifact.isDemo,true);
  assert.equal(result.artifact.promotion,'RESEARCH_ONLY');
  assert.ok(result.artifact.walkForward.length>0);
  assert.equal(result.artifact.costSensitivity.length,2);
  assert.ok(result.equity.every(e=>Number(e.cash)>=0&&Math.abs(Number(e.nav)-Number(e.cash)-Number(e.pending_cash)-Number(e.holdings_value))<.02));
  assert.ok(result.trades.every(t=>t.entry_date<t.exit_date));
  reports.push({strategy,id:run.id,hash:result.artifact.reproducibilityHash,elapsedMs:Date.now()-start,metrics:result.metrics_json,warnings:result.warnings_json});
  console.log(strategy,result.status,`${result.metrics_json.tradeCount} trades`,`${Date.now()-start}ms`);
}
assert.equal(reports[0].hash,reports[4].hash);
const exported=await call(token,`backtests/${reports[0].id}/export`);
assert.equal(exported.equityCsv.split('\r\n').length,reports[0].metrics.sessions+1);
assert.match(exported.ordersCsv,/"decision_date"/);
assert.match(exported.tradesCsv,/"pnl"/);
await assert.rejects(()=>call(token,'backtests',{...config,testStart:config.trainStart}),/INVALID_SPLITS/);
await assert.rejects(()=>call(token,'backtests',{...config,slippage:-1}));
const cancel=await call(token,'backtests',config);
await call(token,`backtests/${cancel.id}/cancel`,{});
for(let i=0;i<15;i++){
  const state=await call(token,`backtests/${cancel.id}`);
  if(state.status==='CANCELLED'){assert.equal(state.equity.length,0);break;}
  if(i===14)throw new Error('Cancellation did not complete');
  await new Promise(r=>setTimeout(r,2000));
}
writeFileSync('.runtime/m3-results.json',JSON.stringify(reports,null,2));
console.log('M3 PASS: all strategies, reproducibility, ledger reconciliation, validation, cancellation.');
