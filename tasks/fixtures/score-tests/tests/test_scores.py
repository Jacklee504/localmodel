import unittest
from scoring import score_label


class ScoreTests(unittest.TestCase):
    def test_success(self):
        self.assertEqual(score_label(2), "successful")
