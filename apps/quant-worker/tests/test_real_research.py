import copy
import unittest
from decimal import Decimal as D
from quant.backtest import simulate
from quant.vndirect_research import normalize_price, actions_from_events


class RealResearchTests(unittest.TestCase):
    def test_raw_fills_separate_from_adjusted_features(self):
        row = {"code": "ABC", "floor": "HOSE", "date": "2024-01-02", "open": 10, "high": 11,
               "low": 9, "close": 10, "adOpen": 5, "adHigh": 5.5, "adLow": 4.5, "adClose": 5,
               "nmVolume": 100000, "nmValue": 1000000000, "floorPrice": 8, "ceilingPrice": 12}
        b = normalize_price(row, "2026-10-21T00:00:00Z", "test")
        self.assertEqual(D(b["close"]), 10000)
        self.assertEqual(D(b["adjusted_close"]), 5000)
        self.assertEqual(D(b["factor"]), D(".5"))
        self.assertEqual(D(b["traded_value"]), 1000000000)
        with self.assertRaises(ValueError):
            normalize_price({**row, "high": 13}, "2026-10-21T00:00:00Z", "test")

    def test_bonus_dedup_and_additive_same_day_ratios(self):
        base = {"code": "ABC", "effectiveDate": "2024-01-03", "disclosureDate": "2024-01-01", "ratio": 10}
        events = [{**base, "id": "1", "type": "STOCKDIV"}, {**base, "id": "2", "type": "STOCKDIV"},
                  {**base, "id": "3", "type": "KINDDIV", "ratio": 20}]
        actions, issues = actions_from_events(events, ["2024-01-01", "2024-01-03", "2024-01-05"])
        self.assertEqual(issues, [])
        self.assertEqual(len(actions), 1)
        self.assertEqual(D(actions[0]["ratio"]), D(".3"))
        self.assertIsNone(actions[0]["available_date"])

    def fixture(self):
        days = [f"2024-01-{d:02}" for d in range(1, 13)]
        bars = [{"symbol": s, "session_date": d, "exchange": "HOSE", "open": "10000", "close": "10000",
                 "high": "11000", "low": "9000", "floor": "8000", "ceiling": "12000", "volume": 100000,
                 "is_final": True, "factor": "1"} for d in days for s in ("ABC", "VNINDEX")]
        payload = {"calendar": days, "bars": bars, "warnings": [], "instruments": [{"symbol": "ABC", "sector": "X"}], "actions": []}
        config = {"capital": 50000000, "strategy": "S2", "maxHold": 1, "minLiquidity": 0,
                  "buyFee": .0015, "sellFee": .0015, "sellTax": .001, "slippage": 0}
        def signals(day):
            return {"riskMultiplier": 1}, ([{"symbol": "ABC", "side": "LONG", "score": 90,
                                            "decision_date": day, "invalidation_price": 8000}] if day == days[0] else [])
        return payload, config, signals

    def test_bonus_not_sellable_until_receipt_and_cost_allocated_once(self):
        p, c, signals = self.fixture()
        p["actions"] = [{"type": "STOCK_DIVIDEND", "symbol": "ABC", "ratio": 1, "ex_date": "2024-01-03",
                         "known_at": "2024-01-01", "available_date": "2024-01-09"}]
        for b in p["bars"]:
            if b["symbol"] == "ABC" and b["session_date"] >= "2024-01-03":
                for k in ("open", "close", "high", "low", "floor", "ceiling"):
                    b[k] = str(D(b[k])/2)
        r = simulate(p, c, "2024-01-02", "2024-01-12", {"ABC": {}}, signal_source=signals)
        self.assertEqual([(t["exit_date"], t["quantity"]) for t in r["trades"]], [("2024-01-05", 100), ("2024-01-09", 100)])
        self.assertEqual(r["equity"][-1]["nav"], "49996000.00")
        self.assertEqual(sum(D(t["pnl"]) for t in r["trades"]), D(-4000))
        self.assertFalse(r["open_positions"])

    def test_dividend_after_horizon_is_receivable_and_in_trade_pnl(self):
        p, c, signals = self.fixture()
        p = copy.deepcopy(p)
        p["actions"] = [{"type": "CASH_DIVIDEND", "symbol": "ABC", "cash_amount": 100, "ex_date": "2024-01-03",
                         "known_at": "2024-01-01", "payable_date": "2024-02-01", "withholding_rate": ".05"}]
        r = simulate(p, c, "2024-01-02", "2024-01-12", {"ABC": {}}, signal_source=signals)
        self.assertEqual(r["trades"][0]["pnl"], "5500.00")
        self.assertEqual(r["trades"][0]["dividend_income"], "9500.00")
        self.assertEqual(r["equity"][-1]["nav"], "50005500.00")
        self.assertEqual(r["equity"][-1]["pending_cash"], "9500.00")
