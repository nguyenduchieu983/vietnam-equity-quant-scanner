import copy
import json
from pathlib import Path
import unittest
from quant.provider import FixtureProvider, classify, normalize

FIXTURE = Path(__file__).resolve().parents[3] / "tests/fixtures/eod-demo.json"


class FoundationTests(unittest.TestCase):
    def setUp(self):
        self.payload = FixtureProvider(FIXTURE).fetch()
        self.row = copy.deepcopy(self.payload["bars"][0])

    def test_decimal_and_provenance(self):
        bar = normalize(self.row)
        self.assertEqual(str(bar.close), "20200")
        self.assertEqual(bar.revision, "fixture-v1")
        self.assertIsNotNone(bar.observed_at.tzinfo)

    def test_invalid_ohlc(self):
        self.row["high"] = "100"
        with self.assertRaisesRegex(ValueError, "INVALID_OHLC"):
            normalize(self.row)

    def test_nonfinite_and_fractional_volume(self):
        for field, value in [("close", "NaN"), ("volume", 1.5), ("volume", -1), ("traded_value", -1)]:
            row = {**self.row, field: value}
            with self.assertRaises(ValueError):
                normalize(row)

    def test_zero_volume_is_valid_not_missing(self):
        self.row["volume"] = 0
        self.row["traded_value"] = "0"
        self.assertEqual(normalize(self.row).volume, 0)

    def test_status_transitions(self):
        bars = [normalize(row) for row in self.payload["bars"]]
        expected = set(self.payload["expected_symbols"])
        self.assertEqual(classify(bars, expected), ("COMPLETE", []))
        status, reasons = classify(bars[:-1], expected)
        self.assertEqual(status, "PARTIAL")
        self.assertIn("MISSING_BENCHMARK", reasons)
        self.assertIn("MISSING_SYMBOLS", classify(bars[1:], expected)[1])

    def test_non_final(self):
        self.row["is_final"] = False
        self.assertIn("NON_FINAL_BARS", classify([normalize(self.row)], {"DEMOA"})[1])

    def test_fixture_is_labelled(self):
        self.assertEqual(json.loads(FIXTURE.read_text())["classification"], "DEMO")


if __name__ == "__main__":
    unittest.main()
