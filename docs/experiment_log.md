# Experiment log

For each run record date, Git commit, base model, adapter/version, dataset version and counts, training parameters, validation result, benchmark result, observations, and decision. Record failures too.

## 2026-10-21: cloud ceiling reference and live endpoint probes

- Decision: use the remaining `minimax-m3.1-flash:cloud` access window to calibrate the
  evaluation method before downloading the larger local models. No weights were
  downloaded. No training was started. The frozen 30-task benchmark and the V1 training
  assets are unchanged.
- Base model: `minimax-m3.1-flash:cloud`, served locally through Ollama v0.40.0 on the
  OpenAI-compatible endpoint at `127.0.0.1:11434/v1`. This is a cloud model and is a
  ceiling reference, not a candidate for daily local use.
- Suite: the ten-task practical suite in `tasks/core.json`, repo mode, one attempt per
  task, `max_tokens: 8192`, no repair loop, no manual scoring applied yet.
- Result: **10/10 objective validation passing**, every task category at 1/1, zero parse
  failures, zero timeouts, every `finish_reason` of `stop`. Per-task timings ranged from
  9.8 to 96.9 seconds.
- Comparison: the historical Qwen2.5-Coder-7B run passed 4/10 on the same suite at
  `max_tokens: 1024`. The suite therefore separates a weak model from a strong one, and
  the 7B result is not an artefact of a mis-specified suite.
- Observations, endpoint behaviour measured on this machine:
  - `think` is accepted by the endpoint and silently ignored. It must not be sent as a
    setting that is expected to apply.
  - `reasoning_effort` is the only reasoning control that changed behaviour. On
    `qwen3.5:9b` it cut reasoning output from 3,548 characters to 112.
  - A `reasoning` field is returned on some responses and absent on others. The extractor
    must treat its absence as normal and must never merge it into `content`.
  - `options.num_ctx` in the request body has no effect. The served context must be read
    from `ollama ps` or `/api/ps` and recorded, not assumed.
  - `qwen3.5:9b` was observed at `context_length: 262144`, `100% GPU`, occupying
    15,280,436,673 bytes of VRAM against a 6.6 GB on-disk model. The KV cache at a long
    context is roughly double the weight footprint, so context length dominates the
    memory budget on this machine.
  - `/usr/bin/sandbox-exec` is available, so agent-mode isolation is feasible.
  - `OPENCODE_CONFIG` is honoured by OpenCode v1.18.35 and is **additive**, not a
    replacement. A generated config supplies a target provider but does not remove the
    user's existing providers or global plugins. Model targeting by filtered query works;
    directory isolation does not.
- Observations, suite calibration: every task needed at least 238 and up to 3,602
  completion tokens, and the reasoning channel ran to 22,250 characters on the hardest
  task. The harness default of 1024 tokens is below what half the suite requires. All
  local candidates must be evaluated at one identical, generous token budget, and that
  budget must be part of the comparison key.
- Open question resolved by an external measurement: an independent 24 GB Apple Silicon
  machine reports that `qwen3.8:27b` runs out of GPU memory once a 20K-token prompt
  arrives, while `gpt-oss:20b` loads fully onto the GPU. This is not a measurement from
  this machine and must be re-verified here, but it makes `gpt-oss:20b` the first
  candidate to test and `qwen3.8:27b` the most likely to be ineligible on this hardware.
- Agent-mode feasibility: a full agent-driven run was executed on a temporary copy of the
  `result-summary` fixture using the cloud model through OpenCode. `opencode run` exited
  0, the harness's independent validation passed, and only `summary.py` was modified. The
  transcript shows 6 `bash`, 2 `read`, and 1 `write` tool calls, and includes per-message
  token accounting with `cache.read` and `cache.write`. The agent discovered that
  `unittest discover` does not work against `tests/` without a package marker and adapted
  its command, which is genuine developer behaviour rather than a single-shot generation.
  Wall clock was 447.6 seconds for the one task, against 47.8 seconds for the same task in
  JSON repo mode, so agent mode costs roughly an order of magnitude more time. Agent mode
  is therefore feasible but should be applied to a representative subset of tasks, not
  the whole suite, and it is expected to be impractical on a slow local 27B model.
- Decision: quality ranking and operational eligibility are recorded as two separate
  axes. A candidate that cannot hold a 64K context on this machine is excluded from
  daily-use consideration regardless of its benchmark quality. Manual 0/1/2 scores for
  this ceiling run are still outstanding and must be supplied by a reviewer before the
  ceiling is used as a rubric anchor.

## 2026-10-21: harness rebuilt for candidate evaluation

- Decision: the Qwen3.5-9B candidate was discarded as unsuitable for the intended tasks,
  and the evaluation harness was rebuilt so that the larger candidates can be run
  overnight with one command. No training was started. The frozen 30-task benchmark and
  the V1 training assets are unchanged.
- Harness changes: result schema version 2 with a deliberate comparison key; streaming
  endpoint access with first-token timing; a closed failure taxonomy; robust JSON
  recovery that tolerates reasoning preambles, code fences, and prose wrappers; withheld
  tests for all ten tasks; agent-driven repository mode; and a comparison report with
  run identity, failure-mode, and category breakdowns.
