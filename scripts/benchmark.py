"""Single-command benchmark runner for candidate models.

This wraps the whole overnight procedure: check the model is present, check the served
context, run one or more suites, and write a summary. It never downloads weights and
never deletes anything.

Examples:

    python scripts/benchmark.py --model gpt_oss_20b
    python scripts/benchmark.py --model gpt_oss_20b --suites implementation,debugging
    python scripts/benchmark.py --model gpt_oss_20b --repeats 3
    python scripts/benchmark.py --model gpt_oss_20b --report reports/summary.json
"""

import argparse
import json
import shutil
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import evalcore  # noqa: E402
import evaluate  # noqa: E402


def ollama(*arguments):
    """Run an ollama command and return (exit_code, output)."""
    try:
        process = subprocess.run(
            ["ollama", *arguments],
            capture_output=True,
            text=True,
            timeout=120,
        )
        return process.returncode, (process.stdout or "") + (process.stderr or "")
    except (OSError, subprocess.SubprocessError) as exc:
        return 1, "could not run ollama: " + str(exc)


def ollama_json(*arguments):
    """Run an ollama command that returns JSON and parse it."""
    code, output = ollama(*arguments)
    if code != 0:
        return None


def ollama_api(path, base_url="http://127.0.0.1:11434"):
    """Read a JSON document from the Ollama HTTP API."""
    try:
        request = urllib.request.Request(
            base_url.rstrip("/") + path, headers={"Accept": "application/json"}
        )
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.load(response)
    except Exception:
        return None
    try:
        return json.loads(output)
    except ValueError:
        return None


def ollama_ps():
    """Return the loaded models."""
    payload = ollama_api("/api/ps") or {}
    return payload.get("models") or []


def model_is_installed(tag):
    """Whether the given tag is present in the local Ollama store."""
    if not tag:
        return False
    payload = ollama_api("/api/tags") or {}
    entries = payload.get("models") or []
    for entry in entries:
        name = entry.get("name") or ""
        if name == tag or name == tag + ":latest":
            return True
    return False


def disk_free_gib():
    try:
        return shutil.disk_usage(ROOT).free / 2 ** 30
    except OSError:
        return None


def check_preconditions(config):
    """Check the model is present and the served context is adequate."""
    problems = []
    served = config.get("model")
    if not served:
        return problems
    if not model_is_installed(served):
        pull = (config.get("ollama") or {}).get("pull_command")
        problems.append(
            "Model " + served + " is not installed. Run: "
            + (pull or "ollama pull " + served)
        )
        return problems
    required = (config.get("context") or {}).get("num_ctx")
    if not required:
        return problems
    entry = next(
        (item for item in ollama_ps() if item.get("name") == served), None
    )
    if entry is None:
        problems.append(
            "Model " + served + " is installed but not loaded, so the served context "
            "cannot be confirmed yet. It loads on the first request."
        )
        return problems
    observed = entry.get("context_length")
    if observed and observed < required:
        problems.append(
            "Model " + served + " is serving a context of " + str(observed)
            + ", below the required " + str(required) + ". Restart Ollama with "
            + "OLLAMA_CONTEXT_LENGTH=" + str(required) + " and retry."
        )
    return problems


def run_suite(model_key, mode, suite, repeats, max_tokens, timeout_seconds):
    """Run one suite and return the run directories it produced."""
    directories = []
    for attempt in range(1, repeats + 1):
        command = [
            sys.executable,
            str(ROOT / "scripts/evaluate.py"),
            "run",
            "--model", model_key,
            "--mode", mode,
            "--repeats", "1",
            "--timeout-seconds", str(timeout_seconds),
        ]
        if suite:
            command += ["--suite", suite]
        if max_tokens:
            command += ["--max-tokens", str(max_tokens)]
        print()
        print("=== " + mode + " suite " + (suite or "all")
              + " attempt " + str(attempt) + "/" + str(repeats) + " ===", flush=True)
        subprocess.run(command, cwd=ROOT, text=True)
        found = sorted((ROOT / "results" / model_key).glob("2026*"))
        if found:
            directories.append(found[-1])
    return directories


