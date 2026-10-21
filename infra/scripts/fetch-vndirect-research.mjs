// Read-only public data, local personal research. Raw responses stay under ignored .runtime.
import {mkdirSync,readFileSync,writeFileSync,existsSync} from 'node:fs';
import {createHash} from 'node:crypto';
const root='.runtime/vndirect-s1-20261016';mkdirSync(root,{recursive:true});
const base='https://api-finfo.vndirect.com.vn/v4/';
const manifest={provider:'VNDIRECT public finfo',classification:'REAL_RESEARCH',cutoff:'2026-10-16',requests:[]};
let last=0;
async function get(name,path){
 const url=path.startsWith('https://')?path:base+path, file=`${root}/${name}.json`,meta=`${root}/${name}.meta.json`;
 if(existsSync(file)&&existsSync(meta)){const m=JSON.parse(readFileSync(meta));if(m.url===url){manifest.requests.push(m);return JSON.parse(readFileSync(file));}}
 await new Promise(r=>setTimeout(r,Math.max(0,4000-(Date.now()-last))));
 for(let attempt=0;attempt<3;attempt++){
  last=Date.now();const response=await fetch(url,{headers:{'User-Agent':'QuantResearch/0.3 personal research'},signal:AbortSignal.timeout(45000)});
  if([429,503].includes(response.status)){const wait=Number(response.headers.get('retry-after')??15);await new Promise(r=>setTimeout(r,Math.min(120,Math.max(4,wait))*1000));continue;}
  if(!response.ok)throw new Error(`${name}: HTTP ${response.status}`);
  const text=await response.text(),data=JSON.parse(text);
  const rows=Array.isArray(data)?data:data.data;
  if(!Array.isArray(rows)||(!Array.isArray(data)&&(data.totalPages>1||data.totalElements!==rows.length)))throw new Error(`${name}: incomplete pagination`);
  const m={url,fetchedAt:new Date().toISOString(),sha256:createHash('sha256').update(text).digest('hex'),rows:rows.length};
  writeFileSync(file,text);writeFileSync(meta,JSON.stringify(m,null,2));manifest.requests.push(m);console.log(name,m.rows);return data;
 }throw new Error(`${name}: retry limit`);
}
const baseline=await get('baseline','stock_prices?sort=date&q=date:gte:2023-12-01~date:lte:2023-12-29~floor:HOSE,HNX~type:STOCK&size=20000&page=1');
const values=new Map();for(const b of baseline.data){if(!values.has(b.code))values.set(b.code,[]);values.get(b.code).push(b.nmValue);}
const universe=[...values].filter(([,v])=>v.length>=20).map(([code,v])=>{v.sort((a,b)=>a-b);return{code,medianValue:(v[Math.floor((v.length-1)/2)]+v[Math.floor(v.length/2)])/2};}).sort((a,b)=>b.medianValue-a.medianValue||a.code.localeCompare(b.code)).slice(0,100);
writeFileSync(`${root}/universe.json`,JSON.stringify({selectionDate:'2023-12-29',policy:'Top 100 HOSE/HNX stocks by median matched VND value in December 2023; >=20 observations. Frozen before test; no future-return selection.',stocks:universe},null,2));
await get('index','vnmarket_prices?sort=date&q=code:VNINDEX~date:gte:2022-01-01~date:lte:2026-10-16&size=2000&page=1');
for(let i=0;i<universe.length;i+=10){
 const codes=universe.slice(i,i+10).map(s=>s.code).join(',');
 await get(`prices-${i/10}`,`stock_prices?sort=date&q=code:${codes}~date:gte:2022-01-01~date:lte:2026-10-16&size=20000&page=1`);
 await get(`events-${i/10}`,`events?q=code:${codes}~locale:VN&size=10000&page=1`);
 await get(`masters-${i/10}`,`stocks?q=code:${codes}&size=100&page=1`);
}
await get('sectors','https://trading.vietcap.com.vn/api/price/symbols/getAll');
writeFileSync(`${root}/manifest.json`,JSON.stringify(manifest,null,2));
console.log('COMPLETE',root,'100 symbols; no data committed or uploaded.');
