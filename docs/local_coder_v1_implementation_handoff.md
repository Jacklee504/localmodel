# Local Coder V1 — QLoRA Implementation Handoff

## Purpose

Build the smallest credible end-to-end experiment for training a local coding model on Apple Silicon.

The objective of V1 is **not** to build the final planner/implementer architecture. It is to prove that we can:

1. run a fixed baseline benchmark,
2. fine-tune a local coding model using QLoRA,
3. run the exact same benchmark with the adapter,
4. compare the results reproducibly,
5. decide whether further specialisation is worth pursuing.

The project should remain deliberately small and inspectable.

## Core decision

Use:

- **Base model:** `mlx-community/Qwen2.5-Coder-7B-Instruct-4bit`
- **Training framework:** MLX-LM
- **Training method:** QLoRA
- **Host:** Apple Silicon macOS
- **Initial task:** software implementation / code editing
- **Dataset format:** MLX-LM chat JSONL
- **Primary evaluation:** fixed benchmark before vs. after training

Do not add a planner model, Julia, RL, model routing, multiple adapters, continued pretraining, or a larger model in V1.

## V1 research question

> Can a small, carefully curated implementation-focused QLoRA adapter improve Qwen2.5-Coder-7B-Instruct on a fixed set of realistic software-engineering tasks without materially degrading its general coding ability?

Everything implemented in V1 should contribute directly to answering this question.

# 1. Repository layout

Create a clean repository with approximately this structure:

```text
local-coder/
├── README.md
├── requirements.txt
├── .gitignore
├── configs/
│   └── train_v1.sh
├── data/
│   ├── README.md
│   ├── train.jsonl
│   ├── valid.jsonl
│   └── test.jsonl
├── benchmarks/
│   ├── README.md
│   ├── tasks.jsonl
│   ├── baseline/
│   └── trained/
├── scripts/
│   ├── check_environment.py
│   ├── validate_dataset.py
│   ├── run_benchmark.py
│   └── compare_results.py
├── adapters/
│   └── .gitkeep
├── reports/
│   └── .gitkeep
└── docs/
    └── experiment_log.md
```

Large models, generated benchmark outputs, adapters and caches should not be committed unless there is a clear reason.

The exact internal layout may be adjusted if there is a simpler design, but keep the repository small.

# 2. Environment validation

Implement `scripts/check_environment.py`.

It should report enough information to reproduce a run:

- macOS version
- Apple Silicon chip
- total memory if available
- Python version
- MLX version
- MLX-LM version
- whether Metal is available
- configured model path/repository
- whether the model can be loaded

Do not make this elaborate.

Acceptance criteria:

- one command checks the local training environment,
- failures are clear and actionable,
- no training starts if the environment is obviously invalid.

# 3. Model smoke test

Before any training, prove the selected model can run locally.

Use:

```text
mlx-community/Qwen2.5-Coder-7B-Instruct-4bit
```

Create a minimal inference path that can accept:

```text
prompt → model → response
```

Keep generation settings explicit and recorded.

The implementation should make it easy to run either:

```text
base model
```

or:

```text
base model + adapter
```

using the same inference path.

Do not create separate evaluation logic for each.

# 4. Frozen benchmark

This is the most important part of V1.

Create a small benchmark **before training**.

Target approximately **30–50 tasks** initially. Quality is more important than quantity.

Suggested categories:

```text
Python implementation        ~20%
Python debugging             ~15%
unit-test generation         ~15%
TypeScript / JavaScript      ~15%
Java                         ~10%
refactoring                  ~10%
small multi-file reasoning   ~15%
```

These percentages are guidance, not hard constraints.

Tasks should resemble genuine work rather than trivia.

Good examples:

- implement a specified function in an existing code fragment,
- repair a bug from a traceback,
- preserve an API while changing internal behaviour,
- add edge-case tests,
- modify a small TypeScript component,
- fix a Java implementation against requirements,
- refactor without changing behaviour,
- make two related file changes from a concise specification.

Avoid benchmark questions such as:

```text
What is a Python decorator?
Write hello world.
Explain a for loop.
```

Those do not measure the behaviour we are trying to improve.

## Benchmark format

Use a simple structured format such as JSONL.

Each task should at minimum have:

```json
{
  "id": "py-001",
  "category": "python_implementation",
  "prompt": "...",
  "notes": "..."
}
```

If deterministic validation is possible, allow optional fields for it.

Do not over-engineer a sandboxed coding benchmark in V1.

The benchmark runner must:

