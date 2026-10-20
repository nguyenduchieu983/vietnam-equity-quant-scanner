# VIETNAM EQUITY QUANT SCANNER — CODEX IMPLEMENTATION SPEC

**Version:** 1.1 (native Linux deployment + PrimeVue UI)  
**Date:** 2026-10-20  
**Market:** Vietnamese cash equities (HOSE/HNX for MVP; UPCoM future)  
**Mode:** EOD research + signal scanner + dashboard + paper trading; NO REAL ORDER PLACEMENT  
**Reference capital:** configurable, default 50,000,000 VND; intended range below 100,000,000 VND  
**Audience:** Codex coding agent, backend/frontend engineers, individual quant researcher.

> IMPORTANT: This is an engineering specification, not a promise of returns. No signal may be presented as guaranteed. Codex MUST NOT add live broker order submission, margin or derivatives to MVP. No simulated performance numbers may be fabricated. Everything must be auditable and reproducible.

## 0. Instructions to Codex: execution contract

1. Inspect current repository first. Do not overwrite existing services. If empty, initialize monorepo per section 3.
2. Implement one vertical slice end-to-end per milestone, including migrations, tests, API, UI and sample/demo data. Leave the repository runnable at each milestone.
3. Commit progress in logical units if Git is configured. Maintain `docs/IMPLEMENTATION_STATUS.md` with completed items, blockers, actual working commands, tests and pending tasks.
4. Never invent API response payloads, API credentials, historical prices, benchmark returns, win rates or backtest results. Fixture/synthetic data must be clearly labeled `DEMO` and excluded from production rankings.
5. Check provider API versions, entitlement, rate limits and licenses. Implement provider-specific code behind adapters; use configuration rather than hard-coding endpoints. Work offline with fixtures if no credentials exist; mark scans `DATA_UNAVAILABLE` rather than pretending they succeeded.
6. Produce code, not only plans or UI mockups. Run migrations, lint, typecheck, unit tests, integration tests and an end-to-end smoke path; record outputs.
7. No leakage of credentials into logs, browser or Git. Use `.env.example`; never commit real tokens.
8. Always compute features only from inputs available at decision time, and separate signal timestamp from earliest plausible order timestamp.
9. Signal scanner is **informational**. Execution is paper-only and explicit; no live broker write endpoint should exist.
10. Implement clean architecture, explicit errors, DTO validation, dependency injection, structured logging, simple maintainable code and documentation. Avoid unneeded microservices/Kubernetes.
11. **HARD CONSTRAINT: NO DOCKER**. Do not create Dockerfile, docker-compose.yml, container images, or use Docker commands in setup, tests, CI, or deployment. Run all services natively.
12. **HARD CONSTRAINT: PrimeVue** is the UI component framework for Vue 3; no shadcn-vue, Naive UI, Vuetify, Element Plus, Quasar or other competing component framework. Follow current PrimeVue official docs and lock compatible versions.

## 1. Product goals and scope

### 1.1 Goals

- Daily EOD ingestion for full active universe of HOSE/HNX cash equities plus VNINDEX/VN30 (optional sector indices when available).
- Market-regime dashboard: bullish/neutral/bearish plus data-quality freshness.
- Four independently configurable, backtestable strategies, common signal schema and explainable rankings.
- Scanner: filters, sort, compare scores, inspect underlying reasons, exclusion reasons, price/volume charts and risk budget.
- Backtesting: point-in-time universe, honest fill assumptions, costs/taxes, no lookahead, date-split OOS, walk-forward.
- Paper trading: manual approval of hypothetical transactions, immutable ledger, capital reservation, realistic settlement and portfolio analytics.
- Daily scheduled scan after reliable EOD publication; idempotent reruns, alerts with dedup, operational observability.

### 1.2 Deliberate exclusions (MVP)

- No live execution, real money, automatic order submission or broker trade credentials.
- No intraday/HFT/order-book alpha, derivatives, leverage, short-selling, LLM-based buy/sell decision engine.
- No multi-tenant redistribution of market data or unlicensed commercial data resale.
- No unsupported extrapolation of fundamentals (post-MVP optional).
- No guarantee of positive returns, predefined minimum Sharpe, or forced positive backtest result.

### 1.3 Initial trading universe and account defaults

- Universe: listed common equities on HOSE/HNX, not ETFs, bonds, warrants or preferred shares. Use `security_type` and historic listing intervals; do not filter solely on today's surviving symbols.
- UPCoM: separate provider support and exchange rules, disabled for MVP scoring by default.
- Liquidity baseline (configurable): minimum 20-day median daily matched value >= **5,000,000,000 VND**; 60 trading sessions historical data; no current halt / listing restriction. Median is preferable to mean for one-day spikes. For 20-day windows require >= 18 valid sessions.
- Default capital 50m VND; max 5 simultaneous positions; initial per-stock exposure <=20%; sector <=35%; cash reserve >=10%; max aggregate market exposure <=80%; no margin. With 100-share board lots, skip orders that do not fit; optional broker-agnostic odd-lot simulation only if venue support is verified and toggle enabled.
- Signal timeframe daily close; recommended hold 5–30 sessions. Full backtest may simulate up to 60 sessions.

## 2. Provider research and data governance

### 2.1 Sources

- `vnstock`: Python library adapter for personal research ONLY within current license/quota. Verify usage rights, data origin, quotas, package interface, and source provenance. Do not publish raw licensed data to third parties.
- `SSI FastConnect V3`: candidate primary authorized market-data provider; API key and secret managed backend-side. Check current docs and account eligibility.
- `DNSE OpenAPI`: alternative market-data provider; confirm actual access and limitations. A provider may not be used without credentials if required.
- Exchange / corporate-action official or licensed feeds: prioritize verifiable effective date, announcement date and adjustment factor.

