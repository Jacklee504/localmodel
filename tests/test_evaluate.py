import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import evalcore
import evaluate

ROOT = Path(__file__).resolve().parents[1]


class ExtractionTests(unittest.TestCase):
    def test_reasoning_and_fence_are_stripped(self):
        answer = (
            "<think>I need to update the parser.</think>\n"
            "Here is the change:\n\n```json\n"
            '{"files": {"config_reader.py": "def load_models(path):\\n    ...\\n"}}\n'
            "```"
        )
        files, _ = evalcore.find_files_object(answer)
        self.assertEqual(files, {"config_reader.py": "def load_models(path):\n    ...\n"})

    def test_prose_around_json_is_recovered(self):
        files, _ = evalcore.find_files_object(
            'I will make the minimal change.\n\n{"files":{"retry.py":"x = 1\\n"}}\n\nDone.'
        )
        self.assertEqual(files, {"retry.py": "x = 1\n"})

    def test_bare_json_object_is_recovered(self):
        files, _ = evalcore.find_files_object('{"files":{"a.py":"b"}}')
        self.assertEqual(files, {"a.py": "b"})

    def test_list_content_parts_are_concatenated(self):
        message = {"content": [{"type": "text", "text": "a"}, {"type": "text", "text": "b"}]}
        self.assertEqual(evalcore.extract_content(message), "ab")

    def test_alternate_field_is_used_when_content_missing(self):
        self.assertEqual(evalcore.extract_content({"output_text": "hello"}), "hello")

    def test_reasoning_is_read_from_separate_fields(self):
        self.assertEqual(evalcore.extract_reasoning({"reasoning": "think"}), "think")
        self.assertEqual(evalcore.extract_reasoning({"reasoning_content": "think"}), "think")

    def test_braces_inside_strings_do_not_break_parsing(self):
        files, _ = evalcore.find_files_object('{"files":{"a.py":"def f(): return {\\"k\\": 1}"}}')
        self.assertIn("a.py", files)

    def test_unparseable_returns_nothing(self):
        files, first_object = evalcore.find_files_object("there is no json here")
        self.assertIsNone(files)
        self.assertIsNone(first_object)


class FailureTaxonomyTests(unittest.TestCase):
    def test_disallowed_path_is_classified(self):
        task = next(t for t in evaluate.load_tasks() if t["id"] == "api-key")
        with self.assertRaises(evalcore.ModelFailure) as caught:
            evaluate.parse_changes(
                json.dumps({"files": {"tests/test_api.py": "pass"}}), set(task["editable"])
            )
        self.assertEqual(caught.exception.kind, "disallowed_path")

    def test_missing_files_key_is_a_protocol_violation(self):
        with self.assertRaises(evalcore.ModelFailure) as caught:
            evaluate.parse_changes(json.dumps({"other": {}}), {"a.py"})
        self.assertEqual(caught.exception.kind, "protocol_violation")

    def test_unparseable_answer_is_classified(self):
        with self.assertRaises(evalcore.ModelFailure) as caught:
            evaluate.parse_changes("no json at all", {"a.py"})
        self.assertEqual(caught.exception.kind, "unparseable")


