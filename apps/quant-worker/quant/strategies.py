import math
from .features import active, regime


def percentile(values: dict[str, float]) -> dict[str, float]:
    ordered = sorted(values, key=lambda symbol: (values[symbol], symbol))
    return {symbol: 100 * i / max(1, len(ordered)-1) if len(ordered) > 1 else 100
            for i, symbol in enumerate(ordered)}


def evaluate(payload: dict, book: dict, session: str, code: str, config: dict) -> tuple[dict, list[dict]]:
    state = regime(payload, book, session)
    index = book.get("VNINDEX", {}).get(session, {})
    position = payload["calendar"].index(session)
    earliest = payload["calendar"][position+1] if position+1 < len(payload["calendar"]) else None
    rows, eligible = [], {}
    for instrument in active(payload, session):
        symbol = instrument["symbol"]
        f = dict(book.get(symbol, {}).get(session, {}))
        reasons = []
        if not f:
            reasons.append("MISSING_BAR")
        else:
            for period in (20, 60):
                f[f"rel{period}"] = (f[f"ret{period}"] - index[f"ret{period}"]
                                     if f[f"ret{period}"] is not None and index.get(f"ret{period}") is not None else None)
            warmup = {"S1": 130, "S2": 60, "S3": 220, "S4": 200}[code]
            if f["n"] < warmup or f["rel20"] is None or f["rel60"] is None:
                reasons.append("INSUFFICIENT_WARMUP")
            if f["median_value20"] is None or f["median_value20"] < config["minLiquidity"]:
                reasons.append("LOW_LIQUIDITY")
            if not f["is_final"] or f["halted"] or not f["volume"]:
                reasons.append("NOT_TRADABLE")
            if state["regime"] == "UNKNOWN":
                reasons.append("UNKNOWN_REGIME")
            if not reasons:
                conditions = {
                    "S1": f["close"] > f["ema50"] and f["ema50_slope10"] > 0 and f["ret60"] > 0,
                    "S2": f["close"] > f["high_20_prev"] * 1.002 and (f["volume_ratio20"] or 0) >= 1.5 and f["close"] > f["ema50"],
                    "S3": (f["ema200"] is not None and f["ema20"] > f["ema50"] > f["ema200"] and
                           f["ema50_slope20"] > 0 and -.01 <= f["close"]/f["ema20"]-1 <= .02 and
                           40 <= f["rsi14"] <= 60 and f["rising_close"] and f["raw_bullish"] and f["rel60"] > 0),
                    "S4": (f["ema200"] is not None and f["close"] > f["ema200"] and
                           f["negative_run5"] >= 3 and f["rsi14"] < 35 and state["regime"] in ("RISK_ON", "NEUTRAL")),
                }
                if not conditions[code]:
                    reasons.append("STRATEGY_CONDITIONS_NOT_MET")
                else:
                    eligible[symbol] = f
        stop = None
        if f and f.get("atr14"):
            stop = (min(f["low"] if code == "S2" else f["low5"], f["close"] - 2*f["atr14"]) if code != "S3" else
                    max(f["low5"], f["close"] - 2*f["atr14"])) / f["factor"]
            if not 0 < stop < f["raw_close"] or (f["raw_close"] - stop)/f["raw_close"] > .2:
                reasons.append("INVALID_STOP")
                eligible.pop(symbol, None)
        rows.append({"symbol": symbol, "exchange": instrument["exchange"], "sector": instrument["sector"],
                     "strategy_code": code, "side": "NONE", "score": None, "features_used": f,
                     "reasons": reasons, "invalidation_price": stop, "decision_date": session,
                     "earliest_trade_date": earliest, "quality_flags": payload["warnings"] +
                     (["EXPERIMENTAL"] if code == "S4" else []), "hold_sessions": config["maxHold"]})
    components: list[dict] = []
    if eligible:
        if code == "S1":
            components = [percentile({s: f[k] for s, f in eligible.items()}) for k in ("rel60", "rel20")]
            components += [percentile({s: -f["vol20"] for s, f in eligible.items()})]
            weights = [.5, .3, .2]
        elif code == "S2":
            components = [percentile({s: min(.15, f["close"]/f["high_20_prev"]-1) for s, f in eligible.items()}),
                          percentile({s: f["volume_ratio20"] for s, f in eligible.items()}),
                          percentile({s: f["rel20"] for s, f in eligible.items()})]
            weights = [.4, .3, .3]
        elif code == "S3":
            components = [percentile({s: f["ema50"]/f["ema200"]-1 for s, f in eligible.items()}),
                          percentile({s: -abs(f["close"]/f["ema20"]-1) for s, f in eligible.items()}),
                          percentile({s: f["rel60"] for s, f in eligible.items()})]
            weights = [.4, .3, .3]
        else:
            components = [percentile({s: -f["rsi14"] for s, f in eligible.items()}),
                          percentile({s: 1-f["close"]/f["ema20"] for s, f in eligible.items()}),
                          percentile({s: f["rel60"] for s, f in eligible.items()})]
            weights = [.4, .3, .3]
        for row in rows:
            symbol = row["symbol"]
            if symbol in eligible:
                row["sub_scores"] = [p[symbol] for p in components]
                row["score"] = round(sum(w*p[symbol] for w, p in zip(weights, components)), 6)
        ranked = sorted((r for r in rows if r["score"] is not None), key=lambda r: (-r["score"], r["symbol"]))
        for rank, row in enumerate(ranked, 1):
            row["rank"] = rank
            if code == "S1" and (rank > math.ceil(len(ranked)*.15) or row["score"] < 70):
                row["reasons"].append("BELOW_S1_SELECTION_THRESHOLD")
            if code in ("S1", "S4") and state["regime"] not in ("RISK_ON", "NEUTRAL"):
                row["reasons"].append("REGIME_BLOCKED")
            if not row["reasons"]:
                row["side"] = "LONG"
    for row in rows:
        row["actionable"] = row["side"] == "LONG" and state["riskMultiplier"] > 0 and earliest is not None and code != "S4"
        row["evidence"] = {k: row["features_used"].get(k) for k in
                           ("source_date", "observed_at", "rel60", "ema50", "rsi14", "volume_ratio20", "median_value20")}
    return state, rows