Document provider selection in `docs/DATA_PROVIDER_MATRIX.md`: coverage, historic depth, adjustment policy, index availability, latency/freshness, rate limits, cost, legal rights, known gaps and API version. Never silently merge incompatible adjusted/unadjusted histories.

### 2.2 Data contract and provenance

`DailyBar`: `{symbol, exchange, session_date, open_raw, high_raw, low_raw, close_raw, volume, traded_value, reference_price?, ceiling_price?, floor_price?, provider, observed_at, ingested_at, source_revision, is_final}`. Monetary amounts in VND; prices in VND per share; volumes in shares. Store DECIMAL/NUMERIC, never float for financial accounting. Normalize timezone `Asia/Ho_Chi_Minh` for trading calendar; database timestamps UTC.

Keep raw payload snapshots plus canonical normalized tables. Introduce `adjusted_close`/adjustment factors in a separate curated table; do not replace original execution prices. Raw OHLC must be consistent `high>=max(open,close)`, `low<=min(open,close)`, volume >=0. Zero-volume legitimate sessions are different from missing records. Deduplicate using `(symbol, exchange, date, provider, revision)` and store ingestion run IDs.

Corporate action fields include `type, announced_at, ex_date, record_date, payable_date, adjustment_ratio, source, revision, known_at`. Backtests only see events/metadata announced before decision time. If corporate-action series is unavailable/uncertain, mark adjusted-price indicators as degraded and prevent unjustified long-history return comparisons.

Point-in-time security master: `symbol`, `instrument_id`, `exchange`, `sector`, `security_type`, `listed_at`, `delisted_at`, `status`, `valid_from`, `valid_to`, `known_at`; symbols can migrate/change. Store sector membership changes as dated records when possible.

### 2.3 EOD pipeline

`discover symbols -> load security master -> fetch dates/bars/index -> fetch actions -> validate -> stage -> normalize -> reconcile adjustments -> calculate features -> classify regime -> generate signals -> rank/filter -> evaluate risk -> publish scan run -> notify`.

- Run scheduling configurable only for Vietnamese trading dates with exchange holiday calendar. Default initial attempt 16:30 local, repeat with controlled retry/backoff until provider marks final; do not assume 16:30 always final.
- Per-provider rate-limit token bucket, bounded concurrency, exponential backoff + jitter, 429 handling, idempotent checkpoints and partial-resume.
- Incremental fetch last N (default 7) sessions for corrections; nightly historical gap scan; full history import supports batching and retries.
- A scan must be `COMPLETE`, `PARTIAL`, `STALE` or `FAILED`; only `COMPLETE` or explicitly accepted `PARTIAL` may publish production notifications. UI shows final bar date, index date, data-source and freshness.
- Block scan ranking if benchmark daily bar missing, actionable symbol OHLC inconsistent, or >5% universe bars missing. Threshold configurable and logged.
- Detect impossible daily changes; do not reject large corporate-action/exception dates without verifying event and exchange rules.

## 3. Architecture / monorepo

```
quant-vn/
  apps/
    api/                   # NestJS REST API, WS/SSE optional, auth, schedule orchestration
    web/                   # Vue 3 + TypeScript + Vite + PrimeVue (mandatory)
    quant-worker/          # Python 3.12 FastAPI/CLI worker: ingest, features, scan, backtest
  packages/
    contracts/             # OpenAPI-generated DTO client, JSON schemas, API errors
    config/                # shared non-secret config / schemas
  infra/
    systemd/               # quant-worker.service, optional native timers, health checks
    nginx/                 # reverse proxy to API + static Vue SPA
    scripts/               # native setup, start, stop, backup, restore, smoke
    migrations/            # preferably Alembic for DB shared with Python; single migration authority
    prometheus/            # optional if lightweight enough
  docs/
    ARCHITECTURE.md
    DATA_PROVIDER_MATRIX.md
    STRATEGIES.md
    MARKET_RULES.md
    BACKTEST_METHODOLOGY.md
    API_SPEC.md
    OPERATIONS.md
    IMPLEMENTATION_STATUS.md
  tests/
    fixtures/
    e2e/
  .env.example
  Makefile
  README.md
```

**Technology:** NestJS Node 22 LTS compatible runtime (check supported version), Vue3/TS, Python3.12 + Polars/Pandas/NumPy, PostgreSQL16+, Redis7 + BullMQ or Python job queue. Use Redis/BullMQ in API to enqueue Python worker requests via durable DB job records / API or Redis Streams. Do not rely on in-memory per-process jobs. Native Linux install on single VPS; Nginx serves Vue static files and proxies API, PM2 supervises NestJS, systemd supervises Python worker, PostgreSQL and Redis run as native system services. Charts via TradingView Lightweight Charts (respect license). Avoid dual migration ownership; choose one canonical migration tool.

**Separation:** API owns auth, configuration, job orchestration, paper ledger and UI responses. Python owns provider ingestion, normalized features, all strategy decisions, deterministic backtest. PostgreSQL is the common durable interface. Workers are idempotent. Never expose API secrets to UI. Health checks for API, DB, Redis, worker and provider freshness.

## 4. Database schema (minimum)

Create proper SQL migrations with UUID PKs, foreign keys, unique constraints, UTC timestamps, date indexes, NUMERIC amounts and status enums/checks:

