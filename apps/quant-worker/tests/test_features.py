import copy
import unittest
from quant.features import ema, features, feature_book, regime, active
from quant.history import demo_history
from quant.strategies import evaluate, percentile


def linear(n=260):
    from datetime import date, timedelta
    return [{"session_date": (date(2020, 1, 1)+timedelta(days=i)).isoformat(),
             "open": str(100+i), "high": str(102+i), "low": str(99+i), "close": str(101+i),
             "factor": "1", "volume": 1000, "traded_value": "6000000000", "is_final": True,
             "observed_at": "2020-01-01T09:30:00+00:00"} for i in range(n)]


class FeatureTests(unittest.TestCase):
    def test_ema_golden_warmup(self):
        self.assertEqual(ema([1, 2, 3, 4, 5], 3), [None, None, 2, 3, 4])
        f = list(features(linear()).values())
        self.assertIsNone(f[18]["sma20"])
        self.assertAlmostEqual(f[19]["sma20"], 110.5)
        self.assertEqual(f[20]["high_20_prev"], 121)
        self.assertEqual(f[20]["low_20_prev"], 99)
        self.assertEqual(f[20]["volume_ratio20"], 1)
        self.assertEqual(f[20]["rsi14"], 100)
        self.assertEqual(f[20]["atr14"], 3)
        self.assertEqual(f[19]["median_value20"], 6e9)
        self.assertAlmostEqual(f[60]["ret60"], 161/101-1)
        self.assertAlmostEqual(f[259]["price_to_52w_high"], 360/361)

    def test_future_cannot_change_past(self):
        bars = linear()
        before = features(bars[:100])
        bars[-1]["close"] = "999999"
        after = features(bars)
        self.assertEqual(before, {k: after[k] for k in before})

    def test_current_high_excluded_and_zero_volume(self):
        bars = linear(30)
        bars[-1]["high"] = "999999"
        f = list(features(bars).values())[-1]
        self.assertEqual(f["high_20_prev"], 130)
        for b in bars:
            b["volume"] = 0
        self.assertIsNone(list(features(bars).values())[-1]["volume_ratio20"])

    def test_split_adjustment_no_false_return(self):
        bars = linear(70)
        before = features(bars)
        split = copy.deepcopy(bars)
        for row in split[40:]:
            for field in ("open", "high", "low", "close"):
                row[field] = str(float(row[field])/2)
            row["factor"] = "2"
        adjusted = features(split)
        self.assertEqual(before[bars[-1]["session_date"]]["ret60"], adjusted[bars[-1]["session_date"]]["ret60"])

    def test_all_strategies_explain_and_regime_unknown(self):
        payload = demo_history()
        book = feature_book(payload)
        session = payload["calendar"][700]
        for code in ("S1", "S2", "S3", "S4"):
            state, rows = evaluate(payload, book, session, code, {"minLiquidity": 5e9, "maxHold": 30})
            self.assertEqual(rows, evaluate(payload, book, session, code, {"minLiquidity": 5e9, "maxHold": 30})[1])
            for row in rows:
                self.assertTrue(row["reasons"] or row["side"] == "LONG")
                self.assertEqual(row["earliest_trade_date"], payload["calendar"][701])
        self.assertEqual(regime(payload, {}, session)["regime"], "UNKNOWN")
        self.assertNotIn("SIM06", [i["symbol"] for i in active(payload, payload["calendar"][900])])
        self.assertNotIn("SIM07", [i["symbol"] for i in active(payload, payload["calendar"][100])])

    def test_percentile_ties_stable(self):
        self.assertEqual(percentile({"B": 1, "A": 1}), {"A": 0, "B": 100})
