# SPEC PROMPT: Local Coding Model Selection, Full Specification of Remaining Work

## How to use this file

You have no access to the repository. Everything you need is inlined below. Read the whole
thing before answering.

Feed it to the cloud model with:

```sh
ollama run minimax-m3.1-flash:cloud < docs/cloud_spec_prompt.md
```

or paste the file into `ollama launch opencode --model minimax-m3.1-flash:cloud`. Save the
model's reply as `docs/local_coder_spec.md` so it is committed alongside the repo it
describes. The window on that cloud model is short (about 2 days), so run it early and keep
the output.

---

## 1. Your role and the objective

You are a senior engineer writing a **complete, implementation-ready specification** for a
repository called `local-coder`. You are not implementing it. You are producing the document
that a competent engineer could hand to an implementer (or to an AI coding agent) and get the
work done without further design decisions.

The repository exists to answer one question:

> **Which local model should I use for day-to-day software development on my machine, and
> is custom fine-tuning therefore unnecessary?**

Custom training is **paused**. A small evaluation harness already exists. Several models have
not yet been downloaded or tested. This specification must cover everything that must be
finished *before* those larger models are downloaded, so that when they arrive the evaluation
is a one-command operation and produces a defensible decision.

Your output is the specification. It must be dense, concrete, and unambiguous. Where you
cannot know something, say so and ask. Do not invent file names, function names, or APIs that
do not exist in the material below.

## 2. Machine and runtime environment (ground truth)

| Item | Value |
|---|---|
| Machine | MacBook Air, Apple M2 (Mac14,2), 8 cores (4P + 4E) |
| Unified memory | 24 GB |
| macOS | Sequoia-era, 15.x |
| GPU | Apple M2 integrated GPU, 8 GB default Metal allocation, unified memory |
| Disk free at time of writing | about 40 to 41 GiB on the data volume (228 GiB total) |
| Swap in use at idle with normal apps open | about 12.3 GB already allocated (normal for this machine, not a fault) |
| Python | system `python3` plus a repo-local `.venv` |
| Local model runtime in daily use | **Ollama** (installed at `/usr/local/bin/ollama`, v0.40.0) |
| Ollama server endpoint | `http://127.0.0.1:11434/v1` (OpenAI-compatible) |
| Coding agent in daily use | **OpenCode** v1.18.35 (`/opt/homebrew/bin/opencode`) |
| Secondary/backup runtime | MLX-LM, pinned `mlx-lm==0.32.0` in `requirements.txt` |
| Node | present (`node --test` is used for a JS fixture) |
| JDK | present (`javac` and `java` are used for a Java fixture) |

### 2.1 Models currently present in the local Ollama store

Read from `~/.ollama/models/manifests/registry.ollama.ai/library/`:

| Tag | Notes |
|---|---|
| `qwen3.5:9b` | **Already downloaded locally.** 6,594,462,816-byte model layer. Architecture `qwen35`, parameter count 9,653,104,368 (about 9.65 B), `general.file_type: 15` (Q4_K_M family), native context length 262,144, multimodal (vision tower present). About 6.1 GB total in `~/.ollama`. |
| `minimax-m3.1-flash:cloud` | **Cloud model, free access for about 2 days.** Manifest present locally. This is the model this specification is being written with. It consumes no local RAM and no local disk for weights. |
| `gemma4:31b-cloud` | Cloud model, present. Not a candidate. |

### 2.2 Models to be downloaded and evaluated later (not yet present)

These are the selection candidates. Sizes are Ollama library download sizes.

| Candidate | Ollama tag (proposed) | Download size | Notes |
|---|---|---|---|
| Lightweight baseline | `qwen3.5:9b` | 6.6 to 7.6 GB | **Already local.** No download needed. |
| Primary | `qwen3.8:27b` | 18 GB | Dense, multimodal, thinking on by default, `reasoning_effort` and `preserve_thinking` supported per the model card. 256K context window. |
| Secondary | `qwen3-coder:30b` | 19 GB | MoE, 3.3 B activated of 30 B, agentic and coder-specialised, 256K context. Expected to be materially faster than the dense 27 B. |
| Control | `gpt-oss:20b` | 14 GB | MXFP4 MoE, 3.6 B active, strong tool calling, 128K context. Useful as a "does the runtime or the model matter?" control and as a good fit for 24 GB. |

**Disk constraint is real.** About 40 GB free means at most **two** candidates on disk at once.
The specification must include an explicit, safe, user-run procedure for pulling one candidate,
evaluating it, recording the result, and reclaiming the space before the next pull. It must not
automate deletion; it must give the user the exact commands to run themselves.

### 2.3 Context-length reality check

- Ollama defaults context by detected VRAM: under 24 GiB gives 4K, 24 to 48 GiB gives 32K,
  48 GiB and above gives 256K. This machine will therefore land on **4K or 32K by default**,
  which is too small.
- **OpenCode requires a 64K or larger context window** for local models (Ollama's own OpenCode
  guide states this; OpenCode's provider docs suggest starting at 16K to 32K if tool calls
  misbehave).
- The OpenAI-compatible endpoint has **no way to set context size per request**. For local
  models it must be set server-side (`OLLAMA_CONTEXT_LENGTH=64000 ollama serve`) or baked into
  a Modelfile (`PARAMETER num_ctx 64000` then `ollama create`), because OpenCode's own docs
  note that models defined only in `opencode.json` do not appear in the `ollama launch` picker.
- **The specification must include the KV-cache arithmetic** for a 20 B and a 27 B model at
  64 K context on 24 GB unified memory, and must state the recommended context length per
  candidate. It must also state what happens to throughput and to memory pressure.

### 2.4 Existing OpenCode configuration (user's global config directory)

```json
{
  "$schema": "https://opencode.ai/config.json",
  "share": "disabled",
  "provider": {
    "ollama-local": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Ollama Local",
      "options": { "baseURL": "http://127.0.0.1:11434/v1" },
      "models": { "qwen3.5:9b": { "name": "Qwen 3.5 9B - Local" } }
    },
    "featherless": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Featherless",
      "options": { "baseURL": "https://api.featherless.ai/v1" },
      "models": {
        "Qwen/Qwen3-Coder-Next": { "name": "Qwen3 Coder Next" },
        "Qwen/Qwen3-Coder-30B-A3B-Instruct": { "name": "Qwen3 Coder 30B A3B" },
        "zai-org/GLM-5.3-Flash": { "name": "GLM-5.3 Flash" },
        "zai-org/GLM-5.3": { "name": "GLM-5.3" },
        "moonshotai/Kimi-K3": { "name": "Kimi K3" }
      }
    }
  }
}
```

Notes: the `ollama-local` provider currently lists **only** `qwen3.5:9b`. There is no
`minimax-m3.1-flash:cloud` entry, so using the cloud model inside OpenCode requires either
adding it to that file or using `ollama launch opencode --model minimax-m3.1-flash:cloud`.
`opencode run` supports `--model provider/model`, `--dir`, `--format json`, `--variant`
(reasoning effort), and `--print-logs`.

### 2.5 Relevant CLI surfaces

```sh
ollama list                      # installed models
ollama ps                        # LOADED models: NAME, ID, SIZE, PROCESSOR, CONTEXT, RUNNER, UNTIL
ollama pull TAG
ollama run TAG
ollama launch opencode --model TAG
ollama launch opencode --config  # write config without launching
OLLAMA_CONTEXT_LENGTH=64000 ollama serve
ollama stop TAG

opencode run "MESSAGE" --model provider/model --dir PATH --format json
opencode run "MESSAGE" --model provider/model --dir PATH --format json --variant high
```

---

## 3. Repository ground truth

### 3.1 Location and git state

- Path: `/Users/jacklee/Other/Me/Projects/local-coder`
- Remote: `https://github.com/Jacklee504/localmodel.git` (branch `main`)
- HEAD: `bdbd2e07cd34a239da820e77610f2fd3069b7351` ("Document paused training and evaluation workflow")
- Working tree: **clean**. Seven commits total:

```
bdbd2e0 Document paused training and evaluation workflow
067b255 Add local model evaluation harness
d1daf09 Add practical coding task fixtures
243958b Expand the original pilot dataset to 100 examples
c8598f0 Record QLoRA smoke run
8c375ac bms
d4377cb Record scored baseline benchmark
d0d8a2f Initial commit
```

- **Git commits are disabled in this environment.** The user must run commit commands manually.
  The specification must therefore deliver commit *commands* and *messages*, never perform commits.
- No AI or tool attribution in commit metadata. Use the user's existing git identity.

### 3.2 File layout (excluding `.git`, `.venv`, `models/`, `__pycache__`)

