import unittest
from scoring import score_label


class HiddenScoreTests(unittest.TestCase):
    """Edge cases the visible tests do not cover."""

    def test_all_valid_labels(self):
        self.assertEqual(score_label(0), "failed")
        self.assertEqual(score_label(1), "partial")
        self.assertEqual(score_label(2), "successful")

    def test_out_of_range_rejected(self):
        for bad in (-1, 3, 100):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                score_label(bad)

    def test_non_integers_rejected(self):
        for bad in (1.0, 2.5, "1", None, [1]):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                score_label(bad)

    def test_booleans_are_rejected(self):
        for bad in (True, False):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                score_label(bad)
