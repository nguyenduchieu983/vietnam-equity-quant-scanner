import argparse
import json
import os
import signal
import threading
from dotenv import load_dotenv
from .db import ROOT, connect, migrate
from .ingest import ingest
from .provider import FixtureProvider

stop = threading.Event()


def consume() -> None:
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    while not stop.is_set():
        try:
            with connect() as conn:
                conn.execute("""INSERT INTO worker_heartbeats(id,observed_at) VALUES('quant-worker',now())
                    ON CONFLICT(id) DO UPDATE SET observed_at=now()""")
                conn.execute("""UPDATE jobs SET status=CASE WHEN attempts >= %s THEN 'FAILED' ELSE 'QUEUED' END,
                    error_code='LEASE_EXPIRED' WHERE status='RUNNING' AND lease_until<now()""",
                    (int(os.getenv("WORKER_MAX_ATTEMPTS", "3")),))
                job = conn.execute("""UPDATE jobs SET status='RUNNING',attempts=attempts+1,
                    lease_until=now()+interval '2 minutes' WHERE id=(
                    SELECT id FROM jobs WHERE status='QUEUED' AND is_demo=%s ORDER BY created_at
                    FOR UPDATE SKIP LOCKED LIMIT 1) RETURNING id,kind""",
                    (os.getenv("DATA_MODE") == "demo",)).fetchone()
            if job:
                try:
                    ingest(FixtureProvider(ROOT / "tests/fixtures/eod-demo.json"))
                    with connect() as conn:
                        conn.execute("UPDATE jobs SET status='COMPLETE',finished_at=now(),lease_until=NULL WHERE id=%s", (job[0],))
                    print(json.dumps({"jobId": str(job[0]), "status": "COMPLETE"}), flush=True)
                except Exception as exc:
                    with connect() as conn:
                        conn.execute("UPDATE jobs SET status='FAILED',finished_at=now(),error_code=%s WHERE id=%s",
                                     (type(exc).__name__, job[0]))
                    print(json.dumps({"jobId": str(job[0]), "status": "FAILED", "error": type(exc).__name__}), flush=True)
        except Exception as exc:
            print(json.dumps({"event": "worker_dependency_error", "error": type(exc).__name__}), flush=True)
        stop.wait(float(os.getenv("WORKER_POLL_SECONDS", "2")))


def main() -> None:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["migrate", "seed-demo", "worker"])
    args = parser.parse_args()
    if args.command == "migrate":
        migrate()
    elif args.command == "seed-demo":
        print(ingest(FixtureProvider(ROOT / "tests/fixtures/eod-demo.json")))
    else:
        consume()


if __name__ == "__main__":
    main()