class RepositoryExecutionTests(unittest.TestCase):
    def test_hidden_files_never_reach_the_prompt(self):
        for task in evaluate.load_tasks():
            prompt = evaluate.make_prompt(task, "repo")
            for name in evaluate.fixture_files(task, include_hidden=True):
                if name.startswith("hidden/"):
                    self.assertNotIn(name, prompt, f"{task['id']} leaked {name}")

    def test_suite_hash_changes_when_a_hidden_file_changes(self):
        tasks = evaluate.load_tasks()
        original = evaluate.suite_hash(tasks)
        hidden = ROOT / "tasks/fixtures/result-summary/hidden/test_summary_hidden.py"
        body = hidden.read_text(encoding="utf-8")
        hidden.write_text(body + "\n# change\n", encoding="utf-8")
        try:
            self.assertNotEqual(original, evaluate.suite_hash(tasks))
        finally:
            hidden.write_text(body, encoding="utf-8")

    def test_repository_response_is_applied_and_validated_in_copy(self):
        task = next(task for task in evaluate.load_tasks() if task["id"] == "api-key")
        original = (evaluate.ROOT / "tasks/fixtures/api-key/api.py").read_text()
        replacement = original.replace(
            "    save(db, key, value)",
            "    if key == '':\n        raise ValueError('empty key')\n    save(db, key, value)",
        )
        result = evaluate.execute_repo(task, json.dumps({"files": {"api.py": replacement}}))
        self.assertTrue(result["validation_passed"], result["validation"])
        self.assertIn("raise ValueError", result["diff"])
        self.assertEqual((evaluate.ROOT / "tasks/fixtures/api-key/api.py").read_text(), original)

    def test_rejects_unlisted_file(self):
        task = next(task for task in evaluate.load_tasks() if task["id"] == "api-key")
        with self.assertRaises(evalcore.ModelFailure):
            evaluate.execute_repo(task, json.dumps({"files": {"tests/test_api.py": "pass"}}))

    def test_trailing_newline_is_preserved_exactly(self):
        task = next(task for task in evaluate.load_tasks() if task["id"] == "api-key")
        original = (evaluate.ROOT / "tasks/fixtures/api-key/api.py").read_text()
        stripped = original.rstrip("\n")
        result = evaluate.execute_repo(task, json.dumps({"files": {"api.py": stripped}}))
        self.assertEqual(result["changes"]["api.py"], stripped)


class ConfigTests(unittest.TestCase):
    def test_shipped_config_is_valid(self):
        data = evalcore.read_json(evaluate.MODELS)
        self.assertEqual(data["schema_version"], 1)
        for key, config in data["models"].items():
            evalcore.validate_model_config(config, key)

    def test_candidate_models_are_configured(self):
        data = evalcore.read_json(evaluate.MODELS)
        for key in ("gpt_oss_20b", "qwen38_27b", "qwen3_coder_30b"):
            self.assertIn(key, data["models"])
            config = data["models"][key]
            self.assertEqual(config["base_url"], "http://127.0.0.1:11434/v1")
            self.assertEqual(config["generation"]["common"]["max_tokens"], 8192)
            self.assertEqual(config["context"]["num_ctx"], 64000)

    def test_unknown_provider_is_rejected(self):
        with self.assertRaises(evalcore.EvaluationError):
            evalcore.validate_model_config({"name": "x", "provider": "nope"}, "x")

    def test_max_tokens_override_wins(self):
        config = {"generation": {"common": {"max_tokens": 8192}}}
        common, _ = evalcore.resolve_generation(config, 4096)
        self.assertEqual(common["max_tokens"], 4096)
        common, _ = evalcore.resolve_generation(config)
        self.assertEqual(common["max_tokens"], 8192)


class ComparisonKeyTests(unittest.TestCase):
    def test_key_contains_the_strict_fields(self):
        key = evaluate.build_comparison_key(
            "repo", ["a", "b"], "hash",
            {"max_tokens": 8192, "temperature": 0.2, "top_p": 0.9}, 64000, 0,
        )
        self.assertEqual(key["protocol_version"], 2)
        self.assertEqual(key["generation"]["max_tokens"], 8192)
        self.assertEqual(key["context_requirement"], 64000)

    def test_mismatched_keys_raise_an_actionable_error(self):
        first = {"comparison_key": {"protocol_version": 2, "generation": {"max_tokens": 8192}}}
        second = {
            "comparison_key": {"protocol_version": 2, "generation": {"max_tokens": 4096}},
            "run_id": "x",
        }
        with self.assertRaises(evalcore.EvaluationError) as caught:
            evaluate.check_comparable(first, [second])
        self.assertIn("max_tokens", str(caught.exception))

    def test_mismatched_protocol_raises_an_actionable_error(self):
        first = {"comparison_key": {"protocol_version": 2}}
        second = {"comparison_key": {"protocol_version": 1}, "run_id": "x"}
        with self.assertRaises(evalcore.EvaluationError) as caught:
            evaluate.check_comparable(first, [second])
        self.assertIn("protocol", str(caught.exception))


