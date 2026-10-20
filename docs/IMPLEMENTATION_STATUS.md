# Implementation status — 2026-10-20

**Not complete. M0 foundation implemented and locally tested; M0 deployment acceptance still open. M1–M4 not started.**

User steering: **run on the local Windows machine first**. Production server
deployment/reboot is deferred. `docs/LOCAL_WINDOWS.md` describes the Windows
launcher and its native WSL backend. This does not cancel the remaining M1–M4 scope.

This follows the spec's gate: do not start a later milestone before the current
vertical slice and required checks pass. Screen placeholders are not delivered
milestones. No performance, backtest or market claims are fabricated.

## M0 implemented

- Monorepo; exact npm versions and lockfile; Python transitive locks with hashes.
- SQL checksum migration authority; provenance tables and DEMO separation.
- Typed provider protocol, FixtureProvider, MockProviderError, Decimal OHLC normalization.
- Three invented symbols, two exchanges, synthetic VNINDEX, one session.
- Idempotent import, immutable revisions by unique key, raw payload snapshots, run status and missing-data reasons.
- NestJS auth, request validation, rate limiting, audit, health, status, UNKNOWN regime, empty scans/results, ingestion jobs.
- PostgreSQL durable job consumer, recovery lease, heartbeat.
- PrimeVue/Aura terminal shell; overview and operations backed by DB; scanner empty state and query controls; remaining screens explicitly pending.
- Windows-local PowerShell start/stop launchers tested with native WSL backend; browser checks passed for M0.
- PM2/systemd/Nginx definitions; install/start/stop/deploy/health/backup/restore/smoke scripts.
- Native CI workflow added, not remotely executed.

## Actual runtime and evidence

- Windows Node 22.19.0 built NestJS/Vue and ran API tests.
- Linux WSL Ubuntu 22.04 originally had Node 12/Python 3.10.
- Isolated Node 22.19.0 and Python 3.12.13 were installed under ignored `.runtime/` for native Linux checks.
- Existing native PostgreSQL 18.6 and Redis 8.10.1 used; a new isolated `quant_m0` role/database was created. Existing database contents were not changed.
- No local Git repository existed at discovery. Delivery initializes local Git
  against the existing GitHub `origin/main` history; M0 is committed separately
  from the pending M1–M4 work.
- See `TEST_REPORT.md` for actual commands/results and failures resolved.

## Open M0 gates / blockers

1. Clean Ubuntu 24.04 installation and the standard `dev-start.sh` flow have not been run. The successful Linux smoke used isolated runtime overrides.
2. Production PM2/systemd/Nginx deployment, TLS, least-privilege DB roles, log rotation, backup/restore and reboot recovery remain unverified.
3. No target server/SSH access, public hostname/certificate or maintenance window was supplied. Do not reboot this workstation to claim AC17.
4. Real source integration: `BLOCKED: PROVIDER_CREDENTIALS`; license/entitlement, complete delisting/action history and market-rule effective dates unresolved. This blocks real mode, not fixture research.
5. OpenAPI response DTO generation and complete schema set remain pending.

## Milestone ledger

| Milestone | State | Remaining |
|---|---|---|
| M0 | IN PROGRESS | Close deployment/reproducibility gates above |
| M1 | NOT STARTED | Real adapters, incremental multi-session ingestion, rate limiting/retry, finality, gaps, adjustment reconciliation, schedule |
| M2 | NOT STARTED | All rolling features, regime, S1–S4, exclusions/ranks, symbol chart, alerts |
| M3 | NOT STARTED | Risk/fills/settlement engine, backtest metrics/artifacts, OOS/walk-forward, lab |
| M4 | NOT STARTED | Immutable paper ledger, preview/approval/session simulation, hardening, profiling |

## Acceptance matrix

| ID | Status | Evidence / missing |
|---|---|---|
| AC01 | NOT RUN | Clean supported Ubuntu installation not verified |
| AC02 | PARTIAL | Fixture provenance exists; authorized real provider absent |
| AC03 | PARTIAL | Exact fixture count/missing-symbol status; historical coverage absent |
| AC04 | NOT IMPLEMENTED | No feature engine |
| AC05 | NOT IMPLEMENTED | No scanners |
| AC06 | NOT IMPLEMENTED | No risk engine |
| AC07 | NOT IMPLEMENTED | No backtest/settlement engine |
| AC08 | NOT IMPLEMENTED | No research metrics or OOS engine |
| AC09 | PARTIAL | Overview/operations and empty scanner; later screens placeholders |
| AC10 | PARTIAL | No real execution surface; paper workflow absent |
| AC11 | PARTIAL | Idempotency/leases/health/scripts; provider retries and recovery unverified |
| AC12 | PARTIAL | Local M0 checks; remote CI and full mandatory matrix not complete |
| AC13 | NOT RUN | No 2,000-symbol/5-year benchmark or UI P95 measurement |
| AC14 | NOT IMPLEMENTED | No recommendations; no invented evidence |
| AC15 | PARTIAL | No prohibited deployment artifacts/runtime commands introduced; native M0 smoke passes; clean setup outstanding |
| AC16 | PARTIAL | PrimeVue/Aura build, theme and real components; six functional screens not delivered |
| AC17 | NOT RUN | Enablement definitions only, no server reboot evidence |
