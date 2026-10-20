import { Injectable, OnModuleDestroy } from '@nestjs/common';
import { Pool } from 'pg';
import Redis from 'ioredis';
import { required } from './config';

@Injectable()
export class Database implements OnModuleDestroy {
  readonly pool = new Pool({ connectionString: required('DATABASE_URL'), max: 8, connectionTimeoutMillis: 3000, statement_timeout: 5000 });
  readonly redis = new Redis(required('REDIS_URL'), { lazyConnect: true, maxRetriesPerRequest: 1, connectTimeout: 2000, retryStrategy: () => null });
  constructor() { this.redis.on('error', () => undefined); }
  async onModuleDestroy() { await this.pool.end(); this.redis.disconnect(); }
}
