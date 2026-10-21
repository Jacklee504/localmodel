import unittest

from ledger import group_by_kind, normalise_entry, total_amount


class HiddenLedgerTests(unittest.TestCase):
    def test_public_api_is_unchanged(self):
        for name in ("normalise_entry", "total_amount", "group_by_kind"):
            self.assertTrue(callable(getattr(__import__("ledger"), name)))

    def test_no_placeholder_tests_remain(self):
        import pathlib

        source = pathlib.Path(__file__).resolve().parents[1] / "tests/test_ledger.py"
        text = source.read_text(encoding="utf-8")
        self.assertNotIn("pass", text.replace("# ", ""))

    def test_the_written_tests_cover_the_functions(self):
        import pathlib

        source = pathlib.Path(__file__).resolve().parents[1] / "tests/test_ledger.py"
        text = source.read_text(encoding="utf-8")
        for name in ("normalise_entry", "total_amount", "group_by_kind"):
            self.assertIn(name, text, f"{name} is not exercised by the written tests")
