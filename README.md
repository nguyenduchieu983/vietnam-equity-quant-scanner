# Quant VN — native equity research terminal

Implementation of `VIETNAM_QUANT_SCANNER_CODEX_SPEC.md` v1.1 is **in progress**.
Current deliverable is the **M0 foundation**, not the completed M0–M4 product.

Vue 3 + TypeScript + PrimeVue/Aura; NestJS API; Python 3.12 worker; PostgreSQL;
Redis. Deployment files target native Ubuntu, PM2, systemd and Nginx.

Implemented: authenticated overview, fixture ingestion, durable job queue, raw
provenance, validation/idempotency, migration runner, empty scanner API/table,
dark/light terminal shell and operational script drafts.

Not implemented: live providers, feature/scanning engines, historical symbol
charts, backtests, paper trading and full acceptance/performance/reboot tests.
Later screens explicitly show their pending milestone; no fake results.

For the current Windows machine, use [local Windows startup](docs/LOCAL_WINDOWS.md):

```powershell
.\infra\scripts\dev-start-windows.ps1
```

The local frontend runs on Windows; backend/data services run natively in WSL.
For a Linux server, start with [operations](docs/OPERATIONS.md), then
[implementation status](docs/IMPLEMENTATION_STATUS.md) and
[test report](docs/TEST_REPORT.md).

```bash
node infra/scripts/init-demo-env.mjs
# Ubuntu native dependencies + isolated demo DB must be prepared per runbook.
bash infra/scripts/dev-start.sh
bash infra/scripts/smoke-test.sh
```

Frontend: `http://127.0.0.1:5173`. API documentation:
`http://127.0.0.1:3000/api/docs` in development.

DEMO fixtures are invented instruments and one invented session; never use them
for investment decisions or production rankings. Not investment advice.
