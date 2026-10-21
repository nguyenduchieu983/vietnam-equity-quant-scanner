"""Durable paired EOD paper ledger. Every advance needs a recorded approval."""
import argparse
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo
from .backtest import simulate
from .db import connect
from .features import feature_book
from .history import digest
from .s1_experiments import BASE, summarize
from .strategies import evaluate
from .vndirect_research import build, read


def engine_hash() -> str:
    return hashlib.sha256(b"".join((Path(__file__).parent/n).read_bytes() for n in
                                 ("backtest.py", "features.py", "strategies.py", "risk.py", "paper.py"))).hexdigest()


def closed_cutoff() -> str:
    now = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))
    return (now.date() if now.hour >= 17 else now.date()-timedelta(days=1)).isoformat()


def import_market(root: Path) -> str:
    payload, quality = build(root)
    if payload["calendar"][-1] > closed_cutoff() or quality["unexplainedAdjustmentChanges"]:
        raise ValueError("PAPER_REQUIRES_CLOSED_VALIDATED_EOD")
    bad = {e["id"] for e in quality["actionIssues"]}
    quality["unresolvedActionDates"] = sorted({e.get("effectiveDate", "") for i in range(10)
        for e in read(root/f"events-{i}.json")["data"] if e["id"] in bad})
    with connect() as c:
        row = c.execute("""INSERT INTO paper_market_snapshots(content_hash,as_of,payload_json,quality_json)
            VALUES(%s,%s,%s,%s) ON CONFLICT(content_hash) DO NOTHING RETURNING id""",
            (payload["content_hash"], payload["calendar"][-1], json.dumps(payload), json.dumps(quality))).fetchone()
        if not row:
            row = c.execute("SELECT id FROM paper_market_snapshots WHERE content_hash=%s", (payload["content_hash"],)).fetchone()
        return str(row[0])


def decision(payload: dict, book: dict, day: str, config: dict) -> dict:
    state, signals = evaluate(payload, book, day, "S1", config)
    return {"day": day, "state": state, "signals": [s for s in signals if s["side"] == "LONG"],
            "features": {symbol: days[day] for symbol, days in book.items() if day in days}}


def step(payload: dict, book: dict, config: dict, state: dict, prior: dict, day: str) -> tuple[dict, dict]:
    previous = payload["calendar"][payload["calendar"].index(day)-1]
    if prior["day"] != previous:
        raise ValueError("PAPER_DECISION_SESSION_MISMATCH")
    missing = [s for s in state["positions"] if not any(b["symbol"] == s and b["session_date"] == day for b in payload["bars"])]
    if missing:
        raise ValueError("PAPER_MISSING_HOLDING_BAR:"+",".join(missing))
    # Snapshot features driving yesterday's decision must not be revised retroactively.
    frozen = {s: {**days} for s, days in book.items()}
    for s in frozen:
        frozen[s].pop(previous, None)
    for s, value in prior["features"].items():
        frozen.setdefault(s, {})[previous] = value
    result = simulate(payload, config, day, day, frozen,
                      signal_source=lambda _: (prior["state"], prior["signals"]), resume=state, checkpoint=True)
    return result, decision(payload, book, day, config)


