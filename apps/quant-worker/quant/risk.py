from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
import json
from .db import ROOT

RULES = json.loads((ROOT / "packages/config/research-rules.json").read_text())


def decimal(value) -> Decimal:
    return Decimal(str(value))


def money(value: Decimal) -> Decimal:
    return value.quantize(Decimal(".01"))


def tick_price(price: Decimal, exchange: str, side: str, session: str, rules: dict = RULES) -> Decimal:
    if not rules["effective_from"] <= session < rules["effective_to"] or exchange not in rules["ticks"]:
        raise ValueError("NO_EFFECTIVE_MARKET_RULES")
    # Round across tier boundaries until the resulting price conforms to its own tier.
    for _ in range(3):
        tick = next(decimal(t["tick"]) for t in rules["ticks"][exchange]
                    if t["below"] is None or price < decimal(t["below"]))
        adjusted = (price/tick).to_integral_value(rounding=ROUND_CEILING if side == "BUY" else ROUND_FLOOR)*tick
        if adjusted == price:
            break
        price = adjusted
    return price


def size_order(nav: Decimal, cash: Decimal, gross: Decimal, sector: Decimal,
               entry: Decimal, stop: Decimal, buy_fee: Decimal, multiplier: Decimal,
               rules: dict = RULES) -> tuple[int, str]:
    if entry <= stop or stop <= 0:
        return 0, "INVALID_STOP"
    if multiplier <= 0:
        return 0, "REGIME_BLOCKED"
    budgets = [
        nav*decimal(rules["risk_per_trade"])*multiplier/(entry-stop),
        nav*decimal(rules["position_cap"])/entry,
        max(Decimal(0), nav*decimal(rules["gross_cap"])-gross)/entry,
        max(Decimal(0), nav*decimal(rules["sector_cap"])-sector)/entry,
        max(Decimal(0), cash-nav*decimal(rules["cash_reserve"]))/(entry*(1+buy_fee)),
    ]
    lot = rules["board_lot"]
    quantity = int(min(budgets)) // lot * lot
    return quantity, "OK" if quantity else "NOT_AFFORDABLE"


def fill_price(bar: dict, side: str, slippage: Decimal, rules: dict = RULES,
               stop_price: Decimal | None = None) -> tuple[Decimal | None, str, Decimal]:
    opening = decimal(bar["open"])
    if bar.get("halted") or bar["volume"] <= 0 or not bar["is_final"]:
        return None, "HALT_OR_NO_VOLUME", opening
    floor, ceiling = decimal(bar["floor"]), decimal(bar["ceiling"])
    if (side == "BUY" and opening >= ceiling) or (side == "SELL" and opening <= floor):
        return None, "LIMIT_NO_FILL", opening
    reference = min(opening, stop_price) if stop_price is not None else opening
    price = tick_price(reference*(1+slippage if side == "BUY" else 1-slippage),
                       bar["exchange"], side, bar["session_date"], rules)
    if not max(floor, decimal(bar["low"])) <= price <= min(ceiling, decimal(bar["high"])):
        return None, "PRICE_OUTSIDE_OBSERVED_RANGE", reference
    return price, "FILLED", reference
