import { randomBytes, scryptSync } from 'node:crypto';
import { writeFileSync } from 'node:fs';
// Run once in the repository root. Never overwrites existing secrets.
const password = randomBytes(24).toString('base64url');
const salt = randomBytes(24).toString('hex');
const dbPassword = randomBytes(24).toString('hex');
writeFileSync('.env', [
  'NODE_ENV=development', 'PORT=3000', 'DATA_MODE=demo',
  `DATABASE_URL=postgresql://quant_m0:${dbPassword}@127.0.0.1:5432/quant_m0`,
  'REDIS_URL=redis://127.0.0.1:6379/0',
  `JWT_SECRET=${randomBytes(48).toString('hex')}`,
  `ADMIN_PASSWORD_SALT=${salt}`,
  `ADMIN_PASSWORD_HASH=${scryptSync(password, salt, 64).toString('hex')}`,
  `SMOKE_ADMIN_PASSWORD=${password}`,
  'WORKER_POLL_SECONDS=2', 'WORKER_MAX_ATTEMPTS=3', ''
].join('\n'), { flag: 'wx', mode: 0o600 });
console.log('Created .env. Read SMOKE_ADMIN_PASSWORD locally to sign in. Do not commit or paste secrets.');
