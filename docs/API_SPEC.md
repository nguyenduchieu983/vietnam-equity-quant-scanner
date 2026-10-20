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
