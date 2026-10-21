from datetime import datetime, timezone
import hashlib
from pathlib import Path
from psycopg.types.json import Jsonb
from .db import connect
from .history import load_dataset, digest
from .features import FEATURE_VERSION, feature_book
from .strategies import evaluate


def definitions() -> list[dict]:
    with connect() as conn:
        return [{"id": str(r[0]), "code": r[1], "version": r[2], "config": r[3]} for r in conn.execute(
            "SELECT DISTINCT ON(code) id,code,version,config_json FROM strategy_definitions ORDER BY code,version DESC")]


def run_scan(dataset_id: str, session: str | None = None) -> str:
    payload = load_dataset(dataset_id)
    session = session or payload["calendar"][-1]
    if session not in payload["calendar"]:
        raise ValueError("NOT_A_DATASET_SESSION")
    is_demo = payload.get("classification") == "DEMO"
    strategies = definitions()
    engine_hash = hashlib.sha256(Path(__file__).with_name("strategies.py").read_bytes()).hexdigest()
    key = digest({"dataset": payload["content_hash"], "feature": FEATURE_VERSION, "date": session,
                  "strategies": strategies, "engine": engine_hash})
    book = feature_book(payload)
    with connect() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(61732003)")
        old = conn.execute("SELECT id FROM scan_runs WHERE request_hash=%s", (key,)).fetchone()
        if old:
            return str(old[0])
        run_id = conn.execute("""INSERT INTO scan_runs(session_date,universe_version,feature_version,strategy_versions_json,
            status,freshness_json,finished_at,is_demo,dataset_id,request_hash) VALUES(%s,%s,%s,%s,'COMPLETE',%s,now(),%s,%s,%s)
            RETURNING id""", (session, payload["content_hash"], FEATURE_VERSION, Jsonb(strategies),
                              Jsonb({"source": "fixture" if is_demo else "VNDIRECT_PUBLIC_REAL", "asOf": session, "label": "DEMO" if is_demo else "PROVISIONAL_REAL", "warnings": payload["warnings"]}),
                              is_demo, dataset_id, key)).fetchone()[0]
        for strategy in strategies:
            state, rows = evaluate(payload, book, session, strategy["code"], strategy["config"])
            for row in rows:
                instrument_id = conn.execute("SELECT id FROM instruments WHERE symbol=%s AND exchange=%s AND is_demo=%s",
                                             (row["symbol"], row["exchange"], is_demo)).fetchone()[0]
                conn.execute("""INSERT INTO feature_snapshots(instrument_id,session_date,dataset_id,features_json,version_hash,known_at)
                    VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                    (instrument_id, session, dataset_id, Jsonb(row["features_used"]), FEATURE_VERSION,
                     session+"T09:30:00+00:00"))
                conn.execute("""INSERT INTO rankings(scan_run_id,instrument_id,strategy_code,composite_score,rank,excluded,
                    exclusion_codes_json,sub_scores_json) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (run_id, instrument_id, strategy["code"], row["score"], row.get("rank"), row["side"] != "LONG",
                     Jsonb(row["reasons"]), Jsonb(row)))
                conn.execute("""INSERT INTO signals(scan_run_id,instrument_id,strategy_id,side,decision_at,earliest_execution_session,
                    strength,entry_reference,invalidation_reference,explanation_json,status)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'RESEARCH')""",
                    (run_id, instrument_id, strategy["id"], row["side"], session+"T09:30:00+00:00",
                     row["earliest_trade_date"], row["score"], row["features_used"].get("raw_close"),
                     row["invalidation_price"], Jsonb(row)))
            conn.execute("INSERT INTO market_regimes(scan_run_id,regime,conditions_json) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING",
                         (run_id, state["regime"], Jsonb(state)))
        conn.execute("INSERT INTO audit_logs(actor,action,entity,entity_id,payload_json) VALUES('worker','SCAN','scan_runs',%s,%s)",
                     (run_id, Jsonb({"at": datetime.now(timezone.utc).isoformat(), "request_hash": key})))
        return str(run_id)
