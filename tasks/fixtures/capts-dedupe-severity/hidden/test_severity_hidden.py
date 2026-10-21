import unittest

import severity
from severity import severity_for, severity_label


class HiddenSeverityTests(unittest.TestCase):
    def test_all_labels_unchanged(self):
        self.assertEqual(severity_label("removed"), "high")
        self.assertEqual(severity_label("renamed"), "high")
        self.assertEqual(severity_label("dependency_removed"), "high")
        self.assertEqual(severity_label("modified"), "high")
        self.assertEqual(severity_label("value_changed"), "medium")
        self.assertEqual(severity_label("dependency_added"), "low")
        self.assertEqual(severity_label("invented"), "unknown")

    def test_unknown_severity_is_zero(self):
        self.assertEqual(severity_for("invented"), 0.0)

    def test_thresholds_are_not_duplicate_literals(self):
        import inspect

        source = inspect.getsource(severity)
        self.assertNotIn("0.7", source.split("def severity_label", 1)[-1])
        self.assertNotIn("0.4", source.split("def severity_label", 1)[-1])

    def test_module_has_a_leading_comment(self):
        import inspect
        import re

        source = inspect.getsource(severity)
        outside = re.sub(r'""".*?"""', "", source, flags=re.DOTALL)
        self.assertRegex(
            outside, r"(?m)^\s*#",
            "the module needs a comment outside the docstring",
        )
