# Local Coder

**Training status: paused pending evaluation of existing local models.** The V1 training script and frozen 30-task benchmark are preserved for possible later use.

The practical model-selection suite is in [tasks/README.md](tasks/README.md), with its method in [docs/evaluation_method.md](docs/evaluation_method.md). Configure a locally installed model or running OpenAI-compatible endpoint in `config/models.json`. No weights are downloaded automatically.

```sh
.venv/bin/python scripts/evaluate.py tasks
.venv/bin/python scripts/evaluate.py run --model qwen25_7b --mode response
.venv/bin/python scripts/evaluate.py run --model qwen25_7b --mode repo
.venv/bin/python scripts/evaluate.py score results/qwen25_7b/RUN_ID --task config-parse --score 1 --notes 'Missing validation' --failure 'ignored requirement' --corrections 0
.venv/bin/python scripts/evaluate.py compare results/qwen25_7b/RUN_A results/qwen35_9b/RUN_B --output reports/comparison.md
```

Each run has a unique directory under `results/`. Repository mode validates applied changes in a temporary fixture copy and captures a diff. Response mode records text and timing only. Scores are entered manually. Comparison requires matching suites and modes; see [reports/model_selection.md](reports/model_selection.md) for the pending final decision.

## Earlier V1 experiment

The commands below document the earlier experiment. Training is paused; do not run the training step while evaluating existing models.

A small QLoRA experiment for `mlx-community/Qwen2.5-Coder-7B-Instruct-4bit` on Apple Silicon. The frozen benchmark is separate from the training, validation and test splits. See [the handoff](docs/local_coder_v1_implementation_handoff.md) for the research question.

The model is expected at `models/qwen2.5-coder-7b-instruct-4bit`. Set `LOCAL_CODER_MODEL` to another local copy if needed. Create an environment with `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` if one does not exist.

```sh
.venv/bin/python scripts/check_environment.py
.venv/bin/python scripts/infer.py --prompt 'Implement a Python clamp function.'
.venv/bin/python scripts/run_benchmark.py --run-name baseline
.venv/bin/python scripts/validate_dataset.py
```

Score responses in `benchmarks/baseline/baseline/scores.jsonl`: score 0 (incorrect), 1 (partial), or 2 (correct), with notes and `constraints_met` / `code_correct` booleans. Keep raw responses unchanged. After freezing, running and scoring the base benchmark, generate a summary with `.venv/bin/python scripts/compare_results.py --baseline baseline` and commit the task definition and summary. Then train with `bash configs/train_v1.sh`, run the same benchmark with `--adapter adapters/impl-v1 --run-name impl-v1`, and compare with `.venv/bin/python scripts/compare_results.py --baseline baseline --candidate impl-v1`.

For a pipeline smoke run after baseline scoring, use `ITERS=5 ADAPTER_PATH=./adapters/smoke bash configs/train_v1.sh`, then pass `--adapter adapters/smoke` to inference. The original 20 examples were pipeline data; the expanded 100-example set is an offline pilot and remains below the handoff's suggested size for a real run. The 500-iteration default is for a later reviewed dataset. Generated runs and adapters should not be committed. No training starts during repository setup.
