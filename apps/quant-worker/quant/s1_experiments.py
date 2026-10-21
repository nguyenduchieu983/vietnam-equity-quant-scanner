"""Bounded exploratory S1 study. Never promotes a fitted variant to production."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
import statistics

from .backtest import simulate
from .features import feature_book, regime
from .history import digest
from .strategies import evaluate
from .vndirect_research import build


# Freeze a small hypothesis set before examining candidate performance.
CANDIDATES = [
    {"name": "baseline", "entry": "original", "ema": 50, "hold": 30},
    {"name": "risk_on", "entry": "risk_on", "ema": 50, "hold": 30},
    {"name": "confirmed", "entry": "confirmed", "ema": 50, "hold": 30},
    {"name": "ema20_exit", "entry": "original", "ema": 20, "hold": 30},
    {"name": "hold15", "entry": "original", "ema": 50, "hold": 15},
    {"name": "risk_on_ema20", "entry": "risk_on", "ema": 20, "hold": 30},
]
BASE = {"strategy": "S1", "capital": 50000000, "maxHold": 30, "minLiquidity": 5e9,
        "buyFee": .0015, "sellFee": .0015, "sellTax": .001, "slippage": .001}


def accepts(entry: str, state: dict, feature: dict) -> bool:
    if entry == "risk_on":
        return state["regime"] == "RISK_ON"
    if entry == "confirmed":
        return feature["rising_close"] and feature["raw_bullish"] and feature["close"] > feature["ema20"]
    return True


def summarize(result: dict, calendar: list[str]) -> dict:
    closed: dict[tuple, D] = defaultdict(lambda: D(0))
    for t in result["trades"]:
        opened = result["open_positions"].get(t["symbol"])
        if opened and calendar[opened["bought"]] == t["entry_date"]:
            continue
        closed[(t["symbol"], t["entry_date"])] += D(t["pnl"])
    wins, losses = sum(v > 0 for v in closed.values()), sum(v < 0 for v in closed.values())
    for e in result["equity"]:
        assert abs(D(e["nav"])-D(e["cash"])-D(e["pending_cash"])-D(e["holdings_value"])) <= D(".02")
        assert D(e["cash"]) >= 0
    return {"closed": len(closed), "wins": wins, "losses": losses,
            "winRate": wins/len(closed) if closed else None,
            "return": result["metrics"]["totalReturn"], "drawdown": result["metrics"]["maxDrawdown"],
            "openSymbols": list(result["open_positions"]), "metrics": result["metrics"],
            "warnings": result["warnings"], "resultHash": digest(result)}


def study(root: Path) -> Path:
    payload, quality = build(root)
    if quality["unexplainedAdjustmentChanges"]:
        raise ValueError("UNEXPLAINED_ADJUSTMENT_CHANGE")
    bad_ids = {x["id"] for x in quality["actionIssues"]}
    for i in range(10):
        for event in json.loads((root/f"events-{i}.json").read_text(encoding="utf8"))["data"]:
            if event["id"] in bad_ids and event.get("effectiveDate", "") >= "2024-02-15":
                raise ValueError("UNRESOLVED_STUDY_ACTION")
    calendar = payload["calendar"]
    book = feature_book(payload)
    output = root/"s1-studies"/datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output.mkdir(parents=True, exist_ok=False)
    protocol = {"classification": "EXPLORATORY_ALREADY_SEEN_TEST", "candidates": CANDIDATES,
                "validation": ["2024-02-15", "2024-06-28"], "comparison": ["2024-09-04", "2026-10-16"],
                "selection": "Validation only: >=8 closed, win rate > baseline, return >= baseline, drawdown >= baseline; highest return then name; otherwise retain baseline",
                "datasetHash": payload["content_hash"],
                "engineHash": hashlib.sha256(b"".join(p.read_bytes() for p in sorted(Path(__file__).parent.glob("*.py")))).hexdigest()}
    (output/"protocol.json").write_text(json.dumps(protocol, indent=2), encoding="utf8")
    cache: dict[str, tuple] = {}

    def source(day: str, candidate: dict):
        if day not in cache:
            cache[day] = evaluate(payload, book, day, "S1", BASE)
        state, signals = cache[day]
        # Filter already ranked original S1 signals; do not rerank after exclusions.
        return state, [s for s in signals if s["side"] == "LONG" and accepts(candidate["entry"], state, s["features_used"])]

    def execute(candidate: dict, period: list[str], suffix: str, slippage: float = .001):
        config = {**BASE, "maxHold": candidate["hold"], "s1ExitEma": candidate["ema"], "slippage": slippage}
        result = simulate(payload, config, period[0], period[1], book, signal_source=lambda day: source(day, candidate))
        summary = {"name": candidate["name"], "config": config, **summarize(result, calendar)}
        (output/f'{candidate["name"]}-{suffix}.json').write_text(json.dumps(result, indent=2), encoding="utf8")
        print(json.dumps({"period": suffix, **{k: summary[k] for k in ("name", "closed", "wins", "winRate", "return", "drawdown")}}), flush=True)
        return summary, result

    validation = [execute(c, protocol["validation"], "validation")[0] for c in CANDIDATES]
    baseline = validation[0]
    eligible = [s for s in validation[1:] if s["closed"] >= 8 and s["winRate"] > (baseline["winRate"] or 0)
                and s["return"] >= baseline["return"] and s["drawdown"] >= baseline["drawdown"]]
    selected = sorted(eligible, key=lambda s: (-s["return"], s["name"]))[0]["name"] if eligible else "baseline"
    (output/"selection.json").write_text(json.dumps({"selected": selected, "validation": validation}, indent=2), encoding="utf8")
    # Selection is persisted before evaluating any candidate on the later period.
    comparison = []
    losses = []
    for candidate in CANDIDATES:
        summary, result = execute(candidate, protocol["comparison"], "comparison")
        comparison.append(summary)
        if candidate["name"] == "baseline":
            for t in result["trades"]:
                opened = result["open_positions"].get(t["symbol"])
                if opened and calendar[opened["bought"]] == t["entry_date"]:
                    continue
                day = calendar[calendar.index(t["entry_date"])-1]
                f = book[t["symbol"]][day]
                losses.append({**t, "pnl": float(t["pnl"]), "decisionDate": day,
                               "regime": regime(payload, book, day)["regime"], "rsi": f["rsi14"],
                               "stretch": f["close"]/f["ema20"]-1,
                               "held": calendar.index(t["exit_date"])-calendar.index(t["entry_date"])})
    diagnostics = {}
    for label, positive in (("wins", True), ("losses", False)):
        rows = [t for t in losses if (t["pnl"] > 0 if positive else t["pnl"] < 0)]
        diagnostics[label] = {"count": len(rows), "pnl": sum(t["pnl"] for t in rows),
                              "exits": dict(Counter(t["exit_reason"] for t in rows)),
                              "regimes": dict(Counter(t["regime"] for t in rows)),
                              "meanRSI": statistics.mean(t["rsi"] for t in rows) if rows else None}
    stress = [execute(c, protocol["comparison"], "stress", .003)[0] for c in CANDIDATES]
    summary = {**protocol, "quality": {"missingEligibleBars": quality["testMissingEligibleBars"]},
               "selected": selected, "validation": validation, "comparison": comparison,
               "stress": stress, "diagnostics": diagnostics}
    (output/"summary.json").write_text(json.dumps(summary, indent=2), encoding="utf8")
    (output/"baseline-trades.json").write_text(json.dumps(losses, indent=2), encoding="utf8")
    (root/"latest-s1-study.txt").write_text(str(output.resolve()), encoding="utf8")
    print(json.dumps({"output": str(output), "selected": selected}), flush=True)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    study(parser.parse_args().directory)