1. load the frozen tasks,
2. run them against the specified model configuration,
3. save raw outputs,
4. record generation parameters,
5. identify whether the run used the base model or an adapter.

Do **not** silently overwrite old runs.

# 5. Benchmark scoring

V1 needs comparison, but it does not need a sophisticated judge model.

Prefer deterministic signals where available:

- code parses,
- unit tests pass,
- expected output matches,
- required function exists,
- prohibited API changes are absent.

Where deterministic scoring is not practical, support a lightweight manual score:

```text
0 = incorrect / unusable
1 = partially correct
2 = correct
```

Keep manual notes with the score.

The benchmark should eventually report at least:

- total tasks,
- pass/correct rate,
- score by category,
- baseline result,
- trained result,
- difference.

Do not claim improvement from training loss alone.

# 6. Training dataset

Use MLX-LM chat JSONL.

Each example should contain a user request/context and the desired implementation response.

Example shape:

```json
{"messages":[
  {"role":"user","content":"Implement retry support in this HTTP client. Retry timeout and 5xx failures at most three times. Do not retry 4xx responses.\n\n<code>...</code>"},
  {"role":"assistant","content":"<desired implementation>"}
]}
```

Every record must remain on a single JSONL line.

The training target should primarily be the assistant response.

Use prompt masking during training.

## Data quality rules

For V1, favour **small and trusted** over large and noisy.

Training examples should:

- have a clear requirement,
- contain sufficient context,
- have a high-quality target implementation,
- avoid obvious generated garbage,
- avoid secrets/private credentials,
- avoid benchmark leakage,
- preserve source/licence metadata where applicable.

Do not put any frozen benchmark task, solution, lightly rewritten equivalent, or derived answer in training or validation data.

Create `scripts/validate_dataset.py` to check at least:

- valid JSONL,
- expected `messages` structure,
- user and assistant messages exist,
- empty examples are rejected,
- duplicate examples are flagged,
- benchmark IDs/text are not accidentally included where practical.

# 7. Initial dataset size

Do **not** block V1 waiting for thousands of examples.

Use two stages.

### Pipeline validation set

Start with approximately:

```text
20–50 examples
```

This is only to prove:

```text
data → QLoRA → adapter → inference
```

works end to end.

Do not interpret its model quality seriously.

### First real V1 experiment

After the pipeline works, target approximately:

```text
500–2,000 high-quality examples
```

The exact count is deliberately flexible.

If a smaller high-quality set gives a useful experiment, prefer that over padding the dataset.

# 8. Train/validation/test separation

Maintain three files:

```text
data/train.jsonl
data/valid.jsonl
data/test.jsonl
```

The **benchmark** is separate from these.

Important distinction:

```text
training data
      ≠
training test split
      ≠
frozen external benchmark
```

The external benchmark is the primary before/after comparison.

Do not repeatedly alter it in response to model failures.

# 9. QLoRA training

MLX-LM should be used directly rather than implementing a custom trainer.

The first training script should use the 4-bit MLX model so MLX-LM performs QLoRA.

The initial command should be conservative:

```bash
mlx_lm.lora   --model mlx-community/Qwen2.5-Coder-7B-Instruct-4bit   --train   --data ./data   --adapter-path ./adapters/impl-v1   --batch-size 1   --iters 500   --mask-prompt
```

This is a starting configuration, not a sacred hyperparameter set.

If memory pressure occurs, investigate in this order:

1. keep batch size at 1,
2. reduce sequence/example length where reasonable,
3. reduce the number of trainable layers,
4. enable gradient checkpointing,
5. only then make larger architectural changes.

Record every material training configuration.

# 10. Experiment logging

Create `docs/experiment_log.md`.

Every meaningful run should record:

```text
date
git commit
base model
adapter/version
dataset version/count
training parameters
validation result
benchmark result
observations
decision
```

The goal is to avoid an untraceable sequence of tuning attempts.

A failed experiment is still useful and should remain recorded.

# 11. Baseline-before-training rule

Before the first real training run:

1. freeze the benchmark,
2. run the untouched base model,
3. save the raw responses,
4. score the baseline,
5. commit the benchmark definition and baseline summary.

Only then perform the real QLoRA run.

This rule is mandatory.

# 12. Post-training evaluation

Run the exact same benchmark with:

```text
base model + impl-v1 adapter
```

Use the same:

- prompts,
- generation settings,
- scoring procedure,
- deterministic tests where applicable.

Generate a comparison report under:

