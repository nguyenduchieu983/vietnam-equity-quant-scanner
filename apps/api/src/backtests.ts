import { Body, Controller, Get, Post, Param, ParseUUIDPipe, UseGuards, ConflictException } from '@nestjs/common';
import { IsUUID, IsIn, IsDateString, IsNumber, IsInt, Min, Max } from 'class-validator';
import { createHash } from 'node:crypto';
import { Database } from './db';
import { AuthGuard } from './auth';
import { mode } from './config';
class BacktestDto {
  @IsUUID() datasetId!: string;
  @IsIn(['S1','S2','S3','S4']) strategy!: string;
  @IsDateString() trainStart!: string;
  @IsDateString() trainEnd!: string;
  @IsDateString() validationStart!: string;
  @IsDateString() validationEnd!: string;
  @IsDateString() testStart!: string;
  @IsDateString() testEnd!: string;
  @IsNumber() @Min(1) @Max(100000000) capital = 50000000;
  @IsNumber() @Min(0) @Max(.03) buyFee = .0015;
  @IsNumber() @Min(0) @Max(.03) sellFee = .0015;
  @IsNumber() @Min(0) @Max(.03) sellTax = .001;
  @IsNumber() @Min(0) @Max(.03) slippage = .001;
  @IsInt() @Min(1) @Max(60) maxHold = 30;
  @IsInt() @Min(1) @Max(120) embargoSessions = 30;
  @IsNumber() @Min(0) @Max(1e12) minLiquidity = 5e9;
}
@UseGuards(AuthGuard)
@Controller('backtests')
export class BacktestsController {
  constructor(private readonly db: Database) {}
  @Post()
  async create(@Body() config: BacktestDto) {
    const c=await this.db.pool.connect();
    try {
      await c.query('BEGIN');
      const ds=(await c.query("SELECT payload_json FROM research_datasets WHERE id=$1 AND is_demo=$2 AND (status='COMPLETE' OR (NOT is_demo AND status='PARTIAL' AND quality_json->>'researchEligible'='true'))",[config.datasetId,mode()==='demo'])).rows[0];
      if(!ds) throw new ConflictException('DATASET_NOT_COMPLETE');
      const dates=[config.trainStart,config.trainEnd,config.validationStart,config.validationEnd,config.testStart,config.testEnd];
      const indices=dates.map(d=>ds.payload_json.calendar.indexOf(d));
      if(indices.some(i=>i<0)||indices.some((v,i)=>i>0&&v<=indices[i-1])||config.embargoSessions<config.maxHold||indices[2]-indices[1]-1<config.embargoSessions||indices[4]-indices[3]-1<config.embargoSessions) throw new ConflictException('INVALID_SPLITS_OR_EMBARGO');
      if(config.strategy==='S4'&&![5,10].includes(config.maxHold)) throw new ConflictException('S4_HOLD_MUST_BE_5_OR_10');
      const strategy=(await c.query('SELECT id FROM strategy_definitions WHERE code=$1 ORDER BY version DESC LIMIT 1',[config.strategy])).rows[0];
      const job=(await c.query("INSERT INTO jobs(kind,idempotency_key,payload_json,is_demo) VALUES('BACKTEST',$1,'{}',$2) RETURNING id",[crypto.randomUUID(),mode()==='demo'])).rows[0];
      const hash=createHash('sha256').update(JSON.stringify(config)).digest('hex');
      const run=(await c.query(`INSERT INTO backtest_runs(job_id,dataset_id,strategy_id,parameter_hash,data_cutoff,train_start,train_end,test_start,test_end,config_json,fees_json,assumptions_json,status,is_demo)
        VALUES($1,$2,$3,$4,$5,$6,$7,$8,$5,$9,$10,$11,'QUEUED',$12) RETURNING id,job_id,status`,
        [job.id,config.datasetId,strategy.id,hash,config.testEnd,config.trainStart,config.trainEnd,config.testStart,JSON.stringify(config),JSON.stringify({buyFee:config.buyFee,sellFee:config.sellFee,sellTax:config.sellTax,slippage:config.slippage}),JSON.stringify({mode:mode()==='demo'?'DEMO':'REAL_RESEARCH_PROVISIONAL',rules:'illustrative-v1'}),mode()==='demo'])).rows[0];
      await c.query('UPDATE jobs SET payload_json=$1 WHERE id=$2',[JSON.stringify({backtestId:run.id}),job.id]);
      await c.query("INSERT INTO audit_logs(actor,action,entity,entity_id) VALUES('admin','REQUEST_BACKTEST','backtest_runs',$1)",[run.id]);
      await c.query('COMMIT'); return run;
    } catch(e){await c.query('ROLLBACK');throw e;}finally{c.release();}
  }
  @Get()
  async list(){return (await this.db.pool.query('SELECT id,job_id,status,config_json,metrics_json,created_at,error_code FROM backtest_runs WHERE is_demo=$1 ORDER BY created_at DESC LIMIT 50',[mode()==='demo'])).rows;}
  @Get(':id')
  async detail(@Param('id',ParseUUIDPipe) id:string){
    const run=(await this.db.pool.query('SELECT * FROM backtest_runs WHERE id=$1 AND is_demo=$2',[id,mode()==='demo'])).rows[0];
    if(!run)throw new ConflictException('BACKTEST_NOT_FOUND');
    const artifact=(await this.db.pool.query('SELECT payload_json FROM backtest_artifacts WHERE run_id=$1',[id])).rows[0]?.payload_json;
    const equity=(await this.db.pool.query('SELECT payload_json FROM backtest_daily_equity WHERE run_id=$1 ORDER BY session_date LIMIT 2000',[id])).rows.map(r=>r.payload_json);
    const trades=(await this.db.pool.query('SELECT payload_json FROM backtest_trades WHERE run_id=$1 ORDER BY sequence LIMIT 5000',[id])).rows.map(r=>r.payload_json);
    return {...run,artifact,equity,trades};
  }
  @Post(':id/cancel')
  async cancel(@Param('id',ParseUUIDPipe) id:string){
    const c=await this.db.pool.connect();
    try{
      await c.query('BEGIN');
      const row=(await c.query('SELECT j.id,j.status,b.status AS run_status FROM jobs j JOIN backtest_runs b ON b.job_id=j.id WHERE b.id=$1 AND b.is_demo=$2 FOR UPDATE OF j',[id,mode()==='demo'])).rows[0];
      if(!row||!['QUEUED','RUNNING'].includes(row.status)||!['QUEUED','RUNNING'].includes(row.run_status))throw new ConflictException('JOB_NOT_CANCELLABLE');
      await c.query("UPDATE jobs SET cancel_requested=true,status=CASE WHEN status='QUEUED' THEN 'CANCELLED' ELSE status END WHERE id=$1",[row.id]);
      if(row.status==='QUEUED')await c.query("UPDATE backtest_runs SET status='CANCELLED',finished_at=now() WHERE id=$1",[id]);
      await c.query("INSERT INTO audit_logs(actor,action,entity,entity_id) VALUES('admin','CANCEL_BACKTEST','backtest_runs',$1)",[id]);
      await c.query('COMMIT');return {cancelRequested:true};
    }catch(e){await c.query('ROLLBACK');throw e;}finally{c.release();}
  }
  @Get(':id/equity')
  async equity(@Param('id',ParseUUIDPipe) id:string){return (await this.detail(id)).equity;}
  @Get(':id/trades')
  async trades(@Param('id',ParseUUIDPipe) id:string){return (await this.detail(id)).trades;}
  @Get(':id/export')
  async export(@Param('id',ParseUUIDPipe) id:string){
    const result=await this.detail(id);
    if(result.status!=='COMPLETE')throw new ConflictException('BACKTEST_NOT_COMPLETE');
    const orders=(await this.db.pool.query('SELECT payload_json FROM backtest_orders WHERE run_id=$1 ORDER BY sequence LIMIT 20000',[id])).rows.map(r=>r.payload_json);
    const csv=(rows:Record<string,unknown>[])=>{
      if(!rows.length)return '';
      const keys=Object.keys(rows[0]);
      const cell=(v:unknown)=>{let s=String(v??'');if(/^[=+@\t\r]/.test(s)||(/^-/ .test(s)&&!Number.isFinite(Number(s))))s="'"+s;return '"'+s.replaceAll('"','""')+'"';};
      return [keys.map(cell).join(','),...rows.map(row=>keys.map(k=>cell(row[k])).join(','))].join('\r\n');
    };
    return {result,ordersCsv:csv(orders),equityCsv:csv(result.equity),tradesCsv:csv(result.trades)};
  }
}