class RunAndReportTests(unittest.TestCase):
    def test_legacy_run_is_refused_by_default(self):
        legacy = ROOT / "results/qwen25_7b/20261007T094236959071Z"
        if not legacy.is_dir():
            self.skipTest("legacy run directory is not present")
        with self.assertRaises(evalcore.EvaluationError) as caught:
            evaluate.compare(SimpleNamespace(runs=[str(legacy)], output=None, legacy=False))
        self.assertIn("legacy", str(caught.exception).lower())

    def test_legacy_run_has_a_separate_summary(self):
        legacy = ROOT / "results/qwen25_7b/20261007T094236959071Z"
        if not legacy.is_dir():
            self.skipTest("legacy run directory is not present")
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "legacy.md"
            evaluate.compare(
                SimpleNamespace(runs=[str(legacy)], output=str(output), legacy=True)
            )
            text = output.read_text()
            self.assertIn("Legacy run summary", text)
            self.assertIn("not comparable", text)

    def test_response_run_and_report_keep_unscored_separate(self):
        class FakeModel:
            def __init__(self, config):
                pass

            def generate(self, prompt, common, model_settings, timeout_seconds):
                return "proposal", "", {
                    "generation_seconds": 0.1, "first_token_seconds": None,
                    "tokens_generated": 2, "prompt_tokens": 1, "tokens_per_second": 20,
                    "reasoning_chars": 0, "answer_chars": 8, "finish_reason": "stop",
                    "timeout_seconds": 3600, "peak_memory_bytes": None, "warning": None,
                }

        with tempfile.TemporaryDirectory() as folder, patch.object(evaluate, "RESULTS", Path(folder)), \
             patch.object(evaluate, "Model", FakeModel):
            args = SimpleNamespace(
                model="gpt_oss_20b", mode="response", task="api-key", max_tokens=None,
                repeats=1, timeout_seconds=3600, repair_attempts=0,
                _run_id="20260101T000000000000Z",
            )
            evaluate.run(args)
            run_path = next((Path(folder) / "gpt_oss_20b").iterdir())
            record = evaluate.read_json(run_path / "api-key.json")
            self.assertIsNone(record["repo"])
            self.assertIsNone(record["manual"]["score"])
            self.assertEqual(record["failure_kind"], "none")
            output = Path(folder) / "comparison.md"
            evaluate.compare(SimpleNamespace(runs=[str(run_path)], output=str(output)))
            text = output.read_text()
            self.assertIn("Unscored | 1", text)
            self.assertNotIn("Validation passing", text)

    def test_full_repository_suite_records_every_validation(self):
        class FakeModel:
            def __init__(self, config):
                pass

            def generate(self, prompt, common, model_settings, timeout_seconds):
                task = next(item for item in evaluate.load_tasks()
                            if prompt.startswith("Task: " + item["title"] + "\n"))
                name = task["editable"][0]
                body = evaluate.fixture_files(task)[name]
                return json.dumps({"files": {name: body}}), "", {
                    "generation_seconds": 0.1, "first_token_seconds": None,
                    "tokens_generated": 1, "prompt_tokens": 1, "tokens_per_second": 10,
                    "reasoning_chars": 0, "answer_chars": 5, "finish_reason": "stop",
                    "timeout_seconds": 3600, "peak_memory_bytes": None, "warning": None,
                }

        with tempfile.TemporaryDirectory() as folder, patch.object(evaluate, "RESULTS", Path(folder)), \
             patch.object(evaluate, "Model", FakeModel):
            args = SimpleNamespace(
                model="gpt_oss_20b", mode="repo", task=None, max_tokens=None,
                repeats=1, timeout_seconds=3600, repair_attempts=0,
                _run_id="20260101T000000000000Z",
            )
            evaluate.run(args)
            run_path = next((Path(folder) / "gpt_oss_20b").iterdir())
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
            text = output.read_text()
            self.assertIn("Validation passing", text)
            self.assertIn("Failure modes", text)
            self.assertIn("Context required", text)


if __name__ == "__main__":
    unittest.main()
