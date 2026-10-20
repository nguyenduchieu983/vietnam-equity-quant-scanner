# Backtest methodology — local DEMO M3

Only COMPLETE immutable synthetic-history-v2 datasets are usable. The calendar
is weekdays, not verified Vietnam exchange holidays. Universe includes a late
listing and a delisting. No real-market validation is claimed.

## Execution and accounting

Signals use FINAL session t; entries use t+1 OPEN plus adverse slippage and
venue/price-tier tick rounding. Halt, zero volume, limit-up buys, limit-down
sells and prices outside observed OHLC/bands produce NO_FILL. Participation
<=5% of whole-day volume is explicitly ex-post conservatism, not liquidity
known at open. Lot size 100. Targets disabled; gap stops use the worse of open
and stop. Daily candles do not establish the true intraday execution path.

Decimal NAV = settled cash + receivables + marked holdings. Buy fee, sell fee,
sell tax charged once. Shares/proceeds become available at T+2 end-of-day plus
one next-session opening offset. No unsettled proceeds reuse, margin or shorts.
Risk budgets include existing positions, sector/gross exposure and cash reserve.
Effective-dated packages/config/research-rules.json is an **unverified illustrative
assumption**, not a verified exchange/broker policy.

Splits change shares/entry/stop without duplicating cost. Dividends become
receivables on ex-date, cash on payable date; unsupported events fail closed.
Closed-trade PnL excludes dividend allocation; total NAV includes dividends.
Open positions are marked, not forcibly liquidated. Unavailable/delisted marks
remain stale with a warning; no invented liquidation price.

## Research protocol

Distinct TRAIN < VALIDATION < TEST; embargo >= maxHold between splits. Features
use prior causal warmup; each segment restarts capital. Defaults: train
2022-01-03..2023-12-29, validation 2024-02-15..2024-06-28, final test
2024-09-02..2026-10-16. Rolling walk-forward uses 252 train/126 test sessions
with embargo and ends before final test. No learning/optimization is performed.
Contemporaneous cross-sectional percentiles are not fitted scalers. The app
labels final test separately but does not prevent repeated inspection: users
must not call a repeatedly examined holdout untouched confirmatory research.

Benchmark: synthetic VNINDEX price index from first test open, plus 0% cash.
No dividend reinvestment benchmark. Annualization 252 sessions, Sharpe risk-free
0. Undefined metrics are null/N/A. Fewer than 30 closed trades triggers warning.
Slippage sensitivity .05%/.30% per side versus .10% base can alter fills and
trade count; returns need not be monotonic. No automatic strategy promotion.

## Reproducibility and jobs

Each run keeps config, immutable dataset/strategy IDs, content/feature/engine
hashes, rules, Git commit and dirty state, ordered fills and daily equity.
Reproducibility hash excludes run IDs/timestamps. Outputs cannot be overwritten.
Exports include JSON plus order/equity/trade CSV with escaped text. Cancellation
publishes no partial artifact. Heartbeat renews leases; at most three retries;
only one BACKTEST claimed concurrently. Each simulation segment is capped at
120 seconds. No 2,000-symbol capacity claim has been established.
