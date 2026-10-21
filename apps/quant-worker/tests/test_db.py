import os
import unittest
from unittest.mock import patch
from quant.db import ROOT, connect
from quant.ingest import ingest
from quant.provider import FixtureProvider


@unittest.skipUnless(os.getenv("QUANT_INTEGRATION") == "1", "requires migrated native PostgreSQL test database")
class DatabaseTests(unittest.TestCase):
    @patch.dict(os.environ, {"DATA_MODE": "demo"})
    def test_ingest_idempotent_with_provenance(self):
        provider = FixtureProvider(ROOT / "tests/fixtures/eod-demo.json")
        ingest(provider)
        with connect() as conn:
            before = conn.execute("SELECT count(*) FROM market_bars").fetchone()[0]
        run_id = ingest(provider)
        with connect() as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM market_bars").fetchone()[0], before)
            status, counts = conn.execute("SELECT status,counts_json FROM ingestion_runs WHERE id=%s", (run_id,)).fetchone()
            self.assertEqual(status, "COMPLETE")
            self.assertEqual(counts["inserted"], 0)
            self.assertEqual(counts["expected"], 3)
            self.assertEqual(conn.execute("SELECT count(*) FROM raw_payloads WHERE ingestion_run_id=%s", (run_id,)).fetchone()[0], 1)
