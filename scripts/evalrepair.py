"""Optional bounded repair loop for JSON repository mode.

Off by default. At most two attempts. Each attempt is evaluated in a fresh copy
of the original fixture, so attempts are independent rather than cumulative.
Withheld test source code is never included in a repair prompt; only its
validation output may be shown.
"""

import json
import shutil
import tempfile
import time
from pathlib import Path

import evalcore
from evalcore import ModelFailure

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_CAP = 16000


def build_repair_prompt(task, files, response, failure, diff, validation, withheld):
    """Build the repair prompt. Withheld test source is never included."""
    if validation and not isinstance(validation, str):
        validation = _validation_text(validation)
    if withheld and not isinstance(withheld, str):
        withheld = _validation_text(withheld)
    blocks = []
    blocks.append("The previous attempt did not satisfy the task.\n")
    blocks.append("Task:\n" + task["title"] + "\n" + task["prompt"] + "\n")
    blocks.append("Original files:\n")
    for name in sorted(files):
        blocks.append("--- " + name + " ---\n" + files[name] + "\n")
    blocks.append("Previous response:\n" + (response or "") + "\n")
    blocks.append("Previous failure:\n" + str(failure) + "\n")
    if diff:
        blocks.append("Current diff:\n" + diff + "\n")
    if validation:
        blocks.append("Validation output:\n" + validation[-OUTPUT_CAP:] + "\n")
    if withheld:
        blocks.append("Withheld validation output:\n" + withheld[-OUTPUT_CAP:] + "\n")
    blocks.append(
        "Return only a JSON object with a \"files\" object mapping each changed path "
        "to its complete new UTF-8 contents. Change only these paths: "
        + ", ".join(task["editable"]) + "."
    )
    return "\n".join(blocks)


def _validation_text(checks):
    parts = []
    for check in checks or []:
        parts.append(
            "$ " + " ".join(check["command"]) + "\nexit=" + str(check["exit_code"]) + "\n"
            + (check.get("output") or "")[-OUTPUT_CAP:]
        )
    return "\n".join(parts)[-OUTPUT_CAP:]


def attempt_repair(task, model, common, model_settings, timeout_seconds, previous):
    """Run one repair attempt in a fresh copy of the fixture.

    Returns (answer, timings, repo_result) where repo_result may be None if the
    repair could not be applied.
    """
    fixture = ROOT / "tasks/fixtures" / task["id"]
    files = {}
    for path in sorted(fixture.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        relative = str(path.relative_to(fixture))
        if relative.split("/")[0] == "hidden":
            continue
        files[relative] = path.read_text(encoding="utf-8", errors="replace")

    prompt = build_repair_prompt(
        task,
        files,
        previous.get("response"),
        previous.get("failure"),
        previous.get("diff"),
        _validation_text(previous.get("validation")),
        _validation_text(previous.get("withheld_validation")),
    )
    answer, reasoning, timings = model.generate(
        prompt, common, model_settings, timeout_seconds
    )
    return answer, reasoning, timings


def run_repair_loop(task, model, common, model_settings, timeout_seconds, max_attempts, record):
    """Run repair attempts for a failed task, returning the list of attempt records."""
    attempts = []
    previous = {
        "response": record.get("response"),
        "failure": record.get("error") or record.get("failure_kind"),
        "diff": (record.get("repo") or {}).get("diff"),
        "validation": (record.get("repo") or {}).get("validation"),
        "withheld_validation": (record.get("repo") or {}).get("withheld_validation"),
    }
    for index in range(1, max_attempts + 1):
        started = time.perf_counter()
        entry = {"attempt": index, "answer": None, "timings": None,
                 "failure_kind": "none", "error": None, "repo": None}
        try:
            answer, reasoning, timings = attempt_repair(
                task, model, common, model_settings, timeout_seconds, previous
            )
            entry["answer"] = answer
            entry["timings"] = timings
            from evaluate import execute_repo
            entry["repo"] = execute_repo(task, answer, timings)
            if not entry["repo"]["validation_passed"]:
                entry["failure_kind"] = "validation_failed"
        except ModelFailure as failure:
            entry["failure_kind"] = failure.kind
            entry["error"] = failure.message
        except Exception as exc:
            entry["failure_kind"] = "unparseable"
            entry["error"] = f"{type(exc).__name__}: {exc}"
        entry["wall_seconds"] = round(time.perf_counter() - started, 3)
        attempts.append(entry)
        if entry["failure_kind"] == "none":
            break
        previous = {
            "response": entry.get("answer"),
            "failure": entry.get("error") or entry.get("failure_kind"),
            "diff": (entry.get("repo") or {}).get("diff"),
            "validation": (entry.get("repo") or {}).get("validation"),
            "withheld_validation": (entry.get("repo") or {}).get("withheld_validation"),
        }
    return attempts