```
.
|-- .gitignore
|-- README.md
|-- adapters/.gitkeep
|-- adapters/smoke/{adapter_config.json, adapters.safetensors}
|-- benchmarks/
|   |-- README.md
|   |-- baseline/baseline/{metadata.json, responses.jsonl, scores.jsonl}
|   |-- tasks.jsonl
|   `-- trained/.gitkeep
|-- config/models.json
|-- configs/train_v1.sh
|-- data/{README.md, train.jsonl, valid.jsonl, test.jsonl}
|-- docs/
|   |-- evaluation_method.md
|   |-- experiment_log.md
|   `-- local_coder_v1_implementation_handoff.md
|-- reports/{.gitkeep, baseline_summary.md, model_selection.md}
|-- requirements.txt
|-- results/
|   |-- .gitkeep
|   `-- qwen25_7b/RUN-ID/   (six runs, see 3.13)
|-- scripts/
|   |-- check_environment.py
|   |-- compare_results.py
|   |-- evaluate.py
|   |-- infer.py
|   |-- run_benchmark.py
|   `-- validate_dataset.py
|-- tasks/
|   |-- README.md
|   |-- core.json
|   `-- fixtures/TASK-ID/
`-- tests/test_evaluate.py
```

`.gitignore` contains: `models/`, `.venv/`, `adapters/`, `results/*` (with `!results/.gitkeep`),
`__pycache__/`, `*.pyc`, `*.class`. Total repo size on disk is about 4.7 GB, dominated by the
`models/` directory and the smoke adapter, both ignored.

### 3.3 `README.md` (current, verbatim)

```markdown
# Local Coder

**Training status: paused pending evaluation of existing local models.** The V1 training script and frozen 30-task benchmark are preserved for possible later use.

The practical model-selection suite is in [tasks/README.md](tasks/README.md), with its method in [docs/evaluation_method.md](docs/evaluation_method.md). Configure a locally installed model or running OpenAI-compatible endpoint in `config/models.json`. No weights are downloaded automatically.

.venv/bin/python scripts/evaluate.py tasks
.venv/bin/python scripts/evaluate.py run --model qwen25_7b --mode response
.venv/bin/python scripts/evaluate.py run --model qwen25_7b --mode repo
.venv/bin/python scripts/evaluate.py score results/qwen25_7b/RUN_ID --task config-parse --score 1 --notes 'Missing validation' --failure 'ignored requirement' --corrections 0
.venv/bin/python scripts/evaluate.py compare results/qwen25_7b/RUN_A results/qwen35_9b/RUN_B --output reports/comparison.md

Each run has a unique directory under `results/`. Repository mode validates applied changes in a temporary fixture copy and captures a diff. Response mode records text and timing only. Scores are entered manually. Comparison requires matching suites and modes; see [reports/model_selection.md](reports/model_selection.md) for the pending final decision.

## Earlier V1 experiment

The commands below document the earlier experiment. Training is paused; do not run the training step while evaluating existing models.

A small QLoRA experiment for `mlx-community/Qwen2.5-Coder-7B-Instruct-4bit` on Apple Silicon. The frozen benchmark is separate from the training, validation and test splits. See [the handoff](docs/local_coder_v1_implementation_handoff.md) for the research question.

The model is expected at `models/qwen2.5-coder-7b-instruct-4bit`. Set `LOCAL_CODER_MODEL` to another local copy if needed. Create an environment with `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` if one does not exist.

.venv/bin/python scripts/check_environment.py
.venv/bin/python scripts/infer.py --prompt 'Implement a Python clamp function.'
.venv/bin/python scripts/run_benchmark.py --run-name baseline
.venv/bin/python scripts/validate_dataset.py

Score responses in `benchmarks/baseline/baseline/scores.jsonl`: score 0 (incorrect), 1 (partial), or 2 (correct), with notes and `constraints_met` / `code_correct` booleans. Keep raw responses unchanged. After freezing, running and scoring the base benchmark, generate a summary with `.venv/bin/python scripts/compare_results.py --baseline baseline` and commit the task definition and summary. Then train with `bash configs/train_v1.sh`, run the same benchmark with `--adapter adapters/impl-v1 --run-name impl-v1`, and compare with `.venv/bin/python scripts/compare_results.py --baseline baseline --candidate impl-v1`.

For a pipeline smoke run after baseline scoring, use `ITERS=5 ADAPTER_PATH=./adapters/smoke bash configs/train_v1.sh`, then pass `--adapter adapters/smoke` to inference. The original 20 examples were pipeline data; the expanded 100-example set is an offline pilot and remains below the handoff's suggested size for a real run. The 500-iteration default is for a later reviewed dataset. Generated runs and adapters should not be committed. No training starts during repository setup.
```

### 3.4 `docs/evaluation_method.md` (current, verbatim)

```markdown
# Local model evaluation

Training is paused pending comparison of existing local models. The previous 30-task baseline and training artifacts remain available.

The new suite asks each model to handle the same ten fixture repositories. Response mode records its proposal and generation timing. Repository mode asks for complete replacement contents for changed files as JSON, applies allowed changes to a temporary fixture copy, runs the task's listed commands, and records their status, output, and a unified diff. A failed response parse is recorded as an execution error. No response is treated as a successful code change until it has been applied and validated.

Manual review supplies a 0/1/2 score, requirement failures, notes, and correction count. A score of 2 means the task and its stated constraints are met, 1 means useful but incomplete, and 0 means failed. Review unrelated changes and unnecessary complexity even if validation passes. Correction count is entered by the reviewer; this harness runs one model attempt per task and does not conduct an automatic repair loop. A first-pass success has score 2 and zero corrections. Unscored records stay unscored in reports.

The comparison command requires identical task IDs, mode, generation settings, and hashes of the task definition plus fixtures. It reports objective repository validation separately from manual success. Model timing is approximate. MLX token count is calculated from the response; endpoint token count uses provider usage when supplied. Time to first token and peak memory remain null where unavailable. A nonstreaming endpoint response cannot give a reliable first-token time.

Models are configured in `config/models.json`. MLX models require an existing local path. OpenAI-compatible models require a running local server and a served model ID; optional `api_key_env` names an environment variable. Configuration does not download weights or start servers. Paths and endpoints in the candidate entries are placeholders to edit after installing the models.
```

### 3.5 `docs/experiment_log.md` (current, verbatim)

```markdown
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
```

### 3.6 `reports/model_selection.md` (current, verbatim)

```markdown
# Local model selection

Status: pending candidate runs. Training remains paused.

The Qwen3.5-9B, Qwen3.8-27B, and Qwen3-Coder-30B-A3B weights are not installed in this repository. No comparison or recommendation among them is supported yet. Run the response and repository suites for each feasible candidate, manually score requirement adherence, and use `scripts/evaluate.py compare` on matching runs. Record the best overall model, difficult-task model, routine-work model, whether maintaining two is worthwhile, repeated weaknesses, and whether any weakness justifies returning to fine-tuning.

The installed Qwen2.5-Coder-7B is available as a workflow check when Metal is accessible. The attempted run in this execution session stopped before inference because MLX reported no Metal device. It is a reference model rather than one of the three selection candidates.
```

### 3.7 `reports/baseline_summary.md` (the frozen V1 baseline, must NOT be modified)

Benchmark SHA-256 `da6167e89cbc333b23a21b90164db7d91337703831f9f726b270e7ad2d6067f6`,
model `mlx-community/Qwen2.5-Coder-7B-Instruct-4bit`, greedy, `max_tokens: 512`.

| Category | Tasks | Correct | Rate | Mean score |
|---|---:|---:|---:|---:|
| overall | 30 | 11 | 36.7% | 1.07 |
| java | 3 | 1 | 33.3% | 0.67 |
| multi_file_reasoning | 4 | 3 | 75.0% | 1.75 |
| python_debugging | 5 | 2 | 40.0% | 1.00 |
| python_implementation | 6 | 2 | 33.3% | 1.00 |
| refactoring | 3 | 2 | 66.7% | 1.67 |
| typescript_javascript | 5 | 1 | 20.0% | 1.00 |
| unit_test_generation | 4 | 0 | 0.0% | 0.50 |

Documented failure examples: `pyi-03` calls `fsync` after closing the file; `pyd-05` calls `len`
on a one-shot iterable; `test-02` checks the wrong sleep function; `js-04` accepts partial
numeric strings; `java-01` uses a nonexistent `HashSet` constructor; `java-03` was truncated
at the 512-token limit.

### 3.8 `config/models.json` (current, verbatim)

```json
{
  "models": {
    "qwen25_7b": {"name": "Qwen2.5-Coder-7B-Instruct-4bit", "provider": "mlx", "path": "models/qwen2.5-coder-7b-instruct-4bit", "quantization": "4-bit", "runtime": "mlx-lm"},
    "qwen35_9b": {"name": "Qwen3.5-9B", "provider": "openai_compatible", "base_url": "http://localhost:8000/v1", "model": "qwen3.5-9b", "quantization": null, "runtime": null},
    "qwen38_27b": {"name": "Qwen3.8-27B", "provider": "openai_compatible", "base_url": "http://localhost:8000/v1", "model": "qwen3.8-27b", "quantization": null, "runtime": null},
    "qwen3_coder_30b": {"name": "Qwen3-Coder-30B-A3B", "provider": "openai_compatible", "base_url": "http://localhost:8000/v1", "model": "qwen3-coder-30b-a3b", "quantization": null, "runtime": null}
  }
}
```

