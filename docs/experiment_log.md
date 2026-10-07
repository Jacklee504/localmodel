# Experiment log

For each run record date, Git commit, base model, adapter/version, dataset version and counts, training parameters, validation result, benchmark result, observations, and decision. Record failures too.

## 2026-10-07: training paused for local model selection

- Decision: pause custom training while evaluating available local coding models on realistic repository tasks.
- Preserve the frozen 30-task baseline, dataset, adapter work, and runnable training script for a possible later experiment.
- New model-selection results belong under `results/`; a final decision remains pending candidate model runs.
- The installed Qwen2.5-Coder-7B workflow run could not start in this execution session because MLX reported no Metal device. Harness tests exercised all ten repository fixtures with a stub model; no real-model quality result was recorded.

## 2026-10-06: untouched base benchmark

- Git commit: `d0d8a2fae26bcfb6e7ae4b3e61601171cdf31f9c`
- Base model: local `mlx-community/Qwen2.5-Coder-7B-Instruct-4bit`; config SHA-256 `08762352ba9fded858f24bdd7b8d2fe61aabe7bce1dfdb663db242d574c3e678`
- Adapter: none
- Dataset: no training performed; pipeline files contain 14 train, 3 validation, and 3 test examples
- Training parameters and validation result: not applicable
- Benchmark: 30 tasks, SHA-256 `da6167e89cbc333b23a21b90164db7d91337703831f9f726b270e7ad2d6067f6`, greedy generation with 512 maximum tokens
- Result: 11/30 correct (36.7%); mean manual score 1.07/2. See `reports/baseline_summary.md` and per-task score notes.
- Observations: strongest on small multi-file changes (3/4); no fully correct unit-test response (0/4). Some outputs contain code that cannot compile or misses explicit constraints. The Java Unicode response was truncated.
- Decision: preserve this baseline and task definition before any real training. A tiny pipeline smoke run may follow. Do not infer adapter quality from this baseline alone.

## 2026-10-06: tiny QLoRA pipeline smoke run

- Git commit: `8c375ac` at the time of the run
- Base model: local `mlx-community/Qwen2.5-Coder-7B-Instruct-4bit`
- Adapter: `adapters/smoke`; local artifact, not committed
- Dataset: 14 train, 3 validation, 3 test pipeline examples
- Training parameters: LoRA on 16 layers, rank 8, batch size 1, learning rate `1e-5`, maximum sequence length 2048, prompt masking, 5 iterations
- Validation result: loss 1.383 at iteration 1 and 0.641 at iteration 5; final reported train loss 1.202
- Benchmark result: not run with the smoke adapter
- Observations: training completed on Apple M2 with Metal available. The saved adapter loaded for inference and answered an underspecified Python-function prompt by requesting details. This verifies the pipeline, not coding quality.
- Decision: smoke training and adapter inference are complete. Curate the first credible dataset before the real V1 run; do not infer improvement from the five-step losses.
