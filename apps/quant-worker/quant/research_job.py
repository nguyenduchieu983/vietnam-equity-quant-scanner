import hashlib
import subprocess
from pathlib import Path
from psycopg.types.json import Jsonb
from .db import ROOT, connect
from .history import load_dataset, digest
from .features import feature_book, FEATURE_VERSION
from .backtest import simulate, validate_config
from .metrics import walk_forward
from .risk import RULES


class Cancelled(Exception):
    pass


def run_backtest(run_id: str, job_id: str) -> dict:
    with connect() as conn:
        run = conn.execute("SELECT dataset_id,config_json,status,strategy_id FROM backtest_runs WHERE id=%s", (run_id,)).fetchone()
        if not run:
            raise ValueError("BACKTEST_NOT_FOUND")
        if run[2] == "COMPLETE":
            return {"backtestId": run_id}
        conn.execute("UPDATE backtest_runs SET status='RUNNING',started_at=now() WHERE id=%s", (run_id,))
    payload = load_dataset(str(run[0]))
    config = run[1]
    validate_config(payload, config)
    book = feature_book(payload)

    def progress(fraction: float) -> None:
        with connect() as conn:
            cancelled = conn.execute("SELECT cancel_requested FROM jobs WHERE id=%s", (job_id,)).fetchone()[0]
            if cancelled:
                raise Cancelled("CANCELLED_BY_USER")
            conn.execute("UPDATE jobs SET progress=%s WHERE id=%s", (min(99, int(fraction*100)), job_id))

    progress(0)
    train = simulate(payload, config, config["trainStart"], config["trainEnd"], book, lambda f: progress(f*.15))
    validation = simulate(payload, config, config["validationStart"], config["validationEnd"], book, lambda f: progress(.15+f*.15))
    test = simulate(payload, config, config["testStart"], config["testEnd"], book, lambda f: progress(.3+f*.4))
    folds = walk_forward(payload["calendar"][payload["calendar"].index(config["trainStart"]):],
                         config["validationEnd"], embargo=config["embargoSessions"])
    fold_results = []
    for i, fold in enumerate(folds):
        def fold_progress(f: float) -> None:
            progress(.7+.29*(i+f)/max(1, len(folds)))
        result = simulate(payload, config, fold["testStart"], fold["testEnd"], book,
                          fold_progress)
        fold_results.append({**fold, "metrics": result["metrics"]})
    sensitivity = []
    for name, slippage in (("optimistic", .0005), ("stress", .003)):
        scenario = simulate(payload, {**config, "slippage": slippage}, config["testStart"], config["testEnd"], book,
                            lambda _: progress(.99))
        sensitivity.append({"name": name, "slippage": slippage, "metrics": scenario["metrics"]})
    version = hashlib.sha256(b"".join(p.read_bytes() for p in sorted(Path(__file__).parent.glob("*.py")))).hexdigest()
    try:
        git_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, stderr=subprocess.DEVNULL).decode().strip()
        git_dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, stderr=subprocess.DEVNULL).strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        git_commit, git_dirty = "UNAVAILABLE", True
    provenance = {"datasetHash": payload["content_hash"], "config": config, "engineHash": version,
                  "featureHash": FEATURE_VERSION, "rules": RULES, "strategyId": str(run[3])}
    result_hash = digest({"provenance": provenance, "equity": test["equity"], "orders": test["orders"]})
    artifact = {**provenance, "gitCommit": git_commit, "gitDirty": git_dirty, "reproducibilityHash": result_hash,
                "trainMetrics": train["metrics"], "validationMetrics": validation["metrics"],
                "testMetrics": test["metrics"], "walkForward": fold_results, "costSensitivity": sensitivity,
                "openPositions": test["open_positions"],
                "cashEvents": test["cash_events"], "warnings": test["warnings"], "isDemo": True,
                "promotion": "RESEARCH_ONLY", "selectionPolicy": "Fixed parameters; no fitting or optimization",
                "units": "VND/share, shares, VND cash; decimal accounting rounded to 0.01 VND",
                "finalHoldout": [config["testStart"], config["testEnd"]]}
    with connect() as conn:
        # Cancellation is serialized with final publication; no partial artifacts.
        cancellation = conn.execute("SELECT cancel_requested FROM jobs WHERE id=%s FOR UPDATE", (job_id,)).fetchone()
        if cancellation[0]:
            raise Cancelled("CANCELLED_BY_USER")
        with conn.cursor() as cur:
            cur.executemany("INSERT INTO backtest_orders(run_id,sequence,payload_json) VALUES(%s,%s,%s)",
                            [(run_id, i, Jsonb(row)) for i, row in enumerate(test["orders"])])
            cur.executemany("INSERT INTO backtest_trades(run_id,sequence,payload_json) VALUES(%s,%s,%s)",
                            [(run_id, i, Jsonb(row)) for i, row in enumerate(test["trades"])])
            cur.executemany("INSERT INTO backtest_daily_equity(run_id,session_date,nav,payload_json) VALUES(%s,%s,%s,%s)",
                            [(run_id, row["session_date"], row["nav"], Jsonb(row)) for row in test["equity"]])
        conn.execute("INSERT INTO backtest_artifacts(run_id,reproducibility_hash,payload_json) VALUES(%s,%s,%s)",
                     (run_id, result_hash, Jsonb(artifact)))
        conn.execute("UPDATE backtest_runs SET status='COMPLETE',finished_at=now(),metrics_json=%s,warnings_json=%s WHERE id=%s",
                     (Jsonb(test["metrics"]), Jsonb(test["warnings"]), run_id))
        conn.execute("INSERT INTO audit_logs(actor,action,entity,entity_id,payload_json) VALUES('worker','BACKTEST_COMPLETE','backtest_runs',%s,%s)",
                     (run_id, Jsonb({"reproducibilityHash": result_hash})))
    return {"backtestId": run_id}