### 3.9 `tasks/core.json` (current, verbatim)

```json
{
  "tasks": [
    {"id":"config-parse","title":"Validate a small model configuration","category":"python_implementation","source":"local-coder configuration workflow","prompt":"Implement load_models(path) in config_reader.py. Read JSON with a top-level models object. Each model needs a nonempty provider. MLX models need a local path; openai_compatible models need a base_url and model. Raise ValueError for malformed data and preserve the mapping returned to callers. Do not add dependencies or alter the public signature.","editable":["config_reader.py"],"validation":[["python3","-m","unittest","discover","-s","tests","-v"]]},
    {"id":"result-summary","title":"Summarize scored evaluation records","category":"python_implementation","source":"local-coder baseline scoring workflow","prompt":"Implement summarize(records) in summary.py. Return a dict with total, scored, successful and average_score. A score of None is unscored; only scores 0, 1, 2 are valid. Reject invalid scores with ValueError. Empty scored sets have average_score None. Do not mutate records.","editable":["summary.py"],"validation":[["python3","-m","unittest","discover","-s","tests","-v"]]},
    {"id":"cache-leak","title":"Prevent cross-user report cache leakage","category":"python_debugging","source":"sanitized report-cache defect pattern","prompt":"Fix report_cache.py so cache entries include user identity as well as filters. Filters can be provided in any insertion order and contain scalar JSON values. Preserve get_report(user_id, filters, build) and avoid extra builds for equivalent requests.","editable":["report_cache.py"],"validation":[["python3","-m","unittest","discover","-s","tests","-v"]]},
    {"id":"retry-final","title":"Correct retry exhaustion behavior","category":"python_debugging","source":"sanitized HTTP retry defect pattern","prompt":"Fix retry.py. Keep call_with_retry(request, sleep, attempts=3). Retry TimeoutError only; sleep with delays 1, 2, ... only before another attempt. Reraise the last timeout, and reject attempts less than 1 with ValueError. Preserve other exceptions.","editable":["retry.py"],"validation":[["python3","-m","unittest","discover","-s","tests","-v"]]},
    {"id":"score-tests","title":"Add boundary tests for manual scoring","category":"unit_testing","source":"local-coder manual scoring workflow","prompt":"Add unittest tests in tests/test_scores.py for score_label in scoring.py. Cover all valid scores 0, 1, 2, invalid negative and high scores, noninteger values, and confirm the input is not coerced. Do not change scoring.py.","editable":["tests/test_scores.py"],"validation":[["python3","-m","unittest","discover","-s","tests","-v"]]},
    {"id":"web-search","title":"Prevent stale search responses","category":"typescript_web","source":"sanitized web search effect pattern","prompt":"Fix search.js so createSearch(fetcher) exposes async search(query) and only the newest request may update its results. Abort the previous request when a new one begins. A rejected or aborted request must not produce an unhandled rejection. Keep the public API and do not add dependencies.","editable":["search.js"],"validation":[["node","--test","search.test.js"]]},
    {"id":"java-names","title":"Normalize unique names","category":"java","source":"sanitized university Java collection exercise","prompt":"Implement Names.uniqueNames(List<String>) in Names.java. Ignore null and blank entries, trim names, deduplicate case-insensitively with Locale.ROOT, preserve the first trimmed spelling and input order, and return a new list. Do not mutate the input.","editable":["Names.java"],"validation":[["javac","Names.java","NamesTest.java"],["java","NamesTest"]]},
    {"id":"api-key","title":"Validate keys at the API boundary","category":"multi_file","source":"sanitized API and storage boundary pattern","prompt":"Change api.py and store.py as needed so put(db, key, value) rejects empty-string keys with ValueError before writing. Direct callers of save must retain its current behavior. Preserve public signatures and avoid unrelated changes.","editable":["api.py","store.py"],"validation":[["python3","-m","unittest","discover","-s","tests","-v"]]},
    {"id":"user-validation","title":"Deduplicate user validation","category":"refactoring","source":"sanitized service validation pattern","prompt":"Refactor users.py to remove duplicate validation in create_user and update_user. Keep signatures, return values, and exact ValueError messages unchanged. Do not change the save functions or introduce a dependency.","editable":["users.py"],"validation":[["python3","-m","unittest","discover","-s","tests","-v"]]},
    {"id":"task-loader","title":"Implement a detailed task-loading specification","category":"implementation_document","source":"local-coder task-loading requirements","prompt":"Implement the requirements in REQUIREMENTS.md in loader.py. Keep the existing load_tasks(path) signature, use only the standard library, and make the focused changes needed to satisfy the document.","editable":["loader.py"],"validation":[["python3","-m","unittest","discover","-s","tests","-v"]]}
  ]
}
```

### 3.10 All ten fixtures (verbatim, complete)

**`tasks/fixtures/config-parse/config_reader.py`**
```python
import json


def load_models(path):
    return json.loads(open(path, encoding="utf-8").read())["models"]
```
A `tests/test_config_reader.py` also exists. Assume it tests the behaviours named in the prompt:
nonempty provider, MLX path, openai_compatible base_url and model, ValueError on malformed
data, and that the mapping is preserved.

**`tasks/fixtures/result-summary/summary.py`**
```python
def summarize(records):
    scores = [record["score"] for record in records]
    return {"total": len(scores), "scored": len(scores), "successful": sum(score == 2 for score in scores),
            "average_score": sum(scores) / len(scores)}
```

**`tasks/fixtures/result-summary/tests/test_summary.py`**
```python
import unittest
from summary import summarize


class SummaryTests(unittest.TestCase):
    def test_mixed(self):
        records = [{"score": 2}, {"score": 0}, {"score": None}]
        self.assertEqual(summarize(records), {"total": 3, "scored": 2, "successful": 1, "average_score": 1.0})
        self.assertEqual(records[-1]["score"], None)

    def test_unscored(self):
        self.assertEqual(summarize([{"score": None}])["average_score"], None)

    def test_invalid(self):
        with self.assertRaises(ValueError):
            summarize([{"score": 4}])
```

**`tasks/fixtures/cache-leak/report_cache.py`**
```python
cache = {}


def get_report(user_id, filters, build):
    key = tuple(sorted(filters.items()))
    if key not in cache:
        cache[key] = build(user_id, filters)
    return cache[key]
```

**`tasks/fixtures/retry-final/retry.py`**
```python
def call_with_retry(request, sleep, attempts=3):
    for attempt in range(attempts):
        try:
            return request()
        except TimeoutError:
            sleep(2 ** attempt)
```

**`tasks/fixtures/score-tests/scoring.py`**
```python
def score_label(score):
    if not isinstance(score, int) or isinstance(score, bool) or score not in (0, 1, 2):
        raise ValueError("score must be 0, 1 or 2")
    return ("failed", "partial", "successful")[score]
```

**`tasks/fixtures/web-search/search.js`**
```javascript
function createSearch(fetcher) {
  let results = [];
  return {
    get results() { return results; },
    async search(query) {
      const response = await fetcher('/api/search?q=' + encodeURIComponent(query));
      results = await response.json();
    }
  };
}
module.exports = { createSearch };
```

**`tasks/fixtures/java-names/Names.java`**
```java
import java.util.List;

public class Names {
    public static List<String> uniqueNames(List<String> names) {
        return names;
    }
}
```

**`tasks/fixtures/api-key/api.py`**
```python
from store import save


def put(db, key, value):
    save(db, key, value)
    return {"ok": True}
```

**`tasks/fixtures/api-key/store.py`**
```python
def save(db, key, value):
    db[key] = value
```

**`tasks/fixtures/user-validation/users.py`**
```python
def save_new(name, age):
    return ("new", name, age)


def save_existing(user_id, name, age):
    return (user_id, name, age)


def create_user(name, age):
    if not name:
        raise ValueError("name required")
    if age < 0:
        raise ValueError("age invalid")
    return save_new(name, age)


def update_user(user_id, name, age):
    if not name:
        raise ValueError("name required")
    if age < 0:
        raise ValueError("age invalid")
    return save_existing(user_id, name, age)
```

**`tasks/fixtures/user-validation/tests/test_users.py`**
```python
import unittest
from users import create_user, update_user


class UserTests(unittest.TestCase):
    def test_returns(self):
        self.assertEqual(create_user("Ada", 20), ("new", "Ada", 20))
        self.assertEqual(update_user(4, "Ada", 20), (4, "Ada", 20))

    def test_errors(self):
        for call in (lambda: create_user("", 1), lambda: update_user(1, "", 1)):
            with self.assertRaisesRegex(ValueError, "^name required$"):
                call()
        for call in (lambda: create_user("A", -1), lambda: update_user(1, "A", -1)):
            with self.assertRaisesRegex(ValueError, "^age invalid$"):
                call()
```

