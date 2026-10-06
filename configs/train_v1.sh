#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
PYTHON="${PYTHON:-.venv/bin/python}"
"$PYTHON" scripts/check_environment.py
"$PYTHON" scripts/validate_dataset.py
if [ ! -f reports/baseline_summary.md ]; then
  echo 'Score and commit the frozen baseline summary before training.' >&2
  exit 1
fi
if ! git cat-file -e HEAD:reports/baseline_summary.md 2>/dev/null || ! git cat-file -e HEAD:benchmarks/tasks.jsonl 2>/dev/null; then
  echo 'Commit the baseline summary and benchmark tasks before training.' >&2
  exit 1
fi
if ! git diff --quiet HEAD -- reports/baseline_summary.md benchmarks/tasks.jsonl; then
  echo 'The committed baseline summary and frozen tasks must match the working tree.' >&2
  exit 1
fi
MODEL="${LOCAL_CODER_MODEL:-models/qwen2.5-coder-7b-instruct-4bit}"
ADAPTER_PATH="${ADAPTER_PATH:-./adapters/impl-v1}"
ITERS="${ITERS:-500}"
"$PYTHON" -m mlx_lm.lora --model "$MODEL" --train --data ./data --adapter-path "$ADAPTER_PATH" --batch-size 1 --iters "$ITERS" --mask-prompt
