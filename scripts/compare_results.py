"""Compare fully reviewed base and adapter runs on identical tasks/settings."""

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_jsonl(path):
    rows = []
    for number, line in enumerate(path.read_text().splitlines(), 1):
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{number}: {exc}") from exc
    return rows


def load_run(path):
    metadata = json.loads((path / "metadata.json").read_text())
    responses = read_jsonl(path / "responses.jsonl")
    scores = read_jsonl(path / "scores.jsonl")
    response_ids = [r["id"] for r in responses]
    score_ids = [s["id"] for s in scores]
    if len(response_ids) != metadata["task_count"] or response_ids != score_ids or len(set(response_ids)) != len(response_ids):
        raise ValueError(f"{path}: incomplete run or scores do not match responses")
    for score in scores:
        if type(score.get("score")) is not int or score["score"] not in (0, 1, 2):
            raise ValueError(f"{path}: {score['id']} needs a reviewed score of 0, 1 or 2")
        if not isinstance(score.get("notes"), str) or not score["notes"].strip():
            raise ValueError(f"{path}: {score['id']} needs reviewer notes")
        for flag in ("constraints_met", "code_correct"):
            if type(score.get(flag)) is not bool:
                raise ValueError(f"{path}: {score['id']} needs a boolean {flag}")
    return metadata, responses, scores


def metrics(responses, scores):
    grouped = defaultdict(list)
    for response, score in zip(responses, scores):
        grouped[response["category"]].append(score)
    def summarize(items):
        count = len(items)
        return {
            "tasks": count,
            "correct": sum(s["score"] == 2 for s in items),
            "correct_rate": sum(s["score"] == 2 for s in items) / count,
            "mean_score": sum(s["score"] for s in items) / count,
            "constraints_rate": sum(s["constraints_met"] for s in items) / count,
            "code_correct_rate": sum(s["code_correct"] for s in items) / count,
        }
    return {"overall": summarize(scores), "categories": {category: summarize(items) for category, items in sorted(grouped.items())}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--candidate", help="Omit to write a baseline-only summary")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    base_path = ROOT / "benchmarks/baseline" / args.baseline
    try:
        base_meta, base_responses, base_scores = load_run(base_path)
        current_hash = hashlib.sha256((ROOT / "benchmarks/tasks.jsonl").read_bytes()).hexdigest()
        if base_meta["tasks_sha256"] != current_hash:
            raise ValueError("Baseline task hash differs from the current frozen benchmark")
        if base_meta["adapter"] is not None:
            raise ValueError("Baseline run must not use an adapter")
        if args.candidate:
            candidate_path = ROOT / "benchmarks/trained" / args.candidate
            candidate_meta, candidate_responses, candidate_scores = load_run(candidate_path)
            for field in ("tasks_sha256", "generation", "model", "model_config_sha256", "task_count"):
                if base_meta[field] != candidate_meta[field]:
                    raise ValueError(f"Run metadata mismatch: {field}")
            if candidate_meta["adapter"] is None:
                raise ValueError("Candidate run must use an adapter")
            if [(r["id"], r["category"]) for r in base_responses] != [(r["id"], r["category"]) for r in candidate_responses]:
                raise ValueError("Task IDs or categories differ")
    except (OSError, KeyError, TypeError, ValueError) as exc:
        parser.exit(1, f"Cannot compare runs: {exc}\n")
    base = metrics(base_responses, base_scores)
    lines = ["# V1 baseline vs adapter" if args.candidate else "# V1 baseline summary", "", f"Benchmark SHA-256: `{base_meta['tasks_sha256']}`", f"Model: `{base_meta['model']}`", f"Generation: `{json.dumps(base_meta['generation'], sort_keys=True)}`", ""]
    if args.candidate:
        candidate = metrics(candidate_responses, candidate_scores)
        lines += [f"Adapter: `{candidate_meta['adapter']}`", "", "| Category | Tasks | Baseline correct | Adapter correct | Difference | Baseline mean | Adapter mean |", "|---|---:|---:|---:|---:|---:|---:|"]
        for category in ["overall", *base["categories"]]:
            b = base["overall"] if category == "overall" else base["categories"][category]
            c = candidate["overall"] if category == "overall" else candidate["categories"][category]
            lines.append(f"| {category} | {b['tasks']} | {b['correct_rate']:.1%} | {c['correct_rate']:.1%} | {c['correct_rate']-b['correct_rate']:+.1%} | {b['mean_score']:.2f} | {c['mean_score']:.2f} |")
        lines += ["", f"Constraint adherence: {base['overall']['constraints_rate']:.1%} → {candidate['overall']['constraints_rate']:.1%}.", f"Code correctness: {base['overall']['code_correct_rate']:.1%} → {candidate['overall']['code_correct_rate']:.1%}.", "", "## Review", "", "Summarize gains, regressions, dataset or training weaknesses, and whether the effect justifies another experiment. These manually scored tasks are a directional signal, not a statistical guarantee.", ""]
    else:
        lines += ["| Category | Tasks | Correct | Correct rate | Mean score | Constraints met | Code correct |", "|---|---:|---:|---:|---:|---:|---:|"]
        for category in ["overall", *base["categories"]]:
            item = base["overall"] if category == "overall" else base["categories"][category]
            lines.append(f"| {category} | {item['tasks']} | {item['correct']} | {item['correct_rate']:.1%} | {item['mean_score']:.2f} | {item['constraints_rate']:.1%} | {item['code_correct_rate']:.1%} |")
        lines += [""]
    output = args.output or ROOT / ("reports/v1_comparison.md" if args.candidate else "reports/baseline_summary.md")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        parser.exit(1, f"Report already exists: {output}\n")
    output.write_text("\n".join(lines))
    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
