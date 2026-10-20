import hashlib
import os
from pathlib import Path
import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]


def connect():
    load_dotenv(ROOT / ".env")
    return psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=5)


def migrate() -> None:
    """Single migration authority. Checksums prevent editing applied SQL."""
    with connect() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(61732001)")
        conn.execute("""CREATE TABLE IF NOT EXISTS schema_migrations(
            version text PRIMARY KEY, checksum text NOT NULL, applied_at timestamptz NOT NULL DEFAULT now())""")
        for path in sorted((ROOT / "infra/migrations").glob("*.sql")):
            sql = path.read_text(encoding="utf-8")
            digest = hashlib.sha256(sql.encode()).hexdigest()
            prior = conn.execute("SELECT checksum FROM schema_migrations WHERE version=%s", (path.name,)).fetchone()
            if prior:
                if prior[0] != digest:
                    raise RuntimeError(f"MIGRATION_CHECKSUM_MISMATCH:{path.name}")
                continue
            conn.execute(sql)
            conn.execute("INSERT INTO schema_migrations(version,checksum) VALUES(%s,%s)", (path.name, digest))
