import { Body, Controller, Get, NotFoundException, Param, ParseUUIDPipe, Patch, Post, Query, UseGuards, ConflictException } from '@nestjs/common';
import { IsDateString, IsInt, IsOptional, IsUUID, Max, Min } from 'class-validator';
import { Type } from 'class-transformer';
import { Database } from './db';
import { AuthGuard } from './auth';
import { mode } from './config';

export class ScanDto {
  @IsUUID() datasetId!: string;
  @IsOptional() @IsDateString({strict:true}) session?: string;
}
class StrategyConfigDto {
  @IsInt() @Min(0) @Max(1000000000000) minLiquidity!: number;
  @IsInt() @Min(1) @Max(60) maxHold!: number;
}
class BarsQuery {
  @IsUUID() datasetId!: string;
  @IsOptional() @IsDateString({strict:true}) from?: string;
  @IsOptional() @IsDateString({strict:true}) to?: string;
  @IsOptional() @Type(()=>Number) @IsInt() @Min(1) @Max(1500) limit = 500;
}
@UseGuards(AuthGuard)
@Controller()
export class ResearchController {
  constructor(private readonly db: Database) {}
  @Post('scans')
  async scan(@Body() body: ScanDto) {
    const dataset = await this.db.pool.query("SELECT id FROM research_datasets WHERE id=$1 AND is_demo=$2 AND (status=$3 OR (NOT is_demo AND status='PARTIAL' AND quality_json->>'researchEligible'='true'))", [body.datasetId, mode()==='demo','COMPLETE']);
    if (!dataset.rowCount) throw new ConflictException('DATASET_NOT_COMPLETE');
    const client = await this.db.pool.connect();
    try {
      await client.query('BEGIN');
      const job = await client.query(`INSERT INTO jobs(kind,idempotency_key,payload_json,is_demo) VALUES('SCAN',$1,$2,$3) RETURNING id,status`,
        [crypto.randomUUID(),JSON.stringify(body),mode()==='demo']);
      await client.query("INSERT INTO audit_logs(actor,action,entity,entity_id) VALUES('admin','REQUEST_SCAN','jobs',$1)",[job.rows[0].id]);
      await client.query('COMMIT');
      return job.rows[0];
    } catch(e) { await client.query('ROLLBACK'); throw e; } finally { client.release(); }
  }
  @Get('strategies')
  async strategies() {
    return (await this.db.pool.query('SELECT DISTINCT ON(code) * FROM strategy_definitions ORDER BY code,version DESC')).rows;
  }
  @Patch('strategies/:id/config')
  async configure(@Param('id',ParseUUIDPipe) id:string,@Body() body:StrategyConfigDto) {
    const client = await this.db.pool.connect();
    try {
      await client.query('BEGIN');
      await client.query('SELECT pg_advisory_xact_lock(61732004)');
      const original = await client.query('SELECT code FROM strategy_definitions WHERE id=$1',[id]);
      if (!original.rowCount) throw new NotFoundException();
      const created = await client.query(`INSERT INTO strategy_definitions(code,version,config_json)
        SELECT $1,max(version)+1,$2 FROM strategy_definitions WHERE code=$1 RETURNING *`,[original.rows[0].code,JSON.stringify(body)]);
      await client.query("INSERT INTO audit_logs(actor,action,entity,entity_id,payload_json) VALUES('admin','STRATEGY_REVISION','strategy_definitions',$1,$2)",[created.rows[0].id,JSON.stringify(body)]);
      await client.query('COMMIT');
      return created.rows[0];
    } catch(e) { await client.query('ROLLBACK'); throw e; } finally { client.release(); }
  }
  @Get('instruments/:symbol/bars')
  async bars(@Param('symbol') symbol:string,@Query() q:BarsQuery) {
    const result = await this.db.pool.query(`SELECT bar FROM research_datasets d,
      LATERAL jsonb_array_elements(d.payload_json->'bars') bar
      WHERE d.id=$1 AND d.is_demo=$2 AND bar->>'symbol'=$3
      AND ($4::text IS NULL OR bar->>'session_date'>=$4) AND ($5::text IS NULL OR bar->>'session_date'<=$5)
      ORDER BY bar->>'session_date' DESC LIMIT $6`,[q.datasetId,mode()==='demo',symbol,q.from??null,q.to??null,q.limit]);
    return result.rows.map(r=>r.bar).reverse();
  }
  @Get('instruments/:symbol/features')
  async features(@Param('symbol') symbol:string) {
    const result = await this.db.pool.query(`SELECT f.* FROM feature_snapshots f JOIN instruments i ON i.id=f.instrument_id
      WHERE i.symbol=$1 AND i.is_demo=$2 ORDER BY session_date DESC LIMIT 1`,[symbol,mode()==='demo']);
    return result.rows[0]??null;
  }
}
