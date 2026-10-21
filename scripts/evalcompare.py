"""Multi-model comparison report.

Groups runs by mode and model key, aggregates repeated attempts, and separates
response, repository, and agent results so a response-mode run is never reported
as if it had validation.
"""

import statistics
from datetime import datetime, timezone
from pathlib import Path

from evalcore import FAILURE_KINDS, REQUIREMENT_FAILURES


def _median(values):
    numbers = [value for value in values if value is not None]
    if not numbers:
        return "n/a"
    return "%.2f" % statistics.median(numbers)


def _mean_score(rows):
    scores = [row["manual"]["score"] for row in rows
              if (row.get("manual") or {}).get("score") is not None]
    if not scores:
        return "n/a"
    return "%.2f" % (sum(scores) / len(scores))


def _majority_success(rows):
    """Tasks where a score of 2 won the majority of scored attempts."""
    by_task = {}
    for row in rows:
        by_task.setdefault(row["id"], []).append(row)
    count = 0
    for attempts in by_task.values():
        scores = [a["manual"]["score"] for a in attempts
                  if (a.get("manual") or {}).get("score") is not None]
        if scores and scores.count(2) > len(scores) / 2:
            count += 1
    return count


def _mixed_tasks(rows):
    """Tasks whose attempts received different scores."""
    by_task = {}
    for row in rows:
        by_task.setdefault(row["id"], []).append(row)
    count = 0
    for attempts in by_task.values():
        scores = {(a.get("manual") or {}).get("score") for a in attempts}
        if len(scores) > 1:
            count += 1
    return count


def is_remote(metadata):
    config = metadata.get("model_config") or {}
    context = config.get("context") or {}
    served = config.get("model") or ""
    if context.get("num_ctx"):
        return False
    return ":cloud" in served or served.endswith("-cloud")


def context_status(metadata):
    required = metadata.get("comparison_key", {}).get("context_requirement")
    observed = metadata.get("runtime", {}).get("observed_context_tokens")
    if not required:
        return "n/a (remote)" if is_remote(metadata) else "not configured"
    if observed is None:
        return "n/a (remote)" if is_remote(metadata) else "not observed"
    return "ok" if observed >= required else "below requirement"


def _group(runs):
    """Group runs by mode, then by model key, preserving order."""
    groups = []
    for metadata, rows in runs:
        mode = metadata.get("mode")
        key = metadata.get("model_key")
        found = None
        for group in groups:
            if group["mode"] == mode and group["key"] == key:
                found = group
                break
        if found is None:
            found = {"mode": mode, "key": key, "attempts": [], "rows": []}
            groups.append(found)
        found["attempts"].append(metadata)
        found["rows"].extend(rows)
    return groups


def _warnings(groups):
    warnings = []
    for group in groups:
        for metadata in group["attempts"]:
            run_id = metadata.get("run_id", "unknown")
            if not metadata.get("comparison_key"):
                warnings.append("Legacy run without a comparison key: " + str(run_id))
            if context_status(metadata) == "below requirement":
                warnings.append(
                    "Operationally non-compliant context in " + str(run_id) + ": serving "
                    + str(metadata.get("runtime", {}).get("observed_context_tokens"))
                    + " below required "
                    + str(metadata.get("comparison_key", {}).get("context_requirement"))
                )
        unscored = sum(1 for row in group["rows"]
                       if (row.get("manual") or {}).get("score") is None)
        if unscored:
            warnings.append(str(unscored) + " unscored record(s) in " + str(group["key"]))
    return warnings


def _summary_rows(mode_groups):
    rows = []

    def add(label, function):
        rows.append("| " + label + " | "
                    + " | ".join(function(group) for group in mode_groups) + " |")

    add("Attempts completed",
        lambda g: str(len(g["attempts"])) + " (" + str(len(g["rows"])) + " records)")
    add("Transport-valid attempts", lambda g: str(sum(
        row.get("failure_kind") not in ("http_error", "timeout") for row in g["rows"]))
        + "/" + str(len(g["rows"])))
    add("Manually reviewed", lambda g: str(sum(
        (row.get("manual") or {}).get("score") is not None for row in g["rows"]))
        + "/" + str(len(g["rows"])))
    add("Mean manual score, scored attempts", lambda g: _mean_score(g["rows"]))
    add("Majority task success", lambda g: str(_majority_success(g["rows"])))
    add("First-pass score-2 tasks", lambda g: str(sum(
        (row.get("manual") or {}).get("score") == 2
        and (row.get("manual") or {}).get("additional_prompts") == 0
        for row in g["rows"])))
    add("Final score-2 tasks", lambda g: str(sum(
        (row.get("manual") or {}).get("score") == 2 for row in g["rows"])))
    return rows


