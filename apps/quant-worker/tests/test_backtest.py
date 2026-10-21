import copy
import unittest
from decimal import Decimal as D
from quant.backtest import simulate, validate_config
from quant.risk import tick_price, size_order, fill_price
from quant.history import demo_history
from quant.metrics import walk_forward


class BacktestTests(unittest.TestCase):
    def setUp(self):
        self.days = [f"2024-01-{i:02}" for i in range(1, 13)]
        self.payload = {"calendar": self.days, "warnings": [], "actions": [],
                        "instruments": [{"symbol": "SIM", "sector": "X"}], "bars": []}
        for date in self.days:
            for symbol in ("SIM", "VNINDEX"):
                self.payload["bars"].append({"symbol": symbol, "session_date": date, "exchange": "HOSE",
                                             "open": "10000", "high": "11000", "low": "9000", "close": "10000",
                                             "floor": "8000", "ceiling": "12000", "volume": 100000,
                                             "is_final": True, "factor": "1"})
        self.config = {"capital": 50000000, "strategy": "S2", "maxHold": 1, "minLiquidity": 0,
                       "buyFee": .0015, "sellFee": .0015, "sellTax": .001, "slippage": 0}
        self.book = {"SIM": {}}

    def signal(self, day):
        return {"riskMultiplier": 1}, ([{"symbol": "SIM", "side": "LONG", "score": 90,
                                        "decision_date": day, "invalidation_price": 8000}]
                                       if day == self.days[0] else [])

    def run_sim(self, payload=None, config=None):
        return simulate(payload or self.payload, config or self.config, self.days[1], self.days[-1],
                        self.book, signal_source=self.signal)

    def test_exact_settlement_fees_and_nav(self):
        r = self.run_sim()
        buy, sell = r["orders"]
        self.assertEqual(buy["quantity"], 100)  # 250k risk / 2k stop, rounded lot
        self.assertEqual(buy["session_date"], self.days[1])
        self.assertEqual(sell["session_date"], self.days[4])  # T+2 EOD; next open
        self.assertEqual(sell["tax"], "1000.00")
        self.assertEqual(r["trades"][0]["pnl"], "-4000.00")
        self.assertEqual(r["equity"][-1]["nav"], "49996000.00")
        self.assertEqual(r["equity"][3]["pending_cash"], "997500.00")
        self.assertEqual(r["equity"][6]["pending_cash"], "0.00")
        self.assertEqual(r["equity"][6]["cash"], "49996000.00")
        for row in r["equity"]:
            self.assertEqual(D(row["nav"]), D(row["cash"])+D(row["pending_cash"])+D(row["holdings_value"]))

    def test_same_bar_signal_rejected(self):
        def bad(day):
            state, signals = self.signal(day)
            for signal in signals:
                signal["decision_date"] = self.days[1]
            return state, signals
        with self.assertRaisesRegex(ValueError, "SAME_BAR"):
            simulate(self.payload, self.config, self.days[1], self.days[-1], self.book, signal_source=bad)

    def test_research_ema20_exit_uses_previous_session_and_preserves_default(self):
        self.book["SIM"][self.days[4]] = {"close": 10000, "ema20": 10100, "ema50": 9000}
        config = {**self.config, "strategy": "S1", "maxHold": 30}
        self.assertEqual(self.run_sim(config=config)["trades"], [])
        result = self.run_sim(config={**config, "s1ExitEma": 20})
        self.assertEqual(len(result["trades"]), 1)
        self.assertEqual(result["trades"][0]["exit_date"], self.days[5])
        self.assertEqual(result["trades"][0]["exit_reason"], "EMA20")
        self.book["SIM"][self.days[6]] = {"close": 1, "ema20": 20000, "ema50": 20000}
        changed = self.run_sim(config={**config, "s1ExitEma": 20})
        self.assertEqual(result["trades"], changed["trades"])

    def test_trailing_stop_is_causal_ratchets_and_adjusts_for_split(self):
        config = {**self.config, "strategy": "S1", "maxHold": 30, "s1TrailAtr": 3}
        self.book["SIM"][self.days[3]] = {"close": 11000, "atr14": 500, "factor": 1}
        self.book["SIM"][self.days[4]] = {"close": 10500, "atr14": 500, "factor": 1}
        for bar in self.payload["bars"]:
            if bar["symbol"] == "SIM" and bar["session_date"] == self.days[4]:
                bar["low"] = "9800"
        result = self.run_sim(config=config)
        self.assertEqual(result["trades"][0]["exit_date"], self.days[5])
        self.assertEqual(result["trades"][0]["exit_price"], "9500")
        # The falling prior close must not loosen the stop from 9500 to 9000.
        self.book["SIM"][self.days[6]] = {"close": 20000, "atr14": 1, "factor": 1}
        self.assertEqual(result["trades"], self.run_sim(config=config)["trades"])
        payload = copy.deepcopy(self.payload)
        payload["actions"] = [{"symbol": "SIM", "type": "SPLIT", "ratio": 2,
                               "ex_date": self.days[5], "known_at": self.days[0]}]
        for bar in payload["bars"]:
            if bar["symbol"] == "SIM" and bar["session_date"] >= self.days[5]:
                for key in ("open", "high", "low", "close", "floor", "ceiling"):
                    bar[key] = str(D(bar[key])/2)
        split = self.run_sim(payload=payload, config=config)
        self.assertEqual(split["trades"][0]["exit_price"], "4750")
        self.assertEqual(split["trades"][0]["quantity"], 200)
        self.assertEqual(split["trades"][0]["pnl"], result["trades"][0]["pnl"])

    def test_profit_target_respects_settlement_and_stop_first(self):
        config = {**self.config, "strategy": "S1", "maxHold": 30, "s1TargetR": 1}
        for bar in self.payload["bars"]:
            if bar["symbol"] == "SIM":
                bar["high"] = "12000"
        result = self.run_sim(config=config)
        trade = result["trades"][0]
        self.assertEqual(trade["exit_date"], self.days[4])
        self.assertEqual(trade["exit_reason"], "TAKE_PROFIT")
        self.assertEqual(trade["exit_price"], "12000")
        for bar in self.payload["bars"]:
            if bar["symbol"] == "SIM" and bar["session_date"] == self.days[4]:
                bar.update(low="7500", floor="7000")
        adverse = self.run_sim(config=config)["trades"][0]
        self.assertEqual(adverse["exit_reason"], "STOP")
        self.assertEqual(adverse["exit_price"], "8000")

    def test_breakeven_uses_previous_close_not_high_and_gap_can_lose(self):
        config = {**self.config, "strategy": "S1", "maxHold": 30, "s1BreakevenR": 1}
        self.book["SIM"][self.days[3]] = {"raw_close": 11000}
        self.book["SIM"][self.days[4]] = {"raw_close": 12000}
        for bar in self.payload["bars"]:
            if bar["symbol"] == "SIM" and bar["session_date"] in self.days[3:5]:
                bar.update(high="13000", ceiling="14000")
            if bar["symbol"] == "SIM" and bar["session_date"] == self.days[5]:
                bar.update(open="9000", low="8500")
        result = self.run_sim(config=config)
        self.assertEqual(result["trades"][0]["exit_date"], self.days[5])
        self.assertEqual(result["trades"][0]["exit_price"], "9000")
        self.assertLess(D(result["trades"][0]["pnl"]), 0)
        self.book["SIM"][self.days[6]] = {"raw_close": 999999}
        self.assertEqual(result["trades"], self.run_sim(config=config)["trades"])

    def test_profit_levels_adjust_for_split(self):
        config = {**self.config, "strategy": "S1", "maxHold": 30, "s1TargetR": 1, "s1BreakevenR": 1}
        for bar in self.payload["bars"]:
            if bar["symbol"] == "SIM":
                bar["high"] = "12000"
        original = self.run_sim(config=config)
        payload = copy.deepcopy(self.payload)
        payload["actions"] = [{"symbol": "SIM", "type": "SPLIT", "ratio": 2,
                               "ex_date": self.days[3], "known_at": self.days[0]}]
        for bar in payload["bars"]:
            if bar["symbol"] == "SIM" and bar["session_date"] >= self.days[3]:
                for key in ("open", "high", "low", "close", "floor", "ceiling"):
                    bar[key] = str(D(bar[key])/2)
        result = self.run_sim(payload=payload, config=config)
        self.assertEqual(result["trades"][0]["exit_price"], "6000")
        self.assertEqual(result["trades"][0]["quantity"], 200)
        self.assertEqual(result["trades"][0]["pnl"], original["trades"][0]["pnl"])

    def test_partial_target_and_runner_costs_and_causality(self):
        config = {**self.config, "strategy": "S1", "maxHold": 30, "s1TargetR": 1,
                  "s1PartialTarget": True, "s1TrailAtr": 3}
        def signal(day):
            state, signals = self.signal(day)
            for s in signals:
                s["invalidation_price"] = 9000
            return state, signals
        for bar in self.payload["bars"]:
            if bar["symbol"] == "SIM":
                bar["low"] = "9500"
                if bar["session_date"] == self.days[5]:
                    bar.update(open="10500", low="10000", close="10500")
        self.book["SIM"][self.days[2]] = {"close": 20000, "atr14": 1, "factor": 1}
        self.book["SIM"][self.days[4]] = {"close": 11000, "atr14": 200, "factor": 1}
        r = simulate(self.payload, config, self.days[1], self.days[-1], self.book, signal_source=signal)
        self.assertEqual([t["quantity"] for t in r["trades"]], [100, 100])
        self.assertEqual([t["exit_reason"] for t in r["trades"]], ["PARTIAL_TAKE_PROFIT", "STOP"])
        self.assertEqual([t["exit_date"] for t in r["trades"]], [self.days[4], self.days[5]])
        self.assertEqual(r["trades"][1]["exit_price"], "10400")
        self.assertEqual(sum(D(t["pnl"]) for t in r["trades"]), D("131650.00"))
        self.assertEqual(D(r["equity"][-1]["nav"]), D("50131650.00"))
        from quant.s1_experiments import summarize
        self.assertEqual(summarize(r, self.days)["closed"], 1)
        # Before the runner closes, the partial profit must not count as a closed win.
        short = simulate(self.payload, config, self.days[1], self.days[4], self.book, signal_source=signal)
        self.assertEqual(summarize(short, self.days)["closed"], 0)

    def test_partial_target_one_lot_is_not_fractionally_sold(self):
        config = {**self.config, "strategy": "S1", "maxHold": 30, "s1TargetR": 1,
                  "s1PartialTarget": True, "s1TrailAtr": 3}
        for bar in self.payload["bars"]:
            if bar["symbol"] == "SIM":
                bar["high"] = "12000"
        self.book["SIM"][self.days[4]] = {"close": 12000, "atr14": 500, "factor": 1}
        r = self.run_sim(config=config)
        self.assertEqual(len(r["trades"]), 1)
        self.assertEqual(r["trades"][0]["quantity"], 100)
        self.assertEqual(r["trades"][0]["exit_date"], self.days[5])
        self.assertEqual(r["trades"][0]["exit_reason"], "STOP")
        self.assertEqual(sum(o["reason"] == "PARTIAL_BELOW_BOARD_LOT" for o in r["orders"]), 1)

    def test_partial_budget_survives_capacity_and_split_without_repeated_halving(self):
        config = {**self.config, "strategy": "S1", "maxHold": 30, "s1TargetR": 1,
                  "s1PartialTarget": True, "s1TrailAtr": 3}
        def signal(day):
            state, signals = self.signal(day)
            for s in signals:
                s["invalidation_price"] = 9500
            return state, signals
        for bar in self.payload["bars"]:
            if bar["symbol"] == "SIM":
                bar["low"] = "9800"
                if bar["session_date"] in self.days[4:6]:
                    bar["volume"] = 2000  # participation cap = 100 shares
        r = simulate(self.payload, config, self.days[1], self.days[-1], self.book, signal_source=signal)
        self.assertEqual([t["quantity"] for t in r["trades"]], [100, 100])
        self.assertEqual(r["open_positions"]["SIM"]["qty"], 300)
        self.assertNotIn("target", r["open_positions"]["SIM"])
        payload = copy.deepcopy(self.payload)
        payload["actions"] = [{"symbol": "SIM", "type": "SPLIT", "ratio": 2,
                               "ex_date": self.days[5], "known_at": self.days[0]}]
        for bar in payload["bars"]:
            if bar["symbol"] == "SIM" and bar["session_date"] >= self.days[5]:
                for key in ("open", "high", "low", "close", "floor", "ceiling"):
                    bar[key] = str(D(bar[key])/2)
        split = simulate(payload, config, self.days[1], self.days[-1], self.book, signal_source=signal)
        self.assertEqual([t["quantity"] for t in split["trades"]], [100, 100, 100])
        self.assertEqual(split["open_positions"]["SIM"]["qty"], 600)
        self.assertNotIn("target", split["open_positions"]["SIM"])

    def test_ticks_limits_and_risk_caps(self):
        self.assertEqual(tick_price(D(10001), "HOSE", "BUY", self.days[0]), D(10050))
        self.assertEqual(tick_price(D(10001), "HOSE", "SELL", self.days[0]), D(10000))
        bar = self.payload["bars"][0].copy()
        bar["open"] = bar["ceiling"]
        self.assertIsNone(fill_price(bar, "BUY", D(0))[0])
        bar["volume"] = 0
        self.assertEqual(fill_price(bar, "SELL", D(0))[1], "HALT_OR_NO_VOLUME")
        quantity, _ = size_order(D(50000000), D(5000000), D(0), D(0), D(10000), D(9000), D(".0015"), D(1))
        self.assertEqual(quantity, 0)  # mandatory cash reserve
        with self.assertRaisesRegex(ValueError, "NO_EFFECTIVE"):
            tick_price(D(10000), "HOSE", "BUY", "2030-01-01")

    def test_deterministic_future_and_cost_sensitivity(self):
        original = self.run_sim()
        self.assertEqual(original, self.run_sim())
        expensive = {**self.config, "buyFee": .003, "sellFee": .003}
        self.assertLess(D(self.run_sim(config=expensive)["equity"][-1]["nav"]), D(original["equity"][-1]["nav"]))
        changed = copy.deepcopy(self.payload)
        changed["bars"][-2]["close"] = "10500"
        self.assertEqual(self.run_sim(payload=changed)["equity"][:-1], original["equity"][:-1])

    def test_split_preserves_nav_and_dividend_receivable(self):
        payload = copy.deepcopy(self.payload)
        payload["actions"] = [{"symbol": "SIM", "type": "SPLIT", "ratio": 2, "ex_date": self.days[2], "known_at": self.days[0]}]
        for bar in payload["bars"]:
            if bar["symbol"] == "SIM" and bar["session_date"] >= self.days[2]:
                for key in ("open", "high", "low", "close", "floor", "ceiling"):
                    bar[key] = str(D(bar[key])/2)
        r = self.run_sim(payload)
        self.assertEqual(r["equity"][0]["nav"], r["equity"][1]["nav"])
        self.assertEqual(r["trades"][0]["quantity"], 200)
        payload = copy.deepcopy(self.payload)
        payload["actions"] = [{"symbol": "SIM", "type": "CASH_DIVIDEND", "cash_amount": 100,
                               "ex_date": self.days[2], "payable_date": self.days[8], "known_at": self.days[0]}]
        r = self.run_sim(payload)
        self.assertEqual(r["equity"][1]["pending_cash"], "10000.00")
        self.assertEqual(r["equity"][-1]["nav"], "50006000.00")

    def test_splits_embargo_and_walk_forward(self):
        payload = demo_history()
        config = {**self.config, "trainStart": "2022-01-03", "trainEnd": "2023-12-29",
                  "validationStart": "2024-02-15", "validationEnd": "2024-06-28",
                  "testStart": "2024-09-02", "testEnd": "2026-10-16", "embargoSessions": 30}
        validate_config(payload, config)
        with self.assertRaisesRegex(ValueError, "OVERLAPPING"):
            validate_config(payload, {**config, "testStart": config["trainStart"]})
        with self.assertRaisesRegex(ValueError, "EMBARGO"):
            validate_config(payload, {**config, "maxHold": 60})
        for fold in walk_forward(payload["calendar"], config["validationEnd"]):
            self.assertLess(fold["trainEnd"], fold["testStart"])
            self.assertLess(fold["testEnd"], config["testStart"])
            self.assertEqual(payload["calendar"].index(fold["testStart"])-payload["calendar"].index(fold["trainEnd"])-1, 30)

    def test_no_fill_volume_cap_and_gap_stop(self):
        payload = copy.deepcopy(self.payload)
        for bar in payload["bars"]:
            if bar["symbol"] == "SIM":
                bar["volume"] = 1000  # 5% < one board lot
        result = self.run_sim(payload)
        self.assertEqual(result["orders"][0]["reason"], "VOLUME_CAP")
        self.assertEqual(result["metrics"]["tradeCount"], 0)
        self.assertIsNone(result["metrics"]["hitRate"])
        payload = copy.deepcopy(self.payload)
        for bar in payload["bars"]:
            if bar["symbol"] == "SIM" and bar["session_date"] == self.days[4]:
                bar.update(open="7500", close="7500", low="7000", high="8000", floor="6500", ceiling="8500")
        result = self.run_sim(payload)
        self.assertEqual(result["trades"][0]["exit_reason"], "STOP")
        self.assertEqual(result["trades"][0]["exit_price"], "7500")  # gap cannot fill at stop 8000
        self.assertLess(result["metrics"]["maxDrawdown"], 0)

    def test_position_sector_gross_and_board_lot(self):
        for gross, sector, expected in ((0, 0, 1000), (39500000, 0, 0), (0, 17400000, 0)):
            qty, _ = size_order(D(50000000), D(50000000), D(gross), D(sector),
                                D(10000), D(9900), D(".0015"), D(1))
            self.assertEqual(qty, expected)
            self.assertEqual(qty % 100, 0)
