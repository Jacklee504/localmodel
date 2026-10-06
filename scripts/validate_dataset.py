"""Validate MLX-LM chat splits and catch simple benchmark leakage."""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def normalized(text):
    return re.sub(r"\s+", " ", text).strip().casefold()


def validate(data_dir, benchmark):
    errors = []
    benchmark_prompts = []
    benchmark_ids = set()
    try:
        for number, line in enumerate(benchmark.read_text().splitlines(), 1):
            task = json.loads(line)
            benchmark_prompts.append(normalized(task["prompt"]))
            benchmark_ids.add(normalized(task["id"]))
    except (OSError, ValueError, KeyError) as exc:
        return [f"Cannot read benchmark: {exc}"], {}
    seen = {}
    counts = {}
    for split in ("train", "valid", "test"):
        path = data_dir / f"{split}.jsonl"
        counts[split] = 0
        try:
            lines = path.read_text().splitlines()
        except OSError as exc:
            errors.append(f"{path}: {exc}")
            continue
        for number, line in enumerate(lines, 1):
            place = f"{path}:{number}"
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"{place}: invalid JSON: {exc}")
                continue
            messages = row.get("messages") if isinstance(row, dict) else None
            if not isinstance(messages, list) or len(messages) < 2:
                errors.append(f"{place}: messages must be a list with user and assistant turns")
                continue
            if any(not isinstance(m, dict) or m.get("role") not in ("user", "assistant", "system") or not isinstance(m.get("content"), str) or not m["content"].strip() for m in messages):
                errors.append(f"{place}: each message needs a valid role and nonempty string content")
                continue
            roles = [m["role"] for m in messages]
            if "user" not in roles or roles[-1] != "assistant":
                errors.append(f"{place}: a user turn and final assistant target are required")
                continue
            counts[split] += 1
            key = json.dumps([(m["role"], normalized(m["content"])) for m in messages], ensure_ascii=False)
            if key in seen:
                errors.append(f"{place}: duplicate of {seen[key]}")
            else:
                seen[key] = place
            text = normalized(" ".join(m["content"] for m in messages))
            if any(re.search(rf"(?<![\w-]){re.escape(task_id)}(?![\w-])", text) for task_id in benchmark_ids):
                errors.append(f"{place}: contains a benchmark task ID")
            if any(prompt and prompt in text for prompt in benchmark_prompts):
                errors.append(f"{place}: contains a benchmark prompt")
    return errors, counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data")
    parser.add_argument("--benchmark", type=Path, default=ROOT / "benchmarks/tasks.jsonl")
    args = parser.parse_args()
    errors, counts = validate(args.data, args.benchmark)
    print("Dataset counts: " + ", ".join(f"{key}={value}" for key, value in counts.items()))
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    sys.exit(1 if errors else 0)