1. `instruments(id, symbol, exchange, type, name, current_status, ...)`
2. `instrument_history(instrument_id, effective_from, effective_to, known_at, sector_id, listing_status, ...)`
3. `market_sessions(exchange, session_date, is_trading_day, ...)`
4. `market_bars(id, instrument_id, session_date, open, high, low, close, volume, traded_value, reference_price, floor_price, ceiling_price, provider_id, revision, is_final, ingested_at, UNIQUE(...))`
5. `index_bars(index_code, session_date, open, high, low, close, volume?, provider_id, revision, ...)`
6. `corporate_actions(id, instrument_id, action_type, announced_at, ex_date, ratio?, cash_amount?, known_at, source, revision, ...)`
7. `adjustment_factors(instrument_id, session_date, factor, methodology, asof_version, ...)`
8. `data_providers(id, name, enabled, license_metadata, ...)`
9. `ingestion_runs(id, provider_id, kind, from_date, to_date, status, counts_json, started_at, finished_at, error_summary)`
10. `data_quality_issues(id, instrument_id?, session_date?, severity, rule, details_json, resolved_at)`
11. `feature_snapshots(instrument_id, session_date, features_json, version_hash, known_at, UNIQUE(...))` — version features; optimize columns later
12. `strategy_definitions(id, code, version, config_json, enabled, created_at)`
13. `scan_runs(id, session_date, universe_version, feature_version, strategy_versions_json, status, freshness_json, started_at, finished_at)`
14. `signals(id, scan_run_id, instrument_id, strategy_id, side, decision_at, earliest_execution_session, strength, entry_reference, invalidation_reference, explanation_json, status, UNIQUE(scan_run_id,instrument_id,strategy_id))`
15. `rankings(scan_run_id, instrument_id, composite_score, rank, excluded, exclusion_codes_json, sub_scores_json, UNIQUE(...))`
16. `watchlists`, `watchlist_items`, `alerts`, `notification_deliveries` (idempotency keys)
17. `backtest_runs(id, strategy_version, parameter_hash, universe_version, data_cutoff, train_start, train_end, test_start, test_end, fees_json, assumptions_json, status, metrics_json, artifact_path, started_at, finished_at)`
18. `backtest_trades`, `backtest_daily_equity`, `backtest_orders` (persist reproducible outputs)
19. `paper_accounts(id, starting_cash, currency, rules_version, ...)`, `paper_orders`, `paper_fills`, `paper_positions`, `paper_cash_ledger`, `paper_corporate_action_events`, `paper_daily_nav`
20. `audit_logs(id, actor, action, entity, entity_id, payload_json, occurred_at)`
21. `users` (one admin default), `app_settings`, `jobs` (state/progress/retries).

Explain retention, indexes, partitioning only if data volume warrants; avoid premature hypertable dependency. Use immutable event ledger for fills/cash; positions are derived or reconciled projections.

## 5. Feature engine & market regime

### 5.1 Point-in-time feature calculations (EOD only)

All rolling calculations exclude future bars and record lookback availability; explicitly differentiate **adjusted return series** vs **raw execution series**:

- `ret_5, ret_20, ret_60, ret_120` adjusted close returns; `rel_20 = stock_ret_20 - vnindex_ret_20` and `rel_60`.
- `ema20, ema50, ema200`, `sma20`, `high_20_prev` = max previous 20 completed highs (exclude current bar), `low_20_prev`.
- `atr14` Wilder true range on appropriately normalized series; `rsi14`; realized `vol20`.
- `volume_ratio20 = today_volume / mean(prev 20 completed sessions' volume)`; handle zero denominator.
- `median_value20`, `turnover20` if free-float data trustworthy; `price_to_52w_high` when sufficient history.
- `breadth_20 = fraction of eligible stocks above adjusted EMA20`, `breadth_50`, counts advance/decline; compute with historical universe at each date.
- Feature pipeline deterministic and version-hashed; no `fillna(0)` for unavailable indicators. Required warmup filter.

### 5.2 Market regime v1 (transparent rule, not ML)

Compute at date t using completed VNINDEX bars:
- `RISK_ON` if VNINDEX adjusted/raw-consistent close > EMA50 and EMA50 slope(10 sessions)>0 and breadth_50 >=0.55.
- `RISK_OFF` if close < EMA50 and breadth_50 <0.40.
- `NEUTRAL` otherwise, or `UNKNOWN` if missing inputs.

Risk multiplier: ON 1.0, NEUTRAL 0.5, OFF 0 (no new long candidates in recommended portfolio; show signals informationally). Regime thresholds config; store conditions and exact values. Do not fabricate breadth if symbol history insufficient; mark UNKNOWN.

## 6. Four strategies: exact MVP specification

Every strategy emits `{strategy_code, version, symbol, decision_date, side:LONG|EXIT|NONE, score:0..100, features_used, reasons, invalidation_price, earliest_trade_date, quality_flags}`. Signal detection is separate from ranking and portfolio construction. Persist all evaluated symbols incl. reasons for exclusion.

### S1 — Momentum Rank

Eligible if last close > adjusted EMA50, EMA50 slope(10)>0, `ret60>0`, median traded value20 >= threshold; at least 130 historic bars. Raw score `0.5 * percentile(rel60) + 0.3 * percentile(rel20) + 0.2 * percentile(-vol20)` across eligible same-date universe; percentiles in [0,100], deterministic tie-break symbol. Emit LONG for rank top 15% with score >=70 and favorable/neutral regime. Exit simulation configurable: drop below EMA50 or max hold 30 sessions; stops managed by portfolio engine. This is a **hypothesis**, not validated edge.

