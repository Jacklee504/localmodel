"""Small local-model evaluator for response and isolated repository tasks."""

import argparse
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "tasks/core.json"
MODELS = ROOT / "config/models.json"
RESULTS = ROOT / "results"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def safe_name(value):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", value):
        raise ValueError(f"Invalid name: {value}")
    return value


def safe_file(value):
    path = Path(value)
    if path.is_absolute() or not path.parts or any(part in (".", "..") for part in path.parts):
        raise ValueError(f"Unsafe fixture path: {value}")
    return path


def load_tasks():
    data = read_json(SUITE)
    tasks = data["tasks"]
    ids = set()
    for task in tasks:
        task_id = safe_name(task["id"])
        if task_id in ids:
            raise ValueError(f"Duplicate task: {task_id}")
        ids.add(task_id)
        fixture = ROOT / "tasks/fixtures" / task_id
        if not fixture.is_dir():
            raise ValueError(f"Missing fixture: {fixture}")
        for name in task["editable"]:
            safe_file(name)
            if not (fixture / name).is_file():
                raise ValueError(f"Missing editable file: {fixture / name}")
        for command in task["validation"]:
            if not isinstance(command, list) or not command or not all(isinstance(x, str) for x in command):
                raise ValueError(f"Invalid validation command in {task_id}")
    return tasks


def suite_hash(tasks):
    digest = hashlib.sha256(SUITE.read_bytes())
    for task in tasks:
        for name, body in fixture_files(task).items():
            digest.update(task["id"].encode())
            digest.update(name.encode())
            digest.update(body.encode())
    return digest.hexdigest()


def fixture_files(task):
    fixture = ROOT / "tasks/fixtures" / task["id"]
    files = {}
    for path in sorted(fixture.rglob("*")):
        if "__pycache__" in path.parts or path.suffix in (".pyc", ".class"):
            continue
        if path.is_symlink():
            raise ValueError(f"Symlink in fixture: {path}")
        if path.is_file():
            files[str(path.relative_to(fixture))] = path.read_text(encoding="utf-8")
    return files


def make_prompt(task, mode):
    files = fixture_files(task)
    shown = "\n\n".join(f"--- {name} ---\n{body}" for name, body in files.items())
    prompt = f"Task: {task['title']}\n\n{task['prompt']}\n\nRepository files:\n{shown}"
    if mode == "repo":
        prompt += ("\n\nReturn only a JSON object with a 'files' object mapping each changed path "
                   "to its complete new UTF-8 contents. Change only these paths: "
                   + ", ".join(task["editable"]) + ". Do not include unchanged files.")
    return prompt


class Model:
    def __init__(self, config):
        self.config = config
        self.loaded = None
        if config["provider"] == "mlx":
            path = Path(config["path"])
            if not path.is_absolute():
                path = ROOT / path
            if not (path / "config.json").is_file():
                raise ValueError(f"Local model unavailable: {path}")
            from mlx_lm import load
            self.loaded = load(str(path))
        elif config["provider"] != "openai_compatible":
            raise ValueError(f"Unsupported provider: {config['provider']}")

    def generate(self, prompt, max_tokens):
        start = time.perf_counter()
        if self.loaded:
            from mlx_lm import generate
            model, tokenizer = self.loaded
            chat = tokenizer.apply_chat_template(
                [{"role": "user", "content": prompt}], tokenize=False, add_generation_prompt=True
            )
            answer = generate(model, tokenizer, chat, max_tokens=max_tokens, verbose=False)
            tokens = len(tokenizer.encode(answer))
            first_token = None
        else:
            config = self.config
            url = config["base_url"].rstrip("/") + "/chat/completions"
            body = json.dumps({"model": config["model"], "messages": [{"role": "user", "content": prompt}],
                               "max_tokens": max_tokens, "stream": False}).encode()
            headers = {"Content-Type": "application/json"}
            if config.get("api_key_env"):
                headers["Authorization"] = "Bearer " + os.environ[config["api_key_env"]]
            request = urllib.request.Request(url, body, headers)
            with urllib.request.urlopen(request, timeout=600) as response:
                result = json.load(response)
            answer = result["choices"][0]["message"]["content"]
            tokens = result.get("usage", {}).get("completion_tokens")
            first_token = None
        seconds = time.perf_counter() - start
        return answer, {"generation_seconds": round(seconds, 3), "first_token_seconds": first_token,
                        "tokens_generated": tokens, "tokens_per_second": round(tokens / seconds, 2) if tokens and seconds else None,
                        "peak_memory_bytes": None}


