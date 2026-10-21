import json
import tempfile
import unittest
from pathlib import Path

from config_reader import load_models


class HiddenConfigTests(unittest.TestCase):
    """Edge cases the visible tests do not cover."""

    def read(self, data):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "models.json"
            path.write_text(json.dumps(data))
            return load_models(path)

    def test_empty_provider_is_rejected(self):
        for provider in ("", "   ", None):
            with self.subTest(provider=provider), self.assertRaises(ValueError):
                self.read({"models": {"x": {"provider": provider, "path": "p"}}})

    def test_empty_models_object_is_allowed(self):
        self.assertEqual(self.read({"models": {}}), {})

    def test_missing_models_key_is_rejected(self):
        with self.assertRaises(ValueError):
            self.read({"other": {}})

    def test_malformed_json_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "models.json"
            path.write_text("{not json")
            with self.assertRaises(ValueError):
                load_models(path)

    def test_extra_fields_are_preserved(self):
        models = {"x": {"provider": "mlx", "path": "p", "note": "keep me"}}
        self.assertEqual(self.read({"models": models}), models)

    def test_openai_compatible_requires_both_fields(self):
        for missing in ("base_url", "model"):
            entry = {"provider": "openai_compatible", "base_url": "http://x/v1", "model": "m"}
            entry.pop(missing)
            with self.subTest(missing=missing), self.assertRaises(ValueError):
                self.read({"models": {"x": entry}})