### S2 — 20-Day Breakout + Volume

At EOD t: adjusted `close_t > max(high_{t-20..t-1}) * 1.002` and `volume_t / mean(volume_{t-20..t-1}) >=1.5`, close>EMA50 and median traded value20 above threshold. Score 40% breakout distance percentile (cap unrealistic jumps), 30% volume expansion percentile, 30% rel20 percentile. Reject likely invalid corporate-action gap if unadjusted series is inconsistent. Invalidation reference `min(low_t, close_t - 2*ATR14)` converted to execution price basis where required. Default expiry next 3 trading sessions; no hindsight intraday fill.

### S3 — Pullback in Uptrend

Trend filter adjusted EMA20>EMA50>EMA200, 20-session slope EMA50 positive; latest completed bar close within [-1%, +2%] of EMA20 (distance signed / EMA20), RSI14 between 40 and 60, `close_t > close_{t-1}` and `close_t > open_t` on raw candle basis, `rel60>0`. Score combines trend strength (40%), pullback closeness (30%), relative strength (30%). Invalidation `recent 5-session low` or ATR2 whichever yields a valid stop below anticipated entry. If distance to stop invalid/excessive, exclude with reason code.

### S4 — 3–5 Day Mean Reversion (research-only initially)

In overall RISK_ON or NEUTRAL regime, adjusted long trend `close>EMA200`; three or more consecutively negative daily returns over last five bars, RSI14<35, positive liquidity and no exchange halt. Signal has lower trust category `EXPERIMENTAL`; no automatic recommendation until OOS validated. Score = 40% RSI extremeness, 30% deviation below EMA20, 30% rel60. Backtest for max 5/10-session holds plus ATR stop. Prevent selecting limit-down illiquid stocks as easy fills.

### Composite rank and explainability

Do not average strategy scores indiscriminately across unrelated objectives. UI default `primary_strategy=S1`, tabs to view each strategy. Optional composite `0.35 momentum + 0.30 breakout + 0.25 pullback + 0.10 mean_reversion` ONLY if each sub-score exists and weights configured; show missing scores and do not treat missing as 0. Avoid double-counting by persisting subcomponents. Each signal card lists 3–5 measurable reasons, source bar timestamp, data quality, intended hold horizon and explicit **Not investment advice** label.

## 7. Vietnam market rules, risk & hypothetical orders

### 7.1 Exchange rules must be versioned, verified and tested

- Normal-session price bands commonly HOSE +/-7%, HNX +/-10%, UPCoM +/-15%, subject to listing/relisting/ex-rights exceptions and effective-date updates.
- Regular board-lot typically 100 shares; odd-lot rules vary by venue/order channel; tick size varies by venue and price level.
- Vietnamese equities settle on T+2 **business/trading settlement calendar** with time-of-day/broker availability nuance. Model separate `trade_date`, `settlement_date`, `sellable_at`, and `cash_available_at`; avoid pretending a T+0 stock exit. Confirm actual venue/broker rule and effective dates before enabling live-related features.
- Price-ceiling/floor candles should not be treated as guaranteed executable fills. If no genuine liquidity data, use conservative no-fill or capped participation scenarios.
- Keep effective-dated rules in DB/config; link each assumption to source URL and revision. DO NOT encode all limits in hard-coded code constants.

### 7.2 Position sizing and guardrails (configurable **defaults**, not advice)

Reference NAV 50m VND; default buy-side risk budget per trade `0.5% NAV` = 250,000 VND; absolute max per security 20% NAV, gross equity <=80% NAV, sector <=35% NAV, max 5 open positions, cash >=10%, max daily new entries 2, no margin. Rules evaluated against existing/pending allocations, not per order independently.

For EOD signals only a *candidate* next-session entry is displayed; proposed limit based on next observable session price constraints. Risk calculation: `stop_distance = proposed_entry - stop`; reject <=0. `shares_by_risk=floor(risk_budget/stop_distance)`, `shares_by_exposure=floor(position_cap/proposed_entry)`, `shares_by_cash=floor(available_budget/proposed_entry)`. Choose min; round down to board lot 100 (unless verified odd-lot toggle); include buy fees in budget. If result zero => `NOT_AFFORDABLE` not a suggested purchase. Show max theoretical loss excluding price gaps and liquidity risk. Stops are soft **alerts** and not guaranteed executed.

Use `risk_score` (0-100) separate from alpha signal; penalize volatility, low liquidity, concentration and event/price-limit risk; never hide risk.

### 7.3 Transaction cost settings

All cost parameters explicit in backtest input, shown in UI. Default **illustrative assumption** buy broker fee 0.15%, sell broker fee 0.15%, sell-side tax 0.10%, buy/sell slippage 0.10% EACH, with configurable minimums and any applicable ancillary fees. Not a claim about user's actual brokerage tariff. Sensitivity scenarios: `optimistic`, `base`, `stress` (e.g. 0.05%, 0.10%, 0.30% slippage side). Brokerage fee, taxes, effective dates must be verified and adjustable before performance used for decisions.

## 8. Backtest engine (critical)

