"""Bulk scoring and tracked export for evaluation runs."""

import json
from datetime import datetime, timezone
from pathlib import Path

import evalcore
from evalcore import EvaluationError, REQUIREMENT_FAILURES, SCHEMA_VERSION


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def score_sheet(sheet_path, dry_run=False, replace=False):
    """Apply a bulk score sheet to a run, validating everything before writing."""
    sheet = read_json(sheet_path)
    version = sheet.get("schema_version")
    if version != 1:
        raise EvaluationError(
            "Unsupported score sheet schema_version " + repr(version)
            + ". This harness supports version 1."
        )
    run_directory = Path(sheet.get("run") or "")
    if not run_directory.is_dir():
        raise EvaluationError("Score sheet run directory not found: " + str(run_directory))
    items = sheet.get("items")
    if not isinstance(items, list):
        raise EvaluationError("Score sheet must contain an 'items' list")

    metadata = read_json(run_directory / "metadata.json")
    task_ids = metadata.get("comparison_key", {}).get("task_ids") or []

    planned = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise EvaluationError("Score sheet item " + str(index) + " must be an object")
        task_id = item.get("task")
        if task_id not in task_ids:
            raise EvaluationError(
                "Score sheet item " + str(index) + " refers to task " + repr(task_id)
                + ", which is not in the run"
            )
        score_value = item.get("score")
        if score_value not in (0, 1, 2):
            raise EvaluationError(
                "Score sheet item " + str(index) + " for " + str(task_id) + " has score "
                + repr(score_value) + ". Valid scores are 0, 1, and 2."
            )
        prompts = item.get("additional_prompts")
        if prompts is not None and (not isinstance(prompts, int) or prompts < 0):
            raise EvaluationError(
                "Score sheet item " + str(index) + " for " + str(task_id)
                + " has an invalid additional_prompts"
            )
        failures = item.get("requirement_failures") or []
        if not isinstance(failures, list):
            raise EvaluationError(
                "Score sheet item " + str(index) + " for " + str(task_id)
                + " has a non-list requirement_failures"
            )
        for failure in failures:
            category = failure if isinstance(failure, str) else (
                failure.get("category") if isinstance(failure, dict) else None
            )
            if category not in REQUIREMENT_FAILURES:
                raise EvaluationError(
                    "Score sheet item " + str(index) + " for " + str(task_id)
                    + " uses unknown failure category " + repr(category)
                    + ". Valid categories: " + ", ".join(REQUIREMENT_FAILURES)
                )
        planned.append((task_id, item))

    changes = []
    for task_id, item in planned:
        path = run_directory / (task_id + ".json")
        record = read_json(path)
        existing = (record.get("manual") or {}).get("score")
        if existing is not None and not replace:
            print("skipping " + str(task_id) + ": already scored " + str(existing)
                  + ". Use --replace to overwrite.")
            continue
        if existing is not None:
            print("WARNING: replacing existing score " + str(existing) + " for " + str(task_id))
        changes.append((task_id, item, path))

    print(str(len(changes)) + " of " + str(len(planned)) + " tasks would be written.")
    for task_id, item, _ in changes:
        print("  " + str(task_id) + ": score " + str(item.get("score")))
    if dry_run:
        print("Dry run. Nothing was written.")
        return 0

    for task_id, item, path in changes:
        record = read_json(path)
        manual = record.get("manual") or {}
        categories = []
        details = []
        for failure in item.get("requirement_failures") or []:
            if isinstance(failure, str):
                categories.append(failure)
            else:
                categories.append(failure.get("category"))
                details.append(failure.get("detail"))
        manual.update({
            "score": item.get("score"),
            "notes": item.get("notes", ""),
            "requirement_failures": categories,
            "failure_details": details,
            "additional_prompts": item.get("additional_prompts"),
            "reviewer": item.get("reviewer"),
        })
        record["manual"] = manual
        temporary = path.with_suffix(".json.tmp")
        write_json(temporary, record)
        temporary.replace(path)
    print("Wrote " + str(len(changes)) + " task records.")
    return len(changes)


