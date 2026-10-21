import { Body, ConflictException, Controller, Get, Param, ParseUUIDPipe, Post, UseGuards } from '@nestjs/common';
import { IsDateString, IsIn, IsOptional, IsUUID } from 'class-validator';
import { randomUUID } from 'node:crypto';
import { Database } from './db';
import { AuthGuard } from './auth';
import { dailyPlan, checklist } from './desk';

class CreatePair {
  @IsUUID() snapshotId!: string;
  @IsIn(['FORWARD','REPLAY']) mode!: string;
  @IsOptional() @IsDateString() startDay?: string;
  @IsUUID() idempotencyKey!: string;
}
class AdvancePair {
  @IsUUID() snapshotId!: string;
  @IsDateString() through!: string;
  @IsDateString() expectedCursor!: string;
}
@UseGuards(AuthGuard)
@Controller('paper')
export class PaperController {
  constructor(private readonly db: Database) {}
  @Get('desk/:id')
  async desk(@Param('id',ParseUUIDPipe) id:string){
    const detail=await this.detail(id);
    const snapshot=(await this.db.pool.query("SELECT payload_json->'instruments' AS items,payload_json->'calendar' AS calendar FROM paper_market_snapshots WHERE id=$1",[detail.pair.snapshot_id])).rows[0];
    const sectors=Object.fromEntries(snapshot.items.map((x:any)=>[x.symbol,x.sector]));
    return {...detail,plans:detail.accounts.map(a=>({code:a.code,...dailyPlan(a,snapshot.calendar,sectors)}))};
  }
  @Get('desk/:id/symbol/:symbol')
  async symbol(@Param('id',ParseUUIDPipe) id:string,@Param('symbol') symbol:string){
    const pair=(await this.db.pool.query('SELECT snapshot_id,cursor_day::text AS day FROM paper_pairs WHERE id=$1',[id])).rows[0];
    if(!pair||! /^[A-Z0-9]{1,12}$/.test(symbol))throw new ConflictException('INVALID_SYMBOL_OR_PAIR');
    const bars=(await this.db.pool.query("SELECT b FROM paper_market_snapshots s,LATERAL jsonb_array_elements(s.payload_json->'bars') b WHERE s.id=$1 AND b->>'symbol'=$2 AND b->>'session_date'<=$3 ORDER BY b->>'session_date' DESC LIMIT 1500",[pair.snapshot_id,symbol,pair.day])).rows.map(r=>r.b).reverse();
    const accounts=(await this.db.pool.query('SELECT code,config_json,decision_json,state_json FROM paper_accounts WHERE pair_id=$1 ORDER BY code',[id])).rows;
    return {symbol,bars,day:pair.day,accounts:accounts.map(a=>({code:a.code,checks:checklist(a,symbol),position:a.state_json.positions[symbol]??null,signal:a.decision_json.signals.find((x:any)=>x.symbol===symbol)??null}))};
  }
  @Get()
  async list() {
    const snapshot=(await this.db.pool.query("SELECT id,as_of::text AS as_of,created_at,content_hash,quality_json,payload_json->'calendar'->>-34 AS suggested_replay_start FROM paper_market_snapshots ORDER BY as_of DESC,created_at DESC LIMIT 1")).rows[0]??null;
    const pairs=(await this.db.pool.query('SELECT id,name,mode,initial_day::text AS initial_day,cursor_day::text AS cursor_day,created_at FROM paper_pairs ORDER BY created_at DESC LIMIT 30')).rows;
    return {source:'VNDIRECT_PUBLIC_REAL',isDemo:false,classification:'PAPER_ONLY_PROVISIONAL',latestSession:snapshot?.as_of,snapshot,pairs};
  }
  @Post('pairs')
  async create(@Body() body: CreatePair) {
    if(!(await this.db.pool.query('SELECT id FROM paper_market_snapshots WHERE id=$1',[body.snapshotId])).rowCount)throw new ConflictException('PAPER_SNAPSHOT_NOT_FOUND');
    const payload={action:'CREATE',snapshotId:body.snapshotId,mode:body.mode,startDay:body.startDay};
    const c=await this.db.pool.connect();
    try {
      await c.query('BEGIN');
      await c.query('SELECT pg_advisory_xact_lock(hashtext($1))',[body.idempotencyKey]);
      const existing=(await c.query("SELECT id,status,payload_json FROM jobs WHERE kind='PAPER' AND idempotency_key=$1",[body.idempotencyKey])).rows[0];
      if(existing){if(JSON.stringify(existing.payload_json)!==JSON.stringify(JSON.parse(JSON.stringify(payload)))){
        // JSONB key order is not significant.
        if(existing.payload_json.mode!==body.mode||existing.payload_json.snapshotId!==body.snapshotId||existing.payload_json.startDay!==body.startDay)throw new ConflictException('IDEMPOTENCY_CONFLICT');
      }await c.query('COMMIT');return existing;}
      const row=(await c.query("INSERT INTO jobs(kind,idempotency_key,payload_json,is_demo) VALUES('PAPER',$1,$2,false) RETURNING id,status",[body.idempotencyKey,JSON.stringify(payload)])).rows[0];
      await c.query("INSERT INTO audit_logs(actor,action,entity,entity_id) VALUES('admin','APPROVE_PAPER_CREATE','jobs',$1)",[row.id]);
      await c.query('COMMIT');return row;
    }catch(e){await c.query('ROLLBACK');throw e;}finally{c.release();}
  }
  @Get('jobs/:id')
  async job(@Param('id',ParseUUIDPipe) id:string){
    return (await this.db.pool.query("SELECT id,status,progress,result_json,error_code FROM jobs WHERE id=$1 AND kind='PAPER'",[id])).rows[0];
  }
  @Get('pairs/:id')
  async detail(@Param('id',ParseUUIDPipe) id:string){
    const pair=(await this.db.pool.query('SELECT p.*,initial_day::text AS initial_day,cursor_day::text AS cursor_day FROM paper_pairs p WHERE id=$1',[id])).rows[0];
    if(!pair)throw new ConflictException('PAPER_PAIR_NOT_FOUND');
    const accounts=(await this.db.pool.query('SELECT id,code,config_json,state_json,summary_json,decision_json FROM paper_accounts WHERE pair_id=$1 ORDER BY code',[id])).rows;
    for(const a of accounts){
      const records=(await this.db.pool.query("SELECT session_date,payload_json - 'decision' AS payload_json FROM paper_sessions WHERE account_id=$1 ORDER BY session_date",[a.id])).rows;
      a.equity=records.flatMap(r=>r.payload_json.equity);
      a.trades=records.flatMap(r=>r.payload_json.trades);
      a.orders=records.flatMap(r=>r.payload_json.orders);
      a.cashEvents=records.flatMap(r=>r.payload_json.cash_events);
    }
    const approvals=(await this.db.pool.query('SELECT p.through_date::text AS through_date,p.created_at,j.id AS job_id,j.status,j.error_code FROM paper_approvals p JOIN jobs j ON j.id=p.job_id WHERE p.pair_id=$1 ORDER BY p.created_at DESC LIMIT 30',[id])).rows;
    return {source:'VNDIRECT_PUBLIC_REAL',isDemo:false,pair,accounts,approvals};
  }
  @Get('pairs/:id/preview')
  async preview(@Param('id',ParseUUIDPipe) id:string){
    const pair=(await this.db.pool.query('SELECT cursor_day::text AS cursor_day,mode FROM paper_pairs WHERE id=$1',[id])).rows[0];
    const snapshot=(await this.db.pool.query('SELECT id,as_of::text AS as_of FROM paper_market_snapshots ORDER BY as_of DESC,created_at DESC LIMIT 1')).rows[0];
    if(!pair||!snapshot)throw new ConflictException('PAPER_NOT_READY');
    return {snapshotId:snapshot.id,through:snapshot.as_of,expectedCursor:pair.cursor_day,mode:pair.mode,
      canAdvance:String(snapshot.as_of)>String(pair.cursor_day),capitalEach:50000000,buyFee:.0015,sellFee:.0015,sellTax:.001,slippage:.001};
  }
  @Post('pairs/:id/advance')
  async advance(@Param('id',ParseUUIDPipe) id:string,@Body() body:AdvancePair){
    const c=await this.db.pool.connect();
    try{
      await c.query('BEGIN');
      const prior=(await c.query('SELECT j.id,j.status FROM paper_approvals a JOIN jobs j ON j.id=a.job_id WHERE a.pair_id=$1 AND a.snapshot_id=$2 AND a.through_date=$3 AND a.expected_cursor=$4',[id,body.snapshotId,body.through,body.expectedCursor])).rows[0];
      if(prior){await c.query('COMMIT');return prior;}
      const pair=(await c.query('SELECT cursor_day::text AS cursor_day FROM paper_pairs WHERE id=$1 FOR UPDATE',[id])).rows[0];
      if(!pair)throw new ConflictException('PAPER_PAIR_NOT_FOUND');
      const snap=(await c.query('SELECT as_of::text AS as_of FROM paper_market_snapshots WHERE id=$1',[body.snapshotId])).rows[0];
      if(!snap||String(pair.cursor_day)!==body.expectedCursor||body.through<=body.expectedCursor||body.through>String(snap.as_of))throw new ConflictException('STALE_PAPER_PREVIEW');
      const row=(await c.query("INSERT INTO jobs(kind,idempotency_key,payload_json,is_demo) VALUES('PAPER',$1,$2,false) RETURNING id,status",[randomUUID(),JSON.stringify({action:'ADVANCE'})])).rows[0];
      await c.query('INSERT INTO paper_approvals(pair_id,snapshot_id,through_date,expected_cursor,job_id) VALUES($1,$2,$3,$4,$5)',[id,body.snapshotId,body.through,body.expectedCursor,row.id]);
      await c.query("INSERT INTO audit_logs(actor,action,entity,entity_id) VALUES('admin','APPROVE_PAPER_ADVANCE','jobs',$1)",[row.id]);
      await c.query('COMMIT');return row;
    }catch(e){await c.query('ROLLBACK');throw e;}finally{c.release();}
  }
}
