import unittest
from unittest.mock import MagicMock, patch
from quant.history import load_dataset


class RealWorkspaceTests(unittest.TestCase):
    def load(self, status, eligible):
        connection = MagicMock()
        connection.__enter__.return_value.execute.return_value.fetchone.return_value = (
            {"classification": "REAL_RESEARCH"}, status, "hash", {"researchEligible": eligible})
        with patch("quant.history.connect", return_value=connection):
            return load_dataset("test")

    def test_partial_real_requires_explicit_quality_gate(self):
        with self.assertRaisesRegex(ValueError, "DATA_QUALITY_BLOCKED"):
            self.load("PARTIAL", False)
        self.assertEqual(self.load("PARTIAL", True)["content_hash"], "hash")

    def test_failed_real_cannot_bypass_quality_gate(self):
        with self.assertRaisesRegex(ValueError, "DATA_QUALITY_BLOCKED"):
            self.load("FAILED", True)
