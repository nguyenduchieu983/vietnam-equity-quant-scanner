"""Causal indicators. Floats only for analytics; execution/accounting use Decimal."""
import hashlib
import math
from pathlib import Path
import statistics

FEATURE_VERSION = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def ema(values: list[float], period: int) -> list[float | None]:
    result: list[float | None] = [None] * len(values)
    if len(values) < period:
        return result
    current = statistics.mean(values[:period])
    result[period - 1] = current
    alpha = 2 / (period + 1)
    for i in range(period, len(values)):
        current += alpha * (values[i] - current)
        result[i] = current
    return result


def features(bars: list[dict]) -> dict[str, dict]:
    if [b["session_date"] for b in bars] != sorted({b["session_date"] for b in bars}):
        raise ValueError("UNSORTED_OR_DUPLICATE_SERIES")
    closes = [float(b["close"]) * float(b["factor"]) for b in bars]
    highs = [float(b["high"]) * float(b["factor"]) for b in bars]
    lows = [float(b["low"]) * float(b["factor"]) for b in bars]
    e20, e50, e200 = (ema(closes, p) for p in (20, 50, 200))
    tr = [highs[i] - lows[i] if i == 0 else max(highs[i] - lows[i], abs(highs[i] - closes[i-1]),
                                               abs(lows[i] - closes[i-1])) for i in range(len(bars))]
    atr = None
    gain = loss = None
    output = {}
    for i, bar in enumerate(bars):
        if i == 13:
            atr = statistics.mean(tr[:14])
        elif i > 13:
            atr = (atr * 13 + tr[i]) / 14  # type: ignore[operator]
        if i == 14:
            changes = [closes[j] - closes[j-1] for j in range(1, 15)]
            gain = statistics.mean(max(0, x) for x in changes)
            loss = statistics.mean(max(0, -x) for x in changes)
        elif i > 14:
            change = closes[i] - closes[i-1]
            gain = (gain * 13 + max(0, change)) / 14  # type: ignore[operator]
            loss = (loss * 13 + max(0, -change)) / 14  # type: ignore[operator]
        rsi = None if gain is None else (50 if gain == 0 and loss == 0 else
                                        100 if loss == 0 else 100 - 100 / (1 + gain / loss))  # type: ignore[operator]
        previous_volumes = [b["volume"] for b in bars[max(0, i-20):i]]
        mean_volume = statistics.mean(previous_volumes) if len(previous_volumes) == 20 else 0
        run = longest = 0
        for j in range(max(1, i-4), i+1):
            run = run + 1 if closes[j] < closes[j-1] else 0
            longest = max(longest, run)
        f = {
            "n": i+1, "close": closes[i], "low": lows[i], "raw_close": float(bar["close"]), "factor": float(bar["factor"]),
            "ema20": e20[i], "ema50": e50[i], "ema200": e200[i],
            "sma20": statistics.mean(closes[i-19:i+1]) if i >= 19 else None,
            "ema50_slope10": e50[i] - e50[i-10] if i >= 59 else None,  # type: ignore[operator]
            "ema50_slope20": e50[i] - e50[i-20] if i >= 69 else None,  # type: ignore[operator]
            "high_20_prev": max(highs[i-20:i]) if i >= 20 else None,
            "low_20_prev": min(lows[i-20:i]) if i >= 20 else None,
            "low5": min(lows[max(0, i-4):i+1]), "atr14": atr, "rsi14": rsi,
            "volume_ratio20": bar["volume"] / mean_volume if mean_volume > 0 else None,
            "median_value20": statistics.median(float(b["traded_value"]) for b in bars[i-19:i+1]) if i >= 19 else None,
            "vol20": statistics.stdev(math.log(closes[j]/closes[j-1]) for j in range(i-19, i+1)) * math.sqrt(252) if i >= 20 else None,
            "price_to_52w_high": closes[i] / max(highs[i-251:i+1]) if i >= 251 else None,
            "negative_run5": longest, "raw_bullish": float(bar["close"]) > float(bar["open"]),
            "rising_close": i > 0 and float(bar["close"]) > float(bars[i-1]["close"]),
            "source_date": bar["session_date"], "observed_at": bar["observed_at"],
            "is_final": bar["is_final"], "halted": bar.get("halted", False), "volume": bar["volume"],
        }
        for period in (5, 20, 60, 120):
            f[f"ret{period}"] = closes[i]/closes[i-period]-1 if i >= period else None
        output[bar["session_date"]] = f
    return output


def feature_book(payload: dict) -> dict[str, dict[str, dict]]:
    grouped: dict[str, list[dict]] = {}
    for row in payload["bars"]:
        grouped.setdefault(row["symbol"], []).append(row)
    return {symbol: features(sorted(bars, key=lambda b: b["session_date"])) for symbol, bars in grouped.items()}


def active(payload: dict, session: str) -> list[dict]:
    return [i for i in payload["instruments"] if i["type"] == "COMMON_STOCK" and
            i["known_at"] <= session and i["listed_at"] <= session and
            (not i["delisted_at"] or session < i["delisted_at"])]


def regime(payload: dict, book: dict, session: str) -> dict:
    index = book.get("VNINDEX", {}).get(session)
    universe = active(payload, session)
    values = [book.get(i["symbol"], {}).get(session) for i in universe]
    eligible = [f for f in values if f and f["ema50"] is not None and f["n"] >= 60 and
                not f["halted"] and f["median_value20"] is not None and f["median_value20"] >= 5e9]
    if not index or index["ema50_slope10"] is None or not eligible or len(eligible) < len(universe) * .5:
        return {"regime": "UNKNOWN", "riskMultiplier": 0, "breadth50": None, "reasons": ["INSUFFICIENT_INDEX_OR_BREADTH"]}
    breadth50 = sum(f["close"] > f["ema50"] for f in eligible)/len(eligible)
    breadth20 = sum(f["close"] > f["ema20"] for f in eligible)/len(eligible)
    state = ("RISK_ON" if index["close"] > index["ema50"] and index["ema50_slope10"] > 0 and breadth50 >= .55 else
             "RISK_OFF" if index["close"] < index["ema50"] and breadth50 < .40 else "NEUTRAL")
    return {"regime": state, "riskMultiplier": {"RISK_ON": 1, "NEUTRAL": .5, "RISK_OFF": 0}[state],
            "breadth50": breadth50, "breadth20": breadth20, "eligible": len(eligible),
            "indexClose": index["close"], "indexEMA50": index["ema50"], "indexSlope10": index["ema50_slope10"],
            "source_date": session}