- Research event cycle: signal after session t FINAL close -> orders can enter at t+1 earliest (next trading session), never fill at signal candle close unless separately modeled as impossible / explicitly labeled sensitivity.
- Choose one engine policy for MVP: execute at next-session OPEN +/- configured slippage if that day's OHLC and tradability permit. OPEN fills are approximations, not guaranteed; different conservative scenarios required.
- Backtest sells only when settled shares available; disallow proceeds reuse before configured cash settlement, unless broker feature explicitly modeled. Hard cash constraint; no negative cash.
- Corporate actions adjust holdings/cost basis and cash appropriately; total returns derived without double-counting dividends. Cases with missing ex-date/ratios flagged or excluded.
- Fill model: effective price bands, halt/no volume, simulated volume participation cap <= 5% of day volume; do not use whole-day liquidity to claim knowledge available at open—treat cap as ex-post conservatism and label it. Limit-up buys and limit-down sells default `NO_FILL` when unable to prove opposite-side liquidity.
- Deterministic order: no overlapping capital, round lots/ticks, no future feature use. Stop detection from daily OHLC is ambiguous if stop and target both hit same candle: choose conservative adverse-first outcome, or disable target in MVP; no intraday perfect foresight.
- Backtest whole universe point-in-time including delisted/delisting when provider permits. If not available, mark `SURVIVORSHIP_BIAS_RISK` prominently; do not publish such backtests as fully validated.
- Strict TRAIN/VALIDATION/TEST time splits; untouched final holdout; expanding/rolling walk-forward with embargo appropriate to label horizon; fit percentile/scalers only on training period when learned transforms are used. Multiple-comparison caution across parameter searches.
- Benchmarks: VNINDEX buy-and-hold price index (with caveat re total return), cash, optionally equal-weight eligible universe and chosen ETF if comparable.
- Metrics net: total return, annualized CAGR, max drawdown, annualized volatility, Sharpe (risk-free assumption specified), Sortino, Calmar, exposure, turnover, hit rate, average win/loss, expectancy, profit factor, total trade count, year-by-year returns, worst month, fee/tax/slippage breakdown, benchmark excess return. Show `N/A` if mathematically undefined/too few observations.
- Backtest artifacts: input configuration JSON, data versions/provider, Git commit hash, random seed (if any), order ledger CSV, daily equity CSV and reproducibility hash. Never overwrite previous run results.
- Require initial go/no-go validation: sufficient trades, OOS vs in-sample degradation, robustness over fees, multiple market regimes, stable sensitivity to parameter changes. Do NOT set profitable thresholds as a code condition that discards inconvenient findings.

## 9. API endpoints (NestJS under /api/v1)

**Authentication:** single-admin JWT/secure cookie session; rate limiting, input validation, CSRF mitigation for cookie auth, audit of mutating actions; no broker secret exposure.

- `GET /health/live`, `GET /health/ready`, `GET /system/status`
- `GET /market/calendar?from=&to=`, `GET /market/regime?date=`, `GET /market/breadth?date=`, `GET /market/indexes/:code/bars?from=&to=`
- `GET /instruments?exchange=&query=&status=`, `GET /instruments/:symbol/overview`, `GET /instruments/:symbol/bars?from=&to=&adjustment=raw|adjusted`, `GET /instruments/:symbol/features?date=`
- `POST /ingestion/runs`, `GET /ingestion/runs`, `GET /ingestion/runs/:id`, `GET /data-quality/issues`
- `POST /scans`, `GET /scans`, `GET /scans/:id`, `GET /scans/:id/results?strategy=&minScore=&exchange=&sort=&page=&limit=`, `GET /signals/:id/explanation`
- `GET /strategies`, `PATCH /strategies/:id/config` (version on every change)
- `POST /backtests`, `GET /backtests`, `GET /backtests/:id`, `GET /backtests/:id/equity`, `GET /backtests/:id/trades`, `GET /backtests/:id/export`
- `GET/POST /watchlists`, `POST/DELETE /watchlists/:id/items`, `GET/POST /alerts`, `GET /alerts/history`
- `GET /paper/accounts/:id`, `POST /paper/orders/preview`, `POST /paper/orders` (manual fake order only), `POST /paper/simulate-session`, `GET /paper/accounts/:id/positions`, `GET /paper/accounts/:id/ledger`, `GET /paper/accounts/:id/performance`
- `GET /jobs/:id` for progress/cancellation where safe, `GET /audit`.

Responses include `{data, meta:{asOf, source, runId, freshness, isDemo}, error:{code,message,details,requestId}}`. Paginate large scans, enforce historical range limits, timezone conventions, OpenAPI docs; no unbounded history loads.

## 10. Dashboard screens and UX (Vietnamese)

### Mandatory UI framework: PrimeVue

- Stack must be **Vue 3 + TypeScript + Vite + PrimeVue + PrimeIcons + Vue Router + Pinia**. Prefer PrimeVue `styled` mode with **Aura preset** (custom semantic/design tokens). Verify and pin currently compatible PrimeVue and `@primeuix/themes` versions from https://primevue.dev/installation/ and https://primevue.dev/theming/styled/ before writing setup code. Do not mix snippets from conflicting major versions.
- PrimeVue is the **only component library**. PrimeFlex or light custom CSS may be used if needed; no Tailwind/shadcn-vue/Naive UI/Element Plus/Vuetify or additional design systems. PrimeVue theming must be centralized in `apps/web/src/theme/`, with dark/light mode, semantic trading colors, consistent spacing, typography, table density and accessible contrast. Do not indiscriminately override component internals with CSS.
- Use PrimeVue **DataTable** (server paging/lazy loading/virtual scrolling where justified), Column, Paginator, Tag, Badge, Card, Toolbar, Button, Select, MultiSelect, DatePicker, InputText, InputNumber, Drawer, Dialog, ConfirmDialog, Toast, Tabs, Skeleton, ProgressBar, Message, Tooltip, Menu as applicable; check actual installed component names for chosen major version. Avoid custom reimplementation of primitives PrimeVue already supports.
- Charting is **TradingView Lightweight Charts** (candlestick, volume, indicators) and optionally a clearly documented separate charting library for equity/drawdown/heatmaps; PrimeVue is not itself a candlestick chart engine. No fake trading charts or randomly generated live prices.
- Suggested UI architecture: `src/{main.ts,router/,stores/,theme/,layouts/,components/{common,charts,scanner},views/{DashboardView,ScannerView,SymbolView,StrategyLabView,PortfolioView,OperationsView},composables/,services/api/,types/}`. Reusable app shell: sidebar, compact header, toolbar, global notifications, error boundary, skeletons, DataFreshnessBadge, RiskTag, SignalScoreCell.
- Design direction: restrained professional **financial terminal**, not a generic AI dashboard. Desktop-first tables with dense but readable columns, obvious exchange/session timestamp, empty/loading/error states, sensible responsive behavior, keyboard usability and Vietnamese VND number formatting.
- **PrimeVue-specific acceptance**: all six screens actually use PrimeVue UI components, theme switches persist within user settings, no incompatible versions or competing UI kits, pagination/filtering/sorting work with backend, and `npm run build`/typecheck pass.


