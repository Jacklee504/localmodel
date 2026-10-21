import unittest

from severity import severity_for, severity_label


class SeverityTests(unittest.TestCase):
    def test_success(self):
        self.assertEqual(severity_for("removed"), 1.0)
