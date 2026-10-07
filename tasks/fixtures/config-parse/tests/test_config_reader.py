import json
import tempfile
import unittest
from pathlib import Path

from config_reader import load_models


class ConfigTests(unittest.TestCase):
    def read(self, data):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "models.json"
            path.write_text(json.dumps(data))
            return load_models(path)

    def test_valid(self):
        models = {"small": {"provider": "mlx", "path": "weights"},
                  "remote": {"provider": "openai_compatible", "base_url": "http://localhost/v1", "model": "x"}}
        self.assertEqual(self.read({"models": models}), models)

    def test_missing_fields(self):
        for value in ({}, {"models": []}, {"models": {"x": {"provider": "mlx"}}},
                      {"models": {"x": {"provider": "openai_compatible", "model": "x"}}}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.read(value)
