"""Publish a validated paper market snapshot to the real research workspace."""
from psycopg.types.json import Jsonb
from .db import connect
from .history import quality, digest


def publish_latest() -> str:
    with connect() as conn:
        snapshot = conn.execute("SELECT payload_json,quality_json FROM paper_market_snapshots ORDER BY as_of DESC,created_at DESC LIMIT 1").fetchone()
    if not snapshot:
        raise ValueError("IMPORT_REAL_SNAPSHOT_FIRST")
    payload, provider_quality = snapshot
    if payload.get("classification") != "REAL_RESEARCH" or provider_quality["unexplainedAdjustmentChanges"]:
        raise ValueError("UNVERIFIED_REAL_SNAPSHOT")
    report = quality(payload)
    if report["invalid"] or report["missing_benchmark"] or not report["is_final"]:
        raise ValueError("REAL_SNAPSHOT_QUALITY_BLOCKED")
    report.update(researchEligible=True, source="VNDIRECT_PUBLIC_REAL", providerQuality=provider_quality)
    checksum = digest(payload)
    with connect() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(61732002)")
        existing = conn.execute("SELECT id FROM research_datasets WHERE content_hash=%s", (checksum,)).fetchone()
        if existing:
            return str(existing[0])
        provider = conn.execute("INSERT INTO data_providers(name,enabled,license_metadata) VALUES('vndirect_public',true,%s) ON CONFLICT(name) DO UPDATE SET enabled=true RETURNING id", (Jsonb({"classification":"PUBLIC_RESEARCH_PROVISIONAL"}),)).fetchone()[0]
        run = conn.execute("""INSERT INTO ingestion_runs(provider_id,kind,status,is_demo,from_date,to_date,counts_json,finished_at)
            VALUES(%s,'HISTORY',%s,false,%s,%s,%s,now()) RETURNING id""",
            (provider, report["status"], payload["calendar"][0], payload["calendar"][-1], Jsonb(report))).fetchone()[0]
        conn.execute("INSERT INTO raw_payloads(ingestion_run_id,payload_json,sha256) VALUES(%s,%s,%s)",
                     (run, Jsonb(payload), checksum))
        ids = {}
        for instrument in payload["instruments"]:
            ids[instrument["symbol"]] = conn.execute("""INSERT INTO instruments(symbol,exchange,name,is_demo,current_status)
                VALUES(%s,%s,%s,false,%s) ON CONFLICT(symbol,exchange,is_demo) DO UPDATE SET
                current_status=excluded.current_status RETURNING id""",
                (instrument["symbol"], instrument["exchange"], instrument["symbol"],
                 "DELISTED" if instrument["delisted_at"] else "ACTIVE")).fetchone()[0]
            conn.execute("""INSERT INTO instrument_history(instrument_id,effective_from,effective_to,known_at,sector_id,listing_status)
                VALUES(%s,%s,%s,%s,%s,'ACTIVE') ON CONFLICT DO NOTHING""",
                (ids[instrument["symbol"]], instrument["listed_at"], instrument["delisted_at"],
                 instrument["known_at"] + "T00:00:00+00:00", instrument["sector"]))
        # Failed validation is retained for audit but never enters canonical bars.
        if report["status"] != "FAILED":
            with conn.cursor() as cur:
                cur.executemany("""INSERT INTO market_sessions(exchange,session_date,is_trading_day,is_demo,source)
                    VALUES(%s,%s,true,false,'VNINDEX-observed-calendar') ON CONFLICT DO NOTHING""",
                    [(exchange, d) for exchange in ("HOSE", "HNX") for d in payload["calendar"]])
                cur.executemany("""INSERT INTO market_bars(instrument_id,session_date,open,high,low,close,volume,traded_value,
                    provider_id,revision,is_final,observed_at,ingestion_run_id,is_demo,floor_price,ceiling_price)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,false,%s,%s) ON CONFLICT DO NOTHING""",
                    [(ids[b["symbol"]], b["session_date"], b["open"], b["high"], b["low"], b["close"], b["volume"],
                      b["traded_value"], provider, b["revision"], b["is_final"], b["observed_at"], run, b["floor"],
                      b["ceiling"]) for b in payload["bars"] if b["kind"] == "stock"])
                cur.executemany("""INSERT INTO index_bars(index_code,session_date,open,high,low,close,provider_id,revision,
                    is_final,observed_at,ingestion_run_id,is_demo) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,false)
                    ON CONFLICT DO NOTHING""",
                    [(b["symbol"], b["session_date"], b["open"], b["high"], b["low"], b["close"], provider,
                      b["revision"], b["is_final"], b["observed_at"], run) for b in payload["bars"] if b["kind"] == "index"])
        if report["status"] != "COMPLETE":
            conn.execute("""INSERT INTO data_quality_issues(ingestion_run_id,severity,rule,details_json,is_demo)
                VALUES(%s,'ERROR','HISTORY_QUALITY',%s,false)""", (run, Jsonb(report)))
        result = conn.execute("""INSERT INTO research_datasets(content_hash,name,provider,is_demo,status,from_date,to_date,
            quality_json,payload_json,ingestion_run_id) VALUES(%s,%s,'vndirect_public',false,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (checksum, "VNDIRECT public EOD " + payload["calendar"][-1], report["status"], payload["calendar"][0], payload["calendar"][-1],
             Jsonb(report), Jsonb(payload), run)).fetchone()
        return str(result[0])


if __name__ == "__main__":
    import os
    from .scanner import run_scan
    dataset_id = publish_latest()
    os.environ["DATA_MODE"] = "real"
    print({"datasetId": dataset_id, "scanId": run_scan(dataset_id)})
