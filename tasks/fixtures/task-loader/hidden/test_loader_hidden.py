import json
import tempfile
import unittest
from pathlib import Path
from loader import load_tasks


class HiddenLoaderTests(unittest.TestCase):
    """Edge cases the visible tests do not cover."""

    def read(self, data):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "tasks.json"
            path.write_text(json.dumps(data))
            return load_tasks(path)

    def test_blank_prompt_is_rejected(self):
        for prompt in ("", "   ", None):
            with self.subTest(prompt=prompt), self.assertRaises(ValueError):
                self.read({"tasks": [{"id": "x", "prompt": prompt}]})

    def test_missing_id_is_rejected(self):
        with self.assertRaises(ValueError):
            self.read({"tasks": [{"prompt": "x"}]})

    def test_non_string_id_is_rejected(self):
        with self.assertRaises(ValueError):
            self.read({"tasks": [{"id": 5, "prompt": "x"}]})

    def test_unreadable_file_raises_value_error(self):
        with self.assertRaises(ValueError):
            load_tasks(Path("/nonexistent/tasks.json"))

    def test_order_is_preserved(self):
        tasks = [{"id": "z", "prompt": "a"}, {"id": "a", "prompt": "b"}]
        self.assertEqual(self.read({"tasks": tasks}), tasks)