def summarise(directories):
    """Return a summary of the run directories."""
    summary = {"runs": []}
    for directory in directories:
        metadata_path = directory / "metadata.json"
        if not metadata_path.is_file():
            continue
        metadata = evalcore.read_json(metadata_path)
        task_ids = metadata.get("comparison_key", {}).get("task_ids") or []
        rows = []
        for task_id in task_ids:
            path = directory / (task_id + ".json")
            if path.is_file():
                rows.append(evalcore.read_json(path))
        validation = 0
        withheld = 0
        failures = {}
        seconds = []
        tokens = []
        for row in rows:
            repo = row.get("repo") or {}
            if repo.get("validation_passed"):
                validation += 1
            hidden = repo.get("withheld_validation") or []
            if hidden and all(check["exit_code"] == 0 for check in hidden):
                withheld += 1
            kind = row.get("failure_kind", "none")
            failures[kind] = failures.get(kind, 0) + 1
            timings = row.get("timings") or {}
            if timings.get("generation_seconds"):
                seconds.append(timings["generation_seconds"])
            if timings.get("tokens_per_second"):
                tokens.append(timings["tokens_per_second"])
        runtime = metadata.get("runtime") or {}
        key = metadata.get("comparison_key") or {}
        summary["runs"].append({
            "path": str(directory),
            "mode": metadata.get("mode"),
            "tasks": len(rows),
            "validation_passing": validation,
            "withheld_passing": withheld,
            "failures": failures,
            "average_seconds": round(sum(seconds) / len(seconds), 2) if seconds else None,
            "average_tokens_per_second": round(sum(tokens) / len(tokens), 2) if tokens else None,
            "observed_context": runtime.get("observed_context_tokens"),
            "required_context": key.get("context_requirement"),
        })
    return summary


def print_summary(summary, model_key):
    print()
    print("=" * 68)
    print("BENCHMARK SUMMARY: " + model_key)
    print("=" * 68)
    for run in summary["runs"]:
        print()
        print(run["path"])
        print("  mode              " + str(run["mode"]))
        print("  tasks             " + str(run["tasks"]))
        print("  validation pass   " + str(run["validation_passing"]) + "/" + str(run["tasks"]))
        print("  withheld pass     " + str(run["withheld_passing"]) + "/" + str(run["tasks"]))
        print("  avg seconds       " + str(run["average_seconds"]))
        print("  avg tokens/sec    " + str(run["average_tokens_per_second"]))
        print("  context           required " + str(run["required_context"])
              + ", observed " + str(run["observed_context"]))
        other = {k: v for k, v in run["failures"].items() if k != "none"}
        if other:
            parts = []
            for kind in sorted(other):
                parts.append(kind + "=" + str(other[kind]))
            print("  failures          " + ", ".join(parts))
    print()
    print("Scores are still manual. Record them with:")
    print("  .venv/bin/python scripts/evaluate.py score results/" + model_key + "/RUN_ID \\")
    print("    --task TASK_ID --score 0|1|2 --notes '...' --reviewer local-user")
    print("Then compare candidates with:")
    print("  .venv/bin/python scripts/evaluate.py compare RUN_A RUN_B "
          "--output reports/comparison.md")


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--model", required=True, help="Model key from config/models.json")
    parser.add_argument("--suites", default="all",
                        help="Comma-separated suite names from config/suites.json")
    parser.add_argument("--mode", choices=("repo", "response", "both"), default="repo")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--max-tokens", type=int, default=None)
    parser.add_argument("--timeout-seconds", type=int, default=3600)
    parser.add_argument("--report", help="Write the JSON summary to this path")
    args = parser.parse_args()

    try:
        config = evalcore.load_model_config(ROOT / "config/models.json", args.model)
    except evalcore.EvaluationError as exc:
        parser.exit(1, "Evaluation error: " + str(exc) + "\n")

    free = disk_free_gib()
    print("Model:    " + str(config.get("name")) + " (" + args.model + ")")
    print("Endpoint: " + str(config.get("base_url")))
    if free:
        print("Disk free: " + ("%.1f" % free) + " GiB")
    print("Started:  " + datetime.now(timezone.utc).isoformat())

    problems = check_preconditions(config)
    if problems:
        print()
        print("PRE-RUN PROBLEMS:")
        for problem in problems:
            print("  - " + problem)
        if not model_is_installed(config.get("model") or ""):
            parser.exit(1, "\nThe model is not installed. Pull it, then run again.\n")
        print()
        print("The run will continue, but fix these first for a comparable result.")

    suites = [name.strip() for name in args.suites.split(",") if name.strip()]
    known = set(evaluate.load_suites())
    for suite in suites:
        if suite not in known:
            parser.exit(1, "Evaluation error: unknown suite " + repr(suite)
                           + ". Available: " + ", ".join(sorted(known)) + "\n")

    modes = ["repo", "response"] if args.mode == "both" else [args.mode]
    all_directories = []
    for mode in modes:
        for suite in suites:
            all_directories.extend(run_suite(
                args.model, mode, suite, args.repeats, args.max_tokens, args.timeout_seconds
            ))

    summary = summarise(all_directories)
    summary["model"] = args.model
    summary["created_utc"] = datetime.now(timezone.utc).isoformat()
    print_summary(summary, args.model)

    if args.report:
        path = Path(args.report)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print()
        print("Summary written to " + str(path))

    print()
    print("Finished: " + datetime.now(timezone.utc).isoformat())


if __name__ == "__main__":
    main()
