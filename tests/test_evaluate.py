import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import sys
from io import BytesIO
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import evaluate


class EvaluationTests(unittest.TestCase):
    def test_repository_response_is_applied_and_validated_in_copy(self):
        task = next(task for task in evaluate.load_tasks() if task["id"] == "api-key")
        original = (evaluate.ROOT / "tasks/fixtures/api-key/api.py").read_text()
        replacement = original.replace("    save(db, key, value)",
                                       "    if key == '':\n        raise ValueError('empty key')\n    save(db, key, value)")
        result = evaluate.execute_repo(task, json.dumps({"files": {"api.py": replacement}}))
        self.assertTrue(result["validation_passed"], result["validation"])
        self.assertIn("raise ValueError", result["diff"])
        self.assertEqual((evaluate.ROOT / "tasks/fixtures/api-key/api.py").read_text(), original)

    def test_rejects_unlisted_file(self):
        task = next(task for task in evaluate.load_tasks() if task["id"] == "api-key")
        with self.assertRaises(ValueError):
            evaluate.execute_repo(task, json.dumps({"files": {"tests/test_api.py": "pass"}}))

    def test_openai_compatible_request_and_usage(self):
        class Response(BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.close()

        def urlopen(request, timeout):
            self.assertEqual(request.full_url, "http://localhost:8000/v1/chat/completions")
            self.assertEqual(json.loads(request.data)["messages"][0]["content"], "hello")
            return Response(json.dumps({"choices": [{"message": {"content": "answer"}}],
                                        "usage": {"completion_tokens": 3}}).encode())

        model = evaluate.Model({"provider": "openai_compatible", "base_url": "http://localhost:8000/v1", "model": "test"})
        with patch.object(evaluate.urllib.request, "urlopen", urlopen):
            answer, timings = model.generate("hello", 20)
        self.assertEqual(answer, "answer")
        self.assertEqual(timings["tokens_generated"], 3)

    def test_response_run_and_report_keep_unscored_separate(self):
        class FakeModel:
            def __init__(self, config):
                pass

            def generate(self, prompt, max_tokens):
                return "proposal", {"generation_seconds": 0.1, "first_token_seconds": None,
                                    "tokens_generated": 2, "tokens_per_second": 20, "peak_memory_bytes": None}

        with tempfile.TemporaryDirectory() as folder, patch.object(evaluate, "RESULTS", Path(folder)), \
             patch.object(evaluate, "Model", FakeModel):
            evaluate.run(SimpleNamespace(model="qwen25_7b", mode="response", task="api-key", max_tokens=32))
            run_path = next((Path(folder) / "qwen25_7b").iterdir())
            record = evaluate.read_json(run_path / "api-key.json")
            self.assertIsNone(record["repo"])
            self.assertIsNone(record["manual"]["score"])
            output = Path(folder) / "comparison.md"
            evaluate.compare(SimpleNamespace(runs=[str(run_path)], output=str(output)))
            self.assertIn("Unscored | 1", output.read_text())
            self.assertNotIn("Validation passing", output.read_text())

    def test_full_repository_suite_records_every_validation(self):
        class FakeModel:
            def __init__(self, config):
                pass

            def generate(self, prompt, max_tokens):
                task = next(item for item in evaluate.load_tasks()
                            if prompt.startswith("Task: " + item["title"] + "\n"))
                name = task["editable"][0]
                body = evaluate.fixture_files(task)[name]
                return json.dumps({"files": {name: body}}), {"generation_seconds": 0.1,
                    "first_token_seconds": None, "tokens_generated": 1,
                    "tokens_per_second": 10, "peak_memory_bytes": None}

        with tempfile.TemporaryDirectory() as folder, patch.object(evaluate, "RESULTS", Path(folder)), \
             patch.object(evaluate, "Model", FakeModel):
            evaluate.run(SimpleNamespace(model="qwen25_7b", mode="repo", task=None, max_tokens=32))
            run_path = next((Path(folder) / "qwen25_7b").iterdir())
            for task in evaluate.load_tasks():
                record = evaluate.read_json(run_path / (task["id"] + ".json"))
                self.assertIsNone(record["error"], task["id"])
                self.assertEqual(len(record["repo"]["validation"]), len(task["validation"]))
                if task["id"] == "api-key":
                    self.assertFalse(record["repo"]["validation_passed"])
                if task["id"] == "score-tests":
                    self.assertTrue(record["repo"]["validation_passed"])
            output = Path(folder) / "comparison.md"
            evaluate.compare(SimpleNamespace(runs=[str(run_path)], output=str(output)))
            self.assertIn("Validation passing", output.read_text())


if __name__ == "__main__":
    unittest.main()