- Withheld tests: every task now carries a `hidden` directory that is excluded from the
  prompt and from the agent workspace, and is copied in only after a change is applied.
  The suite hash includes hidden files, so two suites differing only in a hidden file are
  never treated as the same suite. All ten tasks' hidden tests were verified to pass
  against reference implementations, proving they are satisfiable and not ambiguous.
- Verification run against `minimax-m3.1-flash:cloud` on the revised harness, one attempt
  per task, `max_tokens: 8192`: **9 of 10 saved, 1 unparseable**, 9 of 10 public and
  withheld validation passing, 10 of 10 transport valid, average 51.96 seconds and 44.45
  tokens per second, average reasoning 11,199 characters.
- The single failure, `web-search`, is informative rather than a harness defect. The
  model produced 40,214 characters of reasoning, hit the 8,192-token limit with
  `finish_reason: length`, and emitted an empty answer. It was classified `unparseable`
  rather than `timeout`, correctly distinguishing a model that ran out of budget from one
  that failed to follow the protocol. This is direct evidence that a thinking model can
  exhaust the answer budget on reasoning alone, so `max_tokens` must be generous and
  identical across every candidate.
- Agent mode verified end to end against the same model: OpenCode ran for 255 seconds,
  exited 0, modified only `summary.py`, and both the public and withheld validation
  passed. The transcript is captured in the record. Agent mode is roughly five times
  slower than JSON repo mode for the same task, so it is intended for a representative
  subset of tasks rather than the full suite.
- Comparison safety verified: two runs whose metadata differ in `max_tokens` are refused
  with the differing field named, rather than producing a wrong comparison.
- Next step: pull `gpt-oss:20b` as the first candidate, serve it with
  `OLLAMA_CONTEXT_LENGTH=64000`, confirm the served context in `ollama ps`, then follow
  `docs/nightly_runbook.md`.

## 2026-10-21: expanded suite and one-command benchmark runner

- Decision: expand the task suite from ten to nineteen tasks so that candidates can be
  benchmarked by work type, and add a single-command runner so a candidate can be
  evaluated without assembling the steps by hand. The Qwen3.5-9B candidate remains
  discarded. No training was started. The frozen 30-task benchmark and the V1 training
  assets are unchanged.
- New tasks, ten, covering the work types the user asked about: complex file
  implementation (`capts-model`, `capts-risk-score`, `capts-change-event`), documentation
  (`capts-document-module`, `capts-write-docstring`), test writing (`capts-test-model`),
  debugging (`capts-cache-key`), refactoring (`capts-dedupe-severity`), and TypeScript
  (`capts-normalise-deal`).
- Provenance: the `capts-` tasks are derived from the CAPTS project in
  `~/Other/Me/Projects/FYP/FourthYearProject`, and `capts-normalise-deal` and
  `capts-test-model` from the DealLedger MCP server in
  `~/Other/Me/Projects/mysite/deal-ledger-mcp`. Only minimum necessary context was
  copied, with no credentials, no configuration, no generated files, and no large
  sections of the original repositories. Each task's `source` field records its origin.
- Every new task has withheld tests, and all nineteen tasks' withheld tests were verified
  to pass against reference implementations, so they are satisfiable rather than
  impossible. Six defects were found and fixed during that verification, all in the
  assertions rather than the harness.
- Suites defined in `config/suites.json`: `all`, `implementation`, `complex`,
  `debugging`, `documentation`, `tests`, `refactoring`, `web`, `java`, `specification`,
  `difficult`, `routine`, and `quick`. The `difficult` and `routine` subsets are the
  pre-registered ones, unchanged.
- One-command runner added at `scripts/benchmark.py`. It checks the model is installed,
  checks the served context against the required context, runs the requested suites, and
  prints a summary with validation counts, failure kinds, timings, and throughput. It
  never downloads weights and never deletes anything.
- **Token budget corrected from 8192 to 32768 for all candidates.** Measured on this
  machine against the cloud model, the `complex` suite failed 3 of 3 at 8192 with
  `finish_reason: length` and zero answer characters, because the model spent the entire
  budget on reasoning. At 32768, one of the three passed and the other two still
  exhausted the budget after 141,719 and 146,509 characters of reasoning. This is a
  reasoning-loop pathology in the model, not only a budget problem, and it is a direct
  argument against a 27B dense model on this hardware. The `documentation` suite passed
  2 of 2 at 8192, so the budget needed depends on the task type.
- Verification: the one-command runner was exercised end to end against the cloud model
  on the `quick`, `documentation`, and `complex` suites. The `quick` suite gave 3 of 3
  validation and 3 of 3 withheld passing.
- Artefacts: `docs/cloud_run/ceiling_suite.py` and `docs/cloud_run/ceiling_suite.json` for
  the run, `docs/cloud_run/probe_endpoint.py` and `docs/cloud_run/probe_reasoning.py` for
  the endpoint probes, `docs/cloud_run/ocprobe/` for the OpenCode configuration probes,
  and `docs/local_coder_spec.md` for the full specification and these findings.

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
