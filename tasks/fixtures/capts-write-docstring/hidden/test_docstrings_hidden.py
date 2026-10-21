import inspect
import unittest

import calculator


class HiddenDocstringTests(unittest.TestCase):
    def test_parameters_are_named_in_the_args_section(self):
        expected = {
            "add": ("left", "right"),
            "divide": ("numerator", "denominator"),
            "mean": ("values",),
        }
        for name, parameters in expected.items():
            function = getattr(calculator, name)
            doc = inspect.getdoc(function)
            args = doc.split("Args:", 1)[1].split("Returns:", 1)[0]
            for parameter in parameters:
                self.assertIn(parameter, args, f"{name} does not document {parameter}")

    def test_return_type_is_mentioned(self):
        self.assertIn("int", inspect.getdoc(calculator.add).lower())
        self.assertIn("float", inspect.getdoc(calculator.divide).lower())
        self.assertIn("float", inspect.getdoc(calculator.mean).lower())

    def test_mean_error_mentions_empty(self):
        doc = inspect.getdoc(calculator.mean).lower()
        self.assertIn("empty", doc)

    def test_mean_raises_on_empty_sequence(self):
        with self.assertRaises(ZeroDivisionError):
            calculator.mean([])