```text
reports/v1_comparison.md
```

It should answer:

1. Did overall performance improve?
2. Which task categories improved?
3. Which categories regressed?
4. Did the model become more likely to follow implementation constraints?
5. Did it become more likely to generate correct code?
6. Are the results large enough to justify further work?
7. What are the likely data/training weaknesses?

Do not hide regressions.

# 13. V1 success criteria

V1 is successful as an engineering experiment if:

- the model runs locally,
- the benchmark is reproducible,
- the baseline is preserved,
- QLoRA training completes,
- the resulting adapter can be loaded,
- the same benchmark can evaluate the adapter,
- before/after results can be compared,
- another developer could repeat the experiment.

The **adapter does not have to outperform the baseline for V1 to be considered a successful experiment**.

If it does not improve, the report should explain the evidence and recommend the next experiment.

# 14. What not to build yet

Explicitly out of scope:

- dedicated planner model,
- planner → implementer orchestration,
- Julia-1 judge/router,
- reinforcement learning,
- DPO,
- full-weight fine-tuning,
- training from scratch,
- continued pretraining on huge code corpora,
- separate Python/Web/Java models,
- autonomous GitHub mining,
- large synthetic-data generation pipeline,
- 14B/27B/30B training,
- production IDE integration.

Small reusable design choices that make these possible later are fine.

Do not implement them in V1.

# 15. Areas where Sol should use judgement

This handoff intentionally leaves room for improvement.

Before or while implementing, Sol may propose better choices for:

- benchmark representation,
- clean result storage,
- deterministic scoring,
- dataset validation,
- training configuration,
- inference wrappers,
- experiment metadata,
- reproducibility,
- avoiding benchmark contamination.

Ideas are welcome if they make V1 **simpler, more measurable, or more reproducible**.

Do not expand scope merely because an idea is interesting.

If changing a core decision, document:

```text
current decision
proposed alternative
why it is materially better
cost/complexity introduced
```

Then choose the simplest defensible option.

# 16. Suggested implementation sequence

Implement in small, reviewable steps.

### Step 1 — Scaffold
Create repository structure, README, `.gitignore`, dependency file and empty experiment log.

### Step 2 — Environment check
Implement and run the environment diagnostics.

### Step 3 — Base inference
Load the selected model and produce a deterministic smoke-test response.

### Step 4 — Benchmark harness
Implement benchmark loading, execution and result persistence.

### Step 5 — Frozen baseline
Add the first benchmark tasks, run the untouched model and save the baseline.

### Step 6 — Dataset tooling
Add sample training data plus validation and leakage/duplicate checks.

### Step 7 — Tiny QLoRA smoke run
Train on a tiny dataset only to verify the complete pipeline.

### Step 8 — Adapter inference
Load the smoke-test adapter and verify inference works.

### Step 9 — First real dataset
Curate the first credible implementation-focused dataset.

### Step 10 — V1 training
Train `impl-v1` with fully recorded parameters.

### Step 11 — Evaluation
Run the frozen benchmark using the adapter.

### Step 12 — Report
Generate the baseline-vs-trained comparison and recommended next experiment.

# 17. Expected end state

At completion, a developer should be able to do approximately:

```bash
python scripts/check_environment.py
python scripts/validate_dataset.py
python scripts/run_benchmark.py --run-name baseline
bash configs/train_v1.sh
python scripts/run_benchmark.py --adapter adapters/impl-v1 --run-name impl-v1
python scripts/compare_results.py --baseline baseline --candidate impl-v1
```

Exact CLI design can differ if Sol identifies a cleaner interface.

The important requirement is that the full experiment can be repeated without remembering hidden manual steps.

# 18. Decision after V1

Do not assume the next step is another training run.

### If the adapter clearly improves implementation quality

Proceed to:

- larger/better dataset,
- better deterministic evaluation,
- more difficult repo-level tasks,
- then investigate a dedicated planner model.

### If gains are small or inconsistent

Investigate:

- data quality,
- target formatting,
- task mix,
- training duration,
- LoRA configuration,
- benchmark noise.

### If it is materially worse

Do not scale training.

Determine whether:

- the data is teaching the wrong behaviour,
- the base model is already stronger than the training targets,
- catastrophic specialisation is occurring,
- the training objective does not match the benchmark.

## Final principle

V1 should answer one question with evidence:

> **Does targeted local fine-tuning make this coding model more useful for implementation work?**

Do not optimise for novelty. Optimise for a clean experiment that tells us what to do next.
