# Local Coder V1

A small QLoRA experiment for `mlx-community/Qwen2.5-Coder-7B-Instruct-4bit` on Apple Silicon. The frozen benchmark is separate from the training, validation and test splits. See [the handoff](docs/local_coder_v1_implementation_handoff.md) for the research question.

The model is expected at `models/qwen2.5-coder-7b-instruct-4bit`. Set `LOCAL_CODER_MODEL` to another local copy if needed. Create an environment with `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` if one does not exist.

```sh
.venv/bin/python scripts/check_environment.py
.venv/bin/python scripts/infer.py --prompt 'Implement a Python clamp function.'
.venv/bin/python scripts/run_benchmark.py --run-name baseline
.venv/bin/python scripts/validate_dataset.py
```

Score responses in `benchmarks/baseline/baseline/scores.jsonl`: score 0 (incorrect), 1 (partial), or 2 (correct), with notes and `constraints_met` / `code_correct` booleans. Keep raw responses unchanged. After freezing, running and scoring the base benchmark, generate a summary with `.venv/bin/python scripts/compare_results.py --baseline baseline` and commit the task definition and summary. Then train with `bash configs/train_v1.sh`, run the same benchmark with `--adapter adapters/impl-v1 --run-name impl-v1`, and compare with `.venv/bin/python scripts/compare_results.py --baseline baseline --candidate impl-v1`.

For a pipeline smoke run after baseline scoring, use `ITERS=5 ADAPTER_PATH=./adapters/smoke bash configs/train_v1.sh`, then pass `--adapter adapters/smoke` to inference. The 20 included examples are pipeline data only. The 500-iteration default is for a later curated dataset. Generated runs and adapters should not be committed. No training starts during repository setup.
