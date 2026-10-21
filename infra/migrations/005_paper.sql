ALTER TABLE jobs DROP CONSTRAINT jobs_kind_check;
ALTER TABLE jobs ADD CONSTRAINT jobs_kind_check CHECK(kind IN ('INGEST','HISTORY','SCAN','BACKTEST','PAPER'));
CREATE TABLE paper_market_snapshots (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), content_hash text NOT NULL UNIQUE,
 as_of date NOT NULL, payload_json jsonb NOT NULL, quality_json jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE paper_pairs (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), name text NOT NULL,
 mode text NOT NULL CHECK(mode IN ('FORWARD','REPLAY')), initial_day date NOT NULL,
 cursor_day date NOT NULL, engine_hash text NOT NULL, calendar_json jsonb NOT NULL,
 snapshot_id uuid NOT NULL REFERENCES paper_market_snapshots,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE paper_accounts (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), pair_id uuid NOT NULL REFERENCES paper_pairs,
 code text NOT NULL CHECK(code IN ('S1','S1_PARTIAL')), config_json jsonb NOT NULL,
 state_json jsonb NOT NULL, decision_json jsonb NOT NULL, summary_json jsonb NOT NULL DEFAULT '{}',
 UNIQUE(pair_id,code)
);
CREATE TABLE paper_sessions (
 account_id uuid NOT NULL REFERENCES paper_accounts, session_date date NOT NULL,
 snapshot_id uuid NOT NULL REFERENCES paper_market_snapshots,
 payload_json jsonb NOT NULL, result_hash text NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY(account_id,session_date)
);
CREATE TABLE paper_approvals (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), pair_id uuid NOT NULL REFERENCES paper_pairs,
 snapshot_id uuid NOT NULL REFERENCES paper_market_snapshots, through_date date NOT NULL,
 expected_cursor date NOT NULL, job_id uuid NOT NULL UNIQUE REFERENCES jobs,
 created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(pair_id,snapshot_id,through_date,expected_cursor)
);
CREATE TRIGGER paper_session_immutable BEFORE UPDATE OR DELETE ON paper_sessions
 FOR EACH ROW EXECUTE FUNCTION reject_audit_mutation();
CREATE TRIGGER paper_approval_immutable BEFORE UPDATE OR DELETE ON paper_approvals
 FOR EACH ROW EXECUTE FUNCTION reject_audit_mutation();
CREATE TRIGGER paper_snapshot_immutable BEFORE UPDATE OR DELETE ON paper_market_snapshots
 FOR EACH ROW EXECUTE FUNCTION reject_audit_mutation();
