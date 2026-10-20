"""Immutable, reproducible DEMO history; no proprietary data or invented market claims."""
from datetime import date, timedelta
from decimal import Decimal
import hashlib
import json
import math
import os
import random
import time
from typing import Any, Callable
from psycopg.types.json import Jsonb
from .db import connect
from .provider import MockProviderError, normalize

HISTORY_VERSION = "synthetic-history-v2"


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def fetch_retry(fetch: Callable, sleep: Callable = time.sleep, attempts: int = 4,
                jitter: Callable = random.random) -> Any:
    for attempt in range(attempts):
        try:
            return fetch()
        except (MockProviderError, TimeoutError) as exc:
            if isinstance(exc, MockProviderError) and exc.code not in ("429", "503", "TIMEOUT"):
                raise
            if attempt + 1 == attempts:
                raise
            retry_after = exc.retry_after if isinstance(exc, MockProviderError) else None
            sleep(min(60, retry_after if retry_after is not None else 2 ** attempt + jitter()))
    raise RuntimeError("RETRY_EXHAUSTED")


def demo_history() -> dict:
    """Fixed formula is test input, never a fitted price path or simulated performance."""
    sessions = []
    day = date(2022, 1, 3)
    while day <= date(2026, 10, 19):
        if day.weekday() < 5:
            sessions.append(day.isoformat())
        day += timedelta(days=1)
    instruments: list[dict[str, Any]] = [
        {"symbol": f"SIM{n:02}", "exchange": "HOSE" if n < 5 else "HNX",
         "sector": f"DEMO-SECTOR-{n % 4}", "listed_at": sessions[0 if n != 7 else 250],
         "delisted_at": sessions[850] if n == 6 else None,
         "known_at": sessions[0], "type": "COMMON_STOCK"}
        for n in range(8)
    ]
    bars: list[dict] = []
    for n in range(9):
        is_index = n == 8
        master = instruments[n] if not is_index else None
        previous = Decimal("1000") if is_index else Decimal(14000 + n * 1500)
        for t, session in enumerate(sessions):
            # Smooth cycles + independent periodic shocks, deterministic, no random generator.
            drift = .00045 + .007 * math.sin(t / 31 + n * .8) + .0025 * math.sin(t / 5 + n)
            if t % 47 == n * 3:
                drift += .025
            close = (previous * Decimal(str(1 + drift))).quantize(Decimal(".01"))
            opening = (previous * Decimal(str(1 + .001 * math.sin(t + n)))).quantize(Decimal(".01"))
            high = (max(opening, close) * Decimal("1.008")).quantize(Decimal(".01"))
            low = (min(opening, close) * Decimal(".992")).quantize(Decimal(".01"))
            volume = int(600000 * (1.15 + .25 * math.sin(t / 6 + n)))
            if t % 47 == n * 3:
                volume *= 2
            if master and (session < master["listed_at"] or
                           (master["delisted_at"] and session >= master["delisted_at"])):
                previous = close
                continue
            band = Decimal(".07" if not master or master["exchange"] == "HOSE" else ".10")
            bars.append({
                "symbol": "VNINDEX" if is_index else master["symbol"],  # type: ignore[index]
                "exchange": "HOSE" if is_index else master["exchange"],  # type: ignore[index]
                "kind": "index" if is_index else "stock", "session_date": session,
                "open": str(opening), "high": str(high), "low": str(low), "close": str(close),
                "volume": volume, "traded_value": str(close * volume), "factor": "1",
                "floor": str((previous * (1 - band)).quantize(Decimal(".01"))),
                "ceiling": str((previous * (1 + band)).quantize(Decimal(".01"))),
                "revision": HISTORY_VERSION, "observed_at": session + "T09:30:00+00:00",
                "is_final": True, "halted": False,
            })
            previous = close
    return {"classification": "DEMO", "provider": "fixture", "version": HISTORY_VERSION,
            "calendar": sessions, "instruments": instruments, "bars": bars, "actions": [],
            "warnings": ["SYNTHETIC_PRICES", "SYNTHETIC_WEEKDAY_CALENDAR", "ILLUSTRATIVE_EXCHANGE_RULES",
                         "NOT_INVESTMENT_ADVICE", "NO_REAL_MARKET_VALIDATION"],
            "adjustment_policy": "DEMO_NO_ACTIONS_FACTOR_ONE"}


def quality(payload: dict) -> dict:
    calendar = payload["calendar"]
    if not calendar or calendar != sorted(set(calendar)):
        raise ValueError("INVALID_CALENDAR")
    seen: set[tuple[str, str]] = set()
    invalid = []
    final = True
    for row in payload["bars"]:
        key = (row["symbol"], row["session_date"])
        if key in seen:
            raise ValueError("DUPLICATE_BAR")
        seen.add(key)
        try:
            normalize(row)
            factor = Decimal(str(row["factor"]))
            if not factor.is_finite() or factor <= 0:
                raise ValueError("INVALID_ADJUSTMENT")
        except (ValueError, KeyError) as exc:
            invalid.append({"symbol": row["symbol"], "date": row["session_date"], "rule": str(exc)})
        final = final and row["is_final"]
    expected = {(i["symbol"], d) for i in payload["instruments"] for d in calendar
                if i["listed_at"] <= d and (not i["delisted_at"] or d < i["delisted_at"])}
    missing = sorted(expected - seen)
    missing_index = [d for d in calendar if ("VNINDEX", d) not in seen]
    status = "FAILED" if invalid else "PARTIAL" if missing or missing_index or not final else "COMPLETE"
    return {"status": status, "expected_bars": len(expected), "missing_bars": len(missing),
            "missing_examples": missing[:30], "missing_benchmark": missing_index[:30],
            "invalid": invalid[:30], "is_final": final, "missing_fraction": len(missing) / max(1, len(expected)),
            "instruments": len(payload["instruments"]), "sessions": len(calendar),
            "delisted": sum(bool(i["delisted_at"]) for i in payload["instruments"]),
            "adjustment_policy": payload["adjustment_policy"]}


