"""Daily event simulator. OPEN fills are approximations; no intraday foresight."""
from decimal import Decimal
import time
from typing import Callable, Any
from .features import feature_book
from .strategies import evaluate
from .risk import RULES, decimal, money, size_order, fill_price
from .metrics import metrics


def validate_config(payload: dict, config: dict) -> None:
    calendar = payload["calendar"]
    fields = ("trainStart", "trainEnd", "validationStart", "validationEnd", "testStart", "testEnd")
    if any(config[k] not in calendar for k in fields):
        raise ValueError("SPLIT_DATE_NOT_IN_CALENDAR")
    indices = [calendar.index(config[k]) for k in fields]
    if not all(a < b for a, b in zip(indices, indices[1:])):
        raise ValueError("OVERLAPPING_SPLITS")
    embargo = config["embargoSessions"]
    if embargo < config["maxHold"] or indices[2]-indices[1]-1 < embargo or indices[4]-indices[3]-1 < embargo:
        raise ValueError("INSUFFICIENT_EMBARGO")
    if config["strategy"] == "S4" and config["maxHold"] not in (5, 10):
        raise ValueError("S4_HOLD_MUST_BE_5_OR_10")
    for name in ("buyFee", "sellFee", "sellTax", "slippage"):
        value = decimal(config[name])
        if not value.is_finite() or not 0 <= value <= Decimal(".03"):
            raise ValueError("INVALID_COST")
    if not 0 < decimal(config["capital"]) <= Decimal("100000000"):
        raise ValueError("INVALID_CAPITAL")


