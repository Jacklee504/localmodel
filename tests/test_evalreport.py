import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import evalcore
import evalreport


class ScoreSheetTests(unittest.TestCase):
    def build_run(self, folder, task_ids=("alpha", "beta")):
        run = Path(folder) / "run"
        run.mkdir(parents=True, exist_ok=True)
        (run / "metadata.json").write_text(json.dumps({
            "model_key": "test",
            "mode": "repo",
            "comparison_key": {"task_ids": list(task_ids), "protocol_version": 2},
        }), encoding="utf-8")
        for task_id in task_ids:
            (run / (task_id + ".json")).write_text(json.dumps({
                "id": task_id,
                "category": "test",
                "failure_kind": "none",
                "repo": {"validation_passed": True, "validation": [], "withheld_validation": []},
                "manual": {"score": None, "notes": "", "requirement_failures": [],
                           "failure_details": [], "additional_prompts": None, "reviewer": None},
            }), encoding="utf-8")
        return run

    def write_sheet(self, folder, run, items):
        path = Path(folder) / "sheet.json"
        path.write_text(json.dumps({
            "schema_version": 1, "run": str(run), "items": items,
        }), encoding="utf-8")
        return path

    def test_sheet_applies_scores(self):
        with tempfile.TemporaryDirectory() as folder:
            run = self.build_run(folder)
            sheet = self.write_sheet(folder, run, [
                {"task": "alpha", "score": 2, "notes": "good", "additional_prompts": 0,
                 "reviewer": "me"},
            ])
            evalreport.score_sheet(sheet)
            record = json.loads((run / "alpha.json").read_text())
            self.assertEqual(record["manual"]["score"], 2)
            self.assertEqual(record["manual"]["notes"], "good")
            self.assertEqual(record["manual"]["reviewer"], "me")

    def test_omitted_task_stays_unreviewed(self):
        with tempfile.TemporaryDirectory() as folder:
            run = self.build_run(folder)
            sheet = self.write_sheet(folder, run, [
                {"task": "alpha", "score": 1, "notes": ""},
            ])
            evalreport.score_sheet(sheet)
            record = json.loads((run / "beta.json").read_text())
            self.assertIsNone(record["manual"]["score"])

    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as folder:
            run = self.build_run(folder)
            sheet = self.write_sheet(folder, run, [{"task": "alpha", "score": 2}])
            evalreport.score_sheet(sheet, dry_run=True)
            record = json.loads((run / "alpha.json").read_text())
            self.assertIsNone(record["manual"]["score"])

    def test_existing_score_is_not_overwritten_without_replace(self):
        with tempfile.TemporaryDirectory() as folder:
            run = self.build_run(folder)
            sheet = self.write_sheet(folder, run, [{"task": "alpha", "score": 2}])
            evalreport.score_sheet(sheet)
            second = self.write_sheet(folder, run, [{"task": "alpha", "score": 0}])
            evalreport.score_sheet(second)
            record = json.loads((run / "alpha.json").read_text())
            self.assertEqual(record["manual"]["score"], 2)

    def test_replace_overwrites(self):
        with tempfile.TemporaryDirectory() as folder:
            run = self.build_run(folder)
            sheet = self.write_sheet(folder, run, [{"task": "alpha", "score": 2}])
            evalreport.score_sheet(sheet)
            second = self.write_sheet(folder, run, [{"task": "alpha", "score": 0}])
            evalreport.score_sheet(second, replace=True)
            record = json.loads((run / "alpha.json").read_text())
            self.assertEqual(record["manual"]["score"], 0)

    def test_invalid_score_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            run = self.build_run(folder)
            sheet = self.write_sheet(folder, run, [{"task": "alpha", "score": 5}])
            with self.assertRaises(evalcore.EvaluationError):
                evalreport.score_sheet(sheet)

    def test_unknown_failure_category_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            run = self.build_run(folder)
            sheet = self.write_sheet(folder, run, [
                {"task": "alpha", "score": 1, "requirement_failures": ["made_up"]},
            ])
            with self.assertRaises(evalcore.EvaluationError):
                evalreport.score_sheet(sheet)

    def test_unknown_task_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            run = self.build_run(folder)
            sheet = self.write_sheet(folder, run, [{"task": "missing", "score": 1}])
            with self.assertRaises(evalcore.EvaluationError):
                evalreport.score_sheet(sheet)

    def test_negative_additional_prompts_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            run = self.build_run(folder)
            sheet = self.write_sheet(folder, run, [
                {"task": "alpha", "score": 1, "additional_prompts": -1},
            ])
            with self.assertRaises(evalcore.EvaluationError):
                evalreport.score_sheet(sheet)


class ExportTests(unittest.TestCase):
    def test_export_writes_three_files(self):
        with tempfile.TemporaryDirectory() as folder:
            run = Path(folder) / "run"
            run.mkdir(parents=True)
            (run / "metadata.json").write_text(json.dumps({
                "model_key": "test",
                "mode": "repo",
                "comparison_key": {"task_ids": ["alpha"], "generation": {"max_tokens": 8192}},
                "runtime": {"observed_context_tokens": 65536},
            }), encoding="utf-8")
            (run / "alpha.json").write_text(json.dumps({
                "id": "alpha",
                "category": "test",
                "failure_kind": "none",
                "repo": {
                    "validation_passed": True,
                    "validation": [{"command": ["x"], "exit_code": 0}],
                    "withheld_validation": [{"command": ["y"], "exit_code": 0}],
                    "changes": {"a.py": "x"},
                    "diff": "--- a/a.py\n+++ b/a.py\n",
                },
                "manual": {"score": 2, "notes": "ok", "requirement_failures": []},
                "timings": {"generation_seconds": 1.5},
            }), encoding="utf-8")
            output = Path(folder) / "out"
            evalreport.export_run(run, output)
            self.assertTrue((output / "summary.json").is_file())
            self.assertTrue((output / "summary.md").is_file())
            self.assertTrue((output / "changes.patch").is_file())
            summary = json.loads((output / "summary.json").read_text())
            self.assertEqual(summary["tasks"][0]["score"] if "score" in summary["tasks"][0]
                             else summary["tasks"][0]["manual"]["score"], 2)
            self.assertIn("a.py", (output / "changes.patch").read_text())

    def test_export_of_a_missing_run_raises(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(evalcore.EvaluationError):
                evalreport.export_run(Path(folder) / "absent", Path(folder) / "out")


if __name__ == "__main__":
    unittest.main()