**`tasks/fixtures/task-loader/REQUIREMENTS.md`**
```markdown
# Task loader requirements

`load_tasks(path)` reads a UTF-8 JSON file containing an object with a `tasks` list.
Each task must be an object with a nonblank string `id` and `prompt`.
IDs must be unique. An empty task list is invalid.
Return the task list in source order, preserving extra fields.
Raise `ValueError` for invalid JSON, unreadable files, wrong shapes, missing
fields, blank values, or duplicate IDs. Include the task index or ID in errors
where useful. Do not silently skip malformed entries.
```

**`tasks/fixtures/task-loader/loader.py`**
```python
import json


def load_tasks(path):
    return json.loads(open(path, encoding="utf-8").read())["tasks"]
```

### 3.11 `scripts/evaluate.py` (current, verbatim, complete: the core of the harness)

```python
"""Small local-model evaluator for response and isolated repository tasks."""

import argparse
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "tasks/core.json"
MODELS = ROOT / "config/models.json"
RESULTS = ROOT / "results"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def safe_name(value):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", value):
        raise ValueError(f"Invalid name: {value}")
    return value


def safe_file(value):
    path = Path(value)
    if path.is_absolute() or not path.parts or any(part in (".", "..") for part in path.parts):
        raise ValueError(f"Unsafe fixture path: {value}")
    return path


def load_tasks():
    data = read_json(SUITE)
    tasks = data["tasks"]
    ids = set()
    for task in tasks:
        task_id = safe_name(task["id"])
        if task_id in ids:
            raise ValueError(f"Duplicate task: {task_id}")
        ids.add(task_id)
        fixture = ROOT / "tasks/fixtures" / task_id
        if not fixture.is_dir():
            raise ValueError(f"Missing fixture: {fixture}")
        for name in task["editable"]:
            safe_file(name)
            if not (fixture / name).is_file():
                raise ValueError(f"Missing editable file: {fixture / name}")
        for command in task["validation"]:
            if not isinstance(command, list) or not command or not all(isinstance(x, str) for x in command):
                raise ValueError(f"Invalid validation command in {task_id}")
    return tasks


def suite_hash(tasks):
    digest = hashlib.sha256(SUITE.read_bytes())
    for task in tasks:
        for name, body in fixture_files(task).items():
            digest.update(task["id"].encode())
            digest.update(name.encode())
            digest.update(body.encode())
    return digest.hexdigest()


def fixture_files(task):
    fixture = ROOT / "tasks/fixtures" / task["id"]
    files = {}
    for path in sorted(fixture.rglob("*")):
        if "__pycache__" in path.parts or path.suffix in (".pyc", ".class"):
            continue
        if path.is_symlink():
            raise ValueError(f"Symlink in fixture: {path}")
        if path.is_file():
            files[str(path.relative_to(fixture))] = path.read_text(encoding="utf-8")
    return files


def make_prompt(task, mode):
    files = fixture_files(task)
    shown = "\n\n".join(f"--- {name} ---\n{body}" for name, body in files.items())
    prompt = f"Task: {task['title']}\n\n{task['prompt']}\n\nRepository files:\n{shown}"
    if mode == "repo":
        prompt += ("\n\nReturn only a JSON object with a 'files' object mapping each changed path "
                   "to its complete new UTF-8 contents. Change only these paths: "
                   + ", ".join(task["editable"]) + ". Do not include unchanged files.")
    return prompt


class Model:
    def __init__(self, config):
        self.config = config
        self.loaded = None
        if config["provider"] == "mlx":
            path = Path(config["path"])
            if not path.is_absolute():
                path = ROOT / path
            if not (path / "config.json").is_file():
                raise ValueError(f"Local model unavailable: {path}")
            from mlx_lm import load
            self.loaded = load(str(path))
        elif config["provider"] != "openai_compatible":
            raise ValueError(f"Unsupported provider: {config['provider']}")

    def generate(self, prompt, max_tokens):
        start = time.perf_counter()
        if self.loaded:
            from mlx_lm import generate
            model, tokenizer = self.loaded
            chat = tokenizer.apply_chat_template(
                [{"role": "user", "content": prompt}], tokenize=False, add_generation_prompt=True
            )
            answer = generate(model, tokenizer, chat, max_tokens=max_tokens, verbose=False)
            tokens = len(tokenizer.encode(answer))
            first_token = None
        else:
            config = self.config
            url = config["base_url"].rstrip("/") + "/chat/completions"
            body = json.dumps({"model": config["model"], "messages": [{"role": "user", "content": prompt}],
                               "max_tokens": max_tokens, "stream": False}).encode()
            headers = {"Content-Type": "application/json"}
            if config.get("api_key_env"):
                headers["Authorization"] = "Bearer " + os.environ[config["api_key_env"]]
            request = urllib.request.Request(url, body, headers)
            with urllib.request.urlopen(request, timeout=600) as response:
                result = json.load(response)
            answer = result["choices"][0]["message"]["content"]
            tokens = result.get("usage", {}).get("completion_tokens")
            first_token = None
        seconds = time.perf_counter() - start
        return answer, {"generation_seconds": round(seconds, 3), "first_token_seconds": first_token,
                        "tokens_generated": tokens, "tokens_per_second": round(tokens / seconds, 2) if tokens and seconds else None,
                        "peak_memory_bytes": None}


def parse_changes(answer, editable):
    value = answer.strip()
    if value.startswith("```"):
        value = re.sub(r"^```(?:json)?\s*|\s*```$", "", value)
    data = json.loads(value)
    changes = data["files"]
    if not isinstance(changes, dict) or not changes:
        raise ValueError("Response has no changed files")
    if any(name not in editable or not isinstance(body, str) for name, body in changes.items()):
        raise ValueError("Response contains a disallowed path or nontext content")
    return changes


