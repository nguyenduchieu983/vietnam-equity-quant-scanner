import argparse
import json
import os
import signal
import threading
from dotenv import load_dotenv
from .db import ROOT, connect, migrate
from .ingest import ingest
from .provider import FixtureProvider
from .history import import_history
from .scanner import run_scan
from .research_job import run_backtest, Cancelled

stop = threading.Event()


def maintain_lease(job_id, done: threading.Event) -> None:
    while not done.wait(5):
        try:
            with connect() as conn:
                conn.execute("UPDATE worker_heartbeats SET observed_at=now() WHERE id='quant-worker'")
                conn.execute("UPDATE jobs SET lease_until=now()+interval '2 minutes' WHERE id=%s AND status='RUNNING'", (job_id,))
        except Exception:
            pass  # Main execution still fails closed on publication if the DB is unavailable.


def consume() -> None:
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    while not stop.is_set():
        try:
            with connect() as conn:
                conn.execute("SELECT pg_advisory_xact_lock(61732005)")
                conn.execute("""INSERT INTO worker_heartbeats(id,observed_at) VALUES('quant-worker',now())
                    ON CONFLICT(id) DO UPDATE SET observed_at=now()""")
                conn.execute("""UPDATE jobs SET status=CASE WHEN attempts >= %s THEN 'FAILED' ELSE 'QUEUED' END,
                    error_code='LEASE_EXPIRED' WHERE status='RUNNING' AND lease_until<now()""",
                    (int(os.getenv("WORKER_MAX_ATTEMPTS", "3")),))
                conn.execute("""UPDATE backtest_runs b SET status='FAILED',error_code='LEASE_EXPIRED',finished_at=now()
                    FROM jobs j WHERE b.job_id=j.id AND j.status='FAILED' AND b.status IN ('QUEUED','RUNNING')""")
                job = conn.execute("""UPDATE jobs SET status='RUNNING',attempts=attempts+1,
                    lease_until=now()+interval '2 minutes' WHERE id=(
                    SELECT id FROM jobs WHERE status='QUEUED' AND NOT cancel_requested AND (is_demo=%s OR kind='PAPER')
                    AND (kind<>'BACKTEST' OR NOT EXISTS(SELECT 1 FROM jobs active WHERE active.kind='BACKTEST' AND active.status='RUNNING'))
                    ORDER BY created_at
                    FOR UPDATE SKIP LOCKED LIMIT 1) RETURNING id,kind,payload_json""",
                    (os.getenv("DATA_MODE") == "demo",)).fetchone()
            if job:
                lease_done = threading.Event()
                heartbeat = threading.Thread(target=maintain_lease, args=(job[0], lease_done), daemon=True)
                heartbeat.start()
                try:
                    if job[1] == "HISTORY":
                        result = {"datasetId": import_history()}
                    elif job[1] == "SCAN":
                        result = {"scanId": run_scan(job[2]["datasetId"], job[2].get("session"))}
                    elif job[1] == "BACKTEST":
                        result = run_backtest(job[2]["backtestId"], str(job[0]))
                    elif job[1] == "PAPER":
                        from .paper import run
                        result = run(str(job[0]), job[2])
                    else:
                        result = {"runId": ingest(FixtureProvider(ROOT / "tests/fixtures/eod-demo.json"))}
                    with connect() as conn:
                        conn.execute("UPDATE jobs SET status='COMPLETE',progress=100,result_json=%s,finished_at=now(),lease_until=NULL WHERE id=%s",
                                     (json.dumps(result), job[0]))
                    print(json.dumps({"jobId": str(job[0]), "status": "COMPLETE"}), flush=True)
                except Exception as exc:
                    status = "CANCELLED" if isinstance(exc, Cancelled) else "FAILED"
                    error = str(exc)[:120] if isinstance(exc, (ValueError, Cancelled, TimeoutError)) else type(exc).__name__
                    with connect() as conn:
                        conn.execute("UPDATE jobs SET status=%s,finished_at=now(),error_code=%s WHERE id=%s",
                                     (status, error, job[0]))
                        if job[1] == "BACKTEST":
                            conn.execute("UPDATE backtest_runs SET status=%s,finished_at=now(),error_code=%s WHERE id=%s AND status<>'COMPLETE'",
                                         (status, error, job[2]["backtestId"]))
                    print(json.dumps({"jobId": str(job[0]), "status": "FAILED", "error": type(exc).__name__}), flush=True)
                finally:
                    lease_done.set()
                    heartbeat.join(timeout=6)
        except Exception as exc:
            print(json.dumps({"event": "worker_dependency_error", "error": type(exc).__name__}), flush=True)
        stop.wait(float(os.getenv("WORKER_POLL_SECONDS", "2")))


def main() -> None:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["migrate", "seed-demo", "seed-history", "worker"])
    args = parser.parse_args()
    if args.command == "migrate":
        migrate()
    elif args.command == "seed-demo":
        print(ingest(FixtureProvider(ROOT / "tests/fixtures/eod-demo.json")))
    elif args.command == "seed-history":
        print(import_history())
    else:
        consume()


if __name__ == "__main__":
    main()
