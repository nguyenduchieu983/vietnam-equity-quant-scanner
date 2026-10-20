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

Still open: licensed real-data adapter and incremental EOD scheduler, full-scale
performance benchmark, paper portfolio M4, clean-server install and reboot
acceptance. See [Linux runbook](docs/OPERATIONS.md) for native deployment scripts.
Not investment advice.
