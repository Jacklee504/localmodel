import inspect
import unittest

import calculator


class DocstringTests(unittest.TestCase):
    def functions(self):
        return [
            (name, obj)
            for name, obj in vars(calculator).items()
            if inspect.isfunction(obj) and obj.__module__ == "calculator"
        ]

    def test_every_function_has_a_docstring(self):
        for name, function in self.functions():
            self.assertTrue(inspect.getdoc(function), f"{name} has no docstring")

    def test_docstrings_have_an_args_and_returns_section(self):
        for name, function in self.functions():
            doc = inspect.getdoc(function)
            self.assertIn("Args:", doc, f"{name} has no Args section")
            self.assertIn("Returns:", doc, f"{name} has no Returns section")

    def test_summary_is_a_single_sentence(self):
        for name, function in self.functions():
            summary = inspect.getdoc(function).splitlines()[0]
            self.assertTrue(summary.endswith("."), f"{name} summary does not end with a period")

    def test_divide_documents_its_error(self):
        doc = inspect.getdoc(calculator.divide)
        self.assertIn("Raises:", doc)
        self.assertIn("ValueError", doc)

    def test_mean_documents_its_error(self):
        doc = inspect.getdoc(calculator.mean)
        self.assertIn("Raises:", doc)
        self.assertIn("ZeroDivisionError", doc)

    def test_add_does_not_claim_to_raise(self):
        doc = inspect.getdoc(calculator.add)
        self.assertNotIn("Raises:", doc)

    def test_behaviour_is_unchanged(self):
        self.assertEqual(calculator.add(2, 3), 5)
        self.assertEqual(calculator.divide(6, 3), 2)
        with self.assertRaises(ValueError):
            calculator.divide(1, 0)
        self.assertEqual(calculator.mean([1, 2, 3]), 2)