### A. Overview `/dashboard`

- Header: exchange date, last successful ingest, badge `LIVE DATA / EOD FINAL / PARTIAL / DEMO / STALE` (NO simulated realtime claim).
- VNINDEX/VN30 daily performance, regime, breadth (% above EMA20/EMA50), trading-value overview, qualified universe count.
- Four strategy cards: signals today, accepted/rejected, example candidates (no fabricated returns).
- Top candidates table: symbol, venue, last close, score, strategy, risk grade, 20d median value, suggested *hypothetical* max shares, rejection reason.
- Pipeline operations: last run, missing bars, provider error, job status.

### B. Scanner `/scanner`

- Tabs strategy S1–S4, filters exchange, sectors, score, liquidity, market regime, risk, signal freshness, exclusion flags.
- Search/sort/page, watchlist toggles, detail drawer with feature reason tree and chart annotations.
- Run scan button, async progress, rerun idempotent; compare current and previous trading session signals.
- Export CSV with timestamps and `DATA_SOURCE`/`SIMULATED` labels.

### C. Symbol Explorer `/symbols/:symbol`

- Candlestick + volume + EMA20/50/200, breakout markers, signal markers (markers appear only after decision time), tooltip explanation, raw/adjusted toggle.
- Latest feature vector, liquidity, historical signals, corporate action, technical exclusions and what-data-is-missing panel.

### D. Strategy Lab `/lab`

- Parameter editor with validation and versioning; select universe/date/test windows, costs and execution assumptions; start/cancel queued backtest.
- Equity + drawdown charts, yearly heatmap, trade ledger, parameter provenance, OOS vs in-sample, benchmark, export artifacts.
- Strong warning when `DEMO`, insufficient history, missing delisted data, no actual fees, OOS leakage or small trade sample.

### E. Paper Portfolio `/portfolio`

- Capital, NAV, liquid cash, pending cash, shares owned vs sellable shares, exposures and concentrations, unrealized/realized P&L, fees/tax.
- Order preview -> user manually approves simulation; show next eligible trade session, lot validation, position size, worst-case gap caveat.
- No 'Buy on broker' UI in MVP. Immutably logged operations and reset paper account through separately confirmed action.

### F. Data/Ops `/operations`

- Provider health, stale series, missing-session heatmap, ingestion/backtest jobs, errors/retries, change log, strategy revisions.

Visual design: professional restrained dark/light theme; desktop first responsive; no decorative AI-generated charts; Vietnamese date/number formatting; VND thousand-group separators; empty/loading/error states and accessibility.

## 11. Alerts & scanner schedule

- Notifications optional Telegram bot (single admin) or in-app; Telegram credentials backend-only. Compose: symbol, strategy, score, decision_date, signal reasons, source/as-of, market regime, risk notice and direct dashboard URL.
- Trigger only when new unique `(strategy_version, instrument_id, decision_date, signal_kind)` appears. Do not resend duplicate on rerun.
- EOD scan daily after final data; no alerts on stale/failed scans; alert on pipeline failure separately once with cooldown.
- Configurable quiet hours, thresholds, per-channel opt-in; support manual `Run scan` from UI.

## 12. Security, reliability, budgets

