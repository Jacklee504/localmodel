import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import evaluate


class AgentAllowlistTests(unittest.TestCase):
    """The agent may only change allowlisted files, and the harness must notice."""

    def run_agent(self, edit):
        """Run agent mode against a fake opencode that edits files in the workspace."""
        task = next(t for t in evaluate.load_tasks() if t["id"] == "api-key")
        config = {
            "provider": "openai_compatible",
            "base_url": "http://127.0.0.1:11434/v1",
            "model": "test:model",
            "opencode": {"provider": "ollama-local", "model": "test:model"},
        }

        def fake_execute_agent(task, config, workspace, timeout_seconds):
            edit(workspace)
            return {"exit_code": 0, "agent_seconds": 1.0, "transcript_chars": 10,
                    "transcript": "", "workspace_files": [], "stderr": ""}

        with patch.object(evaluate, "execute_agent", fake_execute_agent):
            return evaluate.run_agent_task(task, config, 60)

    def test_a_change_inside_the_allowlist_is_accepted(self):
        def edit(workspace):
            (workspace / "api.py").write_text(
                "from store import save\n\n\ndef put(db, key, value):\n"
                "    if key == '':\n        raise ValueError('empty key')\n"
                "    save(db, key, value)\n    return {'ok': True}\n",
                encoding="utf-8",
            )

        agent = self.run_agent(edit)
        self.assertEqual(agent["unexpected_paths"], [])
        self.assertIn("api.py", agent["modified_files"])
        self.assertNotIn("failure_kind", agent)
        self.assertTrue(agent["validation_passed"])

    def test_a_change_outside_the_allowlist_is_detected(self):
        def edit(workspace):
            (workspace / "api.py").write_text("x = 1\n", encoding="utf-8")
            (workspace / "tests/test_api.py").write_text("# hijacked\n", encoding="utf-8")

        agent = self.run_agent(edit)
        self.assertIn("tests/test_api.py", agent["unexpected_paths"])
        self.assertEqual(agent["failure_kind"], "disallowed_path")
        self.assertIn("tests/test_api.py", agent["error"])

    def test_a_new_file_outside_the_allowlist_is_detected(self):
        def edit(workspace):
            (workspace / "extra.py").write_text("x = 1\n", encoding="utf-8")

        agent = self.run_agent(edit)
        self.assertIn("extra.py", agent["unexpected_paths"])
        self.assertEqual(agent["failure_kind"], "disallowed_path")

    def test_untouched_allowed_files_are_reported(self):
        def edit(workspace):
            pass

        agent = self.run_agent(edit)
        self.assertEqual(agent["modified_files"], [])
        self.assertEqual(sorted(agent["untouched_files"]), ["api.py", "store.py"])


class AgentConfigTests(unittest.TestCase):
    def test_generated_config_targets_one_model(self):
        config = {
            "provider": "openai_compatible",
            "base_url": "http://127.0.0.1:11434/v1",
            "model": "gpt-oss:20b",
            "opencode": {"provider": "ollama-local", "model": "gpt-oss:20b"},
        }
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "opencode.json"
            reference = evaluate.build_agent_config(config, path)
            payload = json.loads(path.read_text())
        self.assertEqual(reference, "ollama-local/gpt-oss:20b")
        provider = payload["provider"]["ollama-local"]
        self.assertEqual(provider["options"]["baseURL"], "http://127.0.0.1:11434/v1")
        self.assertIn("gpt-oss:20b", provider["models"])


if __name__ == "__main__":
    unittest.main()