def simulate(payload: dict, config: dict, start: str, end: str, book: dict | None = None,
             progress: Callable[[float], None] | None = None,
             signal_source: Callable | None = None, rules: dict = RULES) -> dict:
    book = book or feature_book(payload)
    calendar = payload["calendar"]
    start_idx, end_idx = calendar.index(start), calendar.index(end)
    bars = {(b["symbol"], b["session_date"]): b for b in payload["bars"]}
    masters = {i["symbol"]: i for i in payload["instruments"]}
    initial = cash = decimal(config["capital"])
    fees = {k: decimal(config[k]) for k in ("buyFee", "sellFee", "sellTax", "slippage")}
    exit_ema = config.get("s1ExitEma", 50)
    if exit_ema not in (20, 50):
        raise ValueError("INVALID_S1_EXIT_EMA")
    trail_atr = config.get("s1TrailAtr")
    if trail_atr is not None and (config["strategy"] != "S1" or trail_atr not in (2, 3)):
        raise ValueError("INVALID_S1_TRAIL_ATR")
    target_r, breakeven_r = config.get("s1TargetR"), config.get("s1BreakevenR")
    partial = config.get("s1PartialTarget", False)
    if partial and (target_r != 1 or trail_atr not in (2, 3) or breakeven_r is not None):
        raise ValueError("INVALID_PARTIAL_TARGET_CONFIG")
    if any(v is not None and (config["strategy"] != "S1" or v not in (1, 2)) for v in (target_r, breakeven_r)):
        raise ValueError("INVALID_S1_PROFIT_RULE")
    positions: dict[str, dict[str, Any]] = {}
    pending: list[tuple[int, Decimal]] = []
    equity: list[dict] = []
    trades: list[dict] = []
    orders: list[dict] = []
    warnings = set(payload["warnings"] + ["OPEN_FILL_APPROXIMATION", "EX_POST_VOLUME_CAP", "TARGET_DISABLED",
                                        "ILLUSTRATIVE_COSTS", "PRICE_INDEX_NOT_TOTAL_RETURN", "FIXED_PARAMETERS_NO_OPTIMIZATION"])
    cash_events: list[dict] = []
    if target_r is not None:
        warnings.discard("TARGET_DISABLED")
        warnings.add("TARGET_MARKET_TRIGGER_ADVERSE_FIRST")
    if breakeven_r is not None:
        warnings.add("BREAKEVEN_ESTIMATED_COSTS_NOT_GUARANTEED")
    peak = initial
    benchmark_base = decimal(bars[("VNINDEX", start)]["open"])
    clock_start = time.monotonic()

    def nav_at(session: str, price_field: str) -> tuple[Decimal, Decimal, dict[str, Decimal]]:
        sectors: dict[str, Decimal] = {}
        gross = Decimal(0)
        for symbol, position in positions.items():
            bar = bars.get((symbol, session))
            price = decimal(bar[price_field]) if bar else position["last"]
            if not bar:
                warnings.add("STALE_OR_DELISTED_HOLDING_MARK")
            value = price*position["qty"]
            gross += value
            sector = masters[symbol]["sector"]
            sectors[sector] = sectors.get(sector, Decimal(0)) + value
        return cash + sum((amount for _, amount in pending), Decimal(0)) + gross, gross, sectors

    for idx in range(start_idx, end_idx+1):
        session = calendar[idx]
        if time.monotonic()-clock_start > 120:
            raise TimeoutError("BACKTEST_RUNTIME_LIMIT")
        if progress and (idx-start_idx) % 10 == 0:
            progress((idx-start_idx)/max(1, end_idx-start_idx))
        settled = sum((amount for day, amount in pending if day <= idx), Decimal(0))
        cash += settled
        if settled:
            cash_events.append({"session": session, "kind": "SETTLEMENT", "amount": str(settled)})
        pending = [(day, amount) for day, amount in pending if day > idx]
        if breakeven_r is not None and idx:
            for symbol, position in positions.items():
                prior = book.get(symbol, {}).get(calendar[idx-1], {})
                if prior.get("raw_close", 0) >= position["be_trigger"]:
                    # Previous close activates protection for today, never retroactively.
                    unit_cost = (position["cost"]-position.get("income", Decimal(0)))/position["qty"]
                    level = unit_cost/((1-fees["sellFee"]-fees["sellTax"])*(1-fees["slippage"]))
                    position["stop"] = max(position["stop"], level)
        # Ratchet using only the previous session, before today's action adjustment.
        if trail_atr is not None and idx:
            for symbol, position in positions.items():
                if partial and not position["runner_active"]:
                    continue
                prior = book.get(symbol, {}).get(calendar[idx-1], {})
                if prior.get("atr14") is not None and prior.get("factor", 0) > 0:
                    candidate_stop = (decimal(prior["close"])-decimal(trail_atr)*decimal(prior["atr14"]))/decimal(prior["factor"])
                    position["stop"] = max(position["stop"], candidate_stop)
        for event in payload.get("actions", []):
            if event["ex_date"] != session or event["symbol"] not in positions:
                continue
            if event["known_at"][:10] > session:
                raise ValueError("ACTION_NOT_KNOWN_AT_DECISION")
            position = positions[event["symbol"]]
            if event["type"] == "STOCK_DIVIDEND":
                # Entitlements have value at ex-date but cannot be sold before listing.
                ratio = decimal(event["ratio"])
                if ratio <= 0:
                    raise ValueError("INVALID_STOCK_DIVIDEND")
                entitled = position["qty"] * ratio
                bonus = int(entitled)
                if entitled != bonus:
                    warnings.add("FRACTIONAL_BONUS_ROUNDED_DOWN")
                available = event.get("available_date")
                release = next((j for j, d in enumerate(calendar) if available and d >= available), len(calendar)+1)
                if not available:
                    warnings.add("BONUS_AVAILABILITY_UNKNOWN_LOCKED_TO_END")
                position.setdefault("locks", []).append((release, bonus))
                old_qty = position["qty"]
                position["qty"] += bonus
                position["entry"] *= decimal(old_qty)/position["qty"]
                position["stop"] /= 1+ratio
                position["last"] /= 1+ratio
                for key in ("target", "be_trigger"):
                    if key in position:
                        position[key] /= 1+ratio
                if partial:
                    position["partial_remaining"] = int(position["partial_remaining"]*(1+ratio)) // rules["board_lot"]*rules["board_lot"]
                cash_events.append({"session": session, "kind": "STOCK_DIVIDEND_LOCKED", "symbol": event["symbol"],
                                    "quantity": bonus, "available_date": available})
                warnings.add("STOCK_DIVIDEND_DISPOSAL_TAX_NOT_MODELED")
                continue
            if event["type"] == "RIGHTS_ISSUE":
                # No automatic subscription or invented sale proceeds for unquoted rights.
                warnings.add("RIGHTS_NOT_EXERCISED_VALUE_ZERO")
                continue
            if event["type"] == "SPLIT":
                ratio = decimal(event["ratio"])
                new_quantity = position["qty"]*ratio
                if ratio <= 0 or new_quantity != new_quantity.to_integral_value():
                    raise ValueError("UNSUPPORTED_FRACTIONAL_CORPORATE_ACTION")
                position["qty"] = int(new_quantity)
                position["stop"] /= ratio
                position["last"] /= ratio
                position["entry"] /= ratio
                for key in ("target", "be_trigger"):
                    if key in position:
                        position[key] /= ratio
                if partial:
                    position["partial_remaining"] = int(position["partial_remaining"]*ratio) // rules["board_lot"]*rules["board_lot"]
            elif event["type"] == "CASH_DIVIDEND":
                if event["payable_date"] < session:
                    raise ValueError("UNVERIFIED_DIVIDEND_PAYABLE_DATE")
                amount = money(decimal(event["cash_amount"])*position["qty"]*(1-decimal(event.get("withholding_rate", 0))))
                payable_idx = next((j for j, d in enumerate(calendar) if d >= event["payable_date"]), len(calendar)+1)
                position["income"] = position.get("income", Decimal(0)) + amount
                if event.get("adjust_stop"):
                    position["stop"] = max(Decimal(".01"), position["stop"]-decimal(event["cash_amount"]))
                    for key in ("target", "be_trigger"):
                        if key in position:
                            position[key] = max(Decimal(".01"), position[key]-decimal(event["cash_amount"]))
                if payable_idx == idx:
                    cash += amount
                else:
                    pending.append((payable_idx, amount))
                cash_events.append({"session": session, "kind": "DIVIDEND_RECEIVABLE", "amount": str(amount)})
            else:
                raise ValueError("UNSUPPORTED_CORPORATE_ACTION")
        previous = calendar[idx-1] if idx else None
        state, signals = (signal_source(previous) if signal_source and previous else
                          evaluate(payload, book, previous, config["strategy"],
                                   {"minLiquidity": config["minLiquidity"], "maxHold": config["maxHold"]})
                          if previous else ({"riskMultiplier": 0}, []))
        # Exit only settled stock. Stop wins when daily OHLC cannot resolve ordering.
        for symbol, position in list(positions.items()):
            bar = bars.get((symbol, session))
            if not bar or idx < position["sellable"]:
                continue
            prior_feature = book.get(symbol, {}).get(previous, {}) if previous else {}
            exit_key = f"ema{exit_ema}"
            strategy_exit = config["strategy"] == "S1" and prior_feature.get(exit_key) is not None and prior_feature["close"] < prior_feature[exit_key]
            stop_hit = decimal(bar["low"]) <= position["stop"]
            held_exit = idx-position["bought"] > config["maxHold"]
            target_hit = "target" in position and decimal(bar["high"]) >= position["target"]
            if not (stop_hit or strategy_exit or held_exit or target_hit):
                continue
            target_exit = target_hit and not (stop_hit or strategy_exit or held_exit)
            fill_bar = {**bar, "open": str(max(decimal(bar["open"]), position["target"]))} if target_exit else bar
            price, reason, reference = fill_price(fill_bar, "SELL", fees["slippage"], rules, position["stop"] if stop_hit else None)
            capacity = int(decimal(bar["volume"])*decimal(rules["participation"])) // rules["board_lot"]*rules["board_lot"]
            locked = sum(q for release, q in position.get("locks", []) if release > idx)
            available_qty = max(0, position["qty"]-locked)
            quantity = min(available_qty, capacity)
            if partial and target_exit:
                position["partial_remaining"] = min(position["partial_remaining"], max(0, position["qty"]-rules["board_lot"]) // rules["board_lot"]*rules["board_lot"])
                quantity = min(quantity, position["partial_remaining"], max(0, position["qty"]-rules["board_lot"]))
                quantity = quantity // rules["board_lot"]*rules["board_lot"]
                if position["partial_remaining"] == 0 and price is not None and available_qty >= rules["board_lot"]:
                    # One-lot positions cannot be halved; keep all and trail from tomorrow.
                    position["runner_active"] = True
                    del position["target"]
                    warnings.add("PARTIAL_BELOW_BOARD_LOT_TRAIL_WHOLE_POSITION")
            if position.get("locks"):
                quantity = quantity // rules["board_lot"] * rules["board_lot"]
                if available_qty % rules["board_lot"]:
                    warnings.add("ODD_LOT_RESIDUAL_MARKED_NOT_SOLD")
            order = {"session_date": session, "decision_date": previous, "symbol": symbol, "side": "SELL",
                     "status": "NO_FILL", "reason": reason, "quantity": 0, "price": None, "fee": "0", "tax": "0", "slippage_cost": "0"}
            if price is not None and quantity:
                notional = price*quantity
                fee, tax = money(notional*fees["sellFee"]), money(notional*fees["sellTax"])
                proceeds = notional-fee-tax
                settle_idx = idx+rules["settlement_sessions"]+rules["availability_offset_sessions"]
                pending.append((settle_idx, proceeds))
                cost = position["cost"]*quantity/position["qty"]
                allocated_income = position.get("income", Decimal(0))*quantity/position["qty"]
                pnl = money(proceeds-cost+allocated_income)
                trades.append({"symbol": symbol, "entry_date": calendar[position["bought"]], "exit_date": session,
                               "quantity": quantity, "entry_price": str(position["entry"]), "exit_price": str(price),
                               "pnl": str(pnl), "fee": str(fee), "tax": str(tax), "dividend_income": str(money(allocated_income)),
                               "exit_reason": "STOP" if stop_hit else f"EMA{exit_ema}" if strategy_exit else "MAX_HOLD" if held_exit else "PARTIAL_TAKE_PROFIT" if partial else "TAKE_PROFIT",
                               "cash_available_at": calendar[settle_idx] if settle_idx < len(calendar) else None})
                order.update(status="FILLED", reason=trades[-1]["exit_reason"], quantity=quantity, price=str(price),
                             fee=str(fee), tax=str(tax), slippage_cost=str(abs(price-reference)*quantity))
                position["cost"] -= cost
                position["income"] = position.get("income", Decimal(0))-allocated_income
                position["qty"] -= quantity
                if partial and target_exit:
                    position["partial_remaining"] -= quantity
                    position["runner_active"] = True
                    if not position["partial_remaining"]:
                        del position["target"]
                if not position["qty"]:
                    del positions[symbol]
            elif not quantity:
                order["reason"] = "SHARES_NOT_AVAILABLE" if not available_qty else "ODD_LOT_NOT_EXECUTABLE" if available_qty < rules["board_lot"] else "VOLUME_CAP"
                if partial and target_exit and not position["partial_remaining"] and "target" not in position:
                    order["reason"] = "PARTIAL_BELOW_BOARD_LOT"
            orders.append(order)
        new_entries = 0
        for signal in sorted((s for s in signals if s["side"] == "LONG"), key=lambda s: (-s["score"], s["symbol"])):
            symbol = signal["symbol"]
            if symbol in positions:
                continue
            bar = bars.get((symbol, session))
            if not bar:
                continue
            price, reason, reference = fill_price(bar, "BUY", fees["slippage"], rules)
            quantity = 0
            nav, gross, sectors = nav_at(session, "open")
            if len(positions) >= rules["max_positions"] or new_entries >= rules["max_daily_entries"]:
                reason = "POSITION_OR_DAILY_ENTRY_CAP"
            elif signal["decision_date"] >= session:
                raise ValueError("SAME_BAR_SIGNAL_FILL_FORBIDDEN")
            elif price is not None:
                quantity, reason = size_order(nav, cash, gross, sectors.get(masters[symbol]["sector"], Decimal(0)),
                                              price, decimal(signal["invalidation_price"]), fees["buyFee"],
                                              decimal(state["riskMultiplier"]), rules)
                cap = int(decimal(bar["volume"])*decimal(rules["participation"])) // rules["board_lot"]*rules["board_lot"]
                quantity = min(quantity, cap)
                if not quantity and reason == "OK":
                    reason = "VOLUME_CAP"
            order = {"session_date": session, "decision_date": signal["decision_date"], "symbol": symbol, "side": "BUY",
                     "status": "NO_FILL", "reason": reason, "quantity": 0, "price": None, "fee": "0", "tax": "0", "slippage_cost": "0"}
            if quantity and price is not None:
                notional = price*quantity
                fee = money(notional*fees["buyFee"])
                cash -= notional+fee
                if cash < 0:
                    raise ArithmeticError("NEGATIVE_BUYING_POWER")
                positions[symbol] = {"qty": quantity, "bought": idx, "sellable": idx+rules["settlement_sessions"]+rules["availability_offset_sessions"],
                                     "entry": price, "cost": notional+fee, "stop": decimal(signal["invalidation_price"]),
                                     "last": price}
                initial_risk = price-decimal(signal["invalidation_price"])
                if target_r is not None:
                    positions[symbol]["target"] = price+decimal(target_r)*initial_risk
                if partial:
                    positions[symbol]["partial_remaining"] = quantity // (2*rules["board_lot"])*rules["board_lot"]
                    positions[symbol]["runner_active"] = False
                if breakeven_r is not None:
                    positions[symbol]["be_trigger"] = price+decimal(breakeven_r)*initial_risk
                new_entries += 1
                order.update(status="FILLED", reason="NEXT_SESSION_OPEN", quantity=quantity, price=str(price),
                             fee=str(fee), slippage_cost=str(abs(price-reference)*quantity))
            orders.append(order)
        for symbol, position in positions.items():
            if (symbol, session) in bars:
                position["last"] = decimal(bars[(symbol, session)]["close"])
        nav, gross, _ = nav_at(session, "close")
        peak = max(peak, nav)
        benchmark = money(initial*decimal(bars[("VNINDEX", session)]["close"])/benchmark_base)
        equity.append({"session_date": session, "nav": str(money(nav)), "cash": str(money(cash)),
                       "pending_cash": str(money(sum((a for _, a in pending), Decimal(0)))),
                       "holdings_value": str(money(gross)), "exposure": float(gross/nav) if nav else 0,
                       "drawdown": float(nav/peak-1), "benchmark": str(benchmark),
                       "positions": len(positions)})
    if positions:
        warnings.add("OPEN_POSITIONS_MARKED_NOT_LIQUIDATED")
    if len(trades) < 30:
        warnings.add("SMALL_TRADE_SAMPLE")
    return {"equity": equity, "trades": trades, "orders": orders, "metrics": metrics(equity, trades, orders, float(initial)),
            "warnings": sorted(warnings), "cash_events": cash_events,
            "open_positions": {s: {k: str(v) if isinstance(v, Decimal) else v for k, v in p.items()} for s, p in positions.items()}}
