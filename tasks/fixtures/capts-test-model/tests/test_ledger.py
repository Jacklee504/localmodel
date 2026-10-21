import unittest

from ledger import group_by_kind, normalise_entry, total_amount


class LedgerTests(unittest.TestCase):
    def test_success(self):
        self.assertEqual(normalise_entry({"amount": 5, "kind": "Deal"}), {"amount": 5, "kind": "deal", "ref": None})
