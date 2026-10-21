import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import evalcore
import evalrepair


class RepairPromptTests(unittest.TestCase):
    def test_prompt_contains_the_contract_and_the_paths(self):
        task = {"title": "Fix it", "prompt": "Do the thing.", "editable": ["a.py"]}
        prompt = evalrepair.build_repair_prompt(
            task, {"a.py": "x = 1\n"}, "bad answer", "unparseable", "", [], []
        )
        self.assertIn('"files" object', prompt)
        self.assertIn("a.py", prompt)
        self.assertIn("Previous response:", prompt)
        self.assertIn("Previous failure:", prompt)

    def test_prompt_never_contains_withheld_source(self):
        task = {"title": "T", "prompt": "P", "editable": ["a.py"]}
        files = {"a.py": "x = 1\n"}
        prompt = evalrepair.build_repair_prompt(task, files, "", "", "", [], [])
        self.assertNotIn("hidden", prompt)
        self.assertNotIn("test_secret", prompt)

    def test_prompt_omits_withheld_output_when_absent(self):
        task = {"title": "T", "prompt": "P", "editable": ["a.py"]}
        prompt = evalrepair.build_repair_prompt(task, {}, "", "", "", [], [])
        self.assertNotIn("Withheld validation output", prompt)

    def test_validation_output_is_capped(self):
        task = {"title": "T", "prompt": "P", "editable": ["a.py"]}
        checks = [{"command": ["x"], "exit_code": 1, "output": "z" * 40000}]
        prompt = evalrepair.build_repair_prompt(task, {}, "", "", "", checks, [])
        self.assertLessEqual(len(prompt), 20000)


class RepairLoopTests(unittest.TestCase):
    def test_stops_after_a_successful_attempt(self):
        class FakeModel:
            def __init__(self):
                self.calls = 0

            def generate(self, prompt, common, model_settings, timeout_seconds):
                self.calls += 1
                return "answer", "", {"generation_seconds": 1.0}

        class FakeExecute:
            calls = 0

            def __call__(self, task, answer, timings=None):
                FakeExecute.calls += 1
                return {"validation_passed": True, "diff": "", "validation": [],
                        "withheld_validation": []}

        import evaluate
        original = evaluate.execute_repo
        evaluate.execute_repo = FakeExecute()
        try:
            model = FakeModel()
            task = {"id": "api-key", "title": "T", "prompt": "P", "editable": ["api.py"]}
            record = {"response": "bad", "failure_kind": "unparseable", "error": "bad",
                      "repo": None}
            attempts = evalrepair.run_repair_loop(
                task, model, {"max_tokens": 100}, {}, 60, 2, record
            )
            self.assertEqual(len(attempts), 1)
            self.assertEqual(attempts[0]["failure_kind"], "none")
            self.assertEqual(model.calls, 1)
        finally:
            evaluate.execute_repo = original

    def test_stops_at_the_attempt_limit(self):
        class FakeModel:
            def generate(self, prompt, common, model_settings, timeout_seconds):
                return "answer", "", {"generation_seconds": 1.0}

        import evaluate
        original = evaluate.execute_repo

        def failing(task, answer, timings=None):
            return {"validation_passed": False, "diff": "d", "validation": [],
                    "withheld_validation": []}

        evaluate.execute_repo = failing
        try:
            task = {"id": "api-key", "title": "T", "prompt": "P", "editable": ["api.py"]}
            record = {"response": "bad", "failure_kind": "validation_failed",
                      "error": "failed", "repo": {"diff": "d", "validation": [],
                                                  "withheld_validation": []}}
            attempts = evalrepair.run_repair_loop(
                task, FakeModel(), {"max_tokens": 100}, {}, 60, 2, record
            )
            self.assertEqual(len(attempts), 2)
            self.assertTrue(all(a["failure_kind"] == "validation_failed" for a in attempts))
        finally:
            evaluate.execute_repo = original


if __name__ == "__main__":
    unittest.main()
