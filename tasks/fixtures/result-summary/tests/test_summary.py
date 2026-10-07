import unittest
from summary import summarize


class SummaryTests(unittest.TestCase):
    def test_mixed(self):
        records = [{"score": 2}, {"score": 0}, {"score": None}]
        self.assertEqual(summarize(records), {"total": 3, "scored": 2, "successful": 1, "average_score": 1.0})
        self.assertEqual(records[-1]["score"], None)

    def test_unscored(self):
        self.assertEqual(summarize([{"score": None}])["average_score"], None)

    def test_invalid(self):
        with self.assertRaises(ValueError):
            summarize([{"score": 4}])
