ALTER TABLE jobs DROP CONSTRAINT jobs_kind_check;
ALTER TABLE jobs ADD CONSTRAINT jobs_kind_check CHECK(kind IN ('INGEST','HISTORY','SCAN'));
CREATE TABLE strategy_definitions (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), code text NOT NULL CHECK(code IN ('S1','S2','S3','S4')),
 version integer NOT NULL CHECK(version>0), config_json jsonb NOT NULL, enabled boolean NOT NULL DEFAULT true,
 created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(code,version)
);
INSERT INTO strategy_definitions(code,version,config_json) VALUES
 ('S1',1,'{"minLiquidity":5000000000,"maxHold":30}'),
 ('S2',1,'{"minLiquidity":5000000000,"maxHold":20}'),
 ('S3',1,'{"minLiquidity":5000000000,"maxHold":20}'),
 ('S4',1,'{"minLiquidity":5000000000,"maxHold":5}');
CREATE TRIGGER strategy_immutable BEFORE UPDATE OR DELETE ON strategy_definitions
FOR EACH ROW EXECUTE FUNCTION reject_audit_mutation();
ALTER TABLE scan_runs ADD COLUMN dataset_id uuid REFERENCES research_datasets;
ALTER TABLE scan_runs ADD COLUMN request_hash text UNIQUE;
CREATE TABLE feature_snapshots (
 instrument_id uuid NOT NULL REFERENCES instruments, session_date date NOT NULL,
 dataset_id uuid NOT NULL REFERENCES research_datasets, features_json jsonb NOT NULL,
 version_hash text NOT NULL, known_at timestamptz NOT NULL,
 PRIMARY KEY(instrument_id,session_date,dataset_id,version_hash)
);
CREATE TABLE signals (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), scan_run_id uuid NOT NULL REFERENCES scan_runs,
 instrument_id uuid NOT NULL REFERENCES instruments, strategy_id uuid NOT NULL REFERENCES strategy_definitions,
 side text NOT NULL CHECK(side IN ('LONG','NONE','EXIT')), decision_at timestamptz NOT NULL,
 earliest_execution_session date, strength numeric, entry_reference numeric, invalidation_reference numeric,
 explanation_json jsonb NOT NULL, status text NOT NULL,
 UNIQUE(scan_run_id,instrument_id,strategy_id)
);
CREATE TABLE market_regimes (
 scan_run_id uuid PRIMARY KEY REFERENCES scan_runs, regime text NOT NULL,
 conditions_json jsonb NOT NULL
);