def run(job_id: str, request: dict) -> dict:
    if request.get("action") == "CREATE":
        return create_pair(job_id, request)
    with connect() as c:
        approval = c.execute("SELECT pair_id,snapshot_id,through_date,expected_cursor FROM paper_approvals WHERE job_id=%s", (job_id,)).fetchone()
        if not approval:
            raise ValueError("PAPER_APPROVAL_REQUIRED")
        pair_id, snapshot_id, through, expected = approval
        pair = c.execute("SELECT mode,cursor_day,engine_hash,calendar_json,created_at FROM paper_pairs WHERE id=%s FOR UPDATE", (pair_id,)).fetchone()
        if pair[1] >= through:
            return {"pairId": str(pair_id), "through": str(pair[1]), "idempotent": True}
        if pair[1] != expected or pair[2] != engine_hash():
            raise ValueError("PAPER_CURSOR_OR_ENGINE_CHANGED")
        payload, quality = c.execute("SELECT payload_json,quality_json FROM paper_market_snapshots WHERE id=%s", (snapshot_id,)).fetchone()
        if payload["calendar"][:len(pair[3])] != pair[3] or str(through) > closed_cutoff():
            raise ValueError("PAPER_CALENDAR_OR_CUTOFF_CHANGED")
        sessions = [d for d in payload["calendar"] if str(pair[1]) < d <= str(through)]
        if not sessions or sessions[-1] != str(through):
            raise ValueError("PAPER_SESSION_UNAVAILABLE")
        if pair[0] == "FORWARD" and sessions[0] < pair[4].astimezone(ZoneInfo("Asia/Ho_Chi_Minh")).date().isoformat():
            raise ValueError("FORWARD_CANNOT_REPLAY_PRE_CREATION_SESSIONS")
        if set(sessions) & set(quality["unresolvedActionDates"]):
            raise ValueError("PAPER_UNRESOLVED_CORPORATE_ACTION")
        book = feature_book(payload)
        accounts = c.execute("SELECT id,config_json,state_json,decision_json FROM paper_accounts WHERE pair_id=%s ORDER BY code", (pair_id,)).fetchall()
        for account_id, config, state, prior in accounts:
            for day in sessions:
                result, prior = step(payload, book, config, state, prior, day)
                state = result.pop("checkpoint")
                c.execute("INSERT INTO paper_sessions(account_id,session_date,snapshot_id,payload_json,result_hash) VALUES(%s,%s,%s,%s,%s)",
                          (account_id, day, snapshot_id, json.dumps({**result, "decision": prior}), digest(result)))
            records = [r[0] for r in c.execute("SELECT payload_json - 'decision' FROM paper_sessions WHERE account_id=%s ORDER BY session_date", (account_id,)).fetchall()]
            combined: dict = {key: [v for record in records for v in record[key]] for key in ("equity", "orders", "trades")}
            from .metrics import metrics
            combined.update(open_positions=state["positions"], warnings=sorted({w for r in records for w in r["warnings"]}),
                            metrics=metrics(combined["equity"], combined["trades"], combined["orders"], config["capital"]))
            summary = summarize(combined, payload["calendar"])
            c.execute("UPDATE paper_accounts SET state_json=%s,decision_json=%s,summary_json=%s WHERE id=%s",
                      (json.dumps(state), json.dumps(prior), json.dumps(summary), account_id))
        c.execute("UPDATE paper_pairs SET cursor_day=%s,snapshot_id=%s,calendar_json=%s WHERE id=%s",
                  (through, snapshot_id, json.dumps([d for d in payload["calendar"] if d <= str(through)]), pair_id))
        c.execute("INSERT INTO audit_logs(actor,action,entity,entity_id,payload_json) VALUES('paper-worker','PAPER_ADVANCE','paper_pairs',%s,%s)",
                  (str(pair_id), json.dumps({"through": str(through), "sessions": len(sessions), "job": job_id})))
        return {"pairId": str(pair_id), "through": str(through), "sessions": len(sessions)}


def create_pair(job_id: str, request: dict) -> dict:
    with connect() as c:
        c.execute("SELECT pg_advisory_xact_lock(61732006)")
        if c.execute("SELECT 1 FROM paper_pairs WHERE id=%s", (job_id,)).fetchone():
            return {"pairId": job_id}
        snapshot = c.execute("SELECT id,payload_json,as_of FROM paper_market_snapshots WHERE id=%s", (request["snapshotId"],)).fetchone()
        if not snapshot or request["mode"] not in ("FORWARD", "REPLAY"):
            raise ValueError("INVALID_PAPER_CREATE")
        snapshot_id, payload, as_of = snapshot
        calendar = payload["calendar"]
        if request["mode"] == "FORWARD":
            if (datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()-as_of).days > 4:
                raise ValueError("PAPER_SNAPSHOT_STALE_REFRESH_FIRST")
            initial = str(as_of)
        else:
            start = request.get("startDay")
            if not isinstance(start, str) or start not in calendar or start < "2024-02-15":
                raise ValueError("INVALID_REPLAY_START")
            initial = calendar[calendar.index(start)-1]
        book = feature_book(payload)
        c.execute("INSERT INTO paper_pairs(id,name,mode,initial_day,cursor_day,engine_hash,calendar_json,snapshot_id) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
                  (job_id, "S1 vs Partial 1R / Trail 2 ATR / 15", request["mode"], initial, initial, engine_hash(), json.dumps([d for d in calendar if d <= initial]), snapshot_id))
        for code in ("S1", "S1_PARTIAL"):
            config = dict(BASE)
            if code == "S1_PARTIAL":
                config.update(maxHold=15, s1TargetR=1, s1PartialTarget=True, s1TrailAtr=2)
            state = {"cash": str(config["capital"]), "pending": [], "peak": str(config["capital"]), "positions": {},
                     "benchmark_base": str(book["VNINDEX"][initial]["raw_close"])}
            c.execute("INSERT INTO paper_accounts(pair_id,code,config_json,state_json,decision_json) VALUES(%s,%s,%s,%s,%s)",
                      (job_id, code, json.dumps(config), json.dumps(state), json.dumps(decision(payload, book, initial, config))))
        c.execute("INSERT INTO audit_logs(actor,action,entity,entity_id) VALUES('paper-worker','PAPER_CREATE','paper_pairs',%s)", (job_id,))
        return {"pairId": job_id, "initialDay": initial, "mode": request["mode"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    print(import_market(parser.parse_args().directory))
