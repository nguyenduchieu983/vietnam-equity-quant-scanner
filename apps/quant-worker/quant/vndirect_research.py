"""Offline real-price research runner; never imports public data as a DEMO dataset."""
import argparse
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
import time
from .backtest import simulate
from .features import feature_book
from .history import digest
from .provider import normalize
from .risk import RULES


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def normalize_price(row: dict, fetched: str, revision: str, index: bool = False) -> dict:
    scale = D(1 if index else 1000)
    bar = {"symbol": row["code"], "exchange": row["floor"], "session_date": row["date"],
           **{k: str(D(str(row[k]))*scale) for k in ("open", "high", "low", "close")},
           "volume": int(row["nmVolume"]), "traded_value": str(row["nmValue"]),
           "kind": "index" if index else "stock", "observed_at": fetched, "revision": revision,
           "is_final": True, "halted": row["nmVolume"] == 0,
           "factor": "1" if index else str(D(str(row["adClose"]))/D(str(row["close"])))}
    if index:
        bar.update(floor="0", ceiling="999999999")
    else:
        bar.update(floor=str(D(str(row["floorPrice"]))*scale), ceiling=str(D(str(row["ceilingPrice"]))*scale))
        for k in ("open", "high", "low", "close"):
            value = D(str(row["ad"+k.title()]))*scale
            if not value.is_finite() or value <= 0:
                raise ValueError("INVALID_ADJUSTED_PRICE")
            bar["adjusted_"+k] = str(value)
    normalize(bar)
    if not index and not D(bar["floor"]) <= D(bar["low"]) <= D(bar["high"]) <= D(bar["ceiling"]):
        raise ValueError("OUTSIDE_PROVIDER_BANDS")
    return bar


def actions_from_events(events: list[dict], calendar: list[str]) -> tuple[list[dict], list[dict]]:
    actions, issues, seen = [], [], set()
    for e in sorted(events, key=lambda e: (e.get("effectiveDate", ""), e["id"])):
        kind, ex = e["type"], e.get("effectiveDate")
        if kind not in ("DIVIDEND", "STOCKDIV", "KINDDIV", "ISSUE") or not ex or not calendar[0] <= ex <= calendar[-1]:
            continue
        if ex not in calendar or not e.get("disclosureDate") or e["disclosureDate"] > ex:
            issues.append({"id": e["id"], "reason": "UNVERIFIED_EVENT_TIMING"})
            continue
        key = (e["code"], kind, ex, e.get("dividend"), e.get("ratio"))
        if key in seen:
            continue
        seen.add(key)
        action = {"symbol": e["code"], "ex_date": ex, "known_at": e["disclosureDate"], "source_id": e["id"]}
        if kind == "DIVIDEND":
            payable = e.get("actualDate")
            if not payable or payable < ex or not e.get("dividend"):
                issues.append({"id": e["id"], "reason": "MISSING_DIVIDEND_PAYMENT"})
                continue
            action.update(type="CASH_DIVIDEND", cash_amount=str(e["dividend"]), payable_date=payable,
                          withholding_rate="0.05", adjust_stop=True)
        elif kind in ("STOCKDIV", "KINDDIV"):
            if not e.get("ratio") or e["ratio"] <= 0:
                issues.append({"id": e["id"], "reason": "MISSING_BONUS_RATIO"})
                continue
            matches = [x["effectiveDate"] for x in events if x["code"] == e["code"] and x["type"] == "LISTED"
                       and x.get("effectiveDate", "") > ex and x.get("numberOfShares") == e.get("numberOfShares")
                       and e.get("numberOfShares") and (date.fromisoformat(x["effectiveDate"])-date.fromisoformat(ex)).days <= 180]
            action.update(type="STOCK_DIVIDEND", ratio=str(D(str(e["ratio"]))/100),
                          available_date=min(matches) if matches else None)
        else:
            action.update(type="RIGHTS_ISSUE")
        actions.append(action)
    # Multiple same-day bonus allocations apply to the same pre-event shares.
    grouped: dict[tuple, dict] = {}
    result = []
    for a in actions:
        if a["type"] != "STOCK_DIVIDEND":
            result.append(a)
            continue
        bonus_key = (a["symbol"], a["ex_date"])
        if bonus_key not in grouped:
            grouped[bonus_key] = dict(a)
        else:
            old = grouped[bonus_key]
            old["ratio"] = str(D(old["ratio"])+D(a["ratio"]))
            old["available_date"] = max(old["available_date"], a["available_date"]) if old["available_date"] and a["available_date"] else None
    result.extend(grouped.values())
    return sorted(result, key=lambda a: (a["ex_date"], a["type"])), issues


