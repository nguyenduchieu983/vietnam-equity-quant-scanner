# Architecture — spec v1.1

Current implementation: M0 foundation only. M1–M4 remain gated, not delivered.

- Vue 3 / TypeScript / Vite / PrimeVue 4.5.5, Aura (`@primeuix/themes` 2.0.3), PrimeIcons, Router, Pinia. Both PrimeVue/theme packages declare MIT.
- Theme tokens live in `apps/web/src/theme`; local browser settings persist dark/light.
- NestJS 11 on Node 22 owns JWT authentication, bounded REST queries, ingestion job requests and audit.
- Python 3.12 owns fixture normalization and ingestion. No price calculation in the frontend.
- PostgreSQL is the durable queue and source of truth. `FOR UPDATE SKIP LOCKED` claims jobs with a lease. A worker restart recovers expired claims up to the configured attempt limit. Fixture ingestion is idempotent.
- Redis is health-checked; scheduling/Redis queue integration is deferred to M1. The current DB queue does not depend on an in-memory job list.
- A single checksum-verified SQL migration runner (`python -m quant migrate`) owns all schema changes. Advisory locking serializes migration runners. Never edit an applied migration.
- Monetary columns use NUMERIC; Python uses Decimal; JSON decimal output remains strings. Timestamps use timestamptz.
- Fixture bars, instruments, calendars, runs and jobs are explicitly DEMO. Real mode cannot enqueue fixture ingestion. No production provider adapter exists.
- Scan API returns stored scans only. M0 does not create scans; `UNKNOWN` regime is explicit.
- Raw snapshots and ingestion run references preserve provenance. Corrections require new revision identifiers.
- Native deployment design: Nginx static SPA/reverse proxy; PM2 single API process; systemd Python; native PostgreSQL and Redis.

Security boundaries: only liveness/readiness and login are public. JWT is memory-only in UI, expires after 30 minutes, and is sent via Authorization (no auth cookies). Throttling is process-local; deployment is one API instance. Request logs omit headers, bodies and query strings. Audit updates/deletes are rejected by a DB trigger. Production is loopback-only until TLS is configured.

M0 limitations: one fixture session; no adjustment computation; no exchange calendar verification; no production freshness evaluation; no migrations for later strategy/backtest/paper domain entities yet. SQL owner is currently shared by migration/API/worker for demo; separate production least-privilege grants remain a deployment gate.

Retention: keep market revisions, raw payloads and audit records until provider licensing and retention policy are approved. Backup retention is 14 days; no market/audit deletion task. Existing session and queue indexes suffice for M0. Partitioning is deferred until measured.
