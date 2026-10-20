# Test report — 2026-10-20

Environment: Windows Node22.19.0 + Edge headless; WSL Ubuntu22.04 Python3.12,
native PostgreSQL18/Redis8, dedicated quant_m0 database. Synthetic data only.

## Commands

Start with infra/scripts/dev-start-windows.ps1, then:

```powershell
.\infra\scripts\test-research-windows.ps1
```

The runner performs lint, TS/Vue typecheck, production build, API unit tests,
WSL migration/DB/Python tests + Ruff/mypy, foundation/M1/M2/M3 API suites and
Edge browser suites. It waits between batches to respect API rate limiting.
Linux CI uses infra/scripts/test-native-slice.sh with apt-installed services.
Remote GitHub Actions completion is not asserted by this report.

## Verified tests

- TypeScript/Nest build + Vue production build, ESLint: pass.
- API unit tests: 2 pass (sort allowlist, unknown data-mode fails closed).
- Python unit + native DB integration: 27 pass, no skips in integration mode.
- Ruff: pass; mypy: 13 source files pass.
- Foundation API: authentication, throttle-compatible requests, bounded query,
  durable/idempotent fixture import and actual health.
- M1 API: history job -> COMPLETE immutable dataset, zero missing expected bars,
  >1,200 synthetic sessions and one delisting; repeat import preserves ID.
- M2 API: same inputs return same scan ID; S1–S4 explanations, server paging,
  30-bar symbol slice and persisted features. Browser: explanations and candle chart.
- M3 API: S1/S2/S3/S4 complete; repeated S1 same reproducibility hash; every NAV
  reconciles cash+receivables+holdings, no negative cash; ordered entry/exit;
  train/test/walk-forward artifacts, slippage scenarios, CSV row counts;
  invalid dates/costs rejected and cancelled job publishes no equity.
- M3 browser: form submits real job, metrics/chart/ledger/provenance and JSON
  download, no uncaught page errors. Screenshots retained in ignored .runtime.

Engine cases include exact fees/tax/PnL, T+2 end availability at next open,
settled proceeds, same-bar prevention, adverse gap stop, 5% participation cap,
price bands/tick rounding, sector/gross/cash/board-lot limits, split neutrality,
dividend receivables, cost sensitivity, no-lookahead and embargo boundaries.

Observed initial small-dataset API jobs: 4–6 seconds before adding two extra
cost-sensitivity runs. Final per-strategy durations are recorded in
.runtime/m3-results.json; these are not the AC13 2,000-symbol benchmark.
DEMO S1–S3 have small closed-trade samples; warnings are preserved, not hidden.

## Explicitly not passed

Real-provider integration/entitlements, exchange holiday/action coverage,
production incremental scheduler, verified exchange/broker assumptions,
production backup/restore/reboot, M4 manual paper flows, large-universe/UI-P95
benchmark. These are marked partial/open in IMPLEMENTATION_STATUS.md.
No passing return threshold or fabricated market claim is used in tests.

Latest full local API suite after cost-sensitivity and stop correction: S1 7,
S2 9, S3 1, S4 31 closed trades (synthetic holdout). Each job including extra
scenarios completed in approximately 6–8 seconds. This is diagnostic coverage,
not evidence of investment performance. During browser verification, lazy
PrimeVue dependency optimization caused a dev-page reload; explicit Vite
prebundling fixed it. The subsequent browser run verified provenance expansion,
JSON and equity CSV download, plus dark/light rendering.

Final rerun of infra/scripts/test-research-windows.ps1 completed with exit code 0: all static, unit, DB/API and both browser suites passed together after the Vite fix.
