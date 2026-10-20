import copy
import unittest
from quant.history import demo_history, digest, quality, fetch_retry
from quant.provider import MockProviderError


class HistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = demo_history()

    def test_full_lifecycle_calendar(self):
        report = quality(self.payload)
        self.assertEqual(report["status"], "COMPLETE")
        self.assertGreater(report["sessions"], 1200)
        self.assertEqual(report["delisted"], 1)
        self.assertEqual(report["instruments"], 8)
        self.assertEqual(digest(self.payload), digest(demo_history()))

    def test_missing_index_blocks_completeness(self):
        data = copy.deepcopy(self.payload)
        data["bars"].pop()
        self.assertEqual(quality(data)["status"], "PARTIAL")
        self.assertTrue(quality(data)["missing_benchmark"])

    def test_invalid_and_missing_not_zero(self):
        data = copy.deepcopy(self.payload)
        data["bars"][0]["high"] = "1"
        self.assertEqual(quality(data)["status"], "FAILED")
        data["bars"].pop(0)
        self.assertEqual(quality(data)["missing_bars"], 1)

    def test_retry_429_timeout_and_permanent_error(self):
        calls, sleeps = [], []

        def fetch():
            calls.append(1)
            if len(calls) == 1:
                raise MockProviderError("429", 3)
            if len(calls) == 2:
                raise TimeoutError()
            return "ok"
        self.assertEqual(fetch_retry(fetch, sleeps.append, jitter=lambda: 0), "ok")
        self.assertEqual(sleeps, [3, 2])
        with self.assertRaises(MockProviderError):
            fetch_retry(lambda: (_ for _ in ()).throw(MockProviderError("401")), sleeps.append)

    def test_duplicate_revision_not_silently_accepted(self):
        data = copy.deepcopy(self.payload)
        data["bars"].append(data["bars"][0])
        with self.assertRaisesRegex(ValueError, "DUPLICATE"):
            quality(data)
