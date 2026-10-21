# Benchmark suites

The suite is nineteen tasks grouped into named suites, so you can benchmark one area at a
time or run everything. Suites are defined in [config/suites.json](../config/suites.json).

```sh
.venv/bin/python scripts/evaluate.py suites
```

## Running a suite

Through the one-command runner, which also checks preconditions and prints a summary:

```sh
.venv/bin/python scripts/benchmark.py --model gpt_oss_20b --suites complex
```

Through the evaluator directly:

```sh
.venv/bin/python scripts/evaluate.py run --model gpt_oss_20b --mode repo --suite complex
```

Several suites at once:

```sh
.venv/bin/python scripts/benchmark.py --model gpt_oss_20b \
  --suites implementation,debugging,documentation
```

## The suites

| Suite | Tasks | What it measures |
|---|---|---|
| `all` | 19 | Everything. Use this for the final comparison. |
| `implementation` | 5 | Writing new behaviour into an existing file against a stated requirement. |
| `complex` | 3 | Implementing a whole module, including its types, from a specification. The hardest single-pass work. |
| `debugging` | 3 | Finding and fixing a defect, sometimes starting from an observed failure. |
| `documentation` | 2 | Explaining existing code accurately in prose, and writing API docstrings from a specification. |
| `tests` | 2 | Writing tests that pin down behaviour, including edge cases. |
| `refactoring` | 2 | Restructuring existing code without changing behaviour. |
| `web` | 2 | JavaScript and TypeScript behaviour, including async control flow. |
| `java` | 1 | Java collections and language semantics. |
| `specification` | 2 | Implementing a detailed written specification, where requirement adherence is the whole task. |
| `difficult` | 6 | The pre-registered difficult subset, frozen before any candidate was scored. |
| `routine` | 5 | The pre-registered routine subset, frozen before any candidate was scored. |
| `quick` | 3 | A fast sanity check that the harness works. Not a quality signal. |

## The task categories

| Category | Tasks | Example |
|---|---|---|
| `python_implementation` | 2 | `config-parse`, `result-summary` |
| `complex_implementation` | 3 | `capts-model`, `capts-risk-score`, `capts-change-event` |
| `python_debugging` | 2 | `cache-leak`, `retry-final` |
| `debugging` | 1 | `capts-cache-key` |
| `documentation` | 2 | `capts-document-module`, `capts-write-docstring` |
| `unit_testing` | 2 | `score-tests`, `capts-test-model` |
| `refactoring` | 2 | `user-validation`, `capts-dedupe-severity` |
| `typescript_web` | 2 | `web-search`, `capts-normalise-deal` |
| `multi_file` | 1 | `api-key` |
| `java` | 1 | `java-names` |
| `implementation_document` | 1 | `task-loader` |

## Where the new tasks came from

The `capts-` tasks are derived from the CAPTS pipeline-analysis project in
`~/Other/Me/Projects/FYP/FourthYearProject`, and `capts-normalise-deal` and
`capts-test-model` are derived from the DealLedger MCP server in
`~/Other/Me/Projects/mysite/deal-ledger-mcp`.

Only the minimum necessary context was copied. Each fixture contains a small
self-contained module and its specification, with no credentials, no configuration, no
generated files, and no large sections of the original repositories. The `source` field
in `tasks/core.json` records the origin of each task.

## Adding a task

1. Create `tasks/fixtures/TASK-ID/` with the source files the model will edit.
2. Put the requirement in `prompt` in `tasks/core.json`, and any longer specification in
   a `SPEC.md` or `REQUIREMENTS.md` file inside the fixture.
3. Add public tests in `tests/` and withheld tests in `hidden/`.
4. Add `validation` and `withheld_validation` commands to the task in `tasks/core.json`.
5. Add the task to any suites it belongs in, in `config/suites.json`.
6. Verify the withheld tests are satisfiable:

```sh
.venv/bin/python docs/cloud_run/verify_hidden.py
```

That script writes a reference implementation over a temporary copy of each fixture and
runs both the public and the withheld validation. Every task must report OK.

## Token budget

The candidate models are configured with `max_tokens: 32768`. This is not generous for
its own sake. Measured on this machine, a thinking model can spend an entire smaller
budget on reasoning alone and emit no answer at all, which the harness records as
`unparseable` with `finish_reason: length` and zero answer characters.

The `complex` suite needs the largest budget because the model must write out a whole
module. Keep `max_tokens` identical across every candidate, because it is part of the
comparison key and the harness refuses to compare runs that differ.
