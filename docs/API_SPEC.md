# M0 API

Base `/api/v1`. Development OpenAPI at `/api/docs`. No other spec endpoints are implemented yet.

Public: GET `health/live`, GET `health/ready`, POST `auth/login` with `{"password":"..."}` (12–128 characters).

Bearer admin token required:

| Method | Path | Behavior |
|---|---|---|
| GET | system/status | DB counts, worker heartbeat, Redis ping; mode and latest fixture session |
| GET | market/regime | UNKNOWN with FEATURE_ENGINE_NOT_IMPLEMENTED |
| GET | scans | Paginated stored scan runs, empty in M0 |
| GET | scans/:id/results | Bounded rows; strategy/exchange/query/minScore/sort/direction |
| GET | instruments | Symbol/venue/name, bounded query |
| GET | ingestion/runs | Latest ingestion reports |
| POST | ingestion/runs | `provider=fixture`, `idempotencyKey`; demo only; durable job and audit |
| GET | jobs/:id | Durable progress/error code |
| GET | data-quality/issues | Bounded quality issues |

Page starts at 1, default size 25, maximum 100. Invalid UUID/query/body fields fail validation. Sort SQL identifiers are allowlisted. An idempotency key is scoped to kind and mode.

Envelope: `data`, `meta {asOf,source,runId,freshness,isDemo}`, `error`. M0 sets unknown timestamps/run IDs to null; does not label fixture as current market data. Errors include generated request ID. Health readiness returns 503 if DB, Redis or worker heartbeat unavailable. Public health never returns connection credentials.

Contract package is hand-authored in M0; generated OpenAPI client and complete response schemas remain pending.

## Research API additions (M1–M3)

All endpoints require the admin bearer token and retain the response envelope.
- GET datasets: immutable COMPLETE/partial history snapshot metadata.
- POST ingestion/runs: provider fixture_history queues synthetic history import.
- POST scans: datasetId plus optional session; GET scans/:id/results is paginated.
- GET strategies; PATCH strategies/:id/config appends minLiquidity/maxHold version.
- GET instruments/:symbol/bars requires datasetId; limit <=1500 and optional dates.
- GET instruments/:symbol/features: latest stored feature snapshot.
- POST backtests: datasetId, strategy S1..S4, six split dates, capital, maxHold,
  embargoSessions, minLiquidity, buyFee/sellFee/sellTax/slippage. Rates are fractions.
- GET backtests: latest 50; GET backtests/:id includes config/artifact/equity/trades.
- GET backtests/:id/equity, /trades, /export (JSON envelope containing CSV strings).
- POST backtests/:id/cancel; GET jobs/:id exposes progress/status/error/result.

Research export/detail caps: equity 2,000 rows, trades 5,000, orders 20,000.
Current dataset and daily position/order limits fit these bounds. Real-data
expansion must add streaming/paged exports before increasing dataset range.
No broker/order execution endpoint is provided.
