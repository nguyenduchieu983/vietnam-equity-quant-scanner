CREATE TABLE data_providers (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), name text NOT NULL UNIQUE,
 enabled boolean NOT NULL DEFAULT false, license_metadata jsonb NOT NULL DEFAULT '{}'
);
INSERT INTO data_providers(name,enabled,license_metadata)
VALUES ('fixture',true,'{"classification":"DEMO","rights":"synthetic fixtures only"}');
CREATE TABLE instruments (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), symbol text NOT NULL, exchange text NOT NULL CHECK(exchange IN ('HOSE','HNX','UPCOM')),
 type text NOT NULL DEFAULT 'COMMON_STOCK', name text NOT NULL, current_status text NOT NULL DEFAULT 'ACTIVE',
 is_demo boolean NOT NULL, UNIQUE(symbol,exchange,is_demo)
);
CREATE TABLE instrument_history (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), instrument_id uuid NOT NULL REFERENCES instruments,
 effective_from date NOT NULL, effective_to date, known_at timestamptz NOT NULL, sector_id text,
 listing_status text NOT NULL, CHECK(effective_to IS NULL OR effective_to>=effective_from),
 UNIQUE(instrument_id,effective_from,known_at)
);
CREATE TABLE market_sessions (
 exchange text NOT NULL, session_date date NOT NULL, is_trading_day boolean NOT NULL,
 is_demo boolean NOT NULL, source text NOT NULL, PRIMARY KEY(exchange,session_date,is_demo)
);
CREATE TABLE ingestion_runs (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), provider_id uuid NOT NULL REFERENCES data_providers,
 kind text NOT NULL, from_date date, to_date date,
 status text NOT NULL CHECK(status IN ('RUNNING','COMPLETE','PARTIAL','FAILED','STALE')),
 counts_json jsonb NOT NULL DEFAULT '{}', started_at timestamptz NOT NULL DEFAULT now(),
 finished_at timestamptz, error_summary text, is_demo boolean NOT NULL
);
CREATE TABLE raw_payloads (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), ingestion_run_id uuid NOT NULL REFERENCES ingestion_runs,
 payload_json jsonb NOT NULL, sha256 text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(ingestion_run_id,sha256)
);
CREATE TABLE market_bars (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), instrument_id uuid NOT NULL REFERENCES instruments,
 session_date date NOT NULL, open numeric(20,4) NOT NULL, high numeric(20,4) NOT NULL,
 low numeric(20,4) NOT NULL, close numeric(20,4) NOT NULL, volume bigint NOT NULL CHECK(volume>=0),
 traded_value numeric(26,4) NOT NULL CHECK(traded_value>=0), reference_price numeric(20,4),
 floor_price numeric(20,4), ceiling_price numeric(20,4), provider_id uuid NOT NULL REFERENCES data_providers,
 revision text NOT NULL, is_final boolean NOT NULL, observed_at timestamptz NOT NULL,
 ingested_at timestamptz NOT NULL DEFAULT now(), ingestion_run_id uuid NOT NULL REFERENCES ingestion_runs,
 is_demo boolean NOT NULL,
 CHECK(low>0 AND high>=greatest(open,close) AND low<=least(open,close) AND high>=low),
 UNIQUE(instrument_id,session_date,provider_id,revision)
);
CREATE INDEX market_bars_date ON market_bars(session_date,instrument_id);
CREATE TABLE index_bars (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), index_code text NOT NULL, session_date date NOT NULL,
 open numeric(20,4) NOT NULL, high numeric(20,4) NOT NULL, low numeric(20,4) NOT NULL, close numeric(20,4) NOT NULL,
 provider_id uuid NOT NULL REFERENCES data_providers, revision text NOT NULL, is_final boolean NOT NULL,
 observed_at timestamptz NOT NULL, ingestion_run_id uuid NOT NULL REFERENCES ingestion_runs,
 is_demo boolean NOT NULL, CHECK(low>0 AND high>=greatest(open,close) AND low<=least(open,close)),
 UNIQUE(index_code,session_date,provider_id,revision,is_demo)
);
CREATE TABLE corporate_actions (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), instrument_id uuid NOT NULL REFERENCES instruments,
 action_type text NOT NULL, announced_at timestamptz NOT NULL, ex_date date NOT NULL, record_date date,
 payable_date date, ratio numeric(20,10), cash_amount numeric(24,4), known_at timestamptz NOT NULL,
 source text NOT NULL, revision text NOT NULL, UNIQUE(instrument_id,action_type,ex_date,source,revision)
);
CREATE TABLE adjustment_factors (
 instrument_id uuid NOT NULL REFERENCES instruments, session_date date NOT NULL, factor numeric(24,12) NOT NULL CHECK(factor>0),
 methodology text NOT NULL, asof_version text NOT NULL, known_at timestamptz NOT NULL,
 PRIMARY KEY(instrument_id,session_date,asof_version)
);
CREATE TABLE data_quality_issues (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), instrument_id uuid REFERENCES instruments,
 ingestion_run_id uuid REFERENCES ingestion_runs, session_date date, severity text NOT NULL,
 rule text NOT NULL, details_json jsonb NOT NULL DEFAULT '{}', resolved_at timestamptz,
 created_at timestamptz NOT NULL DEFAULT now(), is_demo boolean NOT NULL
);
CREATE TABLE scan_runs (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), session_date date NOT NULL, universe_version text NOT NULL,
 feature_version text NOT NULL, strategy_versions_json jsonb NOT NULL,
 status text NOT NULL CHECK(status IN ('COMPLETE','PARTIAL','STALE','FAILED')),
 freshness_json jsonb NOT NULL, started_at timestamptz NOT NULL DEFAULT now(), finished_at timestamptz,
 is_demo boolean NOT NULL
);
CREATE TABLE rankings (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), scan_run_id uuid NOT NULL REFERENCES scan_runs,
 instrument_id uuid NOT NULL REFERENCES instruments, strategy_code text NOT NULL,
 composite_score numeric(7,4) CHECK(composite_score BETWEEN 0 AND 100), rank integer,
 excluded boolean NOT NULL, exclusion_codes_json jsonb NOT NULL, sub_scores_json jsonb NOT NULL,
 UNIQUE(scan_run_id,instrument_id,strategy_code)
);
CREATE TABLE jobs (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), kind text NOT NULL CHECK(kind IN ('INGEST')),
 idempotency_key text NOT NULL, payload_json jsonb NOT NULL, is_demo boolean NOT NULL,
 status text NOT NULL DEFAULT 'QUEUED' CHECK(status IN ('QUEUED','RUNNING','COMPLETE','FAILED')),
 attempts integer NOT NULL DEFAULT 0, error_code text, lease_until timestamptz,
 created_at timestamptz NOT NULL DEFAULT now(), finished_at timestamptz,
 UNIQUE(kind,idempotency_key,is_demo)
);
CREATE INDEX jobs_queue ON jobs(status,created_at);
CREATE TABLE worker_heartbeats (id text PRIMARY KEY, observed_at timestamptz NOT NULL);
CREATE TABLE audit_logs (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), actor text NOT NULL, action text NOT NULL,
 entity text NOT NULL, entity_id uuid, payload_json jsonb NOT NULL DEFAULT '{}',
 occurred_at timestamptz NOT NULL DEFAULT now()
);
CREATE FUNCTION reject_audit_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Audit records are append-only'; END $$;
CREATE TRIGGER audit_immutable BEFORE UPDATE OR DELETE ON audit_logs
FOR EACH ROW EXECUTE FUNCTION reject_audit_mutation();
