import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
const rules=JSON.parse(readFileSync(resolve(__dirname,'../../../packages/config/research-rules.json'),'utf8'));
export function dailyPlan(account:any,calendar:string[],sectorBySymbol:Record<string,string>={}) {
  const d=account.decision_json, p=account.state_json.positions, cfg=account.config_json;
  const cash=Number(account.state_json.cash), pending=account.state_json.pending.reduce((s:number,x:any)=>s+Number(x[1]),0);
  const gross=Object.values(p).reduce((s:number,x:any)=>s+Number(x.qty)*Number(x.last),0);
  const nav=cash+pending+gross;let available=cash,allocated=gross;
  const sectors:Record<string,number>={};
  for(const [symbol,x] of Object.entries(p) as any[]) {const sector=sectorBySymbol[symbol]??'UNKNOWN';sectors[sector]=(sectors[sector]??0)+Number(x.qty)*Number(x.last);}
  let entries=0;
  const buys=[...d.signals].sort((a:any,b:any)=>b.score-a.score||a.symbol.localeCompare(b.symbol)).map((s:any)=>{
    const entry=Number(s.features_used.raw_close)*(1+cfg.slippage),stop=Number(s.invalidation_price);
    let qty=0,reason='';
    if(p[s.symbol])reason='Đang nắm giữ';
    else if(entries>=rules.max_daily_entries||Object.keys(p).length+entries>=rules.max_positions)reason='Đạt giới hạn số vị thế / lệnh mới';
    else if(entry<=stop||stop<=0)reason='Stop không hợp lệ';
    else if(d.state.riskMultiplier<=0)reason='Thị trường chặn mua';
    else {qty=Math.max(0,Math.floor(Math.min(nav*rules.risk_per_trade*d.state.riskMultiplier/(entry-stop),nav*rules.position_cap/entry,Math.max(0,nav*rules.gross_cap-allocated)/entry,Math.max(0,nav*rules.sector_cap-(sectors[s.sector]??0))/entry,Math.max(0,available-nav*rules.cash_reserve)/(entry*(1+cfg.buyFee)))/rules.board_lot)*rules.board_lot);if(!qty)reason='Không đủ hạn mức / lô';}
    if(qty)entries++;available-=qty*entry*(1+cfg.buyFee);allocated+=qty*entry;sectors[s.sector]=(sectors[s.sector]??0)+qty*entry;
    return {symbol:s.symbol,side:'BUY',type:'Mở cửa giả lập',quantity:qty,reference:Number(s.features_used.raw_close),stop,target:cfg.s1PartialTarget?entry+(entry-stop):null,status:reason||'Chờ phiên kế tiếp',score:s.score};
  });
  const nextIndex=calendar.indexOf(d.day)+1,nextDate=calendar[nextIndex];
  const exits=Object.entries(p).map(([symbol,x]:any)=>{
    const heldLocks=(x.locks??[]).reduce((n:number,[release,qty]:any)=>n+((typeof release==='number'?release>nextIndex:!nextDate||release>nextDate)?Number(qty):0),0);
    const quantity=nextIndex<x.sellable?0:Math.max(0,Math.floor((x.qty-heldLocks)/rules.board_lot)*rules.board_lot);
    const f=d.features[symbol]??{};const timed=nextIndex-x.bought>cfg.maxHold,ema=f.close!=null&&f.close<f.ema50;
    const stop=cfg.s1TrailAtr&&(!cfg.s1PartialTarget||x.runner_active)&&f.atr14&&f.factor?Math.max(Number(x.stop),(f.close-cfg.s1TrailAtr*f.atr14)/f.factor):Number(x.stop);
    return {symbol,side:'SELL',type:timed||ema?'Mở cửa giả lập (EMA / hết hạn)':'Chờ stop / chốt 1R',quantity,reference:Number(x.last),stop,target:x.target?Number(x.target):null,status:quantity?'Chờ điều kiện phiên mới':'Cổ phiếu chưa về / lô lẻ',score:null};
  });
  return {decisionDay:d.day,nextSession:calendar[calendar.indexOf(d.day)+1]??null,regime:d.state.regime,buys,exits};
}
export function checklist(account:any,symbol:string){
  const f=account.decision_json.features[symbol]??{},s=account.decision_json.signals.find((x:any)=>x.symbol===symbol),c=account.config_json;
  const row=(label:string,pass:boolean|null,value:unknown)=>({label,pass,value:value??'—'});
  return [row('Giá > EMA50',f.close!=null?f.close>f.ema50:null,f.raw_close),row('EMA50 đang tăng',f.ema50_slope10!=null?f.ema50_slope10>0:null,f.ema50_slope10),row('Lợi suất 60 phiên > 0',f.ret60!=null?f.ret60>0:null,f.ret60==null?null:`${(f.ret60*100).toFixed(2)}%`),row('Thanh khoản 20 phiên',f.median_value20!=null?f.median_value20>=c.minLiquidity:null,f.median_value20),row('Đủ 130 phiên',f.n!=null?f.n>=130:null,f.n),row('Được phép giao dịch',f.is_final!=null?f.is_final&&!f.halted&&f.volume>0:null,f.volume),row('Thị trường cho phép mua',['RISK_ON','NEUTRAL'].includes(account.decision_json.state.regime),account.decision_json.state.regime),row('Được S1 chọn: top 15%, điểm ≥70',!!s,s?.score)];
}
