from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
from typing import Any, Protocol


class MockProviderError(Exception):
    def __init__(self, code: str, retry_after: float | None = None):
        super().__init__(code)
        self.code = code
        self.retry_after = retry_after


class MarketDataProvider(Protocol):
    name: str
    is_demo: bool

    def fetch(self) -> dict[str, Any]: ...


@dataclass(frozen=True)
class Bar:
    symbol: str
    exchange: str
    session_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    traded_value: Decimal
    revision: str
    observed_at: datetime
    is_final: bool
    kind: str


def normalize(row: dict[str, Any]) -> Bar:
    try:
        prices = [Decimal(str(row[key])) for key in ("open", "high", "low", "close")]
        value = Decimal(str(row["traded_value"]))
        volume = Decimal(str(row["volume"]))
    except (InvalidOperation, KeyError, ValueError) as exc:
        raise ValueError("INVALID_NUMERIC") from exc
    if not all(x.is_finite() for x in [*prices, value, volume]):
        raise ValueError("INVALID_NUMERIC")
    o, h, low, c = prices
    if low <= 0 or h < max(o, c) or low > min(o, c) or h < low:
        raise ValueError("INVALID_OHLC")
    if volume < 0 or volume != volume.to_integral_value() or value < 0:
        raise ValueError("INVALID_VOLUME_VALUE")
    observed = datetime.fromisoformat(row["observed_at"])
    if observed.tzinfo is None:
        raise ValueError("TIMEZONE_REQUIRED")
    if row["exchange"] not in ("HOSE", "HNX") or row["kind"] not in ("stock", "index"):
        raise ValueError("UNSUPPORTED_INSTRUMENT")
    if type(row["is_final"]) is not bool:
        raise ValueError("INVALID_FINAL_FLAG")
    if not row["revision"] or not row["symbol"]:
        raise ValueError("MISSING_PROVENANCE")
    return Bar(row["symbol"], row["exchange"], date.fromisoformat(row["session_date"]),
               o, h, low, c, int(volume), value, row["revision"], observed, row["is_final"], row["kind"])


class FixtureProvider:
    name = "fixture"
    is_demo = True

    def __init__(self, path: Path):
        self.path = path

    def fetch(self) -> dict[str, Any]:
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if payload.get("classification") != "DEMO":
            raise ValueError("FIXTURE_MUST_BE_DEMO")
        return payload


def classify(bars: list[Bar], expected: set[str]) -> tuple[str, list[str]]:
    reasons = []
    if not any(b.kind == "index" and b.symbol == "VNINDEX" and b.is_final for b in bars):
        reasons.append("MISSING_BENCHMARK")
    present = {b.symbol for b in bars if b.kind == "stock"}
    if expected - present:
        reasons.append("MISSING_SYMBOLS")
    if any(not b.is_final for b in bars):
        reasons.append("NON_FINAL_BARS")
    return ("PARTIAL" if reasons else "COMPLETE"), reasons
