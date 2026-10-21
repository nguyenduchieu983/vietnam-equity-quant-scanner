# Quant VN — native equity research terminal

Spec v1.1 implementation: local **M1–M3 DEMO research workflow** is runnable.
Vue 3 + TypeScript + PrimeVue 4/Aura, dark/light; NestJS; Python 3.12;
native PostgreSQL/Redis. Linux production definitions use PM2/systemd/Nginx.

Implemented: immutable synthetic history, quality checks, causal features,
S1–S4 scanners with explanations, symbol charts, durable backtest jobs,
settlement-aware portfolio simulation, OOS/walk-forward, metrics and CSV/JSON.
No live broker execution. No real-market performance is claimed.

```powershell
.\infra\scripts\dev-start-windows.ps1
.\infra\scripts\test-research-windows.ps1
```

Open http://127.0.0.1:5173/lab and log in with local `.env` value
`SMOKE_ADMIN_PASSWORD`. First import DEMO history in Operations if needed.
Choose dataset/strategy and run backtest. Defaults use 50m VND illustrative
capital, separate train/validation/test periods and 30-session embargo.

Windows hosts Vite; API/worker/DB run natively in WSL Ubuntu 22.04. This is a
launcher for the prepared local environment, not a clean Windows installer.
See [Windows instructions](docs/LOCAL_WINDOWS.md), [status](docs/IMPLEMENTATION_STATUS.md),
[test report](docs/TEST_REPORT.md), [methodology](docs/BACKTEST_METHODOLOGY.md).

Daily desk is the default localhost page at `/portfolio`; advanced paper ledger
is at `/portfolio/ledger`. [Windows login startup and daily workflow](docs/DAILY_DESK.md).
Paired S1 paper: [paper guide](docs/PAPER_TRADING.md).
It separates real-data forward accounts from historical replay and requires EOD approval.

The prepared local workspace now uses `DATA_MODE=real`: Dashboard, Scanner,
symbol charts and Strategy Lab read the VNDIRECT public EOD snapshot (100-stock
fixed cohort). Run `paper-refresh-windows.ps1` to refresh, import and rescan.
Historical gaps remain visible as PARTIAL/provisional research, never filled
with synthetic prices. Older DEMO records remain isolated in the database.

Still open: licensed real-data adapter and incremental EOD scheduler, full-scale
performance benchmark, unrestricted manual paper order entry, clean-server install and reboot
acceptance. See [Linux runbook](docs/OPERATIONS.md) for native deployment scripts.
Not investment advice.
