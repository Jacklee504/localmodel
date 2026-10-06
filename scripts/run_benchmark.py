"""Run the frozen benchmark, preserving raw responses and a score template."""

import argparse
import hashlib
import importlib.metadata
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from check_environment import check, model_path
from infer import MAX_TOKENS, load_inference, respond

ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / "benchmarks/tasks.jsonl"


def read_tasks(path):
    tasks = []
    ids = set()
    for line_number, line in enumerate(path.read_text().splitlines(), 1):
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: {exc}") from exc
        if not isinstance(item, dict) or any(not isinstance(item.get(k), str) or not item[k].strip() for k in ("id", "category", "prompt")):
            raise ValueError(f"{path}:{line_number}: id, category and prompt must be nonempty strings")
        if item["id"] in ids:
            raise ValueError(f"Duplicate task id: {item['id']}")
        ids.add(item["id"])
        tasks.append(item)
    if not tasks:
        raise ValueError("Benchmark has no tasks")
    return tasks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=model_path())
    parser.add_argument("--adapter")
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--max-tokens", type=int, default=MAX_TOKENS)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", args.run_name):
        parser.error("run name must contain only letters, digits, underscores and hyphens")
    if args.max_tokens < 1:
        parser.error("--max-tokens must be positive")
    try:
        tasks = read_tasks(TASKS)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Benchmark invalid: {exc}\n")
    if not check(args.model):
        return 1
    try:
        model, tokenizer = load_inference(args.model, args.adapter)
    except Exception as exc:
        parser.exit(1, f"Model load failed: {exc}\n")
    group = "trained" if args.adapter else "baseline"
    directory = ROOT / "benchmarks" / group / args.run_name
    try:
        directory.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        parser.exit(1, f"Run already exists: {directory}\n")
    try:
        git_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        git_commit = None
    metadata = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit,
        "model": str(Path(args.model).resolve()),
        "model_config_sha256": hashlib.sha256((Path(args.model) / "config.json").read_bytes()).hexdigest(),
        "mlx_version": importlib.metadata.version("mlx"),
        "mlx_lm_version": importlib.metadata.version("mlx-lm"),
        "adapter": str(Path(args.adapter).resolve()) if args.adapter else None,
        "tasks_sha256": hashlib.sha256(TASKS.read_bytes()).hexdigest(),
        "generation": {"max_tokens": args.max_tokens, "sampler": "greedy", "chat_template": "tokenizer default"},
        "task_count": len(tasks),
    }
    (directory / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    output_path = directory / "responses.jsonl"
    scores_path = directory / "scores.jsonl"
    try:
        with output_path.open("w") as output, scores_path.open("w") as scores:
            for number, task in enumerate(tasks, 1):
                answer = respond(model, tokenizer, task["prompt"], args.max_tokens)
                output.write(json.dumps({"id": task["id"], "category": task["category"], "response": answer}, ensure_ascii=False) + "\n")
                scores.write(json.dumps({"id": task["id"], "score": None, "notes": "", "constraints_met": None, "code_correct": None}) + "\n")
                output.flush()
                scores.flush()
                print(f"{number}/{len(tasks)} {task['id']}", flush=True)
    except Exception as exc:
        parser.exit(1, f"Run stopped; partial files retained at {directory}: {exc}\n")
    print(f"Raw responses and score template: {directory}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