def build_report(runs, output_path=None):
    """Build the comparison report. Runs are (metadata, rows) pairs."""
    groups = _group(runs)
    modes = []
    for group in groups:
        if group["mode"] not in modes:
            modes.append(group["mode"])

    first = runs[0][0]
    key = first.get("comparison_key") or {}
    lines = ["# Local model comparison", ""]
    lines += [
        "- generated: " + datetime.now(timezone.utc).isoformat(),
        "- protocol version: " + str(key.get("protocol_version", "n/a")),
        "- suite sha256: " + str(key.get("suite_sha256", "n/a")),
        "- tasks: " + ", ".join(key.get("task_ids", [])),
        "- max tokens: " + str(key.get("generation", {}).get("max_tokens", "n/a")),
        "- context requirement: " + str(key.get("context_requirement", "n/a")),
        "- run ids: " + ", ".join(
            str(metadata.get("run_id", "unknown")) for metadata, _ in runs
        ),
        "",
        "Response, repository, and agent modes are separate. A response-mode run has no "
        "validation and is never reported as if it had any. Only runs in the same mode "
        "are compared with each other.",
        "",
    ]

    warnings = _warnings(groups)
    if warnings:
        lines += ["## Warnings", ""]
        for warning in warnings:
            lines.append("- " + warning)
        lines.append("")

    for mode in modes:
        mode_groups = [group for group in groups if group["mode"] == mode]
        lines += ["## Mode: " + mode, "", "### Decision summary", ""]
        lines += ["| Metric | " + " | ".join(g["key"] for g in mode_groups) + " |",
                  "|---|" + "---:|" * len(mode_groups)]
        lines += _summary_rows(mode_groups)
        if mode in ("repo", "agent"):
            lines.append("| Validation-passing attempts | " + " | ".join(
                str(sum(bool(row.get("repo") and row["repo"].get("validation_passed"))
                        for row in g["rows"])) + "/" + str(len(g["rows"]))
                for g in mode_groups) + " |")
        lines += [
            "| Requirement failures | " + " | ".join(
                str(sum(len((row.get("manual") or {}).get("requirement_failures") or [])
                        for row in g["rows"]))
                for g in mode_groups) + " |",
            "| Mixed-score tasks | " + " | ".join(
                str(_mixed_tasks(g["rows"])) for g in mode_groups) + " |",
            "| Median tokens/sec | " + " | ".join(
                _median([(row.get("timings") or {}).get("tokens_per_second")
                         for row in g["rows"]])
                for g in mode_groups) + " |",
            "| Median request seconds | " + " | ".join(
                _median([(row.get("timings") or {}).get("generation_seconds")
                         for row in g["rows"]])
                for g in mode_groups) + " |",
            "| Observed Ollama context | " + " | ".join(
                ", ".join(sorted({str(m.get("runtime", {}).get("observed_context_tokens"))
                                  for m in g["attempts"]}))
                for g in mode_groups) + " |",
            "| Operational status | " + " | ".join(
                ", ".join(sorted({context_status(m) for m in g["attempts"]}))
                for g in mode_groups) + " |",
        ]

        lines += ["", "### Task success and stability", "",
                  "| Task | " + " | ".join(g["key"] for g in mode_groups) + " |",
                  "|---|" + "---:|" * len(mode_groups)]
        task_ids = []
        for group in mode_groups:
            for row in group["rows"]:
                if row["id"] not in task_ids:
                    task_ids.append(row["id"])
        for task_id in task_ids:
            cells = []
            for group in mode_groups:
                attempts = [row for row in group["rows"] if row["id"] == task_id]
                scores = [(row.get("manual") or {}).get("score") for row in attempts]
                known = [score for score in scores if score is not None]
                if not known:
                    majority = "n/a"
                elif known.count(2) > len(known) / 2:
                    majority = "2"
                elif known.count(1) > len(known) / 2:
                    majority = "1"
                else:
                    majority = "0"
                validation = sum(
                    bool(row.get("repo") and row["repo"].get("validation_passed"))
                    for row in attempts
                )
                kinds = ", ".join(sorted({row.get("failure_kind", "none") for row in attempts}))
                prompts = ", ".join(
                    str((row.get("manual") or {}).get("additional_prompts")) for row in attempts
                )
                cells.append(
                    str(len(attempts)) + " att | " + ",".join(str(s) for s in scores)
                    + " | maj " + majority + " | val " + str(validation) + "/" + str(len(attempts))
                    + " | " + kinds + " | prom " + prompts
                )
            lines.append("| " + task_id + " | " + " | ".join(cells) + " |")

        lines += ["", "### Category breakdown", "",
                  "| Category | " + " | ".join(g["key"] for g in mode_groups) + " |",
                  "|---|" + "---:|" * len(mode_groups)]
        categories = []
        for group in mode_groups:
            for row in group["rows"]:
                if row.get("category") not in categories:
                    categories.append(row.get("category"))
        for category in categories:
            cells = []
            for group in mode_groups:
                matching = [row for row in group["rows"] if row.get("category") == category]
                task_count = len({row["id"] for row in matching})
                score_two = sum((row.get("manual") or {}).get("score") == 2
                                for row in matching)
                if mode in ("repo", "agent"):
                    validation = str(sum(
                        bool(row.get("repo") and row["repo"].get("validation_passed"))
                        for row in matching)) + "/" + str(len(matching))
                else:
                    validation = "n/a"
                failures = sum(
                    len((row.get("manual") or {}).get("requirement_failures") or [])
                    for row in matching
                )
                unstable = 0
                by_task = {}
                for row in matching:
                    by_task.setdefault(row["id"], []).append(row)
                for attempts in by_task.values():
                    if len({(a.get("manual") or {}).get("score") for a in attempts}) > 1:
                        unstable += 1
                cells.append(
                    str(task_count) + " | " + str(score_two) + " | " + _mean_score(matching)
                    + " | " + validation + " | " + str(failures) + " | " + str(unstable)
                )
            lines.append("| " + str(category) + " | " + " | ".join(cells) + " |")

        lines += ["", "### Failure-mode breakdown", "",
                  "| Failure kind | " + " | ".join(g["key"] for g in mode_groups) + " |",
                  "|---|" + "---:|" * len(mode_groups)]
        for kind in FAILURE_KINDS:
            lines.append("| " + kind + " | " + " | ".join(
                str(sum(row.get("failure_kind") == kind for row in g["rows"]))
                for g in mode_groups) + " |")

        lines += ["", "### Requirement failure categories", "",
                  "| Category | " + " | ".join(g["key"] for g in mode_groups) + " |",
                  "|---|" + "---:|" * len(mode_groups)]
        for category in REQUIREMENT_FAILURES:
            lines.append("| " + category + " | " + " | ".join(
                str(sum((row.get("manual") or {}).get("requirement_failures") or []).count(
                    category) if False else
                    sum(((row.get("manual") or {}).get("requirement_failures") or []).count(
                        category) for row in g["rows"]))
                for g in mode_groups) + " |")

        lines += ["", "### Per-task table", "",
                  "| Task | Category | Model | Score | Validation | Failure | "
                  "Additional prompts | Modified | Untouched | Unexpected | Review note |",
                  "|---|---|---|---:|---|---|---:|---|---|---|---|"]
        for group in mode_groups:
            for row in group["rows"]:
                manual = row.get("manual") or {}
                agent = row.get("agent") or {}
                repo = row.get("repo") or {}
                validation = repo.get("validation_passed")
                score = manual.get("score")
                lines.append(
                    "| " + str(row["id"]) + " | " + str(row.get("category", "")) + " | "
                    + str(group["key"]) + " | "
                    + (str(score) if score is not None else "n/a") + " | "
                    + (str(validation) if validation is not None else "n/a") + " | "
                    + str(row.get("failure_kind", "none")) + " | "
                    + str(manual.get("additional_prompts")) + " | "
                    + (", ".join(agent.get("modified_files") or []) or "n/a") + " | "
                    + (", ".join(agent.get("untouched_files") or []) or "n/a") + " | "
                    + (", ".join(agent.get("unexpected_paths") or []) or "n/a") + " | "
                    + (manual.get("notes") or "") + " |"
                )
        lines.append("")

    output = "\n".join(lines) + "\n"
    if output_path:
        Path(output_path).write_text(output, encoding="utf-8")
        print("Comparison written to " + str(output_path))
    else:
        print(output, end="")
    return output
