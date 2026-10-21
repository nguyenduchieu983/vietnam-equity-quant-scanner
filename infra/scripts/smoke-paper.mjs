import 'dotenv/config';
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,existsSync} from 'node:fs';
import {randomUUID} from 'node:crypto';
const base=process.env.PAPER_TEST_URL??'http://127.0.0.1:5173/api/v1/';
assert.equal((await fetch(base+'paper')).status,401);
const login=await fetch(base+'auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:process.env.SMOKE_ADMIN_PASSWORD})});
const token=(await login.json()).data.accessToken;assert.ok(token);
async function request(path,body){const r=await fetch(base+path,{method:body===undefined?'GET':'POST',headers:{Authorization:`Bearer ${token}`,'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(20000)});const value=await r.json();assert.equal(r.status,body===undefined?200:201,JSON.stringify(value.error));return value;}
async function wait(id){for(let i=0;i<180;i++){const j=(await request(`paper/jobs/${id}`)).data;if(j.status==='FAILED')throw new Error(j.error_code);if(j.status==='COMPLETE')return j.result_json;await new Promise(r=>setTimeout(r,2000));}throw new Error('Paper job timeout');}
const file='.runtime/paper-smoke-state.json';
const phase=process.argv[2]??'init';
let state=existsSync(file)?JSON.parse(readFileSync(file)):{};
if(phase==='init'){
 const listing=await request('paper');assert.equal(listing.meta.isDemo,false);assert.ok(listing.data.snapshot);
 state.snapshot=listing.data.snapshot.id;
 for(const mode of ['REPLAY','FORWARD']){
  if(state[mode])continue;
  const body={snapshotId:state.snapshot,mode,...(mode==='REPLAY'?{startDay:'2026-09-03'}:{}),idempotencyKey:randomUUID()};
  const j=(await request('paper/pairs',body)).data;
  assert.equal((await request('paper/pairs',body)).data.id,j.id);
  state[mode]=(await wait(j.id)).pairId;writeFileSync(file,JSON.stringify(state,null,2));
 }
 const f=(await request(`paper/pairs/${state.FORWARD}`)).data;
 assert.equal(f.accounts.length,2);assert.ok(f.accounts.every(a=>a.equity.length===0&&Number(a.state_json.cash)===50000000));
 assert.equal((await request(`paper/pairs/${state.FORWARD}/preview`)).data.canAdvance,false);
 const p=(await request(`paper/pairs/${state.REPLAY}/preview`)).data;
 const body={snapshotId:p.snapshotId,expectedCursor:p.expectedCursor,through:'2026-09-04'};
 const j=(await request(`paper/pairs/${state.REPLAY}/advance`,body)).data;await wait(j.id);
 assert.equal((await request(`paper/pairs/${state.REPLAY}/advance`,body)).data.id,j.id);
 state.first=(await request(`paper/pairs/${state.REPLAY}`)).data;writeFileSync(file,JSON.stringify(state,null,2));
 console.log('PASS auth, two real-labelled pairs, create/advance idempotency, forward empty, replay checkpoint. Restart services then run continue.');
}else{
 const before=(await request(`paper/pairs/${state.REPLAY}`)).data;
 assert.deepEqual(before.accounts,state.first.accounts,'Restart changed account state');
 const p=(await request(`paper/pairs/${state.REPLAY}/preview`)).data;
 const body={snapshotId:p.snapshotId,expectedCursor:p.expectedCursor,through:p.through};
 const j=(await request(`paper/pairs/${state.REPLAY}/advance`,body)).data;await wait(j.id);
 assert.equal((await request(`paper/pairs/${state.REPLAY}/advance`,body)).data.id,j.id);
 const after=(await request(`paper/pairs/${state.REPLAY}`)).data;
 const stale=await fetch(base+`paper/pairs/${state.REPLAY}/advance`,{method:'POST',headers:{Authorization:`Bearer ${token}`,'Content-Type':'application/json'},body:JSON.stringify({...body,expectedCursor:'2026-01-01'})});
 assert.equal(stale.status,409);
 assert.deepEqual((await request(`paper/pairs/${state.REPLAY}`)).data.accounts,after.accounts,'Rejected stale approval changed ledger');
 for(const a of after.accounts){assert.ok(a.equity.length>state.first.accounts[0].equity.length);assert.ok(a.equity.every(e=>Math.abs(Number(e.nav)-Number(e.cash)-Number(e.pending_cash)-Number(e.holdings_value))<.03));}
 state.result=after;writeFileSync(file,JSON.stringify(state,null,2));
 console.log(JSON.stringify({replay:state.REPLAY,forward:state.FORWARD,through:after.pair.cursor_day,accounts:after.accounts.map(a=>({code:a.code,sessions:a.equity.length,closed:a.summary_json.closed,winRate:a.summary_json.winRate,return:a.summary_json.return,drawdown:a.summary_json.drawdown}))}));
}