- **No containers of any kind**. Target Ubuntu LTS or compatible native Linux. Install PostgreSQL and Redis from trusted OS/vendor repositories; enable and verify `postgresql.service`, `redis-server.service` via `systemctl`. Use a dedicated PostgreSQL role/database and bind DB/Redis to loopback unless there is a documented secure requirement.
- Node.js installed with supported Node LTS (nvm for local developer, pinned runtime path/version for PM2 production); NestJS API runs using **PM2** with `ecosystem.config.cjs`, explicit `cwd`, production environment file injection, `pm2 startup` and `pm2 save`; verify resurrection after reboot. Prefer one scheduler leader to avoid duplicate jobs.
- Python 3.12 isolated in `apps/quant-worker/.venv` (`python -m venv`, lock dependencies) and supervised by **systemd** via `infra/systemd/quant-worker.service` with `Restart=on-failure`, sensible limits, dedicated non-root user and journal logs. For finite jobs, choose worker daemon that consumes durable queue; no infinite busy loop. `systemctl enable --now quant-worker` and verify reboot recovery.
- `apps/web` built with `npm run build` and deployed as static `dist/` under Nginx. Reverse proxy `/api/` to NestJS local port; support Vue history-mode SPA fallback; add HTTPS, headers and gzip where safe. Never run Vite development server as production service.
- Provide `infra/scripts/{install-native.sh,dev-start.sh,dev-stop.sh,deploy.sh,healthcheck.sh,backup-postgres.sh,restore-postgres.sh,smoke-test.sh}`; scripts idempotent when reasonable, executable and documented. `install-native.sh` may require sudo but must not destroy existing server DB/config. `.env` + systemd EnvironmentFile permissions; no passwords in PM2 ecosystem tracked in Git. System services must be native and survive reboot.
- Native deployment runbook must show commands for `systemctl status postgresql redis-server quant-worker`, `pm2 status`, `pm2 logs`, `nginx -t`, `systemctl reload nginx`, `journalctl -u quant-worker -n 100`, DB backup/restore, service restart and log rotation. Demonstrate dependency recovery after server reboot.
- Postgres nightly backup & retention, restore test, `.env` secrets external to repo, HTTPS reverse proxy via Nginx, security headers, DB non-root users, least-privilege IAM, firewall.
- Constrain workers: CPU/memory quotas, bounded backtest concurrency default 1, provider rate cap, max backtest runtime, cancellation.
- Recommended initial VPS 4 vCPU, 8GB RAM, 80GB SSD (estimate, validate with measured data volume). Can run smaller with Parquet/cache optimizations; do not presume pricing.
- Structured logs with request IDs, job IDs, metrics: ingestion duration, bar gaps, scan latency, backtest duration, failure count, freshness lag, notification rate; alerts for dead workers/DB storage >80%.
- Separate demo/test vs real-source datasets, with clear environment markers.

## 13. Test matrix — mandatory

### Unit tests

1. Every rolling feature has known expected values; no future rows accessible to signal at t.
2. Breakout high excludes current bar; corporate-action adjustment avoids artificial +/− price jumps.
3. Missing/zero-volume and incomplete 20/60/200-bar warmup produce explicit exclusion.
4. Price bands/tick size/round-lot calculations for venue/date-specific scenarios.
5. Risk sizing respects smallest of stop budget, 20% position cap, cash and 100-share lot; outputs `NOT_AFFORDABLE` if zero shares.
6. Scanner rerun creates no duplicate signals/alerts.
7. Regime UNKNOWN if index/breadth missing, and no confidence boosting based on absence.

### Integration tests

1. Import 3+ symbols, two exchanges and index with fixture data; execute complete pipeline; verify DB provenance and scan ranks.
2. Simulate provider 429, timeout, revised bar and missing benchmark; retries/revisions correct; scan not silently published.
3. Invalidate adjusted history around cash/stock dividend and symbol lifecycle changes.
4. Backtest next-session execution and forbid same-bar EOD signal fill; unavailable shares after buying cannot sell before configured sellable time.
5. Paper position/cash ledger conserved; sell tax and each fee charged precisely once; no negative buying power.
6. Portfolio max allocation, sector cap, daily entry cap, floor/ceiling no-fill and same-day stop/target ambiguity conservative case.
7. Sample 3-year walk-forward boundary ensures train window never includes future data; parameter hash/re-run deterministic.
8. API auth, illegal payloads, pagination, upload/CSV injection (escape spreadsheet formula values).

### E2E smoke

`infra/scripts/dev-start.sh` (native dependencies preinstalled) -> migration -> seed *labeled synthetic demo dataset* -> ingest/feature/scan -> view dashboard -> inspect symbol -> run backtest -> inspect metrics -> manually preview paper order -> simulate next sessions -> verify audit and logs. Should run without any proprietary API keys in demo mode.

## 14. Acceptance criteria / definition of done

| ID | Requirement | Pass rule |
|---|---|---|
| AC01 | Reproducible installation | Clean supported Ubuntu host can install native dependencies and start demo mode via documented scripts, PM2/systemd/Nginx without containers or hidden steps |
| AC02 | Verified data | Real-data mode requires configured authorized provider; all EOD bars have source/version/as-of |
| AC03 | Coverage | Ingestion reports exact eligible universe, absent sessions, delistings and missing/adjusted series; never claims false completeness |
| AC04 | Feature correctness | Indicator golden fixtures pass; no lookahead; current-breakout bar excluded |
| AC05 | All four scanners | S1-S4 produce deterministic explanation or exclusion reasons; strategy config is versioned |
| AC06 | Risk constraints | 50m account cannot allocate >configured limits, short/margin disabled, board-lot and cash constraints enforced |
| AC07 | Backtest realism | Earliest t+1 trades, configurable T+2/sellability and cash settlement, fees/tax/slippage, halt and no-fill cases tested |
| AC08 | Research integrity | Train/test separation, benchmarks, costs and survivorship warnings visible; no fake profit metrics |
| AC09 | Dashboard | Six screens above work with loading, errors, filters, exports and authentic provenance labels |
| AC10 | Paper-only | No live broker order endpoint/key/screen; manual simulation logged immutably |
| AC11 | Reliability | Retry, idempotency, stale check, health, backups and operator runbook exist |
| AC12 | Tests | CI lint + TS/Python types + unit/integration + smoke pass, test report saved |
| AC13 | Performance | For configured universe of ~2,000 instruments and 5 years daily bars, measured EOD scan <=5 minutes on reference machine *after ingest*, UI list P95 <=1s under local single-user load; if benchmark misses, profile and document bottleneck rather than claiming pass |
| AC14 | Transparency | Every recommendation has exact input dates, explanation, risk, score and evidence source |
| AC15 | No Docker | Repository, CI, scripts and deployment contain no Dockerfile, Compose, Docker CLI or container requirement; setup and smoke pass natively |
| AC16 | PrimeVue UI | Six screens use PrimeVue components with one coherent theme; functional pagination/filtering, proper states, dark/light mode and successful production build |
| AC17 | Boot resilience | Reboot test demonstrates DB, Redis, PM2 API, Python systemd worker and Nginx recover; healthcheck passes |