def parse_changes(answer, editable):
    value = answer.strip()
    if value.startswith("```"):
        value = re.sub(r"^```(?:json)?\s*|\s*```$", "", value)
    data = json.loads(value)
    changes = data["files"]
    if not isinstance(changes, dict) or not changes:
        raise ValueError("Response has no changed files")
    if any(name not in editable or not isinstance(body, str) for name, body in changes.items()):
        raise ValueError("Response contains a disallowed path or nontext content")
    return changes


def execute_repo(task, answer):
    changes = parse_changes(answer, set(task["editable"]))
    fixture = ROOT / "tasks/fixtures" / task["id"]
    with tempfile.TemporaryDirectory(prefix="local-coder-eval-") as directory:
        workspace = Path(directory) / "repo"
        shutil.copytree(fixture, workspace, symlinks=False,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.class"))
        before = {name: (workspace / name).read_text(encoding="utf-8") for name in changes}
        for name, body in changes.items():
            (workspace / name).write_text(body, encoding="utf-8")
        diff = "".join("".join(difflib.unified_diff(before[name].splitlines(keepends=True),
                      body.splitlines(keepends=True), fromfile="a/" + name, tofile="b/" + name))
                      for name, body in changes.items())
        checks = []
        for command in task["validation"]:
            try:
                process = subprocess.run(command, cwd=workspace, capture_output=True, text=True, timeout=60,
                                         env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
                checks.append({"command": command, "exit_code": process.returncode,
                               "output": (process.stdout + process.stderr)[-16000:]})
            except (OSError, subprocess.TimeoutExpired) as exc:
                checks.append({"command": command, "exit_code": None, "output": str(exc)})
        return {"changes": changes, "diff": diff, "validation": checks,
                "validation_passed": bool(checks) and all(x["exit_code"] == 0 for x in checks)}


def git_commit():
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


def run(args):
    tasks = load_tasks()
    if args.task:
        tasks = [task for task in tasks if task["id"] == args.task]
        if not tasks:
            raise ValueError(f"Unknown task: {args.task}")
    config = read_json(MODELS)["models"][args.model]
    try:
        model = Model(config)
    except ImportError as exc:
        raise ValueError(f"Model runtime unavailable: {exc}") from exc
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory = RESULTS / args.model / stamp
    directory.mkdir(parents=True, exist_ok=False)
    metadata = {"model_key": args.model, "model": config, "mode": args.mode,
                "created_utc": datetime.now(timezone.utc).isoformat(), "git_commit": git_commit(),
                "suite_sha256": suite_hash(load_tasks()),
                "generation": {"max_tokens": args.max_tokens}, "task_ids": [task["id"] for task in tasks]}
    write_json(directory / "metadata.json", metadata)
    for index, task in enumerate(tasks, 1):
        prompt = make_prompt(task, args.mode)
        started = time.perf_counter()
        record = {"id": task["id"], "category": task["category"], "mode": args.mode, "prompt": prompt,
                  "response": None, "timings": None, "repo": None, "error": None,
                  "manual": {"score": None, "notes": "", "requirement_failures": [], "corrections": None}}
        try:
            record["response"], record["timings"] = model.generate(prompt, args.max_tokens)
            if args.mode == "repo":
                record["repo"] = execute_repo(task, record["response"])
        except Exception as exc:
            record["error"] = f"{type(exc).__name__}: {exc}"
        record["wall_seconds"] = round(time.perf_counter() - started, 3)
        write_json(directory / (task["id"] + ".json"), record)
        print(f"{index}/{len(tasks)} {task['id']}: " + (record["error"] or "saved"), flush=True)
    print(directory)


def score(args):
    path = Path(args.run) / (safe_name(args.task) + ".json")
    record = read_json(path)
    record["manual"] = {"score": args.score, "notes": args.notes,
                        "requirement_failures": args.failure or [], "corrections": args.corrections}
    write_json(path, record)


def summarize(directory):
    meta = read_json(directory / "metadata.json")
    rows = [read_json(directory / (task_id + ".json")) for task_id in meta["task_ids"]]
    return meta, rows


def compare(args):
    runs = [summarize(Path(name)) for name in args.runs]
    first = runs[0][0]
    if any(meta["mode"] != first["mode"] or meta["task_ids"] != first["task_ids"] or
           meta["suite_sha256"] != first["suite_sha256"] or
           meta["generation"] != first["generation"] for meta, _ in runs[1:]):
        raise ValueError("Runs must use the same mode, suite, task IDs, and generation settings")
    lines = [f"# Local model comparison ({first['mode']})", "", "| Metric | " + " | ".join(
        meta["model_key"] for meta, _ in runs) + " |", "|---|" + "---:|" * len(runs)]
    def metric(label, function):
        lines.append("| " + label + " | " + " | ".join(function(rows) for _, rows in runs) + " |")
    metric("Manually successful (score 2)", lambda rows: str(sum(r["manual"]["score"] == 2 for r in rows)) + f"/{len(rows)}")
    metric("Unscored", lambda rows: str(sum(r["manual"]["score"] is None for r in rows)))
    metric("First pass success", lambda rows: str(sum(r["manual"]["score"] == 2 and r["manual"]["corrections"] == 0 for r in rows)))
    if first["mode"] == "repo":
        metric("Validation passing", lambda rows: str(sum(bool(r["repo"] and r["repo"]["validation_passed"]) for r in rows)) + f"/{len(rows)}")
    metric("Requirement failures", lambda rows: str(sum(len(r["manual"]["requirement_failures"]) for r in rows)))
    metric("Average corrections", lambda rows: average([r["manual"]["corrections"] for r in rows]))
    metric("Average generation seconds", lambda rows: average([r["timings"]["generation_seconds"] for r in rows if r["timings"]]))
    metric("Average tokens/sec", lambda rows: average([r["timings"]["tokens_per_second"] for r in rows if r["timings"]]))
    metric("Peak memory GiB", lambda rows: average([r["timings"]["peak_memory_bytes"] / 2**30
                                                    for r in rows if r["timings"] and r["timings"]["peak_memory_bytes"] is not None]))
    lines += ["", "## Per-task observations", ""]
    for task_id in first["task_ids"]:
        lines.append(f"### {task_id}")
        for meta, rows in runs:
            row = next(r for r in rows if r["id"] == task_id)
            manual = row["manual"]
            validation = row["repo"]["validation_passed"] if row["repo"] else "n/a"
            lines.append(f"- {meta['model_key']}: score {manual['score']}, validation {validation}; "
                         f"{manual['notes'] or row['error'] or 'No review note.'}")
        lines.append("")
    output = "\n".join(lines) + "\n"
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output, end="")


def average(values):
    numbers = [value for value in values if value is not None]
    return f"{sum(numbers) / len(numbers):.2f}" if numbers else "n/a"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("tasks")
    runner = commands.add_parser("run")
    runner.add_argument("--model", required=True)
    runner.add_argument("--mode", choices=("response", "repo"), required=True)
    runner.add_argument("--task")
    runner.add_argument("--max-tokens", type=int, default=1024)
    scoring = commands.add_parser("score")
    scoring.add_argument("run")
    scoring.add_argument("--task", required=True)
    scoring.add_argument("--score", type=int, choices=(0, 1, 2), required=True)
    scoring.add_argument("--notes", default="")
    scoring.add_argument("--failure", action="append")
    scoring.add_argument("--corrections", type=int, default=0)
    comparison = commands.add_parser("compare")
    comparison.add_argument("runs", nargs="+")
    comparison.add_argument("--output")
    args = parser.parse_args()
    try:
        if args.command == "tasks":
            for task in load_tasks():
                print(f"{task['id']}: {task['title']} ({task['category']})")
        elif args.command == "run":
            if args.max_tokens < 1:
                raise ValueError("max tokens must be positive")
            run(args)
        elif args.command == "score":
            if args.corrections < 0:
                raise ValueError("corrections must be nonnegative")
            score(args)
        else:
            compare(args)
    except (KeyError, OSError, ValueError, json.JSONDecodeError) as exc:
        parser.exit(1, f"Evaluation error: {exc}\n")


if __name__ == "__main__":
    main()
