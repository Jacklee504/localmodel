# Experiment log

For each run record date, Git commit, base model, adapter/version, dataset version and counts, training parameters, validation result, benchmark result, observations, and decision. Record failures too.

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
