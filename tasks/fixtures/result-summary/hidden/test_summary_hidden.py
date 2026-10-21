import unittest
from summary import summarize


class HiddenSummaryTests(unittest.TestCase):
    """Edge cases the visible tests do not cover."""

    def test_empty_input(self):
        self.assertEqual(
            summarize([]),
            {"total": 0, "scored": 0, "successful": 0, "average_score": None},
        )

    def test_invalid_score_raises_rather_than_being_filtered(self):
        for bad in (4, -1, 1.5, "2", None if False else 99):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                summarize([{"score": bad}])

    def test_unscored_records_still_count_toward_total(self):
        result = summarize([{"score": None}, {"score": None}])
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["scored"], 0)
        self.assertIsNone(result["average_score"])

    def test_average_is_over_scored_records_only(self):
        result = summarize([{"score": 2}, {"score": 0}, {"score": None}])
        self.assertEqual(result["average_score"], 1.0)

    def test_input_is_not_mutated(self):
        records = [{"score": 2}, {"score": None}]
        copy = [dict(record) for record in records]
        summarize(records)
        self.assertEqual(records, copy)
