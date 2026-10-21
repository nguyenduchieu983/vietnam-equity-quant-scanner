// Standing authorization: installed Windows login workflow, simulated trades only.
import 'dotenv/config';
const base='http://127.0.0.1:5173/api/v1/';
let token;
async function api(path,body){const r=await fetch(base+path,{method:body?'POST':'GET',headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`}:{})},body:body?JSON.stringify(body):undefined,signal:AbortSignal.timeout(30000)});const v=await r.json();if(!r.ok)throw Error(v.error?.message??`HTTP ${r.status}`);return v.data;}
async function wait(id){for(let i=0;i<300;i++){const job=await api(`paper/jobs/${id}`);if(job.status==='COMPLETE')return job.result_json;if(job.status==='FAILED')throw Error(job.error_code);await new Promise(r=>setTimeout(r,3000));}throw Error('Paper job still pending; inspect ledger');}
token=(await api('auth/login',{password:process.env.SMOKE_ADMIN_PASSWORD})).accessToken;
const list=await api('paper');if(!list.snapshot)throw Error('No real snapshot');
let pair=list.pairs.find(p=>p.mode==='FORWARD');
if(!pair){const job=await api('paper/pairs',{snapshotId:list.snapshot.id,mode:'FORWARD',idempotencyKey:crypto.randomUUID()});pair={id:(await wait(job.id)).pairId};}
const preview=await api(`paper/pairs/${pair.id}/preview`);
if(preview.canAdvance){const job=await api(`paper/pairs/${pair.id}/advance`,{snapshotId:preview.snapshotId,through:preview.through,expectedCursor:preview.expectedCursor});await wait(job.id);console.log(`PAPER ONLY: paired forward processed through ${preview.through}; job ${job.id}`);}
else console.log(`PAPER ONLY: no new EOD after ${preview.expectedCursor}; no ledger mutation`);