**Success is correct, reproducible system behavior, NOT a fabricated minimum profitability.** Strategy promotion to `VALIDATED` requires user-defined OOS tests, robust fees and manual approval; never auto-promote on in-sample Sharpe.

## 15. Delivery milestones (recommended 6–10 engineering weeks, NOT validated profitability timing)

**M0 — discovery/setup (2–3 days):** inspect repo, verify provider docs/rules/licensing and requirements; scaffold native Linux runtime scripts, PrimeVue app shell, contracts, auth, DB migrations, demo seed. Deliver runnable overview shell and test pipeline.

**M1 — data foundation (1–2 weeks):** data adapters, incremental ingestion, canonical bars, index, actions, quality dashboard, scheduler, provider matrix. Demonstrate retry on missing/429 data.

**M2 — features, regime, scanner (1–2 weeks):** feature engine, four strategies, ranks/exclusions, `/scanner` + `/symbols/:symbol`, EOD history; Telegram alert optional.

**M3 — backtest/lab (2–3 weeks):** deterministic fills, costs, settlement, portfolio and risk, OOS/walk-forward, metrics, exports, strategy lab.

**M4 — paper portfolio + hardening (1–2 weeks):** ledger, manual hypothetical orders, session simulation, auth/audit/health/backup, E2E and profiling.

Do not begin next milestone until current tests and end-to-end vertical slice succeed. For inaccessible live data, keep integration isolated and report `BLOCKED: PROVIDER_CREDENTIALS` while the demo completes.

## 16. Concrete first Codex task

1. Read this spec and output a concise dependency checklist with provider and market-rule assumptions, then create the monorepo scaffold as specified.
2. Implement PostgreSQL migrations, typed Python `MarketDataProvider` interface, `FixtureProvider`, `MockProviderError`, plus normalized OHLC and index import.
3. Implement `GET /system/status`, `GET /market/regime`, `GET /scans`, `GET /scans/:id/results` with correctly typed empty/demo states.
4. Implement Vue 3 + PrimeVue (Aura themed) dashboard shell, PrimeVue DataTable scanner table, data-quality status and DEMO badge backed by real API responses from fixture DB (NO hardcoded statistics).
5. Write fixture-driven tests for data normalization, idempotent ingestion and status transitions.
6. Run native services with `infra/scripts/dev-start.sh` plus `infra/scripts/smoke-test.sh`, then update `docs/IMPLEMENTATION_STATUS.md` with commands, logs, architecture decisions, blockers. Continue M1-M4 when foundations pass.

## 17. Native Linux quick reference for Codex

- Developer: start existing native PostgreSQL/Redis; create Python virtualenv (`python3.12 -m venv apps/quant-worker/.venv`), install locked Python dependencies, run migrations, start NestJS with `npm run start:dev`, worker with `.venv/bin/python -m ...`, and Vite with `npm run dev`. Document actual runnable package/module names rather than leaving `...` in final README.
- Production: provision PostgreSQL/Redis and secure DB accounts; build NestJS and Vue; run NestJS via PM2 and save startup configuration; run queue consumer via systemd; serve Vue `dist/` with Nginx reverse proxy; SSL certificate lifecycle via Certbot/Nginx; restart and reboot verification. All services use their own least-privilege users where appropriate.
- Example operations (adjust package names to OS):

```bash
sudo systemctl enable --now postgresql redis-server nginx
sudo systemctl status postgresql redis-server nginx
pm2 start ecosystem.config.cjs --env production
pm2 save
# Set up PM2 systemd startup with its generated, reviewed command
sudo systemctl enable --now quant-worker
sudo nginx -t && sudo systemctl reload nginx
bash infra/scripts/healthcheck.sh
bash infra/scripts/smoke-test.sh
```

- Do not expose the DB/Redis ports publicly. Do not execute `pm2 startup` with an unreviewed privileged command. Use native integration tests with a temporary local test DB or isolated schema; do not require containers for CI.

## 18. Source references / verification checklist

- PrimeVue installation: https://primevue.dev/installation/
- PrimeVue styled theme and design tokens: https://primevue.dev/theming/styled/


- SSI FastConnect overview and authentication/data capabilities: https://developers.ssi.com.vn/docs/getting-started/overview
- SSI historical data notes: https://developers.ssi.com.vn/docs/faq/market-data
- SSI release notes (2026-10-14 corporate actions change): https://developers.ssi.com.vn/docs/api-reference/release-notes
- DNSE market data docs: https://developers.dnse.com.vn/docs/dnse/market-data/
- Vnstock license and implementation: https://github.com/thinh-vu/vnstock
- DNSE 2025 post-KRX rules reference: https://cdn.dnse.com.vn/dnse-news/2023/10/DNSE_Cap-nhat-quy-dinh-giao-dich-sau-KRX_2025.pdf
- TCSC reference cash-equity rules: https://tcsc.vn/uploads/san-pham-dich-vu/guiding-customer-to-trade-hose-hnx-upcom-may-09-2025_1.pdf

**Important unresolved verification:** confirm settlement/sellable-time interpretation, effective-dated exchange rule exceptions, provider entitlement and complete historical delisting/corporate-action coverage for intended date range. These are explicit blocking checks before declaring backtest 'high fidelity'.
