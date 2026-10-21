# Overnight candidate runbook

This runbook evaluates a candidate model end to end on this machine. It assumes the
harness is already working and that you have chosen one candidate.

## The short version

```sh
ollama pull gpt-oss:20b
.venv/bin/python scripts/benchmark.py --model gpt_oss_20b
```

That is the whole benchmark. The runner checks the model is present, checks the served
context, runs the suites, writes a summary, and tells you how to score the results.
It never downloads weights and never deletes anything.

To benchmark one area:

```sh
.venv/bin/python scripts/benchmark.py --model gpt_oss_20b --suites complex
```

To run everything three times for stability:

```sh
.venv/bin/python scripts/benchmark.py --model gpt_oss_20b --repeats 3
```

The rest of this document explains what the runner does and what to do around it.

## Before you start

Check free disk space. You need the model weights plus room for the run results.

```sh
df -h /
```

With roughly 40 GB free you can hold one large candidate at a time. Do not pull the
second candidate until the first is evaluated and its space is reclaimed.

## 1. Pull the model

The harness never downloads weights. You do this deliberately.

```sh
ollama pull gpt-oss:20b
```

List the configured models to see the exact command for each candidate.

```sh
.venv/bin/python scripts/evaluate.py models
```

## 2. Set the context length

Ollama picks a default context from detected VRAM, which on this machine is too small
for agent use. OpenCode needs at least 64K.

Quit the Ollama desktop application first, then serve it explicitly:

```sh
OLLAMA_CONTEXT_LENGTH=64000 ollama serve
```

Leave that in its own terminal for the whole run. To restore normal operation later,
stop it and start the Ollama application again.

## 3. Verify the served context

This is the single most important check. A model that loaded is not necessarily a model
that has the context you asked for.

```sh
ollama ps
```

You want to see all three of:

```text
NAME           ID              SIZE     PROCESSOR    CONTEXT    RUNNER
gpt-oss:20b    <digest>        14 GB    100% GPU     65536      llamacpp
```

- `100% GPU` means it is resident in unified memory rather than partly swapped.
- `CONTEXT` must be at least 64000.

If the context is wrong, stop the model, fix the server setting, and reload:

```sh
ollama stop gpt-oss:20b
```

The harness records the observed context in every run's `metadata.json` and the
comparison report shows a `Context compliant` row. A run whose observed context is below
the requirement is marked non-compliant and must not be presented as a 64K result.

## 4. Check headroom before the run

```sh
memory_pressure | tail -2
sysctl vm.swapusage
```

You do not need every other app closed. You do need to know the starting values so you
can tell whether the run caused swapping. Note the swap figure now.

## 5. Run the suite

The runner does this for you:

```sh
.venv/bin/python scripts/benchmark.py --model gpt_oss_20b
```

The commands below are what it runs underneath, if you want to run one piece directly.

Full repository evaluation, one attempt:

```sh
.venv/bin/python scripts/evaluate.py run --model gpt_oss_20b --mode repo
```

Three attempts, for stability:

```sh
.venv/bin/python scripts/evaluate.py run --model gpt_oss_20b --mode repo --repeats 3
```

Response mode, which records proposals without applying them:

```sh
.venv/bin/python scripts/evaluate.py run --model gpt_oss_20b --mode response
```

Agent mode, where OpenCode makes the edit. It is roughly ten times slower per task, so
run it on a subset rather than the whole suite:

```sh
.venv/bin/python scripts/evaluate.py run --model gpt_oss_20b --mode agent \
  --task result-summary --task api-key --task web-search
```

Useful flags:

| Flag | Default | Notes |
|---|---|---|
| `--max-tokens N` | from the model config, 32768 for candidates | Do not change it between candidates. It is part of the comparison key. |
| `--suites NAMES` | `all` | Comma-separated suite names. See [docs/suites.md](suites.md). |
| `--mode MODE` | `repo` | `repo`, `response`, or `both`. |
| `--repeats N` | 1 | Each attempt gets its own run directory. |
| `--timeout-seconds N` | 3600 | Raise it for a slow dense model. |
| `--task ID` | all tasks | Repeat the flag to select several. |
| `--report PATH` | none | Write the JSON summary to a file. |

## 6. Watch the run

Each task prints a line as it completes:

```text
1/10 config-parse: saved
2/10 result-summary: validation_failed
```

`saved` means the harness-level outcome was clean. `validation_failed` means the change
was applied and the tests rejected it. Other labels are the failure taxonomy:
`http_error`, `timeout`, `truncated`, `unparseable`, `protocol_violation`,
`disallowed_path`.

In a second terminal, watch memory during the run:

```sh
while true; do date '+%H:%M:%S'; sysctl -n vm.swapusage; sleep 60; done
```

If swap grows steadily, the model is paging to disk and the timings for that stretch are
contaminated. Record that in the run notes.

## 7. Score the results

Scores are manual, on the same 0/1/2 scale for every candidate. Score each task:

```sh
.venv/bin/python scripts/evaluate.py score results/gpt_oss_20b/RUN_ID \
  --task result-summary --score 2 \
  --notes 'Rejects invalid scores as required' \
  --reviewer local-user
```

Record a requirement failure when one applies:

```sh
.venv/bin/python scripts/evaluate.py score results/gpt_oss_20b/RUN_ID \
  --task api-key --score 1 \
  --failure ignored_requirement \
  --failure-detail 'Rejects the key in store.save instead of the API boundary' \
  --reviewer local-user
```

The valid failure categories are: `ignored_requirement`, `unnecessary_dependency`,
`public_api_changed`, `unrelated_refactor`, `invented_file_or_api`,
`excessive_complexity`, `incomplete_implementation`, `output_corrupted`.

Record how many extra prompts the task needed, if you did a repair:

```sh
.venv/bin/python scripts/evaluate.py score results/gpt_oss_20b/RUN_ID \
  --task task-loader --score 2 --additional-prompts 1 --reviewer local-user
```

## 8. Compare candidates

```sh
.venv/bin/python scripts/evaluate.py compare \
  results/gpt_oss_20b/RUN_A results/qwen38_27b/RUN_B \
  --output reports/comparison.md
```

The comparison refuses to run if the runs are not comparable, and names the differing
field. A difference in `max_tokens` is the most common cause. Do not work around it by
editing metadata. Re-run one candidate under the same settings instead.

## 9. Reclaim disk

Only after the results are recorded:

```sh
ollama rm gpt-oss:20b
df -h /
```

`ollama rm` removes the model weights. It does not touch your run results, which live
under `results/` and are ignored by git.

## What to record

For each candidate, note in `docs/experiment_log.md`:

- the model tag, quantisation, and observed served context;
- the exact command used, including `--max-tokens` and `--repeats`;
- validation passing count and any failure kinds;
- the manual score total and which tasks were not scored;
- the average generation seconds and tokens per second;
- whether swap grew during the run;
- the outcome against the pre-registered thresholds in `docs/local_coder_spec.md`.