def build(root: Path) -> tuple[dict, dict]:
    manifest = read(root/"manifest.json")
    # Verify stored evidence before computing; fail on silently edited caches.
    for path in root.glob("*.meta.json"):
        meta = read(path)
        raw = path.with_name(path.name.replace(".meta.json", ".json")).read_bytes()
        if hashlib.sha256(raw).hexdigest() != meta["sha256"]:
            raise ValueError("CACHE_HASH_MISMATCH:"+path.name)
    universe = read(root/"universe.json")
    symbols = {s["code"] for s in universe["stocks"]}
    sectors = {i["symbol"]: str(i.get("icbCode2", "UNKNOWN")) for i in read(root/"sectors.json")}
    index_rows = read(root/"index.json")["data"]
    calendar = sorted({r["date"] for r in index_rows})
    fetched = read(root/"index.meta.json")["fetchedAt"]
    bars = [normalize_price(r, fetched, "vndirect-snapshot", True) for r in index_rows]
    rows, events, masters = [], [], {}
    for i in range(10):
        rows.extend(read(root/f"prices-{i}.json")["data"])
        events.extend(read(root/f"events-{i}.json")["data"])
        masters.update({m["code"]: m for m in read(root/f"masters-{i}.json")["data"]})
    if {r["code"] for r in rows} != symbols:
        raise ValueError("UNIVERSE_COVERAGE_MISMATCH")
    invalid, seen = [], set()
    for row in rows:
        key = (row["code"], row["date"])
        if key in seen:
            raise ValueError("DUPLICATE_PRICE")
        seen.add(key)
        try:
            bars.append(normalize_price(row, fetched, "vndirect-snapshot"))
        except (ValueError, KeyError, ArithmeticError) as exc:
            invalid.append({"symbol": row["code"], "date": row["date"], "reason": str(exc)})
    instruments = []
    for symbol in sorted(symbols):
        observed = [r for r in rows if r["code"] == symbol]
        first = min(r["date"] for r in observed)
        baseline = [r for r in observed if r["date"] <= universe["selectionDate"]]
        exchange = max(baseline, key=lambda r: r["date"])["floor"]
        # Exchange transfers outside HOSE/HNX leave the entry universe, not silently deleted history.
        transfers = [r["date"] for r in observed if r["date"] > universe["selectionDate"] and r["floor"] not in ("HOSE", "HNX")]
        instruments.append({"symbol": symbol, "exchange": exchange, "sector": sectors.get(symbol, "UNKNOWN"),
                            "listed_at": min(first, masters.get(symbol, {}).get("listedDate", first)),
                            "delisted_at": min(transfers) if transfers else None,
                            "known_at": universe["selectionDate"], "type": "COMMON_STOCK"})
    actions, action_issues = actions_from_events(events, calendar)
    recognized = {(e["code"], e.get("effectiveDate")) for e in events if e["type"] in ("DIVIDEND", "STOCKDIV", "KINDDIV", "ISSUE")}
    previous_factor: dict[str, D] = {}
    unexplained = []
    for row in sorted(rows, key=lambda r: (r["code"], r["date"])):
        if row["close"] <= 0 or row["adClose"] <= 0:
            continue
        factor = D(str(row["adClose"]))/D(str(row["close"]))
        symbol = row["code"]
        if symbol in previous_factor and abs(factor/previous_factor[symbol]-1) > D(".003") and (symbol, row["date"]) not in recognized:
            unexplained.append({"symbol": symbol, "date": row["date"]})
        previous_factor[symbol] = factor
    available = {(b["symbol"], b["session_date"]) for b in bars}
    missing = [(s, d) for s in sorted(symbols) for d in calendar if (s, d) not in available]
    test_missing = [(i["symbol"], d) for i in instruments for d in calendar if d >= "2024-09-02"
                    and (not i["delisted_at"] or d < i["delisted_at"])
                    and (i["symbol"], d) not in available]
    report = {"source": manifest["provider"], "universe": universe, "symbols": len(symbols), "sessions": len(calendar),
              "firstSession": calendar[0], "lastSession": calendar[-1], "bars": len(bars),
              "missingBars": len(missing), "missingExamples": missing[:30], "invalidBars": invalid,
              "testMissingEligibleBars": len(test_missing), "testMissingExamples": test_missing[:30],
              "actionCount": len(actions), "actionIssues": action_issues, "unexplainedAdjustmentChanges": unexplained,
              "status": "PROVISIONAL_REAL_RESEARCH", "isDemo": False}
    payload = {"classification": "REAL_RESEARCH", "calendar": calendar, "instruments": instruments,
               "bars": sorted(bars, key=lambda b: (b["symbol"], b["session_date"])), "actions": actions,
               "adjustment_policy": "Provider adjusted OHLC for signals; raw VND prices and reported bands for fills",
               "warnings": ["PUBLIC_DATA_NOT_EXCHANGE_CERTIFIED", "SURVIVORSHIP_COVERAGE_NOT_GUARANTEED",
                            "FIXED_100_STOCK_COHORT_SELECTED_2023_12", "SECTOR_CLASSIFICATION_CURRENT_SNAPSHOT",
                            "HISTORICAL_REVISIONS_NOT_POINT_IN_TIME_ARCHIVED", "DIVIDEND_WITHHOLDING_5PCT_ASSUMPTION",
                            "CORPORATE_ACTION_PAYMENT_DATES_PROVIDER_REPORTED", "ILLUSTRATIVE_SETTLEMENT_AND_TICKS",
                            "NO_FORWARD_FILL_MISSING_BARS"]}
    payload["content_hash"] = digest(payload)
    return payload, report