def execute_repo(task, answer):
    changes = parse_changes(answer, set(task["editable"]))
    fixture = ROOT / "tasks/fixtures" / task["id"]
    with tempfile.TemporaryDirectory(prefix="local-coder-eval-") as directory:
        workspace = Path(directory) / "repo"
        shutil.copytree(fixture, workspace, symlinks=False,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.class"))
        before = {name: (workspace / name).read_text(encoding="utf-8") for name in changes}
        for name, body in changes.items():
            (workspace / name).write_text(body, encoding="utf-8")
        diff = "".join("".join(difflib.unified_diff(before[name].splitlines(keepends=True),
                      body.splitlines(keepends=True), fromfile="a/" + name, tofile="b/" + name))
                      for name, body in changes.items())
        checks = []
        for command in task["validation"]:
            try:
                process = subprocess.run(command, cwd=workspace, capture_output=True, text=True, timeout=60,
                                         env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
                checks.append({"command": command, "exit_code": process.returncode,
                               "output": (process.stdout + process.stderr)[-16000:]})
            except (OSError, subprocess.TimeoutExpired) as exc:
                checks.append({"command": command, "exit_code": None, "output": str(exc)})
        return {"changes": changes, "diff": diff, "validation": checks,
                "validation_passed": bool(checks) and all(x["exit_code"] == 0 for x in checks)}


def git_commit():
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


def run(args):
    tasks = load_tasks()
    if args.task:
        tasks = [task for task in tasks if task["id"] == args.task]
        if not tasks:
            raise ValueError(f"Unknown task: {args.task}")
    config = read_json(MODELS)["models"][args.model]
    try:
        model = Model(config)
    except ImportError as exc:
        raise ValueError(f"Model runtime unavailable: {exc}") from exc
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory = RESULTS / args.model / stamp
    directory.mkdir(parents=True, exist_ok=False)
    metadata = {"model_key": args.model, "model": config, "mode": args.mode,
                "created_utc": datetime.now(timezone.utc).isoformat(), "git_commit": git_commit(),
                "suite_sha256": suite_hash(load_tasks()),
                "generation": {"max_tokens": args.max_tokens}, "task_ids": [task["id"] for task in tasks]}
    write_json(directory / "metadata.json", metadata)
    for index, task in enumerate(tasks, 1):
        prompt = make_prompt(task, args.mode)
        started = time.perf_counter()
        record = {"id": task["id"], "category": task["category"], "mode": args.mode, "prompt": prompt,
                  "response": None, "timings": None, "repo": None, "error": None,
                  "manual": {"score": None, "notes": "", "requirement_failures": [], "corrections": None}}
        try:
            record["response"], record["timings"] = model.generate(prompt, args.max_tokens)
            if args.mode == "repo":
                record["repo"] = execute_repo(task, record["response"])
        except Exception as exc:
            record["error"] = f"{type(exc).__name__}: {exc}"
        record["wall_seconds"] = round(time.perf_counter() - started, 3)
        write_json(directory / (task["id"] + ".json"), record)
        print(f"{index}/{len(tasks)} {task['id']}: " + (record["error"] or "saved"), flush=True)
    print(directory)


def score(args):
    path = Path(args.run) / (safe_name(args.task) + ".json")
    record = read_json(path)
    record["manual"] = {"score": args.score, "notes": args.notes,
                        "requirement_failures": args.failure or [], "corrections": args.corrections}
    write_json(path, record)


def summarize(directory):
    meta = read_json(directory / "metadata.json")
    rows = [read_json(directory / (task_id + ".json")) for task_id in meta["task_ids"]]
    return meta, rows


def compare(args):
    runs = [summarize(Path(name)) for name in args.runs]
    first = runs[0][0]
    if any(meta["mode"] != first["mode"] or meta["task_ids"] != first["task_ids"] or
           meta["suite_sha256"] != first["suite_sha256"] or
           meta["generation"] != first["generation"] for meta, _ in runs[1:]):
        raise ValueError("Runs must use the same mode, suite, task IDs, and generation settings")
    lines = [f"# Local model comparison ({first['mode']})", "", "| Metric | " + " | ".join(
        meta["model_key"] for meta, _ in runs) + " |", "|---|" + "---:|" * len(runs)]
    def metric(label, function):
        lines.append("| " + label + " | " + " | ".join(function(rows) for _, rows in runs) + " |")
    metric("Manually successful (score 2)", lambda rows: str(sum(r["manual"]["score"] == 2 for r in rows)) + f"/{len(rows)}")
    metric("Unscored", lambda rows: str(sum(r["manual"]["score"] is None for r in rows)))
    metric("First pass success", lambda rows: str(sum(r["manual"]["score"] == 2 and r["manual"]["corrections"] == 0 for r in rows)))
    if first["mode"] == "repo":
        metric("Validation passing", lambda rows: str(sum(bool(r["repo"] and r["repo"]["validation_passed"]) for r in rows)) + f"/{len(rows)}")
    metric("Requirement failures", lambda rows: str(sum(len(r["manual"]["requirement_failures"]) for r in rows)))
    metric("Average corrections", lambda rows: average([r["manual"]["corrections"] for r in rows]))
    metric("Average generation seconds", lambda rows: average([r["timings"]["generation_seconds"] for r in rows if r["timings"]]))
    metric("Average tokens/sec", lambda rows: average([r["timings"]["tokens_per_second"] for r in rows if r["timings"]]))
    metric("Peak memory GiB", lambda rows: average([r["timings"]["peak_memory_bytes"] / 2**30
                                                    for r in rows if r["timings"] and r["timings"]["peak_memory_bytes"] is not None]))
    lines += ["", "## Per-task observations", ""]
    for task_id in first["task_ids"]:
        lines.append(f"### {task_id}")
        for meta, rows in runs:
            row = next(r for r in rows if r["id"] == task_id)
            manual = row["manual"]
            validation = row["repo"]["validation_passed"] if row["repo"] else "n/a"
            lines.append(f"- {meta['model_key']}: score {manual['score']}, validation {validation}; "
                         f"{manual['notes'] or row['error'] or 'No review note.'}")
        lines.append("")
    output = "\n".join(lines) + "\n"
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output, end="")


def average(values):
    numbers = [value for value in values if value is not None]
    return f"{sum(numbers) / len(numbers):.2f}" if numbers else "n/a"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("tasks")
    runner = commands.add_parser("run")
    runner.add_argument("--model", required=True)
    runner.add_argument("--mode", choices=("response", "repo"), required=True)
    runner.add_argument("--task")
    runner.add_argument("--max-tokens", type=int, default=1024)
    scoring = commands.add_parser("score")
    scoring.add_argument("run")
    scoring.add_argument("--task", required=True)
    scoring.add_argument("--score", type=int, choices=(0, 1, 2), required=True)
    scoring.add_argument("--notes", default="")
    scoring.add_argument("--failure", action="append")
    scoring.add_argument("--corrections", type=int, default=0)
    comparison = commands.add_parser("compare")
    comparison.add_argument("runs", nargs="+")
    comparison.add_argument("--output")
    args = parser.parse_args()
    try:
        if args.command == "tasks":
            for task in load_tasks():
                print(f"{task['id']}: {task['title']} ({task['category']})")
        elif args.command == "run":
            if args.max_tokens < 1:
                raise ValueError("max tokens must be positive")
            run(args)
        elif args.command == "score":
            if args.corrections < 0:
                raise ValueError("corrections must be nonnegative")
            score(args)
        else:
            compare(args)
    except (KeyError, OSError, ValueError, json.JSONDecodeError) as exc:
        parser.exit(1, f"Evaluation error: {exc}\n")


if __name__ == "__main__":
    main()
```

### 3.12 `tests/test_evaluate.py` (current, verbatim, complete)

```python
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import sys
from io import BytesIO
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import evaluate


class EvaluationTests(unittest.TestCase):
    def test_repository_response_is_applied_and_validated_in_copy(self):
        task = next(task for task in evaluate.load_tasks() if task["id"] == "api-key")
        original = (evaluate.ROOT / "tasks/fixtures/api-key/api.py").read_text()
        replacement = original.replace("    save(db, key, value)",
                                       "    if key == '':\n        raise ValueError('empty key')\n    save(db, key, value)")
        result = evaluate.execute_repo(task, json.dumps({"files": {"api.py": replacement}}))
        self.assertTrue(result["validation_passed"], result["validation"])
        self.assertIn("raise ValueError", result["diff"])
        self.assertEqual((evaluate.ROOT / "tasks/fixtures/api-key/api.py").read_text(), original)

    def test_rejects_unlisted_file(self):
        task = next(task for task in evaluate.load_tasks() if task["id"] == "api-key")
        with self.assertRaises(ValueError):
            evaluate.execute_repo(task, json.dumps({"files": {"tests/test_api.py": "pass"}}))

    def test_openai_compatible_request_and_usage(self):
        class Response(BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.close()

        def urlopen(request, timeout):
            self.assertEqual(request.full_url, "http://localhost:8000/v1/chat/completions")
            self.assertEqual(json.loads(request.data)["messages"][0]["content"], "hello")
            return Response(json.dumps({"choices": [{"message": {"content": "answer"}}],
                                        "usage": {"completion_tokens": 3}}).encode())

        model = evaluate.Model({"provider": "openai_compatible", "base_url": "http://localhost:8000/v1", "model": "test"})
        with patch.object(evaluate.urllib.request, "urlopen", urlopen):
            answer, timings = model.generate("hello", 20)
        self.assertEqual(answer, "answer")
        self.assertEqual(timings["tokens_generated"], 3)

    def test_response_run_and_report_keep_unscored_separate(self):
        class FakeModel:
            def __init__(self, config):
                pass

            def generate(self, prompt, max_tokens):
                return "proposal", {"generation_seconds": 0.1, "first_token_seconds": None,
                                    "tokens_generated": 2, "tokens_per_second": 20, "peak_memory_bytes": None}

        with tempfile.TemporaryDirectory() as folder, patch.object(evaluate, "RESULTS", Path(folder)), \
             patch.object(evaluate, "Model", FakeModel):
            evaluate.run(SimpleNamespace(model="qwen25_7b", mode="response", task="api-key", max_tokens=32))
            run_path = next((Path(folder) / "qwen25_7b").iterdir())
            record = evaluate.read_json(run_path / "api-key.json")
            self.assertIsNone(record["repo"])
            self.assertIsNone(record["manual"]["score"])
            output = Path(folder) / "comparison.md"
            evaluate.compare(SimpleNamespace(runs=[str(run_path)], output=str(output)))
            self.assertIn("Unscored | 1", output.read_text())
            self.assertNotIn("Validation passing", output.read_text())

    def test_full_repository_suite_records_every_validation(self):
        class FakeModel:
            def __init__(self, config):
                pass

            def generate(self, prompt, max_tokens):
                task = next(item for item in evaluate.load_tasks()
                            if prompt.startswith("Task: " + item["title"] + "\n"))
                name = task["editable"][0]
                body = evaluate.fixture_files(task)[name]
                return json.dumps({"files": {name: body}}), {"generation_seconds": 0.1,
                    "first_token_seconds": None, "tokens_generated": 1,
                    "tokens_per_second": 10, "peak_memory_bytes": None}

        with tempfile.TemporaryDirectory() as folder, patch.object(evaluate, "RESULTS", Path(folder)), \
             patch.object(evaluate, "Model", FakeModel):
            evaluate.run(SimpleNamespace(model="qwen25_7b", mode="repo", task=None, max_tokens=32))
            run_path = next((Path(folder) / "qwen25_7b").iterdir())
            for task in evaluate.load_tasks():
                record = evaluate.read_json(run_path / (task["id"] + ".json"))
                self.assertIsNone(record["error"], task["id"])
                self.assertEqual(len(record["repo"]["validation"]), len(task["validation"]))
                if task["id"] == "api-key":
                    self.assertFalse(record["repo"]["validation_passed"])
                if task["id"] == "score-tests":
                    self.assertTrue(record["repo"]["validation_passed"])
            output = Path(folder) / "comparison.md"
            evaluate.compare(SimpleNamespace(runs=[str(run_path)], output=str(output)))
            self.assertIn("Validation passing", output.read_text())


if __name__ == "__main__":
    unittest.main()
```

### 3.13 The six existing runs, and what they actually show

`results/qwen25_7b/` contains six run directories:

| Run ID | Mode | Tasks | Result |
|---|---|---|---|
| `20261007T093507092632Z` | repo | 1 (`api-key`) | validation false |
| `20261007T093547458557Z` | response | 3 | responses saved |
| `20261007T093710166067Z` | repo | 1 (`retry-final`) | validation false |
| `20261007T093721294443Z` | repo | 1 (`web-search`) | validation false |
| `20261007T093839643647Z` | response | 10 | responses saved |
| `20261007T094236959071Z` | repo | 10 | **4 validation-passing** |

In the final 10-task repo run, `validation_passed: true` for **`cache-leak`, `config-parse`,
`score-tests`, `user-validation`**; `false` for the other six (`api-key`, `java-names`,
`result-summary`, `retry-final`, `task-loader`, `web-search`). No record has a non-null
`error`, so **all six failures were applied changes that then failed the tests**, not
transport or parse failures. Generation was `max_tokens: 1024` throughout, with a
`suite_sha256` of `8dbe038dd7c32fe5bc3ea8b89c1c12bd8624cb79ce4027033b71384dce031637`
and git commit `bdbd2e0`.

**Every record in every run has `manual.score: null`. No run has ever been manually scored.**
The 4/10 figure is an objective validation count only.

Two worked examples of the failure modes:

- `result-summary`: the model produced a *syntactically valid* JSON change that filtered
  invalid scores out of the `valid_scores` list instead of raising `ValueError`, so
  `test_invalid` failed with `AssertionError: ValueError not raised`. It passed 2 of 3
  visible tests. **The visible test was right there and the model still missed it.**
- `user-validation`: the model returned `users.py` with the trailing newline stripped
  (`"age",\n` became `"age"`) and a mangled final line (`"age", ag` truncated in one case).
  It also made no semantic change at all, so it did not deduplicate the validation, and the
  task's actual requirement was not met even though the file was rewritten.

Both are instructive: one is a requirement-adherence failure with tests visible; the other is
a mechanical output-integrity failure (trailing newline or truncation) that a format-robustness
change could partly catch.

### 3.14 `configs/train_v1.sh` and the frozen training assets (for context only)

`configs/train_v1.sh` is runnable and must be left functionally intact. It runs
`check_environment.py`, `validate_dataset.py`, refuses to start unless
`reports/baseline_summary.md` and `benchmarks/tasks.jsonl` are committed and unmodified, then
runs `mlx_lm.lora --train` with `ITERS=500`, `ADAPTER_PATH=./adapters/impl-v1`,
`MODEL=models/qwen2.5-coder-7b-instruct-4bit`. Dataset is 100 examples (71 train, 15 valid,
14 test) in MLX-LM chat JSONL. `adapters/smoke/` holds a 5-iteration smoke adapter
(uncommitted, gitignored).

`requirements.txt` contains exactly one line: `mlx-lm==0.32.0`. The `openai_compatible` path
in `evaluate.py` uses only the standard library (`urllib.request`), so no new dependency is
needed for endpoint evaluation. Do not add dependencies unless the specification justifies a
specific one.

---

## 4. Audit: what is already wrong or missing

This is my own audit of the current implementation, not a list of things you should accept at
face value. Verify each against the code above and **correct me where I am wrong**. These are
the problems the specification must resolve.

### 4.1 Configuration does not match the real machine

1. The three candidate entries in `config/models.json` point at `http://localhost:8000/v1`.
   **No server runs there.** The real Ollama endpoint is `http://127.0.0.1:11434/v1`. The
   model ids (`qwen3.8-27b`, `qwen3-coder-30b-a3b`) are placeholders, not real Ollama tags.
2. There is **no entry for `minimax-m3.1-flash:cloud`**, the one model that is available now.
3. There is **no entry for `qwen3.5:9b`** even though it is already downloaded. The 9B
   lightweight baseline is currently unreachable through the harness.
4. The config schema has no place for per-model generation parameters, context length, notes,
   or a "how to start this model" hint. The README says configuration "should not download
   weights or start servers", which is correct, but the user then has to guess the exact
   `ollama pull` and `ollama launch` commands for each entry.

### 4.2 Response parsing is fragile in exactly the way modern models will break it

5. `parse_changes` does `json.loads(value)` after stripping only a leading or triple-backtick
   fence. Every modern candidate in this evaluation is a **thinking model** that emits
   reasoning before or around the answer (Qwen3.5 and Qwen3.8 have thinking on by default;
   `gpt-oss` exposes a reasoning channel; `minimax-m3.1-flash` is reasoning-first). Any of
   them may wrap the JSON in prose, emit think blocks, or emit the JSON inside a fence with a
   language tag. Each of those currently produces a generic `JSONDecodeError` recorded as
   `error`, which is then indistinguishable from a network timeout in the reports.
6. **Truncation is not detected.** With the default `--max-tokens 1024`, a full-file
   replacement for a 30 to 40 line file plus any reasoning will be cut off mid-string, and
   the resulting parse error is recorded as a *parse failure* rather than a *truncation*. These
   are different signals with different implications: one says the model cannot follow the
   output protocol, the other says the budget was too small.
7. `parse_changes` also accepts a JSON body whose `files` value is a dict with a *disallowed*
   path, and raises a generic `ValueError`. The message is fine, but the record has no
   machine-readable failure kind, so the report cannot tabulate failure modes.

### 4.3 Generation settings are too rigid and under-recorded

8. The request body is exactly `{model, messages, max_tokens, stream: false}`. There is no
   way to set `temperature`, `top_p`, `num_ctx`, a think or reasoning toggle, or
   `reasoning_effort`. The candidates need this: Qwen3.8 documents `reasoning_effort` and a
   thinking toggle; OpenCode exposes `--variant` for exactly this. A harness that cannot set
   them cannot evaluate these models on their intended settings.
9. `--max-tokens` defaults to **1024**, which is too small for repo mode on a reasoning
   model. Raising it is necessary, but `metadata["generation"]` stores only `{"max_tokens": N}`
   and `compare` requires the *entire* `generation` dict to be identical across runs. So any
   change to the token budget, and any future addition of temperature or reasoning settings,
   will silently make older and newer runs incomparable. The comparison key must be designed
   deliberately, not accidentally.
10. `urlopen(request, timeout=600)` is a hard-coded 10-minute ceiling. A 27B dense model on
    an M2 producing 8K tokens at single-digit tokens per second can exceed this. A timeout
    would be recorded as `TimeoutError` with no distinction from a model that chose to stop.
11. `stream: False` means `first_token_seconds` is **always `null`** on the endpoint path, and
    `peak_memory_bytes` is **always `null`**. Both are advertised in the comparison table and
    in the plan, and both currently render as "n/a" for every run. The plan explicitly says not
    to spend large effort on perfect telemetry, but "always null" is not a measurement.
12. The response is read as `result["choices"][0]["message"]["content"]`. A reasoning model
    may return the answer in a different field, or return `content` as a list of parts
    (Anthropic-style blocks), or return empty `content` with the payload elsewhere. The
    harness assumes exactly one shape.

### 4.4 Scoring is impractical at the scale this evaluation requires

13. The `score` subcommand takes one run, one task, one score. A full comparison is
    10 tasks by 4 candidates by 2 modes, which is **80 scoring invocations**, each rewriting
    the `manual` object wholesale. `manual.corrections` defaults to `0`, so a reviewer who
    forgets `--corrections` silently records a first-pass success. There is no bulk scoring,
    no way to leave a score blank, and no way to merge notes without clobbering.
14. There is **no written rubric** beyond the one sentence in `docs/evaluation_method.md`.
    The plan lists the requirement-failure categories that must be tracked (ignored
    requirement, unnecessary dependency, public API changed, unrelated refactor, invented
    file or API, excessive complexity, incomplete implementation), but the harness's `--failure`
    flag is a free-text string with no validation against that list. Two reviewers would
    produce incomparable data.
15. Nothing supports the plan's "how many additional prompts were required" metric.
    `docs/evaluation_method.md` says the reviewer enters it by hand, and there is no tooling
    to *conduct* a correction attempt, so the number is a recollection, not a measurement.

### 4.5 The comparison report cannot support a decision

16. `compare` requires identical mode, task IDs, `suite_sha256` and `generation`, which is
    good, but it has **no per-task failure-mode column**, **no breakdown by task category**
    (the plan explicitly cares about "difficult tasks" versus "routine work"), **no separation
    of error classes** (parse error versus timeout versus applied-but-failed-validation), and
    **no mapping to the plan's outcomes A, B, C, D**. The per-task section prints
    `manual.notes or row['error'] or 'No review note.'`, so an unscored run with no error
    prints "No review note." and is silently indistinguishable from a scored, clean run in
    the prose.
17. `compare` also does not surface **which allowlisted files the model left untouched**,
    so "made unnecessary changes" is only visible by eyeballing the diff. The plan treats
    unnecessary changes as a first-class metric.

### 4.6 Mode B does not measure what the user actually does

18. The plan's Mode B says: "Allow a model **or coding harness** to actually modify a
    temporary copy or worktree of a repository." The implemented repo mode is a **model-only
    JSON full-file-replacement protocol**. That is a genuinely different capability from
    agentic tool use: reading files, running tests, iterating on a failure, and making a
    surgical edit. The user's own daily workflow, that the current local Qwen needs OpenCode
    to make changes, is **not measured by the harness at all**. A model could pass all ten
    repo tasks via JSON output and still be useless inside OpenCode, and the reverse. The
    specification must close this gap, because the stated purpose is "which model should I
    use for day-to-day development".
19. `execute_repo` uses `shutil.copytree(..., symlinks=False)`, which **dereferences**
    symlinks, while `fixture_files` **rejects** them. The two paths disagree about symlink
    handling. Minor, but it is a real inconsistency in a security-relevant code path.
20. The temporary workspace is **not a git repository**, so the `git diff` that the plan
    lists as a Mode B signal is unavailable. The current `difflib` output covers only the
    files the model listed, not a whole-tree diff.
21. `execute_repo` writes files with `Path.write_text`, so file mode and permissions are
    reset and a trailing newline is not guaranteed. At least one observed 7B failure was
    exactly a lost trailing newline.

### 4.7 The task suite has specific weaknesses

22. **All tests are visible to the model.** The prompt includes every fixture file, including
    `tests/`. A model can satisfy the visible assertions without understanding the
    requirement. The `result-summary` run shows this: the model satisfied 2 of 3 visible
    tests while violating the stated "Reject invalid scores with ValueError" requirement.
    The suite needs **withheld tests** that the model never sees, executed only during
    validation. This is the single highest-value change to the suite and it is cheap.
23. **No task penalises unnecessary change.** Every task is satisfied by a minimal edit, but
    nothing measures whether the model rewrote unrelated code, reformatted, or added
    dependencies. The plan cares about this. A task should exist whose correct solution is
    *small* and whose tempting solution is *large*.
24. **No task exercises a non-test validation command.** The plan lists `pytest`,
    `npm test`, `mvn test`, and "tests, build, lint, type checks". All ten tasks use
    `python3 -m unittest`, `node --test`, or `javac` plus `java`. There is no lint, no type
    check, no build.
25. **No task gives the model a failing test output to debug from.** All debugging tasks
    present broken source with no observed symptom. Real debugging usually starts from a
    traceback or a failing assertion.
26. **The fixtures are sanitised stand-ins, not derived from the user's real repositories.**
    The user has explicitly authorised small, sanitised fixtures derived from: **Auto
    Trader**, **Dynamic Task Router**, **CAPTS/FYP**, **DealLedger**, **SoftwareEngineering
    Java coursework**, and this repository itself, with the constraint that only the minimum
    necessary context is copied, no credentials, no private data, no large repository
    sections, no generated files, and nothing licence-sensitive. The current suite only uses
    the last of those.
27. **The `score-tests` task is self-referential in a way that may be a confound.** The model
    is asked to write tests for a scoring function whose exact semantics it can only infer.
    Worth keeping, but note the 7B *passed* it, which suggests the task may be easier than
    intended and inflates the 4/10.

### 4.8 Operational and hygiene gaps

28. `results/` is gitignored, so **every result is untracked**. The final decision depends on
    those results. The specification must decide what needs to be committed (at minimum
    `reports/`, and probably the scored summary of each run) so the decision is reproducible
    and reviewable.
29. `metadata.json` records `git_commit`, `suite_sha256`, `mode`, `generation` and the model
    config, but **not the prompt text hash**, the Ollama or MLX version, the endpoint, or the
    runtime context length actually in force. Two runs with the same `generation` dict could
    have been produced under different context lengths and would still compare as "identical".
30. `docs/experiment_log.md` has no entry for the six 7B runs, and `reports/model_selection.md`
    still says "no comparison or recommendation among them is supported yet" while four
    validation-passing results exist unscored. The documentation is behind the artefacts.
31. The `mlx` provider path loads the model into the parent Python process with no way to
    observe its RSS. The endpoint path never touches the model process, so measuring the
    model's memory requires reading `ollama ps` (which gives SIZE and PROCESSOR) and/or
    sampling the Ollama process RSS from outside.

---

## 5. What I want you to produce

Produce **one specification document**. It must be implementation-ready: an engineer should
be able to work through it top to bottom without inventing design decisions, and without
asking "what did they mean?".

Organise it as follows.

### Part A: gap analysis and priority

- A table of every gap from section 4, with: identifier, one-line description, severity
  (P0 blocks evaluation, P1 materially weakens the decision, P2 improves ergonomics), and
  whether it must be fixed **before** the large models are downloaded.
- Call out any gap in section 4 that you believe is misdiagnosed, is not worth fixing, or is
  actually fine. If my audit is wrong, say so plainly.

### Part B: target design

For each subsystem, give the design precisely enough to implement:

1. **Model configuration schema.** The exact JSON shape for `config/models.json`, with every
   field, its type, whether it is required, and its default. It must support: provider
   (`mlx` or `openai_compatible`), endpoint, model id, per-model generation parameters
   (temperature, top_p, reasoning or thinking control, `reasoning_effort`, `num_ctx`),
   expected context length, download size, the exact `ollama pull` and `ollama launch`
   commands to run it, and free-text notes. It must be possible to add a model **without
   editing any Python**. Show the fully populated file with all five models: `qwen25_7b`
   (MLX), `qwen35_9b`, `minimax_m31_flash_cloud`, `qwen38_27b`, `qwen3_coder_30b`, plus
   `gpt_oss_20b` if you keep it.
2. **Request and response handling.** Exactly what is sent to the endpoint. How reasoning
   content is requested, where it is read from, how it is stripped. How the assistant
   message is extracted robustly (string versus list-of-parts versus alternate fields). A
   robust extraction algorithm for the "JSON object with a `files` map" contract that tolerates
   reasoning preambles, prose wrappers, and code fences, specified as an ordered set of
   rules, with a worked example for at least three different malformed-but-recoverable
   responses. Specify how **truncation** is detected and distinguished from a genuine
   protocol failure, and what a truncated record looks like.
3. **Structured failure taxonomy.** The exact set of machine-readable failure kinds
   (for example `http_error`, `timeout`, `truncated`, `unparseable`, `protocol_violation`,
   `disallowed_path`, `validation_failed`, `none`), where each is set, and how the comparison
   report aggregates them.
4. **Timing and memory telemetry.** Exactly what is measured, how, and what it means when
   unavailable. Cover wall clock, time to first token, tokens generated, tokens per second
   (define precisely: which tokens, prompt or completion or both, and over which interval),
   and peak memory. Specify how to obtain peak memory for an Ollama-served model from
   outside the Python process, and what to record when the model is a cloud model with no
   local memory. Keep it approximate but consistent; do not build a telemetry framework.
5. **Result record schema.** The exact JSON for `metadata.json` and for each per-task
   record, including the manual-scoring fields. Show a filled example. Specify exactly
   which fields are required for two runs to be comparable, and design that as a deliberate
   **comparison key** so that adding a new generation parameter does not silently invalidate
   the comparison of older runs, or, if it must, produces a clear actionable error instead of
   a wrong comparison.
6. **Scoring.** A written rubric a reviewer can apply consistently, with the
   requirement-failure categories from the plan made into a closed, validated vocabulary.
   Specify a bulk scoring workflow that does not require 80 invocations, a way to record a
   score of "not yet reviewed" distinctly from 0, and a way to record a correction attempt
   if one is made.
7. **Optional automatic correction loop.** Decide whether to add one. The plan treats "how
   many additional prompts were required" as one of the most useful metrics, and the current
   harness cannot measure it. Specify a *minimal* repair loop: how the failing validation
   output and the current diff are fed back, how many attempts, how the attempt count is
   recorded, and the cost of running it in time and tokens. It must remain optional and off
   by default, and it must not turn the harness into an autonomous platform.
8. **Agent-driven repository mode.** This is the most important missing capability. Specify
   a mode in which a **coding agent** (OpenCode is the one installed) actually edits a
   temporary copy of a fixture and the harness then applies the same objective validation.
   Address concretely: which agent invocation
   (`opencode run ... --format json --dir PATH`), how to point it at a specific model, how to
   sandbox it (the temp copy is the sandbox; what else must be disabled such as network
   access, `--auto` permission escalation, plugins), how the resulting diff is captured, how
   validation is run afterwards, how the agent's transcript and tool calls are recorded, how
   many tokens and how much time it consumed, and how this mode's results are kept
   **comparable or explicitly incomparable** to the JSON repo mode. Say plainly whether agent
   mode should be scored on the same 0/1/2 scale and why.
9. **Withheld (hidden) tests.** How to extend the task schema so a task can carry validation
   commands that run against files the model never sees, without those files leaking into the
   prompt. Specify the directory convention, how `fixture_files` and the prompt builder must
   change, and how `suite_hash` must incorporate the withheld files, since they must be
   hashed or two suites could differ invisibly.
10. **Task suite extension plan.** How to add 2 to 4 tasks that close the weaknesses in
    section 4.7: a task where the correct answer is a minimal edit and a larger edit is
    wrong; a task that supplies a failing test output as the starting point; a task with a
    lint or type-check validation command; and 1 to 2 tasks derived from the user's real
    repositories under the sanitisation rules. For the real-repository tasks, give the
    **procedure and checklist** for deriving a fixture (minimum necessary context, redaction
    checklist, licence check, how to record `source` metadata), not the task content itself.
11. **CLI surface.** The final command set, with flags, defaults, and a worked example
    invocation for each operation. Include how a user runs a full candidate evaluation end
    to end, how they score it, and how they compare candidates.
12. **Comparison report design.** The exact sections and tables of the generated report,
    including a category breakdown, a failure-mode breakdown, a per-task table, and a section
    that maps the results onto the plan's four outcomes (A: use two models; B: Qwen3-Coder
    matches Qwen3.8 but is faster; C: Qwen3.8 wins outright; D: all models fail the same
    task type, which is the trigger to revisit fine-tuning).
13. **Measurement protocol for the candidate runs.** The exact, ordered procedure for
    evaluating each candidate on this specific machine: the context length to set, the
    `ollama pull` and `ollama launch` commands, the `ollama ps` readings to capture and
    when, the Activity Monitor, `memory_pressure` and `sysctl vm.swapusage` readings to
    capture and when, how many repeats per task to distinguish signal from noise, and how
    to record all of it in the run metadata. Include the disk-space discipline (one or two
    candidates at a time, about 40 GB free) and the exact commands the **user** runs to
    reclaim space afterwards.
14. **The KV-cache and memory feasibility calculation.** For each candidate, the arithmetic
    for weights plus KV cache at 32K and 64K context on 24 GB unified memory, the
    recommended context length, and the predicted consequence for tokens per second and
    memory pressure. Show the working. If the numbers are uncertain, say so and give the
    measurement that would resolve it instead of a false precise figure.
15. **Sequencing plan for the 2-day cloud window.** The `minimax-m3.1-flash:cloud` model is
    available now and free for roughly two days. Specify, hour by hour if you like, what
    should be done **during that window** so that the harness is proven end to end and the
    scoring rubric is calibrated before the large models are downloaded. Include using it as
    a fast end-to-end smoke test of every harness change; using it as a *ceiling* reference
    (what does a strong model score on this suite?); using it to calibrate the rubric by
    scoring the same run twice and checking for self-consistency; and prototyping the
    agent-driven mode against it. Then specify exactly what must be finished before the
    window closes, and what can wait.
16. **The final decision document.** The exact structure of `reports/model_selection.md`,
    answering the plan's six questions: best overall model, best for difficult tasks, best
    for fast routine work, whether maintaining two models is worthwhile, whether there is a
    repeated weakness, and whether custom fine-tuning is justified. Include the **explicit,
    pre-registered thresholds** that decide the fine-tuning question, so the answer is not
    chosen after seeing the data. For example, define exactly what counts as "all models
    fail the same type of task repeatedly" as a category-level rule with a threshold, and a
    requirement that the failure mode be identical, not merely correlated.
17. **What the experiment log must record.** The fields to add to `docs/experiment_log.md`
    for each candidate run, and a backfill entry for the six unscored 7B runs.

### Part C: implementation plan

- An ordered list of implementation steps, each with: the file or files touched, the change in
  one sentence, the acceptance check, and the rough effort.
- A proposed commit sequence: **logically separate, focused commits with proposed commit
  messages**, each one independently meaningful, not squashed. Remember commits are disabled
  in the environment, so present the exact commands for the user to run. No AI or tool
  attribution in commit metadata. Do not propose a single mega-commit.
- The risk register: what could go wrong, what you would notice, and the cheapest mitigation.

### Part D: open questions

- The list of things a knowledgeable engineer would still need to decide, with your
  recommended default for each, so the user can answer in one pass rather than being
  interrogated. Separate "must be answered before implementing" from "can be decided later".

---

## 6. Constraints and non-goals

These are hard constraints. A specification that violates them is wrong.

**Do not:**

- Write, train, or schedule any model training. `configs/train_v1.sh` stays runnable and
  functionally unchanged. The 100-example dataset, the frozen 30-task benchmark, its
  baseline results, and the smoke adapter all stay exactly as they are.
- Rewrite, replace, or "improve" the frozen 30-task benchmark
  (`benchmarks/tasks.jsonl`, `benchmarks/baseline/`, `reports/baseline_summary.md`). The
  new suite sits *alongside* it, for a different purpose. Do not merge them.
- Automatically download model weights. The harness never runs `ollama pull`. The user runs
  it, deliberately, as a documented step.
- Automatically delete anything, ever. Disk reclamation is given as a command the user
  runs. No scripted recursive deletion of the Ollama store.
- Build a general benchmark framework, a web UI, a dashboard, a leaderboard scraper, a
  public-benchmark downloader, distributed inference, a model router, a planner and
  implementer pipeline, a judge model, RL, DPO, or synthetic data generation.
- Add dependencies without a specific justification. The endpoint path needs no
  third-party package today; keep it that way unless you identify a concrete need.
- Touch `benchmarks/`, `data/`, `configs/train_v1.sh`, or `adapters/` at all.
- Claim any result you did not actually observe. You have no access to the machine; you are
  specifying work, not reporting it.
- Use em dashes in your prose. Use en dashes or other punctuation.

**Must:**

- Keep `scripts/evaluate.py` recognisably the same program. The repository is meant to stay
  "understandable without extensive documentation". A rewrite into a package with many modules
  is a failure, not a feature. If you think a modest structural change is justified, say why
  and keep it proportionate.
- Preserve every existing result directory. Never overwrite a run.
- Keep the harness independent of the runtime: MLX, Ollama, LM Studio, llama.cpp and any
  OpenAI-compatible server must all be usable through configuration alone.
- Keep the manual 0/1/2 scale. It is the primary human judgement signal and it is what
  makes two models' results comparable.
- Keep response mode and repo mode as distinct, separately-comparable things. Response
  mode has no validation and must never be reported as if it did.
- Respect the 24 GB memory ceiling and the about 40 GB disk ceiling in every recommendation.

## 7. Quality bar for your answer

- **Be concrete.** "Add better error handling" is worthless. "Add a `failure_kind` field
  set to exactly one of `{http_error, timeout, truncated, unparseable, protocol_violation,
  disallowed_path, validation_failed, none}`, set at the point of failure in `run()`" is
  what is needed.
- **Cite the code.** Refer to real function names: `make_prompt`, `parse_changes`,
  `execute_repo`, `run`, `score`, `compare`, `suite_hash`, `fixture_files`, `Model.generate`.
  Do not invent identifiers.
- **Do the arithmetic.** When you claim a memory figure, show the working and label your
  confidence.
- **Distinguish what you know from what you are inferring.** Where the answer depends on
  something you cannot see (the real behaviour of a specific model's chat template, the
  exact KV-cache size for a given quantisation, how a specific agent CLI reports token
  usage), say what you are assuming, what the assumption buys, and how to verify it cheaply.
- **Be honest about difficulty.** If something genuinely cannot be specified without
  running it, say that and specify the measurement instead. Do not paper over the gap.
- **Prefer the smallest sufficient design.** The plan's guiding principle is: do exactly
  what is needed to answer the question, and do not over-build. A specification that
  proposes a large refactor is the wrong answer even if it is internally consistent.
- **Read all of section 3 before answering.** The design must fit the code that exists.

## 8. What a good answer looks like

A reviewer should be able to take your document, hand it to an implementer, and get a
harness that: evaluates any configured local or cloud model on the ten real tasks, with
hidden tests, robust parsing, structured failures, honest telemetry, a repeatable rubric,
and a report that supports a decision, and that can be operated on a 24 GB M2 laptop with
a 40 GB disk, against four candidate models, two of which are 18 to 19 GB downloads, using
`ollama` and `opencode`, with training paused and no new dependencies.

Produce the specification now. If you need to ask questions, do it once, at the end, in
Part D, with a recommended default for each.
