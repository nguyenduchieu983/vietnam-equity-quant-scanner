# Implementation status — 2026-10-20

**Runnable local M1–M3 DEMO workflow; not full production/spec acceptance.**
User scope: Windows first, backtest working, tests, commit/push. Frontend runs on
Windows, native API/worker/PostgreSQL/Redis inside WSL Ubuntu 22.04. No containers.

## Delivered

- M0 retained: authentication, native lifecycle scripts, health, durable jobs,
  audit, checksummed SQL migrations, PrimeVue/Aura dark/light shell.
- M1 local data slice: deterministic synthetic 2022–2026 history (8 invented
  stocks + index), point-in-time listing/delisting, OHLC/finality/coverage checks,
  explicit missing-vs-zero volume, immutable snapshots, idempotent normalization,
  source hashes, provider retry tests. Real data remains unavailable.
- M2: causal EMA/ATR/RSI/momentum/liquidity features; index/breadth regime;
  four scanner engines with ranks/exclusions and versioned config; server paging,
  explanations, raw/adjusted symbol candlesticks, volume and moving averages.
- M3: durable cancellable backtests, single-backtest claim concurrency,
  heartbeat/lease recovery, Decimal cash accounting, risk caps, lots/ticks,
  conservative fills, settlement, corporate actions, separate OOS periods,
  rolling walk-forward, cost sensitivity, benchmark/net metrics, immutable
  artifacts, JSON/order CSV/equity CSV/trade CSV. Strategy Lab uses actual results.

## Gates and evidence

M1 passed data tests and native API ingest before M2; M2 passed feature tests,
API scanner/paging and browser chart tests before M3. M3 added risk/accounting
and research tests. See TEST_REPORT.md for exact commands and outcomes.
All numbers from synthetic history are test outputs, not market performance.

## Acceptance matrix

| AC | Local evidence / remaining scope |
|---|---|
| 01 | Prepared Windows+WSL start/stop passes. Clean Ubuntu production installation not accepted yet. |
| 02 | Source/version/as-of in DEMO; licensed provider credentials/coverage still blocked. |
| 03 | Synthetic universe, sessions, late listing, delisting and missing bars tested. Real coverage unverified. |
| 04 | Golden features, causal warmup, future perturbation and prior breakout window pass. |
| 05 | Four deterministic explainable scanners/config versions implemented and exercised. |
| 06 | Decimal risk, position/gross/sector/cash/lot constraints tested; no margin/short support. |
| 07 | Next-session entries, settlement, costs, no-fill/gap/volume cases tested under illustrative rules. |
| 08 | Separate splits, embargo, walk-forward, benchmark and cost sensitivity visible. No real validation. |
| 09 | Five research screens work; Paper Portfolio M4 remains a clearly labelled placeholder. |
| 10 | No broker endpoints/keys. Manual paper simulation/ledger belongs to M4. |
| 11 | Retry/idempotency/leases/health/scripts implemented; real EOD scheduler and backup recovery drill pending. |
| 12 | Local lint/types/unit/DB/API/browser checks run; CI workflow expanded, remote run not claimed. |
| 13 | Small synthetic job timings recorded only; 2,000 instruments x 5 years and UI P95 not benchmarked. |
| 14 | Features, exclusions, dates, stops and data provenance available in explanations/artifacts. |
| 15 | Native execution; no container requirement. |
| 16 | Vue3/TS + PrimeVue4.5.5 + Aura, charts, controls, build; full six-screen acceptance awaits M4. |
| 17 | Production Linux reboot and Windows auto-start not tested/configured for acceptance. |

Remaining M1 production work: authorized provider adapter, real incremental EOD
fetch/scheduler and revision reconciliation. Existing retry helper is exercised
against controlled failures, not a live provider. Current history importer is
snapshot/idempotent, not a claim of live incremental fetching.
M4/manual paper and production deployment remain outside this local backtest delivery.
