import copy
import unittest
from quant.paper import step


class PaperTests(unittest.TestCase):
    def test_decision_date_and_missing_holdings_fail_closed(self):
        payload = {"calendar": ["2024-01-01", "2024-01-02"], "bars": []}
        with self.assertRaisesRegex(ValueError, "DECISION_SESSION"):
            step(payload, {}, {}, {"positions": {}}, {"day": "2023-12-31"}, "2024-01-02")
        with self.assertRaisesRegex(ValueError, "MISSING_HOLDING"):
            step(payload, {}, {}, {"positions": {"ABC": {}}}, {"day": "2024-01-01"}, "2024-01-02")

    def test_step_uses_frozen_prior_features_not_revised_snapshot(self):
        from unittest.mock import patch
        payload = {"calendar": ["2024-01-01", "2024-01-02"], "bars": []}
        book = {"ABC": {"2024-01-01": {"close": 999}, "2024-01-02": {"close": 11}}}
        original = copy.deepcopy(book)
        prior = {"day": "2024-01-01", "features": {"ABC": {"close": 10}}, "state": {}, "signals": []}
        with patch("quant.paper.simulate", return_value={}) as engine, patch("quant.paper.decision", return_value={}):
            step(payload, book, {}, {"positions": {}}, prior, "2024-01-02")
            self.assertEqual(engine.call_args.args[4]["ABC"]["2024-01-01"]["close"], 10)
            self.assertEqual(book, original)
