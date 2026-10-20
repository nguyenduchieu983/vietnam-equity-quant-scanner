ALTER TABLE jobs DROP CONSTRAINT jobs_kind_check;
ALTER TABLE jobs ADD CONSTRAINT jobs_kind_check CHECK(kind IN ('INGEST','HISTORY','SCAN','BACKTEST'));
ALTER TABLE jobs DROP CONSTRAINT jobs_status_check;
ALTER TABLE jobs ADD CONSTRAINT jobs_status_check CHECK(status IN ('QUEUED','RUNNING','COMPLETE','FAILED','CANCELLED'));
CREATE TABLE backtest_runs (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), job_id uuid UNIQUE REFERENCES jobs,
 dataset_id uuid NOT NULL REFERENCES research_datasets, strategy_id uuid NOT NULL REFERENCES strategy_definitions,
 parameter_hash text NOT NULL, data_cutoff date NOT NULL, train_start date NOT NULL, train_end date NOT NULL,
 test_start date NOT NULL, test_end date NOT NULL, config_json jsonb NOT NULL, fees_json jsonb NOT NULL,
 assumptions_json jsonb NOT NULL, status text NOT NULL CHECK(status IN ('QUEUED','RUNNING','COMPLETE','FAILED','CANCELLED')),
 metrics_json jsonb, warnings_json jsonb NOT NULL DEFAULT '[]', error_code text, is_demo boolean NOT NULL,
 started_at timestamptz, finished_at timestamptz, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX backtest_recent ON backtest_runs(created_at DESC);
CREATE TABLE backtest_orders (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), run_id uuid NOT NULL REFERENCES backtest_runs,
 sequence integer NOT NULL, payload_json jsonb NOT NULL, UNIQUE(run_id,sequence)
);
CREATE TABLE backtest_trades (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), run_id uuid NOT NULL REFERENCES backtest_runs,
 sequence integer NOT NULL, payload_json jsonb NOT NULL, UNIQUE(run_id,sequence)
);
CREATE TABLE backtest_daily_equity (
 run_id uuid NOT NULL REFERENCES backtest_runs, session_date date NOT NULL,
 nav numeric(24,2) NOT NULL CHECK(nav>=0), payload_json jsonb NOT NULL,
 PRIMARY KEY(run_id,session_date)
);
CREATE TABLE backtest_artifacts (
 run_id uuid PRIMARY KEY REFERENCES backtest_runs, reproducibility_hash text NOT NULL,
 payload_json jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TRIGGER bt_artifacts_immutable BEFORE UPDATE OR DELETE ON backtest_artifacts
FOR EACH ROW EXECUTE FUNCTION reject_audit_mutation();
CREATE TRIGGER bt_orders_immutable BEFORE UPDATE OR DELETE ON backtest_orders
FOR EACH ROW EXECUTE FUNCTION reject_audit_mutation();
CREATE TRIGGER bt_trades_immutable BEFORE UPDATE OR DELETE ON backtest_trades
FOR EACH ROW EXECUTE FUNCTION reject_audit_mutation();
CREATE TRIGGER bt_equity_immutable BEFORE UPDATE OR DELETE ON backtest_daily_equity
FOR EACH ROW EXECUTE FUNCTION reject_audit_mutation();