def export_run(source, output):
    """Write a tracked summary of a run, without the raw responses."""
    source = Path(source)
    if not source.is_dir():
        raise EvaluationError("Run directory not found: " + str(source))
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    metadata = read_json(source / "metadata.json")
    task_ids = metadata.get("comparison_key", {}).get("task_ids") or []

    tasks = []
    patch_parts = []
    for task_id in task_ids:
        path = source / (task_id + ".json")
        if not path.is_file():
            continue
        record = read_json(path)
        repo = record.get("repo") or {}
        validation = repo.get("validation") or []
        withheld = repo.get("withheld_validation") or []
        tasks.append({
            "task": task_id,
            "category": record.get("category"),
            "failure_kind": record.get("failure_kind", "none"),
            "error": record.get("error"),
            "validation_passed": repo.get("validation_passed"),
            "validation": [
                {"command": check["command"], "exit_code": check["exit_code"]}
                for check in validation
            ],
            "withheld_validation": [
                {"command": check["command"], "exit_code": check["exit_code"]}
                for check in withheld
            ],
            "timings": record.get("timings"),
            "manual": record.get("manual"),
            "changed_files": sorted(repo.get("changes") or {}),
            "diff_lines": len((repo.get("diff") or "").splitlines()),
        })
        if repo.get("diff"):
            patch_parts.append(repo["diff"])

    summary = {
        "schema_version": SCHEMA_VERSION,
        "exported_utc": datetime.now(timezone.utc).isoformat(),
        "raw_run": str(source),
        "model_key": metadata.get("model_key"),
        "model": metadata.get("model_config"),
        "mode": metadata.get("mode"),
        "comparison_key": metadata.get("comparison_key"),
        "runtime": metadata.get("runtime"),
        "tasks": tasks,
    }
    write_json(output / "summary.json", summary)

    lines = [
        "# Run summary: " + str(metadata.get("model_key")),
        "",
        "- mode: " + str(metadata.get("mode")),
        "- raw run: `" + str(source) + "`",
        "- suite sha256: " + str(metadata.get("suite", {}).get("sha256", "n/a")),
        "- max tokens: "
        + str(metadata.get("comparison_key", {}).get("generation", {}).get("max_tokens", "n/a")),
        "- required context: "
        + str(metadata.get("comparison_key", {}).get("context_requirement", "n/a")),
        "- observed context: "
        + str(metadata.get("runtime", {}).get("observed_context_tokens", "n/a")),
        "",
        "| Task | Category | Score | Failure | Validation | Withheld | Seconds |",
        "|---|---|---:|---|---|---|---:|",
    ]
    for task in tasks:
        manual = task.get("manual") or {}
        timings = task.get("timings") or {}
        hidden = task.get("withheld_validation") or []
        withheld = "pass" if hidden and all(c["exit_code"] == 0 for c in hidden) else "n/a"
        score = manual.get("score")
        lines.append(
            "| " + str(task["task"]) + " | " + str(task.get("category", "")) + " | "
            + (str(score) if score is not None else "n/a") + " | "
            + str(task.get("failure_kind")) + " | "
            + str(task.get("validation_passed")) + " | " + withheld + " | "
            + str(timings.get("generation_seconds", "n/a")) + " |"
        )
    lines += ["", "## Review notes", ""]
    for task in tasks:
        manual = task.get("manual") or {}
        if manual.get("notes"):
            lines.append("- **" + str(task["task"]) + "**: " + str(manual["notes"]))
        if manual.get("requirement_failures"):
            lines.append(
                "  - requirement failures: " + ", ".join(manual["requirement_failures"])
            )
    (output / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (output / "changes.patch").write_text("".join(patch_parts), encoding="utf-8")
    print("Exported " + str(len(tasks)) + " tasks to " + str(output))
    return len(tasks)
