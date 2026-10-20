import hashlib
import json
import os
from uuid import uuid4
from psycopg.types.json import Jsonb
from .db import connect
from .provider import MarketDataProvider, classify, normalize


def ingest(provider: MarketDataProvider) -> str:
    if os.getenv("DATA_MODE") != "demo" or not provider.is_demo:
        raise RuntimeError("DATA_UNAVAILABLE:PROVIDER_CREDENTIALS")
    payload = provider.fetch()
    run_id = str(uuid4())
    with connect() as conn:
        provider_row = conn.execute("SELECT id FROM data_providers WHERE name=%s AND enabled", (provider.name,)).fetchone()
        if provider_row is None:
            raise RuntimeError("PROVIDER_DISABLED")
        provider_id = provider_row[0]
        conn.execute("""INSERT INTO ingestion_runs(id,provider_id,kind,status,is_demo)
                        VALUES(%s,%s,'EOD','RUNNING',true)""", (run_id, provider_id))
    try:
        bars = [normalize(row) for row in payload["bars"]]
        expected = set(payload["expected_symbols"])
        status, reasons = classify(bars, expected)
        if len({b.session_date for b in bars}) != 1:
            raise ValueError("FIXTURE_REQUIRES_SINGLE_SESSION")
        with connect() as conn:
            raw = json.dumps(payload, sort_keys=True)
            conn.execute("INSERT INTO raw_payloads(ingestion_run_id,payload_json,sha256) VALUES(%s,%s,%s)",
                         (run_id, Jsonb(payload), hashlib.sha256(raw.encode()).hexdigest()))
            inserted = 0
            for bar in bars:
                if bar.kind == "index":
                    result = conn.execute("""INSERT INTO index_bars(index_code,session_date,open,high,low,close,
                        provider_id,revision,is_final,observed_at,ingestion_run_id,is_demo)
                        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,true) ON CONFLICT DO NOTHING""",
                        (bar.symbol, bar.session_date, bar.open, bar.high, bar.low, bar.close, provider_id,
                         bar.revision, bar.is_final, bar.observed_at, run_id))
                else:
                    instrument = conn.execute("""INSERT INTO instruments(symbol,exchange,name,is_demo)
                        VALUES(%s,%s,%s,true) ON CONFLICT(symbol,exchange,is_demo)
                        DO UPDATE SET name=excluded.name RETURNING id""",
                        (bar.symbol, bar.exchange, f"DEMO synthetic {bar.symbol}")).fetchone()
                    assert instrument is not None
                    instrument_id = instrument[0]
                    conn.execute("""INSERT INTO instrument_history(instrument_id,effective_from,known_at,listing_status)
                        VALUES(%s,%s,%s,'ACTIVE') ON CONFLICT DO NOTHING""",
                        (instrument_id, bar.session_date, bar.observed_at))
                    conn.execute("""INSERT INTO market_sessions(exchange,session_date,is_trading_day,is_demo,source)
                        VALUES(%s,%s,true,true,'fixture') ON CONFLICT DO NOTHING""", (bar.exchange, bar.session_date))
                    result = conn.execute("""INSERT INTO market_bars(instrument_id,session_date,open,high,low,close,
                        volume,traded_value,provider_id,revision,is_final,observed_at,ingestion_run_id,is_demo)
                        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,true) ON CONFLICT DO NOTHING""",
                        (instrument_id, bar.session_date, bar.open, bar.high, bar.low, bar.close, bar.volume,
                         bar.traded_value, provider_id, bar.revision, bar.is_final, bar.observed_at, run_id))
                inserted += result.rowcount
            for reason in reasons:
                conn.execute("""INSERT INTO data_quality_issues(ingestion_run_id,severity,rule,details_json,is_demo)
                    VALUES(%s,'ERROR',%s,%s,true)""",
                    (run_id, reason, Jsonb({"missing": sorted(expected - {b.symbol for b in bars if b.kind == "stock"})})))
            conn.execute("""UPDATE ingestion_runs SET status=%s,from_date=%s,to_date=%s,counts_json=%s,
                finished_at=now() WHERE id=%s""",
                (status, bars[0].session_date, bars[0].session_date,
                 Jsonb({"received": len(bars), "inserted": inserted, "expected": len(expected),
                        "symbols": len({b.symbol for b in bars if b.kind == "stock"}), "reasons": reasons,
                        "coverage": "DEMO_SINGLE_SESSION_ONLY", "adjustments": "UNAVAILABLE"}), run_id))
    except Exception as exc:
        with connect() as conn:
            conn.execute("UPDATE ingestion_runs SET status='FAILED',finished_at=now(),error_summary=%s WHERE id=%s",
                         (type(exc).__name__, run_id))
        raise
    return run_id
