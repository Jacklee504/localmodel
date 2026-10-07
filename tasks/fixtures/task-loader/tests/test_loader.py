import json
import tempfile
import unittest
from pathlib import Path
from loader import load_tasks


class LoaderTests(unittest.TestCase):
    def read(self, data):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "tasks.json"
            path.write_text(json.dumps(data))
            return load_tasks(path)

    def test_preserve(self):
        tasks = [{"id": "one", "prompt": "Fix it", "category": "bug"}]
        self.assertEqual(load_tasks_from_data(self, {"tasks": tasks}), tasks)

    def test_invalid(self):
        for data in ({}, {"tasks": []}, {"tasks": [{"id": " ", "prompt": "x"}]},
                     {"tasks": [{"id": "x", "prompt": "x"}, {"id": "x", "prompt": "y"}]}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                self.read(data)


def load_tasks_from_data(test, data):
    return test.read(data)
