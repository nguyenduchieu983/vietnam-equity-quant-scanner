import { Body, Controller, Get, HttpException, HttpStatus, Module, Param, ParseUUIDPipe, Post, Query, ServiceUnavailableException, UseGuards } from '@nestjs/common';
import { APP_GUARD } from '@nestjs/core';
import { JwtModule } from '@nestjs/jwt';
import { ThrottlerGuard, ThrottlerModule } from '@nestjs/throttler';
import { IsIn, IsInt, IsOptional, IsString, Max, MaxLength, Min } from 'class-validator';
import { Type } from 'class-transformer';
import { Database } from './db';
import { AuthController, AuthGuard } from './auth';
import { mode, required, safeSort } from './config';

class ResultsQuery {
  @Type(() => Number) @IsInt() @Min(1) @Max(100000) page = 1;
  @Type(() => Number) @IsInt() @Min(1) @Max(100) limit = 25;
  @IsOptional() @IsIn(['HOSE', 'HNX']) exchange?: string;
  @IsOptional() @IsIn(['S1', 'S2', 'S3', 'S4']) strategy?: string;
  @IsOptional() @Type(() => Number) @Min(0) @Max(100) minScore?: number;
  @IsIn(['symbol', 'score', 'exchange']) sort = 'symbol';
  @IsIn(['asc', 'desc']) direction = 'asc';
  @IsOptional() @IsString() @MaxLength(20) query?: string;
}
class IngestDto {
  @IsIn(['fixture']) provider!: string;
  @IsString() @MaxLength(128) idempotencyKey!: string;
}
@Controller()
class HealthController {
  constructor(private readonly db: Database) {}
  @Get('health/live') live() { return { status: 'UP' }; }
  @Get('health/ready')
  async ready() {
    try {
      await this.db.pool.query('SELECT 1');
      await this.db.redis.ping();
      const worker = await this.db.pool.query("SELECT 1 FROM worker_heartbeats WHERE id='quant-worker' AND observed_at > now()-interval '30 seconds'");
      if (!worker.rowCount) throw new Error('worker unavailable');
      return { status: 'UP' };
    } catch { throw new ServiceUnavailableException('Dependency unavailable'); }
  }
}
@UseGuards(AuthGuard)
@Controller()
class AppController {
  constructor(private readonly db: Database) {}
  @Get('system/status')
  async status() {
    const result = await this.db.pool.query(`SELECT
      (SELECT count(*)::int FROM market_bars WHERE is_demo=$1) AS bars,
      (SELECT count(*)::int FROM instruments WHERE is_demo=$1) AS instruments,
      (SELECT max(finished_at) FROM ingestion_runs WHERE status='COMPLETE' AND is_demo=$1) AS "lastIngest",
      (SELECT max(session_date)::text FROM market_bars WHERE is_demo=$1) AS "latestSession",
      EXISTS(SELECT 1 FROM worker_heartbeats WHERE observed_at > now()-interval '30 seconds') AS worker`, [mode() === 'demo']);
    const redis = await this.db.redis.ping().then(() => true).catch(() => false);
    return { ...result.rows[0], database: true, redis, isDemo: mode() === 'demo', milestone: 'M0' };
  }
  @Get('market/regime')
  regime() { return { regime: 'UNKNOWN', riskMultiplier: 0, reasons: ['FEATURE_ENGINE_NOT_IMPLEMENTED'], breadth50: null }; }
  @Get('scans')
  async scans(@Query() q: ResultsQuery) {
    const result = await this.db.pool.query('SELECT * FROM scan_runs WHERE is_demo=$1 ORDER BY session_date DESC, id LIMIT $2 OFFSET $3', [mode() === 'demo', q.limit, (q.page - 1) * q.limit]);
    return result.rows;
  }
  @Get('scans/:id/results')
  async results(@Param('id', ParseUUIDPipe) id: string, @Query() q: ResultsQuery) {
    const params = [id, mode() === 'demo', q.exchange ?? null, q.minScore ?? null, q.query ?? '', q.strategy ?? null];
    const where = `FROM rankings r JOIN instruments i ON i.id=r.instrument_id JOIN scan_runs s ON s.id=r.scan_run_id
      WHERE s.id=$1 AND s.is_demo=$2 AND ($3::text IS NULL OR i.exchange=$3)
      AND ($4::numeric IS NULL OR r.composite_score >= $4)
      AND i.symbol ILIKE '%' || $5 || '%' AND ($6::text IS NULL OR r.strategy_code=$6)`;
    const count = await this.db.pool.query(`SELECT count(*)::int AS total ${where}`, params);
    const rows = await this.db.pool.query(`SELECT i.symbol,i.exchange,r.* ${where}
      ORDER BY ${safeSort(q.sort)} ${q.direction === 'desc' ? 'DESC' : 'ASC'} NULLS LAST,i.symbol,r.id
      LIMIT $7 OFFSET $8`, [...params, q.limit, (q.page - 1) * q.limit]);
    return { items: rows.rows, total: count.rows[0].total, page: q.page, limit: q.limit };
  }
  @Get('instruments')
  async instruments(@Query() q: ResultsQuery) {
    return (await this.db.pool.query(`SELECT symbol,exchange,name FROM instruments
      WHERE is_demo=$1 AND symbol ILIKE '%' || $2 || '%' AND ($3::text IS NULL OR exchange=$3)
      ORDER BY symbol LIMIT $4 OFFSET $5`, [mode() === 'demo', q.query ?? '', q.exchange ?? null, q.limit, (q.page - 1) * q.limit])).rows;
  }
  @Get('ingestion/runs')
  async runs(@Query() q: ResultsQuery) {
    return (await this.db.pool.query('SELECT * FROM ingestion_runs WHERE is_demo=$1 ORDER BY started_at DESC LIMIT $2 OFFSET $3', [mode() === 'demo', q.limit, (q.page - 1) * q.limit])).rows;
  }
  @Post('ingestion/runs')
  async ingest(@Body() dto: IngestDto) {
    if (mode() !== 'demo') throw new HttpException('DATA_UNAVAILABLE: PROVIDER_CREDENTIALS', HttpStatus.CONFLICT);
    const client = await this.db.pool.connect();
    try {
      await client.query('BEGIN');
      const job = await client.query(`INSERT INTO jobs(kind,idempotency_key,payload_json,is_demo)
        VALUES('INGEST',$1,$2,true) ON CONFLICT(kind,idempotency_key,is_demo) DO UPDATE SET idempotency_key=excluded.idempotency_key RETURNING id,status`,
      [dto.idempotencyKey, JSON.stringify({ provider: dto.provider })]);
      await client.query("INSERT INTO audit_logs(actor,action,entity,entity_id) VALUES('admin','REQUEST_INGEST','jobs',$1)", [job.rows[0].id]);
      await client.query('COMMIT');
      return job.rows[0];
    } catch (e) { await client.query('ROLLBACK'); throw e; } finally { client.release(); }
  }
  @Get('jobs/:id')
  async job(@Param('id', ParseUUIDPipe) id: string) {
    const result = await this.db.pool.query('SELECT id,kind,status,attempts,error_code,created_at,finished_at FROM jobs WHERE id=$1 AND is_demo=$2', [id, mode() === 'demo']);
    if (!result.rowCount) throw new HttpException('Job not found', 404);
    return result.rows[0];
  }
  @Get('data-quality/issues')
  async issues(@Query() q: ResultsQuery) {
    return (await this.db.pool.query('SELECT * FROM data_quality_issues WHERE is_demo=$1 ORDER BY created_at DESC LIMIT $2 OFFSET $3', [mode() === 'demo', q.limit, (q.page - 1) * q.limit])).rows;
  }
}
@Module({
  imports: [
    JwtModule.registerAsync({ global: true, useFactory: () => {
      const secret = required('JWT_SECRET');
      if (secret.length < 32) throw new Error('JWT_SECRET too short');
      return { secret, signOptions: { expiresIn: '30m' } };
    } }),
    ThrottlerModule.forRoot([{ ttl: 60000, limit: 60 }])
  ],
  controllers: [HealthController, AuthController, AppController],
  providers: [Database, AuthGuard, { provide: APP_GUARD, useClass: ThrottlerGuard }]
})
export class AppModule {}
