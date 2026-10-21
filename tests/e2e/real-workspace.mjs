import 'dotenv/config';
import assert from 'node:assert/strict';
import {writeFileSync} from 'node:fs';
const base='http://127.0.0.1:5173/api/v1/';
const login=await fetch(base+'auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:process.env.SMOKE_ADMIN_PASSWORD})});
const token=(await login.json()).data.accessToken;assert.ok(token);
async function api(path,body){const r=await fetch(base+path,{method:body?'POST':'GET',headers:{Authorization:`Bearer ${token}`,'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});const v=await r.json();assert.equal(r.status,body?201:200,JSON.stringify(v.error));assert.equal(v.meta.isDemo,false);return v.data;}
async function wait(id){for(let i=0;i<120;i++){const j=await api(`jobs/${id}`);if(j.status==='FAILED')throw Error(j.error_code);if(j.status==='COMPLETE')return j;await new Promise(r=>setTimeout(r,3000));}throw Error('timeout');}
const status=await api('system/status');assert.equal(status.isDemo,false);assert.equal(status.instruments,100);assert.equal(status.latestSession,'2026-10-20');
const instruments=await api('instruments?limit=100');assert.ok(instruments.some(i=>i.symbol==='FPT'));assert.ok(instruments.every(i=>!i.symbol.startsWith('SIM')));
const datasets=await api('datasets');assert.ok(datasets.every(d=>d.is_demo===false));const ds=datasets[0];assert.equal(ds.provider,'vndirect_public');assert.equal(ds.quality_json.researchEligible,true);
const scan=await api('scans',{datasetId:ds.id});const finished=await wait(scan.id);
const rows=await api(`scans/${finished.result_json.scanId}/results?limit=100`);assert.ok(rows.total>=100);assert.ok(rows.items.every(i=>!i.symbol.startsWith('SIM')));
const bars=await api(`instruments/FPT/bars?datasetId=${ds.id}&limit=20`);assert.equal(bars.length,20);assert.equal(bars.at(-1).session_date,'2026-10-20');
const run=await api('backtests',{datasetId:ds.id,strategy:'S1',capital:50000000,trainStart:'2022-01-04',trainEnd:'2023-12-26',validationStart:'2024-02-15',validationEnd:'2024-06-28',testStart:'2024-09-04',testEnd:'2026-10-20',maxHold:30,embargoSessions:30,minLiquidity:5e9,buyFee:.0015,sellFee:.0015,sellTax:.001,slippage:.001});
await wait(run.job_id);const result=await api(`backtests/${run.id}`);assert.equal(result.is_demo,false);assert.equal(result.artifact.isDemo,false);assert.ok(result.equity.length>500);
writeFileSync('docs/verification/real-workspace-2026-10-21.json',JSON.stringify({status,dataset:{id:ds.id,status:ds.status,missingBars:ds.quality_json.missing_bars},scanRows:rows.total,backtest:{id:run.id,sessions:result.equity.length,metrics:result.metrics_json},checks:['mode separation','real instruments/bars','real scan job','real backtest artifact']},null,2)+'\n');
console.log('PASS real workspace API: 100 real symbols, source/date, scan, bars and full S1 backtest');
