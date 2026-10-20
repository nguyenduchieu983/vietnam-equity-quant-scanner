CREATE TABLE research_datasets (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), content_hash text NOT NULL UNIQUE,
 name text NOT NULL, provider text NOT NULL, is_demo boolean NOT NULL,
 status text NOT NULL CHECK(status IN ('COMPLETE','PARTIAL','FAILED')),
 from_date date NOT NULL, to_date date NOT NULL, quality_json jsonb NOT NULL,
 payload_json jsonb NOT NULL, ingestion_run_id uuid NOT NULL REFERENCES ingestion_runs,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TRIGGER datasets_immutable BEFORE UPDATE OR DELETE ON research_datasets
FOR EACH ROW EXECUTE FUNCTION reject_audit_mutation();
ALTER TABLE jobs DROP CONSTRAINT jobs_kind_check;
ALTER TABLE jobs ADD CONSTRAINT jobs_kind_check CHECK(kind IN ('INGEST','HISTORY'));
ALTER TABLE jobs ADD COLUMN result_json jsonb;
ALTER TABLE jobs ADD COLUMN cancel_requested boolean NOT NULL DEFAULT false;
ALTER TABLE jobs ADD COLUMN progress integer NOT NULL DEFAULT 0 CHECK(progress BETWEEN 0 AND 100);