def import_history(payload: dict | None = None) -> str:
    if os.getenv("DATA_MODE") != "demo":
        raise ValueError("DATA_UNAVAILABLE:PROVIDER_CREDENTIALS")
    payload = payload or fetch_retry(demo_history)
    if payload.get("classification") != "DEMO":
        raise ValueError("UNAUTHORIZED_DATA_SOURCE")
    report = quality(payload)
    checksum = digest(payload)
    with connect() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(61732002)")
        existing = conn.execute("SELECT id FROM research_datasets WHERE content_hash=%s", (checksum,)).fetchone()
        if existing:
            return str(existing[0])
        provider = conn.execute("SELECT id FROM data_providers WHERE name='fixture'").fetchone()[0]
        run = conn.execute("""INSERT INTO ingestion_runs(provider_id,kind,status,is_demo,from_date,to_date,counts_json,finished_at)
            VALUES(%s,'HISTORY',%s,true,%s,%s,%s,now()) RETURNING id""",
            (provider, report["status"], payload["calendar"][0], payload["calendar"][-1], Jsonb(report))).fetchone()[0]
        conn.execute("INSERT INTO raw_payloads(ingestion_run_id,payload_json,sha256) VALUES(%s,%s,%s)",
                     (run, Jsonb(payload), checksum))
        ids = {}
        for instrument in payload["instruments"]:
            ids[instrument["symbol"]] = conn.execute("""INSERT INTO instruments(symbol,exchange,name,is_demo,current_status)
                VALUES(%s,%s,%s,true,%s) ON CONFLICT(symbol,exchange,is_demo) DO UPDATE SET
                current_status=excluded.current_status RETURNING id""",
                (instrument["symbol"], instrument["exchange"], "SYNTHETIC " + instrument["symbol"],
                 "DELISTED" if instrument["delisted_at"] else "ACTIVE")).fetchone()[0]
            conn.execute("""INSERT INTO instrument_history(instrument_id,effective_from,effective_to,known_at,sector_id,listing_status)
                VALUES(%s,%s,%s,%s,%s,'ACTIVE') ON CONFLICT DO NOTHING""",
                (ids[instrument["symbol"]], instrument["listed_at"], instrument["delisted_at"],
                 instrument["known_at"] + "T00:00:00+00:00", instrument["sector"]))
        # Failed validation is retained for audit but never enters canonical bars.
        if report["status"] != "FAILED":
            with conn.cursor() as cur:
                cur.executemany("""INSERT INTO market_sessions(exchange,session_date,is_trading_day,is_demo,source)
                    VALUES(%s,%s,true,true,'synthetic-weekday-calendar') ON CONFLICT DO NOTHING""",
                    [(exchange, d) for exchange in ("HOSE", "HNX") for d in payload["calendar"]])
                cur.executemany("""INSERT INTO market_bars(instrument_id,session_date,open,high,low,close,volume,traded_value,
                    provider_id,revision,is_final,observed_at,ingestion_run_id,is_demo,floor_price,ceiling_price)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,true,%s,%s) ON CONFLICT DO NOTHING""",
                    [(ids[b["symbol"]], b["session_date"], b["open"], b["high"], b["low"], b["close"], b["volume"],
                      b["traded_value"], provider, b["revision"], b["is_final"], b["observed_at"], run, b["floor"],
                      b["ceiling"]) for b in payload["bars"] if b["kind"] == "stock"])
                cur.executemany("""INSERT INTO index_bars(index_code,session_date,open,high,low,close,provider_id,revision,
                    is_final,observed_at,ingestion_run_id,is_demo) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,true)
                    ON CONFLICT DO NOTHING""",
                    [(b["symbol"], b["session_date"], b["open"], b["high"], b["low"], b["close"], provider,
                      b["revision"], b["is_final"], b["observed_at"], run) for b in payload["bars"] if b["kind"] == "index"])
        if report["status"] != "COMPLETE":
            conn.execute("""INSERT INTO data_quality_issues(ingestion_run_id,severity,rule,details_json,is_demo)
                VALUES(%s,'ERROR','HISTORY_QUALITY',%s,true)""", (run, Jsonb(report)))
        result = conn.execute("""INSERT INTO research_datasets(content_hash,name,provider,is_demo,status,from_date,to_date,
            quality_json,payload_json,ingestion_run_id) VALUES(%s,%s,'fixture',true,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (checksum, HISTORY_VERSION, report["status"], payload["calendar"][0], payload["calendar"][-1],
             Jsonb(report), Jsonb(payload), run)).fetchone()
        return str(result[0])


def load_dataset(dataset_id: str) -> dict:
    with connect() as conn:
        row = conn.execute("SELECT payload_json,status,content_hash FROM research_datasets WHERE id=%s AND is_demo=%s",
                           (dataset_id, os.getenv("DATA_MODE") == "demo")).fetchone()
    if not row:
        raise ValueError("DATASET_NOT_FOUND")
    if row[1] != "COMPLETE":
        raise ValueError("DATA_QUALITY_BLOCKED")
    return {**row[0], "content_hash": row[2]}