def run(root: Path) -> dict:
    payload, quality = build(root)
    if quality["unexplainedAdjustmentChanges"]:
        raise ValueError("UNEXPLAINED_ADJUSTMENT_CHANGE")
    if any(issue.get("id") for issue in quality["actionIssues"]):
        # Pre-test revisions are disclosed; a relevant incomplete action blocks execution.
        raw_events = [e for i in range(10) for e in read(root/f"events-{i}.json")["data"]]
        bad_ids = {e["id"] for e in quality["actionIssues"]}
        if any(e["id"] in bad_ids and e.get("effectiveDate", "") >= "2024-09-02" for e in raw_events):
            raise ValueError("UNRESOLVED_TEST_PERIOD_CORPORATE_ACTION")
    calendar = payload["calendar"]
    start = next(d for d in calendar if d >= "2024-09-02")
    end = calendar[-1]
    config = {"strategy": "S1", "capital": 50000000, "maxHold": 30, "minLiquidity": 5e9,
              "buyFee": .0015, "sellFee": .0015, "sellTax": .001, "slippage": .001}
    began = time.monotonic()
    book = feature_book(payload)
    result = simulate(payload, config, start, end, book)
    # Closed round trips, not individual partial executions, are the headline denominator.
    closed: dict[tuple, D] = defaultdict(lambda: D(0))
    for trade in result["trades"]:
        opened = result["open_positions"].get(trade["symbol"])
        if opened and calendar[opened["bought"]] == trade["entry_date"]:
            continue
        closed[(trade["symbol"], trade["entry_date"])] += D(trade["pnl"])
    wins = sum(p > 0 for p in closed.values())
    losses = sum(p < 0 for p in closed.values())
    order_reasons = Counter(o["reason"] for o in result["orders"] if o["status"] != "FILLED")
    # Cross-check all realized cash identities without hiding bad days.
    assert all(abs(D(e["nav"])-D(e["cash"])-D(e["pending_cash"])-D(e["holdings_value"])) <= D(".02") for e in result["equity"])
    assert all(D(e["cash"]) >= 0 for e in result["equity"])
    summary = {"classification": "REAL_RESEARCH_PROVISIONAL", "isDemo": False,
               "period": {"from": start, "to": end, "sessions": len(result["equity"])}, "config": config,
               "quality": quality, "metrics": result["metrics"], "closedPositions": len(closed),
               "winningPositions": wins, "losingPositions": losses, "breakevenPositions": len(closed)-wins-losses,
               "winRateClosedPositions": wins/len(closed) if closed else None,
               "openPositions": result["open_positions"], "noFillReasons": dict(order_reasons),
               "warnings": result["warnings"], "datasetHash": payload["content_hash"],
               "engineHash": hashlib.sha256(b"".join(p.read_bytes() for p in sorted(Path(__file__).parent.glob("*.py")))).hexdigest(),
               "rules": RULES, "elapsedSeconds": time.monotonic()-began,
               "fetchedAt": read(root/"manifest.json")["requests"][0]["fetchedAt"]}
    summary["reproducibilityHash"] = digest({"dataset": payload["content_hash"], "config": config, "result": result})
    output = root/"runs"/datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output.mkdir(parents=True, exist_ok=False)
    for name, value in (("summary", summary), ("result", result)):
        (output/f"{name}.json").write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf8")
    (root/"latest-run.txt").write_text(str(output.resolve()), encoding="utf8")
    print(json.dumps({"output": str(output), "winRate": summary["winRateClosedPositions"], "closed": len(closed),
                      "wins": wins, "losses": losses, "return": result["metrics"]["totalReturn"],
                      "maxDrawdown": result["metrics"]["maxDrawdown"], "elapsed": summary["elapsedSeconds"]}), flush=True)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    run(parser.parse_args().directory)
