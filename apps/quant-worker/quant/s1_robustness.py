"""Second bounded S1 study; validation under both base and stress costs."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from .backtest import simulate
from .features import feature_book
from .s1_experiments import BASE, summarize
from .strategies import evaluate
from .vndirect_research import build, read

CANDIDATES: list[dict] = [
    {"name": "baseline", "entry": "original", "hold": 30, "trail": None},
    {"name": "hold15", "entry": "original", "hold": 15, "trail": None},
    {"name": "trail3", "entry": "original", "hold": 30, "trail": 3},
    {"name": "trail2", "entry": "original", "hold": 30, "trail": 2},
    {"name": "trend200", "entry": "trend200", "hold": 30, "trail": None},
    {"name": "trend200_hold15", "entry": "trend200", "hold": 15, "trail": None},
    {"name": "volume1", "entry": "volume1", "hold": 30, "trail": None},
    {"name": "extension2atr", "entry": "extension2atr", "hold": 30, "trail": None},
    {"name": "trail3_hold15", "entry": "original", "hold": 15, "trail": 3},
]
PROFIT_CANDIDATES: list[dict] = [
    {"name": "baseline", "entry": "original", "hold": 30, "trail": None},
    {"name": "hold15", "entry": "original", "hold": 15, "trail": None},
    {"name": "tp1", "entry": "original", "hold": 30, "trail": None, "target": 1},
    {"name": "tp2", "entry": "original", "hold": 30, "trail": None, "target": 2},
    {"name": "be1", "entry": "original", "hold": 30, "trail": None, "breakeven": 1},
    {"name": "tp1_be1", "entry": "original", "hold": 30, "trail": None, "target": 1, "breakeven": 1},
    {"name": "tp2_be1", "entry": "original", "hold": 30, "trail": None, "target": 2, "breakeven": 1},
    {"name": "tp2_be1_hold15", "entry": "original", "hold": 15, "trail": None, "target": 2, "breakeven": 1},
]
PARTIAL_CANDIDATES: list[dict] = CANDIDATES[:2] + [
    {"name": f"partial1_trail{atr}_hold{hold}", "entry": "original", "hold": hold,
     "trail": atr, "target": 1, "partial": True} for atr in (2, 3) for hold in (30, 15)
]


def accepts(entry: str, f: dict) -> bool:
    if entry == "trend200":
        return f.get("ema200") is not None and f["close"] > f["ema50"] > f["ema200"]
    if entry == "volume1":
        return f.get("volume_ratio20") is not None and f["volume_ratio20"] >= 1
    if entry == "extension2atr":
        return f.get("atr14") is not None and f["close"]-f["ema20"] <= 2*f["atr14"]
    return True


def qualifies(row: dict, controls: list[dict], minimum: int) -> bool:
    return (row["closed"] >= minimum and row["winRate"] is not None
            and row["winRate"] > controls[0]["winRate"]
            and all(row["winRate"] >= c["winRate"] and row["return"] >= c["return"]
                    and row["drawdown"] >= c["drawdown"] for c in controls))


def study(root: Path, profit: bool = False, partial: bool = False) -> Path:
    candidates = PARTIAL_CANDIDATES if partial else PROFIT_CANDIDATES if profit else CANDIDATES
    label = "s1-partial" if partial else "s1-profit" if profit else "s1-robustness"
    payload, quality = build(root)
    if quality["unexplainedAdjustmentChanges"]:
        raise ValueError("UNEXPLAINED_ADJUSTMENT_CHANGE")
    bad = {e["id"] for e in quality["actionIssues"]}
    if any(e["id"] in bad and e.get("effectiveDate", "") >= "2024-02-15"
           for i in range(10) for e in read(root/f"events-{i}.json")["data"]):
        raise ValueError("UNRESOLVED_STUDY_ACTION")
    output = root/label/datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output.mkdir(parents=True, exist_ok=False)
    protocol = {"classification": "EXPLORATORY_REUSED_VALIDATION_AND_TEST", "candidates": candidates,
                "periods": {"validation": ["2024-02-15", "2024-06-28"], "comparison": ["2024-09-04", "2026-10-16"]},
                "slippage": {"base": .001, "stress": .003}, "datasetHash": payload["content_hash"],
                "engineHash": hashlib.sha256(b"".join(p.read_bytes() for p in sorted(Path(__file__).parent.glob("*.py")))).hexdigest(),
                "selection": "At both validation costs: >=8 closed, win rate strictly above baseline and >= hold15, return and drawdown >= BOTH controls; highest minimum validation win rate, then minimum return, then name. Otherwise baseline. Comparison confirmation requires same dominance and >=30 closed at both costs.",
                "priorStudyNewVariants": 18 if partial else 12 if profit else 5, "newVariants": len(candidates)-2}
    if partial:
        protocol["partialSemantics"] = "50% of entry quantity rounded down to 100-share lots at 1R; leave >=100 shares. Activate previous-close ATR trail only from session after partial fill. One-lot positions skip partial and trail whole position after feasible 1R touch. Unfilled partial budget persists across sessions; corporate actions rescale it. EMA50 and maxHold remain. Stop first on ambiguous bars. No risk/position sizing increase."
    if profit:
        protocol["profitSemantics"] = "R=actual entry minus initial stop. Target market trigger sells available board lots with slippage; stop wins ambiguous bars, scheduled exits precede target. BE activates from prior close >= entry+R and estimates remaining net cost including fees/tax/slippage; gaps and ticks can still lose. No same-day activation from high. Corporate actions adjust levels."
    (output/"protocol.json").write_text(json.dumps(protocol, indent=2), encoding="utf8")
    book = feature_book(payload)
    cache: dict[str, tuple] = {}

    def source(day, candidate):
        if day not in cache:
            cache[day] = evaluate(payload, book, day, "S1", BASE)
        state, signals = cache[day]
        return state, [s for s in signals if s["side"] == "LONG" and accepts(candidate["entry"], s["features_used"])]

    results: dict[str, list[dict]] = {}
    selected = "baseline"
    for phase, period in protocol["periods"].items():
        for cost, slippage in protocol["slippage"].items():
            key = f"{phase}_{cost}"
            results[key] = []
            for candidate in candidates:
                config = {**BASE, "maxHold": candidate["hold"], "slippage": slippage}
                if candidate["trail"] is not None:
                    config["s1TrailAtr"] = candidate["trail"]
                for setting, option in (("target", "s1TargetR"), ("breakeven", "s1BreakevenR"), ("partial", "s1PartialTarget")):
                    if setting in candidate:
                        config[option] = candidate[setting]
                r = simulate(payload, config, period[0], period[1], book,
                             signal_source=lambda day: source(day, candidate))
                row = {"name": candidate["name"], "config": config, **summarize(r, payload["calendar"])}
                if partial:
                    partial_trades = [t for t in r["trades"] if t["exit_reason"] == "PARTIAL_TAKE_PROFIT"]
                    row["partialStats"] = {"executions": len(partial_trades),
                                           "positions": len({(t["symbol"], t["entry_date"]) for t in partial_trades}),
                                           "oneLotFallbacks": sum(o["reason"] == "PARTIAL_BELOW_BOARD_LOT" for o in r["orders"]),
                                           "oneLotEntries": sum(o["side"] == "BUY" and o["status"] == "FILLED" and o["quantity"] == 100 for o in r["orders"])}
                results[key].append(row)
                (output/f'{candidate["name"]}-{key}.json').write_text(json.dumps(r, indent=2), encoding="utf8")
                print(json.dumps({"scenario": key, **{k: row[k] for k in ("name", "closed", "winRate", "return", "drawdown")}}), flush=True)
        if phase == "validation":
            eligible = [c["name"] for c in candidates[2:] if all(
                qualifies(next(r for r in results[f"validation_{cost}"] if r["name"] == c["name"]),
                          results[f"validation_{cost}"][:2], 8) for cost in ("base", "stress"))]
            def rank(name):
                rows = [next(r for r in results[f"validation_{cost}"] if r["name"] == name) for cost in ("base", "stress")]
                return (-min(r["winRate"] for r in rows), -min(r["return"] for r in rows), name)
            selected = sorted(eligible, key=rank)[0] if eligible else "baseline"
            (output/"selection.json").write_text(json.dumps({"selected": selected, "eligible": eligible}, indent=2), encoding="utf8")
    confirmed = selected != "baseline" and all(qualifies(
        next(r for r in results[f"comparison_{cost}"] if r["name"] == selected), results[f"comparison_{cost}"][:2], 30)
        for cost in ("base", "stress"))
    report = {**protocol, "selected": selected, "confirmed": confirmed, "results": results,
              "quality": {"missingEligibleBars": quality["testMissingEligibleBars"]}}
    (output/"summary.json").write_text(json.dumps(report, indent=2), encoding="utf8")
    (root/f"latest-{label}.txt").write_text(str(output.resolve()), encoding="utf8")
    print(json.dumps({"output": str(output), "selected": selected, "confirmed": confirmed}), flush=True)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--profit", action="store_true")
    mode.add_argument("--partial", action="store_true")
    args = parser.parse_args()
    study(args.directory, args.profit, args.partial)
