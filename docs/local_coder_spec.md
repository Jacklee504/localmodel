# Local Coder: remaining implementation specification

This document specifies the work required before downloading the larger candidate models. It does not report observed model results, modify the frozen training experiment, or authorize automatic model downloads or deletions.

## Part A: gap analysis and priority

### A.1 Audit corrections

Most of the audit is accurate. The following points need correction or qualification.

1. **G-19, symlink handling, is less severe than stated.**  
   `fixture_files()` rejects symlinks before `execute_repo()` is reached for normal suite runs, so the current fixtures cannot exploit the `shutil.copytree(..., symlinks=False)` discrepancy. The inconsistency should still be removed, but it is P2 rather than a current evaluation blocker.

2. **G-20 overstates the absence of a diff.**  
   `execute_repo()` already produces a unified `difflib` diff. What is absent is a whole-tree Git diff that includes untracked files and changes outside the response's declared file map. That matters most for agent mode, where the model does not declare which files it changed.

3. **G-21 is not a `Path.write_text()` defect.**  
   `Path.write_text()` writes the supplied string exactly. It does not strip a trailing newline, and it does not reset the mode of an existing file. The observed newline loss and truncated line were already present in the model's JSON content. The appropriate fix is to preserve and review model output exactly, not to silently alter it. A task may explicitly require a final newline, but the harness must not repair model output invisibly.

4. **G-24 is partially false.**  
   The Java fixture already includes `javac`, which is a compile or build validation command. The suite nevertheless lacks a lint, type-check, or package-build check beyond compilation. The extension should be described accurately as adding a dedicated lint or type-check task, not as adding the first non-test command.

5. **G-27 overstates the opacity of `score-tests`.**  
   The model is shown `scoring.py`, including its exact validation logic. The task is not semantically opaque. It may be relatively easy, but the claim that it "inflates" the old 4/10 result is unsupported. Keep the task, retain it as a separate category, and do not use it as the only evidence of test-writing ability.

6. **`num_ctx` cannot be a normal per-request OpenAI-compatible parameter.**  
   The configuration must support a per-model `num_ctx` value because that is the intended server context setting, but the harness must not pretend to send it in the OpenAI chat-completions body. It is configured through Ollama and recorded in run metadata. A context setting that is only declared in JSON, but not observed in `ollama ps`, is not evidence that the intended context was used.

7. **A context comparison needs a deliberate policy.**  
   The harness should distinguish the configured context requirement, the observed Ollama context, and the cloud case where local context is not applicable. A run whose observed local context differs from the required context is operationally non-compliant and must be marked accordingly.

### A.2 Priority table

| ID | Gap | Severity | Required before large-model download |
|---|---|---:|---:|
| G-01 | Candidate endpoints and served model IDs in `config/models.json` are wrong or placeholders. | P0 | Yes |
| G-02 | The available `minimax-m3.1-flash:cloud` model has no harness entry. | P1 | Yes |
| G-03 | The already installed `qwen3.5:9b` baseline cannot be reached by the harness. | P0 | Yes |
| G-04 | Model configuration lacks generation controls, context, operational commands, and notes. | P0 | Yes |
| G-05 | `parse_changes()` fails on reasoning preambles, prose wrappers, and common fences. | P0 | Yes |
| G-06 | Truncation is not distinguished from a JSON or protocol failure. | P0 | Yes |
| G-07 | Disallowed-path failures lack a stable machine-readable classification. | P1 | Yes |
| G-08 | `Model.generate()` cannot express the relevant generation and reasoning controls. | P0 | Yes |
| G-09 | The comparison key is accidental and will silently become incompatible when generation metadata grows. | P0 | Yes |
| G-10 | The hard-coded 600-second request timeout is too short for large reasoning-model runs. | P0 | Yes |
| G-11 | Endpoint runs always report null first-token and peak-memory telemetry. | P1 | Yes |
| G-12 | Assistant extraction assumes `choices[0].message.content` is always a string. | P0 | Yes |
| G-13 | Per-task scoring is too cumbersome and risks accidental data loss. | P1 | Yes |
| G-14 | Manual scoring lacks a complete rubric and validated failure vocabulary. | P1 | Yes |
| G-15 | The number of additional prompts required cannot be measured. | P1 | Yes |
| G-16 | The comparison report lacks categories, failure modes, untouched files, and decision mapping. | P0 | Yes |
| G-17 | The report does not show which allowlisted files were changed or left untouched. | P1 | Yes |
| G-18 | Repository mode does not measure the agent-driven workflow used in daily development. | P0 | Yes |
| G-19 | `fixture_files()` rejects symlinks while `execute_repo()` dereferences them. | P2 | No, but fix with hidden-test work |
| G-20 | The current diff is not a whole-tree Git diff and omits untracked files. | P2 | No for JSON mode, yes as part of agent mode |
| G-21 | Claimed newline and permission loss in `Path.write_text()` is not caused by that function. | P2 | No |
| G-22 | All visible tests are included in prompts, and there are no withheld tests. | P0 | Yes |
| G-23 | No task rewards a minimal, surgical edit over a larger rewrite. | P1 | Yes |
| G-24 | No dedicated lint or type-check validation task exists, although `javac` already provides compilation. | P1 | Yes |
| G-25 | No debugging task supplies an observed failure or traceback. | P1 | Yes |
| G-26 | The suite lacks fixtures derived from the authorized real repositories. | P1 | Yes |
| G-27 | The `score-tests` task may be easy, but the claimed score inflation is unproven. | P2 | No |
| G-28 | Raw results are ignored and the evidence supporting a final decision would not be committed. | P0 | Yes |
| G-29 | Metadata omits prompt identity, runtime version, endpoint, observed context, and other comparison-critical facts. | P0 | Yes |
| G-30 | The experiment log and selection report are behind the available 7B artifacts. | P1 | Yes |
| G-31 | Local model memory cannot currently be measured from outside the evaluator process. | P1 | Yes |

**Release gate:** every P0 and P1 item must be complete and tested before the first large-model pull. P2 items may follow if they do not weaken the primary comparison.

---

## Part B: target design

## B.1 Model configuration schema

### B.1.1 Schema and validation rules

Use this top-level shape:

```json
{
  "schema_version": 1,
  "models": {
    "MODEL_KEY": {
      "name": "DISPLAY NAME",
      "provider": "openai_compatible",
      "base_url": "http://127.0.0.1:11434/v1",
      "model": "SERVED_MODEL_ID",
      "api_key_env": null,
      "path": null,
      "quantization": null,
      "runtime": "ollama 0.40.0",
      "generation": {
        "common": {
          "max_tokens": 8192,
          "temperature": 0.2,
          "top_p": 0.9
        },
        "model": {
          "reasoning_effort": null,
          "think": null,
          "preserve_thinking": null
        }
      },
      "context": {
        "num_ctx": 64000,
        "model_max": 262144,
        "kv_cache_type": null
      },
      "download_size": "HUMAN READABLE SIZE",
      "ollama": {
        "pull_command": "ollama pull TAG",
        "launch_command": "ollama launch opencode --model TAG",
        "serve_command": "OLLAMA_CONTEXT_LENGTH=64000 ollama serve"
      },
      "opencode": {
        "provider": "ollama-local",
        "model": "SERVED_MODEL_ID"
      },
      "notes": "FREE TEXT"
    }
  }
}
```

Field contract:

| Field | Type | Required and default | Rules |
|---|---|---|---|
| `schema_version` | integer | Required, currently `1` | Reject unsupported versions with an actionable error. |
| `models` | object | Required | Keys must match `[A-Za-z0-9_-]+`. |
| `name` | string | Required | Human-readable display name. |
| `provider` | string | Required | Exactly `mlx` or `openai_compatible`. |
| `base_url` | string | Required for `openai_compatible` | Must be an absolute HTTP or HTTPS URL. |
| `model` | string | Required for `openai_compatible` | Exact ID accepted by the endpoint, normally the Ollama tag. |
| `api_key_env` | string or null | Optional, default null | If set, the referenced environment variable must exist when the model is used. |
| `path` | string or null | Required for `mlx` | Relative paths resolve from the repository root. |
| `quantization` | string or null | Optional, default null | Informational and included in metadata. |
| `runtime` | string or null | Optional, default null | Informational, for example `ollama 0.40.0` or `mlx-lm 0.32.0`. |
| `generation.common.max_tokens` | integer | Optional, default `4096` | Must be positive. Candidate configuration overrides this to `8192`. |
| `generation.common.temperature` | number or null | Optional, default `0.2` | Must be between 0 and 2 inclusive. |
| `generation.common.top_p` | number or null | Optional, default `0.9` | Must be between 0 and 1 inclusive. |
| `generation.model.reasoning_effort` | null, `low`, `medium`, or `high` | Optional, default null | Sent only when non-null. |
| `generation.model.think` | boolean or null | Optional, default null | Sent only when non-null. |
| `generation.model.preserve_thinking` | boolean or null | Optional, default null | Sent only when non-null. |
| `context.num_ctx` | integer or null | Optional, default null | Server-side target. It is never sent in the OpenAI request body. |
| `context.model_max` | integer or null | Optional, default null | Advertised maximum, used for reporting only. |
| `context.kv_cache_type` | string or null | Optional, default null | Expected Ollama KV-cache type, such as `f16` or `q8_0`. Null means server default. |
| `download_size` | string or null | Optional, default null | Human-readable estimate. Do not present rounded values as byte-exact. |
| `ollama.pull_command` | string or null | Optional, default null | Informational only. The harness must never execute it. |
| `ollama.launch_command` | string or null | Optional, default null | Informational only. The harness must never execute it. |
| `ollama.serve_command` | string or null | Optional, default null | Informational only. The harness must never start a server. |
| `opencode.provider` | string | Optional, default `ollama-local` | Used to build the temporary OpenCode provider configuration. |
| `opencode.model` | string or null | Optional, default null | Served model ID. The OpenCode reference is `provider/model`. |
| `notes` | string | Optional, default empty string | Operational caveats, not executable instructions. |

Validation rules:

1. For `provider: "mlx"`, `path` is required and `base_url` and `model` must be absent or null.
2. For `provider: "openai_compatible"`, `base_url` and `model` are required and `path` must be absent or null.
3. Unknown top-level or model fields must produce an error rather than being ignored.
4. The harness may add a model by editing only `config/models.json`.
5. Commands in `ollama` are displayed to the user. They are never run by `evaluate.py`.
6. `context.num_ctx` is a declaration of the required server setting. The observed value comes from `ollama ps`, not from this field.

### B.1.2 Fully populated configuration

The following is the intended initial file. The proposed Ollama tags are used exactly as given in the source material. If the registry exposes a different tag, only this file changes.

```json
{
  "schema_version": 1,
  "models": {
    "qwen25_7b": {
      "name": "Qwen2.5-Coder-7B-Instruct-4bit",
      "provider": "mlx",
      "base_url": null,
      "model": null,
      "api_key_env": null,
      "path": "models/qwen2.5-coder-7b-instruct-4bit",
      "quantization": "4-bit",
      "runtime": "mlx-lm 0.32.0",
      "generation": {
        "common": {
          "max_tokens": 2048,
          "temperature": 0.2,
          "top_p": 0.9
        },
        "model": {
          "reasoning_effort": null,
          "think": null,
          "preserve_thinking": null
        }
      },
      "context": {
        "num_ctx": null,
        "model_max": null,
        "kv_cache_type": null
      },
      "download_size": "Existing local MLX model; exact size not recorded",
      "ollama": {
        "pull_command": null,
        "launch_command": null,
        "serve_command": null
      },
      "opencode": {
        "provider": "ollama-local",
        "model": null
      },
      "notes": "Reference workflow model only. It is not one of the four primary selection candidates."
    },
    "qwen35_9b": {
      "name": "Qwen3.5 9B - Local",
      "provider": "openai_compatible",
      "base_url": "http://127.0.0.1:11434/v1",
      "model": "qwen3.5:9b",
      "api_key_env": null,
      "path": null,
      "quantization": "Q4_K_M",
      "runtime": "ollama 0.40.0",
      "generation": {
        "common": {
          "max_tokens": 8192,
          "temperature": 0.2,
          "top_p": 0.9
        },
        "model": {
          "reasoning_effort": null,
          "think": true,
          "preserve_thinking": false
        }
      },
      "context": {
        "num_ctx": 64000,
        "model_max": 262144,
        "kv_cache_type": null
      },
      "download_size": "6,594,462,816-byte model layer, about 6.1 GiB",
      "ollama": {
        "pull_command": "ollama pull qwen3.5:9b",
        "launch_command": "ollama launch opencode --model qwen3.5:9b",
        "serve_command": "OLLAMA_CONTEXT_LENGTH=64000 ollama serve"
      },
      "opencode": {
        "provider": "ollama-local",
        "model": "qwen3.5:9b"
      },
      "notes": "Already installed. Use as the lightweight local baseline and 64K feasibility control."
    },
    "minimax_m31_flash_cloud": {
      "name": "MiniMax M3.1 Flash - Cloud Reference",
      "provider": "openai_compatible",
      "base_url": "http://127.0.0.1:11434/v1",
      "model": "minimax-m3.1-flash:cloud",
      "api_key_env": null,
      "path": null,
      "quantization": null,
      "runtime": "ollama 0.40.0, cloud model",
      "generation": {
        "common": {
          "max_tokens": 8192,
          "temperature": 0.2,
          "top_p": 0.9
        },
        "model": {
          "reasoning_effort": null,
          "think": true,
          "preserve_thinking": false
        }
      },
      "context": {
        "num_ctx": 64000,
        "model_max": null,
        "kv_cache_type": null
      },
      "download_size": "Cloud model; no local weight download",
      "ollama": {
        "pull_command": "ollama pull minimax-m3.1-flash:cloud",
        "launch_command": "ollama launch opencode --model minimax-m3.1-flash:cloud",
        "serve_command": "ollama serve"
      },
      "opencode": {
        "provider": "ollama-local",
        "model": "minimax-m3.1-flash:cloud"
      },
      "notes": "Temporary cloud ceiling reference. Do not include it in the local-model ranking."
    },
    "qwen38_27b": {
      "name": "Qwen3.8 27B - Local",
      "provider": "openai_compatible",
      "base_url": "http://127.0.0.1:11434/v1",
      "model": "qwen3.8:27b",
      "api_key_env": null,
      "path": null,
      "quantization": null,
      "runtime": "ollama 0.40.0",
      "generation": {
        "common": {
          "max_tokens": 8192,
          "temperature": 0.2,
          "top_p": 0.9
        },
        "model": {
          "reasoning_effort": "medium",
          "think": true,
          "preserve_thinking": false
        }
      },
      "context": {
        "num_ctx": 64000,
        "model_max": 262144,
        "kv_cache_type": null
      },
      "download_size": "18 GB, approximate Ollama library download size",
      "ollama": {
        "pull_command": "ollama pull qwen3.8:27b",
        "launch_command": "ollama launch opencode --model qwen3.8:27b",
        "serve_command": "OLLAMA_CONTEXT_LENGTH=64000 ollama serve"
      },
      "opencode": {
        "provider": "ollama-local",
        "model": "qwen3.8:27b"
      },
      "notes": "Dense primary candidate. It must demonstrate an observed 64000-token Ollama context and acceptable memory pressure before it qualifies for daily OpenCode use."
    },
    "qwen3_coder_30b": {
      "name": "Qwen3-Coder 30B A3B - Local",
      "provider": "openai_compatible",
      "base_url": "http://127.0.0.1:11434/v1",
      "model": "qwen3-coder:30b",
      "api_key_env": null,
      "path": null,
      "quantization": null,
      "runtime": "ollama 0.40.0",
      "generation": {
        "common": {
          "max_tokens": 8192,
          "temperature": 0.2,
          "top_p": 0.9
        },
        "model": {
          "reasoning_effort": null,
          "think": null,
          "preserve_thinking": null
        }
      },
      "context": {
        "num_ctx": 64000,
        "model_max": 262144,
        "kv_cache_type": null
      },
      "download_size": "19 GB, approximate Ollama library download size",
      "ollama": {
        "pull_command": "ollama pull qwen3-coder:30b",
        "launch_command": "ollama launch opencode --model qwen3-coder:30b",
        "serve_command": "OLLAMA_CONTEXT_LENGTH=64000 ollama serve"
      },
      "opencode": {
        "provider": "ollama-local",
        "model": "qwen3-coder:30b"
      },
      "notes": "MoE secondary candidate. Use model-default reasoning controls unless a documented card-supported setting is verified."
    },
    "gpt_oss_20b": {
      "name": "GPT-OSS 20B - Local",
      "provider": "openai_compatible",
      "base_url": "http://127.0.0.1:11434/v1",
      "model": "gpt-oss:20b",
      "api_key_env": null,
      "path": null,
      "quantization": "MXFP4",
      "runtime": "ollama 0.40.0",
      "generation": {
        "common": {
          "max_tokens": 8192,
          "temperature": 0.2,
          "top_p": 0.9
        },
        "model": {
          "reasoning_effort": "medium",
          "think": null,
          "preserve_thinking": null
        }
      },
      "context": {
        "num_ctx": 64000,
        "model_max": 131072,
        "kv_cache_type": null
      },
      "download_size": "14 GB, approximate Ollama library download size",
      "ollama": {
        "pull_command": "ollama pull gpt-oss:20b",
        "launch_command": "ollama launch opencode --model gpt-oss:20b",
        "serve_command": "OLLAMA_CONTEXT_LENGTH=64000 ollama serve"
      },
      "opencode": {
        "provider": "ollama-local",
        "model": "gpt-oss:20b"
      },
      "notes": "Control candidate for model-versus-runtime effects and as a 24 GB-friendly comparison point."
    }
  }
}
```

The free-text notes may be corrected after the first manifest inspection. They must not be used to hide a failed operational requirement.

---

## B.2 Request and response handling

### B.2.1 Endpoint request

`Model.generate()` must send a non-streaming request to:

```text
{base_url without trailing slash}/chat/completions
```

For example:

```text
http://127.0.0.1:11434/v1/chat/completions
```

Headers:

```text
Content-Type: application/json
Accept: text/event-stream
```

Optional bearer token only when `api_key_env` is set:

```text
Authorization: Bearer {value of environment variable}
```

Request body for an OpenAI-compatible model:

```json
{
  "model": "qwen3.8:27b",
  "messages": [
    {
      "role": "user",
      "content": "PROMPT"
    }
  ],
  "max_tokens": 8192,
  "stream": true,
  "stream_options": {
    "include_usage": true
  },
  "temperature": 0.2,
  "top_p": 0.9,
  "reasoning_effort": "medium",
  "think": true,
  "preserve_thinking": false
}
```

Rules:

1. Omit every optional field whose configured value is null.
2. Never include `context.num_ctx` in this body. The OpenAI-compatible endpoint has no supported per-request context-size control in the stated environment.
3. `max_tokens` is resolved in this order:
   1. explicit `--max-tokens`;
   2. `generation.common.max_tokens`;
   3. the schema default of 4096.
4. The effective values are stored in metadata and the comparison key.
5. The default total request deadline is 3600 seconds. `--timeout-seconds` may override it.
6. `urllib.request.urlopen(timeout=...)` alone is not a total deadline because it is primarily an inactivity timeout. Enforce the total deadline with a monotonic-clock check around reads and, on macOS or Linux, `signal.setitimer()` around the request. If signal-based deadlines are unavailable, use the socket timeout as a fallback and record `timeout_mode: "socket_inactivity"`.
7. Do not retry a generation request automatically. A retry can duplicate work and invalidate timing.
8. If the endpoint returns HTTP 400 because it rejects `stream_options` or a model-specific field, record `http_error`. The user then removes or changes that field in configuration. Do not silently retry without streaming or silently change model behavior.

For the MLX path:

1. Preserve the current `mlx_lm.load()` and chat-template behavior.
2. Apply the effective `max_tokens`.
3. Do not claim that temperature or top-p were applied unless the pinned `mlx-lm==0.32.0` API accepts and applies them.
4. Record unsupported common generation settings in metadata under `generation.applied`.
5. The MLX path remains a reference workflow and is not mixed with endpoint candidate rankings.

### B.2.2 Streaming accumulation

The endpoint path should use SSE so first-token timing and final usage can be measured.

1. Read the response line by line.
2. Accumulate SSE events separated by blank lines.
3. For each `data:` line:
   - stop at `[DONE]`;
   - parse the remaining text as JSON;
   - ignore malformed event lines only if a later event contains a complete assistant answer, and record a warning in the task record;
   - abort the request as `unparseable` if no complete answer can be assembled.
4. For each choice delta:
   - extract content and reasoning using the rules below;
   - append content exactly, without adding separators;
   - append reasoning exactly;
   - record the first non-empty content or reasoning delta as the first generated output;
   - retain the last non-null `finish_reason`;
   - retain the last non-null usage object.
5. If the server returns a normal non-streaming JSON object despite `stream: true`, accept it and set first-token timing to null.
6. Usage is provider-reported. If it is absent, token counts remain null. Do not estimate tokens from words or characters.

### B.2.3 Assistant-message extraction

For each response or streamed delta, use this ordered algorithm.

1. Accept a direct string in `content`.
2. If `content` is a list:
   - include every part whose `text` is a string;
   - include parts with type `text`, `output_text`, or `input_text`;
   - ignore non-text parts;
   - concatenate without adding separators.
3. If no usable `content` exists, try these alternate fields in order:
   1. `output_text`
   2. `answer`
   3. `response`
4. For native-style objects, also inspect `message.content` using the same rules.
5. Reasoning is read from, in order:
   1. `reasoning_content`
   2. `reasoning`
   3. `thinking`
   4. list parts with type `thinking` or `reasoning`, or a string `thinking` field
6. Keep raw content, cleaned answer content, and reasoning separately.
7. If the answer is empty and only reasoning is present, the task fails with `protocol_violation`. A reasoning trace is not a substitute for the requested answer.

### B.2.4 Reasoning removal

The cleaned answer is produced as follows:

1. If the server placed reasoning in a separate field, exclude it automatically.
2. Remove complete `<think>...</think>` and `<thinking>...</thinking>` blocks, case-insensitively.
3. Remove a leading `<think>` or `<thinking>` block even if the closing tag is missing. Preserve the unterminated raw content for truncation analysis.
4. Do not remove arbitrary prose that happens to contain the word "thinking".
5. Preserve all non-reasoning text for JSON extraction.

### B.2.5 JSON extraction algorithm

The repository protocol remains:

```json
{
  "files": {
    "relative/path.py": "complete new file contents"
  }
}
```

The parser must follow this ordered procedure:

1. Normalize line endings to `\n` for parsing, while preserving the original raw response.
2. Strip a UTF-8 BOM and surrounding whitespace.
3. Try to parse the entire cleaned answer as JSON.
4. If that fails, remove a single outer code fence, including an optional language tag such as `json` or `JSON`.
5. Try the whole result again.
6. Remove complete reasoning blocks and try the whole result again.
7. Scan for balanced top-level `{...}` spans:
   - braces inside JSON strings must be ignored;
   - escape sequences must be respected;
   - emit only outermost spans;
   - attempt `json.loads()` on each span in source order.
8. Select the first parseable JSON object that has a top-level `files` key.
9. If no such object exists, select the first parseable JSON object and classify its schema failure.
10. Do not repair trailing commas, single-quoted keys, Python literals, comments, or truncated strings. Those are not safely recoverable.
11. Additional top-level JSON keys are allowed and ignored.
12. `files` must be a non-empty object.
13. Every value in `files` must be a string.
14. Every path in `files` must be an exact member of `editable`.
15. File contents are written exactly as supplied. The harness must not add or remove a trailing newline.

#### Worked recoverable examples

Example A, reasoning plus fenced JSON:

```text
<think>
I need to update the parser and preserve the mapping.
</think>
Here is the requested change:

```json
{
  "files": {
    "config_reader.py": "def load_models(path):\n    ...\n"
  }
}
```
```

Expected result: one `files` map, with the reasoning and prose excluded.

Example B, prose before and after JSON:

```text
I will make the minimal change.

{"files":{"retry.py":"def call_with_retry(...):\n    ...\n"}}

This keeps the public signature unchanged.
```

Expected result: the balanced JSON object is selected.

Example C, a language-tagged fence:

````text
```JSON
{"files":{"search.js":"function createSearch(fetcher) {\n  ...\n}\n"}}
```
````

Expected result: the outer fence is removed and the JSON is parsed.

Example D, a nested brace in prose:

```text
The function should return {"ok": true}.
Final patch:
{"files":{"api.py":"..."}}
```

Expected result: the final top-level object with `files` is selected, not the unrelated nested object.

### B.2.6 Truncation detection

Truncation is distinct from malformed JSON.

Set `failure.kind = "truncated"` when any of the following is true:

1. The endpoint reports `finish_reason` equal to `length` or `max_tokens`.
2. The native-style response reports `done_reason` equal to `length`.
3. The response is invalid JSON, usage reports `completion_tokens >= max_tokens`, and the response appears incomplete.
4. The response ends inside an unterminated JSON string, object, or array and the extractor's last error position is at the end of the content.
5. In response mode, the endpoint reports a length stop, even if the partial prose looks complete.

Rules:

1. A valid JSON object with a valid `files` map wins over a length finish reason. The model may have completed the answer exactly at the boundary.
2. A valid JSON object with an invalid `files` schema is `protocol_violation`, not `truncated`.
3. If neither the endpoint nor usage provides truncation evidence, malformed JSON is `unparseable`.
4. Never infer truncation solely from the presence of a closing quote or brace.
5. Store the evidence in `failure.detail`, for example:
   - `finish_reason=length`
   - `completion_tokens=8192 equals max_tokens=8192`
   - `unterminated JSON string at byte offset 4312`

A truncated task record has this shape:

```json
{
  "response_raw": "PARTIAL RESPONSE",
  "response": null,
  "reasoning": "PRESERVED REASONING, IF SEPARATE",
  "failure": {
    "kind": "truncated",
    "stage": "response_parse",
    "detail": "finish_reason=length; completion_tokens=8192"
  }
}
```

---

## B.3 Structured failure taxonomy

The exact closed set is:

```text
http_error
timeout
truncated
unparseable
protocol_violation
disallowed_path
validation_failed
none
```

| Kind | Set when | Examples |
|---|---|---|
| `http_error` | The endpoint request fails before a usable answer exists. | Connection refused, DNS or TLS error, HTTP 4xx or 5xx, malformed response envelope. |
| `timeout` | The total request deadline is exceeded. | Dense model still generating at 3600 seconds. |
| `truncated` | The output is known or strongly evidenced to be incomplete. | `finish_reason=length`, unterminated JSON at the token limit. |
| `unparseable` | Repository mode cannot recover a JSON object from the answer. | Plain prose with no JSON object, invalid JSON with no truncation evidence. |
| `protocol_violation` | An answer exists but violates the required response contract. | Missing `files`, empty `files`, non-string file body, empty assistant content, no effective changes. |
| `disallowed_path` | The `files` map names a path outside the task's `editable` list. | A response changes `tests/test_config_reader.py` when only `config_reader.py` is editable. |
| `validation_failed` | Valid changes were applied, but at least one validation command failed. | A syntactically valid patch fails a unit test. |
| `none` | The task completed without a harness-level failure. | Response received and, in repo mode, validation passed. |

Setting rules:

1. Set the failure at the point of failure in `run()`, not later from a secondary parser.
2. `http_error` and `timeout` are operational failures, not automatically quality score 0.
3. `unparseable`, `protocol_violation`, `disallowed_path`, and `validation_failed` can receive a manual quality score of 0 or 1.
4. Unexpected harness exceptions must not be mislabeled as one of these categories. They should abort with a traceback and a non-zero exit status. Known endpoint, parsing, application, and validation exceptions must be caught and classified.
5. `none` means no harness-level failure. It does not imply a manual score of 2.
6. In response mode, `validation_failed` and `disallowed_path` cannot occur because no patch is applied.

The report must aggregate:

- count and percentage of attempts by failure kind;
- count by failure kind and model;
- count by failure kind and task;
- transport-valid completion rate, defined as attempts whose kind is not `http_error` or `timeout`;
- protocol success rate, defined as attempts with no parsing or protocol failure;
- objective validation rate, shown only for repo and agent modes.

---

## B.4 Timing and memory telemetry

### B.4.1 Timing fields

Measure the following:

| Field | Definition |
|---|---|
| `request_seconds` | Monotonic time from immediately before opening the HTTP request until the complete response is parsed. |
| `first_token_seconds` | Monotonic time from request start to the first non-empty content or reasoning delta. Null for a non-streaming response. |
| `generation_window_seconds` | `response_end - first_token_time` when first-token timing exists, otherwise `request_seconds`. |
| `tokens_generated` | Provider-reported completion tokens, including reasoning tokens if the provider counts them as completion tokens. Null if usage is absent. |
| `prompt_tokens` | Provider-reported input or prompt tokens. Null if usage is absent. |
| `tokens_per_second` | `tokens_generated / generation_window_seconds`. This is steady-state completion throughput and excludes time to first token when TTFT is known. Null if either input is unavailable. |
| `end_to_end_tokens_per_second` | `tokens_generated / request_seconds`. Null if either input is unavailable. |
| `task_wall_seconds` | Time for the complete task operation, including generation, patch application, and validation in repo or agent mode. |
| `first_output_seconds` | Agent mode only. Time from process start to the first non-empty OpenCode JSON event or tool event. It is not claimed to be exact token TTFT. |

Do not use prompt tokens in `tokens_per_second`.

For the MLX path:

1. `tokens_generated` remains the tokenizer count of the generated answer.
2. `prompt_tokens` is the tokenizer count of the rendered chat prompt.
3. `first_token_seconds` remains null unless the existing MLX API exposes a usable callback.
4. `tokens_per_second` uses `generation_window_seconds`, which falls back to `request_seconds`.

### B.4.2 Ollama memory telemetry

Three measurements are needed. They are related but not interchangeable.

1. **`ollama ps` model allocation**
   - Capture after the first request and before `ollama stop`.
   - Record the full text, or parsed fields for name, size, processor, context, and runner.
   - `SIZE` is Ollama's reported model allocation. It is not a process peak-memory measurement.

2. **Sampled runner RSS**
   - While the request is running, sample once per second:
     ```sh
     ps -axo pid=,ppid=,rss=,command= | grep '[o]llama runner'
     ```
   - Sum RSS bytes across matching runner processes.
   - Stop sampling when the request completes.
   - Label the result `sampled_runner_rss_peak_bytes`.
   - Shared pages may be counted more than once, so this is an approximate upper bound, not exact GPU allocation.
   - If another local model is loaded concurrently, the measurement is invalid. The protocol requires only one candidate model at a time.

3. **Manual system observations**
   - Capture at idle, after model load, during the longest generation, after completion, and after `ollama stop`.
   - Required commands:
     ```sh
     sysctl -n hw.memsize
     df -h /Users/jacklee/Other/Me/Projects/local-coder
     sysctl vm.swapusage
     memory_pressure -Q
     ollama ps
     ```
   - If `memory_pressure -Q` is unavailable on the installed macOS build, run `memory_pressure` manually and stop it after the reading.
   - From Activity Monitor, record Memory Pressure, physical memory used, swap used, and the `ollama runner` process's memory value at each checkpoint.

Store these values in the run metadata and export the values, not screenshots, into the committed run summary.

### B.4.3 Cloud model memory

For a cloud model:

- `peak_memory_bytes` is null;
- `sampled_runner_rss_peak_bytes` is null;
- `memory_source` is `not_applicable_remote_service`;
- local system memory samples may still be recorded, but they must not be attributed to the remote model;
- the report must not rank the cloud model on local memory use.

### B.4.4 MLX memory

For the MLX path:

- use `resource.getrusage(resource.RUSAGE_SELF).ru_maxrss` as a process high-water approximation;
- convert bytes correctly on macOS;
- label it `process_peak_rss_bytes`, not model-only memory;
- note that the evaluator process includes Python and harness overhead.

---

## B.5 Result record schema

### B.5.1 Versioning

Use result schema version 2. Existing six run directories remain untouched and are read as legacy results. New code must never rewrite them.

### B.5.2 Run metadata

Each attempt has `metadata.json` with this shape:

```json
{
  "schema_version": 2,
  "run_id": "20261020T120000000000Z",
  "batch_id": "20261020T120000000000Z",
  "attempt_index": 1,
  "created_utc": "2026-10-20T12:00:00.000000+00:00",
  "git_commit": "bdbd2e07cd34a239da820e77610f2fd3069b7351",
  "git_dirty": false,
  "model_key": "qwen35_9b",
  "model_config": {
    "name": "Qwen3.5 9B - Local",
    "provider": "openai_compatible",
    "base_url": "http://127.0.0.1:11434/v1",
    "model": "qwen3.5:9b",
    "api_key_env": null,
    "path": null,
    "quantization": "Q4_K_M",
    "runtime": "ollama 0.40.0",
    "generation": {
      "common": {
        "max_tokens": 8192,
        "temperature": 0.2,
        "top_p": 0.9
      },
      "model": {
        "reasoning_effort": null,
        "think": true,
        "preserve_thinking": false
      }
    },
    "context": {
      "num_ctx": 64000,
      "model_max": 262144,
      "kv_cache_type": null
    }
  },
  "mode": "repo",
  "suite": {
    "path": "tasks/core.json",
    "sha256": "8dbe038dd7c32fe5bc3ea8b89c1c12bd8624cb79ce4027033b71384dce031637",
    "task_ids": [
      "config-parse",
      "result-summary",
      "cache-leak",
      "retry-final",
      "score-tests",
      "web-search",
      "java-names",
      "api-key",
      "user-validation",
      "task-loader"
    ]
  },
  "comparison_key": {
    "protocol_version": 2,
    "mode": "repo",
    "suite_sha256": "8dbe038dd7c32fe5bc3ea8b89c1c12bd8624cb79ce4027033b71384dce031637",
    "task_ids": [
      "config-parse",
      "result-summary",
      "cache-leak",
      "retry-final",
      "score-tests",
      "web-search",
      "java-names",
      "api-key",
      "user-validation",
      "task-loader"
    ],
    "prompt_version": "repo-json-v2",
    "generation": {
      "max_tokens": 8192,
      "temperature": 0.2,
      "top_p": 0.9
    },
    "context_requirement": 64000,
    "repair_attempts": 0
  },
  "runtime": {
    "endpoint": "http://127.0.0.1:11434/v1/chat/completions",
    "served_model": "qwen3.5:9b",
    "runtime_version": "ollama 0.40.0",
    "requested_context_tokens": 64000,
    "observed_context_tokens": 64000,
    "context_source": "ollama ps",
    "kv_cache_type": "server_default",
    "ollama_ps_samples": [],
    "sampled_runner_rss_peak_bytes": null,
    "memory_source": "not_sampled"
  },
  "environment": {
    "machine": "MacBook Air, Apple M2, 24 GB unified memory",
    "memory_total_bytes": null,
    "disk_free_bytes": null,
    "swap_samples": [],
    "memory_pressure_samples": [],
    "activity_monitor_samples": []
  }
}
```

The example is illustrative, not an observed run. Its suite hash will change when the extended suite is committed.

### B.5.3 Deliberate comparison key

The strict comparison key contains only:

1. `protocol_version`;
2. `mode`;
3. `suite_sha256`;
4. exact task IDs and order;
5. `prompt_version`;
6. common generation settings: `max_tokens`, `temperature`, and `top_p`;
7. `context_requirement`;
8. repair policy;
9. for agent mode, a hash of the agent protocol and permission configuration.

Model-specific invocation settings such as `reasoning_effort`, `think`, and `preserve_thinking` are not in the strict key because they describe each candidate's intended behavior. They must be shown in the report so readers know that models were not all invoked identically.

Context is handled as follows:

1. The key stores the required context, normally 64000.
2. A local run whose observed context is not 64000 is marked operationally non-compliant.
3. A cloud run may have a null observed context, but is still identified as remote and is excluded from the local ranking.
4. A candidate evaluated at 32768 cannot be silently presented as a 64000-context result.

Comparison behavior:

- Equal protocol version and equal key: comparable.
- Equal protocol version and unequal key: fail with a field-level difference, for example:
  ```text
  Evaluation error: runs are not comparable:
    generation.max_tokens: 4096 != 8192
    prompt_version: repo-json-v1 != repo-json-v2
  ```
- Different protocol versions: fail with:
  ```text
  Evaluation error: comparison protocol 1 is not compatible with protocol 2.
  Rerun the candidates under one protocol or implement an explicit migration.
  ```
- Legacy run without a comparison key: do not silently include it. Offer a separate legacy summary only.

When a new common generation parameter is introduced:

1. Add it to the explicit comparison-key allowlist.
2. Increment `protocol_version`.
3. Add a test proving old and new runs fail with an actionable error.
4. Do not rely on a generic dictionary equality check that may silently accept or reject the wrong thing.

### B.5.4 Per-task record

Each task record has this shape:

```json
{
  "schema_version": 2,
  "id": "cache-leak",
  "attempt_index": 1,
  "category": "python_debugging",
  "mode": "repo",
  "prompt": "FULL PROMPT",
  "prompt_sha256": "HASH OF EXACT PROMPT",
  "response_raw": "RAW ASSISTANT CONTENT",
  "response": "CLEANED ASSISTANT CONTENT",
  "reasoning": "SEPARATE REASONING CONTENT OR NULL",
  "timings": {
    "request_seconds": 4.25,
    "first_token_seconds": 0.31,
    "generation_window_seconds": 3.94,
    "tokens_generated": 512,
    "prompt_tokens": 684,
    "tokens_per_second": 129.95,
    "end_to_end_tokens_per_second": 120.47,
    "task_wall_seconds": 4.31,
    "peak_memory_bytes": null,
    "sampled_runner_rss_peak_bytes": null,
    "memory_source": "not_sampled"
  },
  "repo": {
    "changes": {
      "report_cache.py": "COMPLETE NEW FILE"
    },
    "diff": "UNIFIED DIFF",
    "diff_stats": {
      "files_changed": 1,
      "insertions": 2,
      "deletions": 1
    },
    "allowed_files_touched": [
      "report_cache.py"
    ],
    "allowed_files_untouched": [],
    "unexpected_paths": [],
    "validation": [
      {
        "command": [
          "python3",
          "-m",
          "unittest",
          "discover",
          "-s",
          "tests",
          "-v"
        ],
        "exit_code": 0,
        "output": "OK"
      }
    ],
    "validation_passed": true
  },
  "agent": null,
  "failure": {
    "kind": "none",
    "stage": null,
    "detail": null
  },
  "error": null,
  "repair": {
    "status": "not_requested",
    "attempt_count": 0,
    "attempts": []
  },
  "manual": {
    "score": 2,
    "initial_score": null,
    "notes": "Includes user identity in the cache key and preserves equivalent-filter reuse.",
    "requirement_failures": [],
    "additional_prompts": null,
    "reviewer": null
  }
}
```

Rules:

1. `response` is the cleaned answer.
2. `response_raw` preserves the exact content returned by the endpoint.
3. `failure.kind` is always present and always one of the closed set.
4. `manual.score` is null when not reviewed.
5. `manual.additional_prompts` is null when unknown. It must not default to 0.
6. `repo` is null in response mode.
7. `agent` is null outside agent mode.
8. `manual.initial_score` is used when a repair attempt is scored separately from the final repaired result.
9. The prompt hash is over the exact UTF-8 prompt sent to the model.

---

## B.6 Scoring

### B.6.1 Review procedure

For each attempt:

1. Read the task prompt.
2. Read the raw answer and reasoning.
3. Read the applied diff.
4. Read every validation command, exit code, and output.
5. Check every explicit requirement independently of test results.
6. Check for unrelated changes, invented APIs, added dependencies, and excessive complexity.
7. Record the requirement-failure categories.
8. Assign the final score.
9. If a repair loop ran, separately record the initial score when reviewed.
10. Record the number of additional prompts if known.

### B.6.2 Score definition

| Score | Definition |
|---:|---|
| 2 | The implementation or answer satisfies every explicit requirement and constraint, all applicable validation commands pass, no requirement-failure category applies, and no unnecessary or unrelated change was made. |
| 1 | The result is useful and demonstrates some correct behavior, but it is incomplete, misses at least one explicit requirement, fails applicable validation, contains avoidable complexity, or has another reviewable defect. The notes must identify the defect. |
| 0 | The result provides no usable implementation or answer, violates a core behavior, is destructive, relies on an invented public API, or otherwise fails the task without a meaningful partial result. |
| null | Not yet reviewed. It must not be treated as 0. |

For response mode:

1. There is no objective validation.
2. Score 2 still requires complete adherence to the prompt.
3. The report must state that a response-mode score is a proposal-quality judgment, not a code-validation result.

For repo and agent mode:

1. Passing visible tests is not sufficient for score 2.
2. A visible test that contradicts the explicit requirement does not override the requirement.
3. The review must specifically check the withheld-test outcome and the diff.

### B.6.3 Closed requirement-failure vocabulary

Use exactly these categories:

```text
ignored_requirement
unnecessary_dependency
public_api_changed
unrelated_refactor
invented_file_or_api
excessive_complexity
incomplete_implementation
```

Each occurrence is stored as:

```json
{
  "category": "ignored_requirement",
  "detail": "Does not raise ValueError for an invalid score.",
  "file": "summary.py",
  "line": null
}
```

`file` may be null. `line` may be null. `detail` is required.

### B.6.4 Corrections and first-pass success

- `manual.additional_prompts` is the number of prompts after the initial attempt.
- It is null if the reviewer does not know.
- It is not automatically 0.
- A first-pass success is:
  - manual score 2;
  - no repair attempt; and
  - `additional_prompts` equal to 0 when known.
- If `additional_prompts` is null, report the result as "score 2, correction count unknown", not as first-pass success.
- With a measured repair loop, use `repair.attempt_count` as the authoritative additional-prompt count.

### B.6.5 Bulk scoring sheet

Add a `score-sheet` command. Use a JSON sheet with this exact shape:

```json
{
  "schema_version": 1,
  "run": "results/qwen35_9b/RUN_ID",
  "items": [
    {
      "task": "cache-leak",
      "score": 2,
      "notes": "Correctly includes user identity and canonicalizes filter order.",
      "requirement_failures": [],
      "additional_prompts": 0,
      "reviewer": "local-user"
    },
    {
      "task": "result-summary",
      "score": 1,
      "notes": "Handles None correctly but does not reject an invalid score.",
      "requirement_failures": [
        {
          "category": "ignored_requirement",
          "detail": "Invalid scores are filtered rather than rejected.",
          "file": "summary.py",
          "line": null
        }
      ],
      "additional_prompts": 0
    }
  ]
}
```

Rules:

1. Validate the whole sheet before writing anything.
2. A task omitted from the sheet remains unreviewed with score null.
3. Do not overwrite an existing non-null score unless `--replace` is supplied.
4. When `--replace` is supplied, show a warning and list the tasks that will change.
5. Merge only the supplied manual fields. Do not rewrite the entire `manual` object.
6. Use a temporary file and `Path.replace()` for each changed record so an interrupted write does not corrupt a record.
7. Reject unknown failure categories.
8. Reject scores outside 0, 1, and 2.
9. Reject negative `additional_prompts`.
10. `--dry-run` validates and prints planned changes without writing.

Keep the existing single-task `score` command for small corrections, but change its correction default to null rather than 0.

### B.6.6 Reviewer calibration during the cloud window

1. Select one cloud-model run.
2. Score all tasks once.
3. Export the first score sheet.
4. Reset the review to the raw run without consulting the first sheet.
5. Score the same run again.
6. Compare task-level scores and failure categories.
7. Target at least 90 percent exact score agreement.
8. For every disagreement, decide whether the rubric was ambiguous, the task was ambiguous, or the reviewer was inconsistent.
9. Amend `docs/evaluation_method.md` and the task prompts before local candidate runs begin.
10. Do not resolve disagreement by majority vote between two scores from the same reviewer. Record the reasoned final score.

---

## B.7 Optional automatic correction loop

### B.7.1 Decision

Add a minimal repair loop for JSON repository mode only.

- It is off by default.
- It is not a general autonomous coding platform.
- It does not run in response mode.
- It does not run in agent mode in this implementation.
- It permits at most two repair attempts.

### B.7.2 CLI

```sh
.venv/bin/python scripts/evaluate.py run \
  --model qwen38_27b \
  --mode repo \
  --repair-attempts 1
```

`--repair-attempts` accepts 0, 1, or 2. The default is 0.

### B.7.3 Repair flow

For each initial failure that can be repaired:

1. Preserve the initial response and failure.
2. Construct a repair prompt containing:
   - the original task title and prompt;
   - the original public file contents;
   - the exact initial response;
   - the parse or protocol error;
   - the current diff, if changes were successfully applied;
   - the validation commands, exit codes, and output;
   - the exact JSON response contract.
3. Do not include withheld test source code.
4. Include withheld validation output if available. The output may guide repair, but the source remains hidden.
5. Limit each validation output to the existing 16000-character cap.
6. Request only a complete `files` map.
7. Parse and apply the repair in a fresh copy of the original fixture, not on top of the previous failed patch. This ensures each attempt is independently evaluated.
8. Run all public and withheld validation commands.
9. Stop after the first attempt that passes validation, or after the configured attempt limit.
10. Keep every attempt, including failures.

A repair prompt should use this structure:

```text
The previous attempt did not satisfy the task.

Task:
{TASK}

Previous response:
{RESPONSE}

Previous failure:
{FAILURE}

Current diff:
{DIFF}

Validation output:
{OUTPUT}

Return only a JSON object with a "files" object mapping each changed path to
its complete new UTF-8 contents. Change only these paths: {EDITABLE}.
```

### B.7.4 Recorded data

```json
{
  "status": "completed",
  "attempt_count": 1,
  "attempts": [
    {
      "attempt_index": 1,
      "prompt": "REPAIR PROMPT",
      "response_raw": "REPAIR RESPONSE",
      "response": "CLEANED RESPONSE",
      "failure": {
        "kind": "none",
        "stage": null,
        "detail": null
      },
      "repo": {},
      "timings": {},
      "task_wall_seconds": 5.2
    }
  ]
}
```

`status` is one of:

```text
not_requested
completed
exhausted
error
```

The final task record contains the final attempt's repository result. The `repair.attempts` array retains the full history.

### B.7.5 Metrics and cost

Report:

- initial objective validation rate;
- final objective validation rate after repair;
- initial manual score;
- final manual score;
- repair success count;
- additional prompts per task;
- additional completion tokens;
- additional wall time.

A single repair attempt can add up to the configured `max_tokens`, here 8192 completion tokens, plus the repair prompt. Two attempts can add up to 16384 completion tokens. Set the per-attempt request timeout to 3600 seconds.

The primary first-pass comparison must use `--repair-attempts 0`. A repair-enabled report is a separate, explicitly labeled analysis.

---

## B.8 Agent-driven repository mode

### B.8.1 Purpose and separability

Add a third mode:

```text
agent
```

The modes remain distinct:

- `response`: proposal only, no validation;
- `repo`: model returns a complete-file JSON patch, harness applies and validates it;
- `agent`: OpenCode edits a temporary repository, harness captures the resulting tree and validates it.

Never pool response, repo, and agent records in one quality metric.

### B.8.2 Workspace construction

For each task:

1. Create a unique root below `/private/tmp`:
   ```text
   /private/tmp/local-coder-agent-<uuid>/
   ```
2. Create:
   ```text
   workspace/
   opencode-config/
   ```
3. Copy only public fixture files into `workspace`.
4. Do not copy `tasks/fixtures/<id>/hidden/` until after the agent exits.
5. Reject symlinks before copying.
6. Initialize Git in `workspace`:
   ```sh
   git init -q
   git add .
   git -c user.name='Local Coder Eval' \
       -c user.email='local-coder@example.invalid' \
       commit -qm baseline
   ```
7. Do not touch the user's Git identity or repository configuration.
8. The temporary baseline commit provides a whole-tree diff and untracked-file detection.

### B.8.3 Temporary OpenCode configuration

Generate an `opencode.json` in the separate configuration directory, not in the fixture workspace.

```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "ollama-local": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Ollama Local",
      "options": {
        "baseURL": "http://127.0.0.1:11434/v1"
      },
      "models": {
        "qwen3.8:27b": {
          "name": "Qwen3.8 27B - Local"
        }
      }
    }
  },
  "permission": {
    "read": "allow",
    "list": "allow",
    "glob": "allow",
    "grep": "allow",
    "edit": "allow",
    "bash": {
      "*": "deny",
      "python3 *": "allow",
      "node --test *": "allow",
      "javac *": "allow",
      "java *": "allow",
      "git status *": "allow",
      "git diff *": "allow"
    },
    "webfetch": "deny"
  },
  "plugin": []
}
```

The exact allowed bash patterns must be generated from the task's public validation commands. The `*` deny rule is the default.

Set the OpenCode configuration environment variable supported by the installed version, preferably `OPENCODE_CONFIG`, to the generated file. The implementation must first verify this behavior with:

```sh
opencode --version
opencode run --help
```

If `OPENCODE_CONFIG` is not supported by OpenCode v1.18.35, use a documented dedicated configuration-directory mechanism. If no isolated configuration mechanism can be verified, agent mode must fail closed rather than use the user's global plugin set silently.

### B.8.4 OS sandbox

The temporary directory is the code-write sandbox, but it is not sufficient by itself. The OpenCode process also needs OS-level restrictions.

Prefer the built-in macOS `sandbox-exec` mechanism. Verify:

```sh
test -x /usr/bin/sandbox-exec
```

The generated profile must:

- allow normal process execution and reading system binaries;
- allow reads and writes below the unique `/private/tmp/local-coder-agent-*` root;
- deny writes below the user's home directory;
- deny general reads below the user's home directory, except narrowly defined OpenCode cache or package paths that are proven necessary;
- deny all external network access;
- allow outbound connections only to the local Ollama endpoint at `127.0.0.1:11434` or `localhost`.

A profile in this form is the starting point:

```text
(version 1)
(allow default)
(deny network-outbound)
(allow network-outbound (remote ip "localhost:*"))
(deny file-read* (subpath "/Users/jacklee"))
(deny file-write* (subpath "/Users/jacklee"))
(allow file-read* (subpath "/Users/jacklee/.cache/opencode"))
(allow file-read* (subpath "/Users/jacklee/.local/share/opencode"))
(allow file-read* (subpath "/private/tmp"))
(allow file-write* (subpath "/private/tmp"))
```

The implementation must verify actual sandbox precedence on macOS rather than assuming that rule order behaves as expected.

Required preflight checks:

1. The agent can read and edit the temporary workspace.
2. The agent can reach `127.0.0.1:11434`.
3. The agent cannot reach an external HTTPS host.
4. The agent cannot read a user-home canary file.
5. The agent cannot write outside the temporary root.

The canary must be a disposable, non-sensitive file created by the user or implementer for this check. Do not use an existing credential or private file as a test target.

If a working sandbox cannot be established:

- disable agent mode;
- do not use an unsandboxed fallback;
- record the blocker in the experiment log;
- do not download large models until a human-run, explicitly documented OpenCode procedure is used as a temporary substitute.

### B.8.5 Agent invocation

Use an argument vector, not a shell string:

```text
opencode
run
PROMPT
--model
ollama-local/qwen3.8:27b
--dir
/private/tmp/local-coder-agent-<uuid>/workspace
--format
json
```

The model reference comes from `config/models.json`:

```text
{opencode.provider}/{opencode.model}
```

The prompt must:

1. state the task title and task prompt;
2. list the editable paths;
3. tell the agent to inspect the repository and make the requested changes;
4. prohibit changes outside the editable paths;
5. prohibit network research;
6. tell the agent to use the available local test commands where useful;
7. avoid revealing the existence or contents of withheld tests.

Do not pass `--auto`. Do not enable broad shell permissions. `--print-logs` may be used only for a separately labeled diagnostic run, because logs may contain extra system information.

### B.8.6 Transcript and telemetry

Record:

- the exact command and sanitized environment;
- stdout and stderr verbatim in files under the run directory;
- parsed JSON events when available;
- process exit code;
- wall time;
- first non-empty event time;
- tool names and call counts when parseable;
- provider-reported input and output tokens when discoverable in the JSON events.

The parser must accept either:

- one JSON document; or
- JSON Lines.

For usage extraction, recursively search event objects for a usage-like object containing one of:

```text
input_tokens
inputTokens
prompt_tokens
completion_tokens
output_tokens
outputTokens
```

If several usage objects appear, use the final or most complete one. Do not sum repeated cumulative usage objects. If no usage is present, token counts remain null.

The raw transcript is authoritative. A transcript parse failure does not erase a valid workspace change, but it is recorded as a telemetry warning and prevents first-output or token claims.

### B.8.7 Diff and validation

After OpenCode exits:

1. Run:
   ```sh
   git status --porcelain=v1 --untracked-files=all
   git diff --binary --no-ext-diff
   ```
2. Capture the status output.
3. Capture tracked diffs.
4. For untracked files, capture a no-index diff against `/dev/null` or include their complete contents in a separate archive. Normalize these into one reviewable patch.
5. Compare changed paths with `editable`.
6. Set:
   - `allowed_files_touched`;
   - `allowed_files_untouched`;
   - `unexpected_paths`.
7. If any unexpected path changed, set `failure.kind = "disallowed_path"`.
8. Copy withheld files into the workspace only now.
9. Run public validation commands, then withheld validation commands.
10. Set `validation_failed` if any command fails, unless `disallowed_path` has higher priority.
11. Never modify the source fixture.
12. Store the patch and transcript in the run directory, which remains ignored by Git.

### B.8.8 Scoring agent results

Use the same manual 0/1/2 scale because the task requirements and human quality judgment are the same.

Differences from JSON repo mode:

1. The primary unit is the final workspace state.
2. A score 2 requires the final state to meet requirements and validation to pass.
3. Tool-call quality is recorded descriptively, not as a separate manual score.
4. One OpenCode invocation is the initial attempt.
5. Agent mode has no repair loop in this implementation.
6. Agent-mode results are compared only with other agent-mode runs under the same agent protocol hash.
7. The report must not rank agent and JSON repo results in the same quality column.

---

## B.9 Withheld tests

### B.9.1 Directory convention

For each fixture:

```text
tasks/fixtures/<task-id>/
  public fixture files, including visible tests
  hidden/
    withheld test files
```

`hidden/` is reserved. It is not copied into the agent workspace before the agent finishes, and it is never included in the prompt.

### B.9.2 Task schema

Add this optional field:

```json
"withheld_validation": [
  [
    "python3",
    "-m",
    "unittest",
    "discover",
    "-s",
    "hidden",
    "-v"
  ]
]
```

Rules:

1. `withheld_validation` is optional and defaults to an empty list.
2. Every command must satisfy the same list-of-strings validation as `validation`.
3. Public and withheld commands run in the listed order.
4. A task may have public validation, withheld validation, or both.

### B.9.3 Changes to `fixture_files()`

Change the function to:

```python
def fixture_files(task, include_hidden=False):
```

Behavior:

1. Exclude the top-level `hidden` directory when `include_hidden` is false.
2. Include it when true.
3. Continue excluding `__pycache__`, `.pyc`, and `.class`.
4. Reject every symlink in either public or hidden content.
5. Preserve relative paths using forward slashes.

`make_prompt()` must call `fixture_files(task)` with the default, so hidden files cannot leak.

### B.9.4 Changes to `suite_hash()`

The suite hash must include:

1. the exact `tasks/core.json` bytes;
2. every public file;
3. every hidden file;
4. an explicit namespace marker for public and hidden files;
5. task ID, relative path, and file bytes in deterministic order.

For example, update the digest with:

```text
task ID
"public" or "hidden"
relative path
file bytes
```

This prevents a public file and hidden file with the same relative name from colliding.

### B.9.5 Changes to `execute_repo()`

1. Copy public files first.
2. Reject symlinks before copy.
3. Apply changes.
4. Copy hidden files only after the model response is applied and before validation.
5. Run public validation.
6. Run withheld validation.
7. Store public and withheld command results in separate arrays or with an explicit `source` field.
8. Set `validation_passed` only if all commands in both lists pass.
9. For agent mode, hidden files are copied only after OpenCode exits.

### B.9.6 Required hidden coverage for the existing ten tasks

Add at least one withheld test file for every existing task:

| Task | Withheld cases that must be covered |
|---|---|
| `config-parse` | Non-object top level, missing provider, empty provider, missing MLX path, missing endpoint fields, malformed JSON, mapping preservation. |
| `result-summary` | Empty records, invalid negative and high scores, non-integers, booleans, and no mutation. |
| `cache-leak` | Different users with equal filters, equivalent filter insertion order, one build for equivalent requests, and no cross-user leakage. |
| `retry-final` | `attempts=1` performs no sleep, delay sequence 1 then 2, non-timeout errors are preserved, and attempts below 1 raise `ValueError`. |
| `score-tests` | Validate the scoring contract and manually review whether the submitted test file actually covers the requested cases. |
| `web-search` | Newest request wins, previous request is aborted, rejection is handled, and no unhandled rejection occurs. |
| `java-names` | Null and blank values, trimming, case-insensitive deduplication, first-spelling preservation, order, new-list semantics, and no mutation. |
| `api-key` | Empty key is rejected before write, direct `save` behavior is unchanged, and signatures are preserved. |
| `user-validation` | Shared validation is used by both create and update, exact messages remain, and save functions are unchanged. |
| `task-loader` | Invalid JSON, wrong shapes, missing fields, blank values, duplicate IDs, empty task list, source order, extra-field preservation, and unreadable files. |

The hidden test source is not shown to the model. Its output may be shown during a repair attempt.

---

## B.10 Task suite extension plan

Extend the suite from ten to fourteen tasks before candidate evaluation.

### B.10.1 New task 1: `minimal-repair`

Purpose: close both the missing-failure-output and unnecessary-change gaps in one task.

Proposed public fixture:

```python
# policy.py
def is_enabled(name, flags):
    return bool(flags.get(name, False))


def enabled_names(flags):
    return [name for name, value in flags.items() if value]
```

Proposed `FAILURE.txt`:

```text
AssertionError: expected False, got True
is_enabled("beta", {"beta": "false"}) returned True
```

Task requirements:

- Fix `is_enabled` so a flag is enabled only when its value is exactly the boolean `True`.
- Preserve the function signature.
- Preserve missing-key behavior.
- Do not change `enabled_names`.
- Make the smallest source edit that satisfies the requirement.
- Do not add dependencies.

Use the observed failure in the prompt and make the hidden tests check:

- string `"false"` is disabled;
- integer `1` is disabled;
- boolean `True` is enabled;
- missing keys are disabled;
- `enabled_names` is unchanged;
- the input mapping is not mutated.

The task is not automatically failed for a long diff. The reviewer applies `unrelated_refactor` or `excessive_complexity` when the larger edit was not required.

### B.10.2 New task 2: `strict-lint`

Purpose: add a dedicated standard-library lint or static-quality validation without a new dependency.

Use a small Python fixture with a deterministic `tabnanny` failure. Validation must include:

```json
[
  ["python3", "-m", "tabnanny", "-v"]
]
```

Also include a public or withheld unit test that establishes the intended behavior. The task asks for the smallest correction that fixes the lint failure without changing public behavior.

The report must label the validation as lint, not as a test.

### B.10.3 New task 3: first real-repository fixture

Recommended source: Auto Trader or DealLedger, selected by the procedure below.

Purpose: add a realistic configuration, validation, or data-boundary change with sanitized project context.

Do not specify task content until the derivation checklist is completed.

### B.10.4 New task 4: second real-repository fixture

Recommended source: Dynamic Task Router or CAPTS/FYP, selected by the procedure below. If neither has a suitable licence and testable boundary, use SoftwareEngineering Java coursework for a second Java fixture, but retain a second Python or TypeScript fixture when possible.

### B.10.5 Real-repository derivation procedure

For each selected real repository:

1. **Choose a bounded defect or change**
   - One clear requirement.
   - One or two editable files.
   - At least one deterministic validation command.
   - No external service or credential requirement.
   - Prefer a bug with one visible failure and one withheld edge case.

2. **Record source metadata**
   ```json
   "source_metadata": {
     "repository": "Auto Trader",
     "repository_url": "EXACT REPOSITORY URL",
     "commit_sha": "EXACT COMMIT SHA",
     "origin_paths": [
       "path/one.py",
       "path/two.py"
     ],
     "sanitization": [
       "names and identifiers replaced",
       "configuration values removed"
     ],
     "license": "SPDX ID OR EXPLICIT NOTE",
     "derived_at": "YYYY-MM-DD"
   }
   ```

3. **Copy the minimum necessary context**
   - Include only the changed files, direct interfaces, and focused tests.
   - Exclude unrelated application sections.
   - Exclude generated files, caches, build outputs, lockfiles, and large data.
   - Exclude licence headers if the licence allows modification without attribution obligations, otherwise preserve required notices.
   - Do not copy the full repository history.

4. **Redaction checklist**
   - No API keys, tokens, passwords, cookies, or session data.
   - No `.env` content.
   - No customer, user, portfolio, trading, or production data.
   - No internal hostnames, IP addresses, database URLs, or private paths.
   - No real account identifiers.
   - No private messages or logs.
   - No production error dumps.
   - No embedded binary data.
   - Replace realistic identifiers with neutral names.
   - Replace proprietary business constants with small synthetic values.

5. **Licence check**
   - Record the repository licence and whether fixture redistribution is permitted.
   - Do not include licence-sensitive material.
   - If permission is unclear, do not commit the fixture. Recreate the task from abstract behavior instead.

6. **Security check**
   - Search the candidate fixture for secrets and personal data before committing.
   - The implementer should use a local pattern scan, but must manually inspect matches.
   - Do not upload the candidate fixture to an external service.

7. **Isolation check**
   - The fixture must not call external services.
   - Validation must be deterministic and offline.
   - The task must not require the original repository to exist.

8. **Hidden-test derivation**
   - Add one withheld edge case based on the original requirement.
   - Do not copy a large upstream test suite.

9. **Task wording**
   - Sanitize names and business details.
   - State all required behavior.
   - Do not refer to proprietary implementation details the model cannot see.
   - Record sanitization decisions in the task source metadata.

10. **Review**
    - A second person or the user reviews the fixture before candidate models run.
    - Confirm that the task is solvable from the visible context and hidden requirements.

---

## B.11 CLI surface

Retain the recognizable single-file `scripts/evaluate.py` program. Do not split it into a package.

### B.11.1 Commands

#### List tasks

```sh
.venv/bin/python scripts/evaluate.py tasks
```

No flags.

#### Run one or more attempts

```sh
.venv/bin/python scripts/evaluate.py run \
  --model MODEL_KEY \
  --mode {response|repo|agent} \
  [--task TASK_ID] \
  [--max-tokens N] \
  [--repeats N] \
  [--timeout-seconds N] \
  [--repair-attempts {0,1,2}]
```

Defaults:

- `task`: all tasks;
- `max-tokens`: model configuration, then 4096;
- `repeats`: 1;
- `timeout-seconds`: 3600;
- `repair-attempts`: 0.

`--repeats N` executes N independent attempts. Every attempt gets a unique timestamped run directory. A `batch.json` manifest links the attempt directories. A repeat index is not part of the comparison key.

Full local candidate repository evaluation:

```sh
for repeat in 1 2 3; do
  .venv/bin/python scripts/evaluate.py run \
    --model qwen38_27b \
    --mode repo \
    --repeats 1
done
```

With the batch option, the equivalent single command is:

```sh
.venv/bin/python scripts/evaluate.py run \
  --model qwen38_27b \
  --mode repo \
  --repeats 3
```

Response evaluation:

```sh
.venv/bin/python scripts/evaluate.py run \
  --model qwen38_27b \
  --mode response \
  --repeats 3
```

Agent evaluation:

```sh
.venv/bin/python scripts/evaluate.py run \
  --model qwen38_27b \
  --mode agent \
  --repeats 1
```

#### Score one task

```sh
.venv/bin/python scripts/evaluate.py score RUN \
  --task TASK_ID \
  --score {0|1|2} \
  --notes "..." \
  --failure ignored_requirement \
  --additional-prompts 0 \
  --reviewer local-user
```

The `--failure` value is now a closed category, not free text. Add `--failure-detail` if a category occurrence needs explanation.

#### Score a batch

```sh
.venv/bin/python scripts/evaluate.py score-sheet SCORE_SHEET.json \
  [--dry-run] \
  [--replace]
```

#### Export a tracked run summary

```sh
.venv/bin/python scripts/evaluate.py export RUN_OR_BATCH \
  --output reports/runs/RUN_ID
```

The export must create:

```text
reports/runs/RUN_ID/summary.json
reports/runs/RUN_ID/summary.md
reports/runs/RUN_ID/changes.patch
```

Raw responses remain under ignored `results/`. The summary contains metadata, manual scores, failure taxonomy, validation results, timings, diff statistics, and a pointer to the raw run.

#### Compare

```sh
.venv/bin/python scripts/evaluate.py compare \
  RUN_OR_BATCH_1 \
  RUN_OR_BATCH_2 \
  [...] \
  --output reports/model_comparison.md
```

The comparator must:

- reject incompatible runs;
- group attempts by model key;
- aggregate repeated attempts;
- keep response, repo, and agent results in separate sections;
- never report response mode as having validation.

### B.11.2 Batch manifest

```json
{
  "schema_version": 1,
  "batch_id": "20261020T120000000000Z",
  "model_key": "qwen38_27b",
  "mode": "repo",
  "created_utc": "2026-10-20T12:00:00.000000+00:00",
  "attempt_run_ids": [
    "20261020T120000000001Z",
    "20261020T120000000002Z",
    "20261020T120000000003Z"
  ]
}
```

---

## B.12 Comparison report design

The generated report must have these sections in this order.

### 1. Report identity and comparability

Include:

- report generation time;
- protocol version;
- suite hash;
- task list;
- common generation settings;
- context requirement;
- run IDs;
- model keys;
- warnings for legacy, unscored, incomplete, or operationally non-compliant runs;
- explicit statement that response, repo, and agent modes are separate.

### 2. Decision summary

| Metric | Model A | Model B |
|---|---:|---:|
| Attempts completed | | |
| Transport-valid attempts | | |
| Manually reviewed | | |
| Mean manual score, scored attempts | | |
| Majority task success | | |
| First-pass score-2 tasks | | |
| Final score-2 tasks | | |
| Validation-passing attempts, repo or agent only | | |
| Requirement failures | | |
| Mixed-score tasks | | |
| Median completion tokens/sec | | |
| Median request seconds | | |
| Peak sampled runner RSS | | |
| Observed Ollama context | | |
| Operational status | | |

### 3. Task success and stability

For each task:

- number of attempts;
- manual scores;
- majority result;
- whether results were mixed;
- objective validation count;
- failure kinds;
- number of repair prompts.

### 4. Category breakdown

One row per category:

| Category | Tasks | Score-2 attempts | Mean score | Validation pass rate | Requirement failures | Unstable tasks |
|---|---:|---:|---:|---:|---:|---:|

### 5. Failure-mode breakdown

| Failure kind | Model A count | Model A rate | Model B count | Model B rate |
|---|---:|---:|---:|---:|

Also list each requirement-failure category separately.

### 6. Per-task table

| Task | Category | Model | Score | Validation | Failure kind | Additional prompts | Allowed files touched | Allowed files untouched | Unexpected paths | Review note |
|---|---|---|---:|---|---|---:|---|---|---|---|

### 7. Diff and scope hygiene

For each model:

- files changed;
- allowlisted files touched;
- allowlisted files untouched;
- unexpected paths;
- total insertions and deletions;
- number of substantive tasks with unrelated changes;
- number with excessive complexity.

### 8. Timing and operational feasibility

- median and range request time;
- median completion tokens per second;
- first-token timing availability;
- sampled runner RSS;
- Ollama-reported allocation;
- observed context;
- swap and memory-pressure observations;
- disk download size;
- whether the model is practical for daily use on this machine.

### 9. Agent-mode results

A separate section with the same task, category, and failure tables, but no pooling with JSON repo mode.

### 10. Outcome mapping

Show which of A, B, C, or D is supported, using the pre-registered rules.

### 11. Evidence gaps

List:

- unscored attempts;
- failed transports;
- non-compliant context;
- missing telemetry;
- unavailable raw runs;
- protocol mismatches;
- unverified model tags or model-specific controls.

### 12. Aggregated repeated-attempt rules

If three attempts are available:

1. A task is a **majority success** when at least two of three attempts receive score 2.
2. A task is **unstable** when the three scores are not all equal.
3. Report both per-attempt rates and majority-success rates.
4. Do not claim statistical significance from ten correlated tasks.
5. A difference of fewer than one task or less than 0.10 mean score is inconclusive unless objective validation or timing is decisively better.

---

## B.13 Measurement protocol for candidate runs

### B.13.1 General preparation

Before each candidate:

1. Confirm the repository is on the intended commit.
2. Run:
   ```sh
   git status --short
   .venv/bin/python -m unittest discover -s tests -v
   .venv/bin/python scripts/evaluate.py tasks
   ```
3. Close unrelated heavy applications.
4. Connect AC power.
5. Record the idle state:
   ```sh
   date -u
   sysctl -n hw.memsize
   df -h /Users/jacklee/Other/Me/Projects/local-coder
   sysctl vm.swapusage
   memory_pressure -Q
   ollama ps
   ```
6. Record the same values in Activity Monitor.
7. Do not run another local model concurrently.

### B.13.2 Server startup

The user must stop any existing Ollama server or desktop instance that was not started with the required environment. Verify the listener:

```sh
lsof -nP -iTCP:11434 -sTCP:LISTEN
```

Start a dedicated server:

```sh
OLLAMA_CONTEXT_LENGTH=64000 ollama serve
```

Use the absolute binary path if desired:

```sh
OLLAMA_CONTEXT_LENGTH=64000 /usr/local/bin/ollama serve
```

Do not assume the environment took effect. After the first request, `ollama ps` must show a context of 64000. If it does not, stop the run and correct server startup.

A KV-cache quantization experiment is permitted only as a separately labeled policy. If `q8_0` is used for one candidate, it must be used for every candidate in the primary local comparison, and the KV-cache type must be recorded in the comparison report.

### B.13.3 Pull and disk discipline

At most two candidates may be present on disk, counting the already installed 9B baseline.

The safe sequence is:

1. Keep `qwen3.5:9b`.
2. Pull one new candidate.
3. Evaluate and export it.
4. Unload it.
5. Remove it.
6. Confirm free space.
7. Pull the next candidate.

The user runs the pull:

```sh
ollama pull qwen3.8:27b
```

The harness never runs this command.

After the pull:

```sh
ollama list
df -h /Users/jacklee/Other/Me/Projects/local-coder
du -sh ~/.ollama/models
```

The user may keep at most one new candidate and the 9B baseline. Do not retain both the 27B and 30B candidates while another new candidate is being evaluated.

### B.13.4 Loading and context verification

Run one task first:

```sh
.venv/bin/python scripts/evaluate.py run \
  --model qwen38_27b \
  --mode repo \
  --task config-parse
```

Immediately afterward, while the model remains loaded:

```sh
ollama ps
```

Required observations:

- served model name;
- reported size;
- processor;
- observed context, expected to be 64000;
- runner type;
- unload time.

If context is not 64000, the run is not eligible for the primary daily-use comparison.

### B.13.5 Per-candidate run sequence

For each candidate:

1. Capture the pre-pull disk and memory state.
2. Pull the candidate, if it is not already present.
3. Start or reuse the correctly configured server.
4. Run one short task to load the model.
5. Capture `ollama ps` and confirm context.
6. Capture idle and loaded memory observations.
7. Run the response suite with three attempts per task.
8. Run the repo suite with three attempts per task.
9. Run the agent suite with one attempt per task.
10. During the longest generation, capture:
    - `ollama ps`;
    - runner RSS sample;
    - `memory_pressure -Q`;
    - `sysctl vm.swapusage`;
    - Activity Monitor memory values.
11. After completion, capture the same values before unloading.
12. Export scored summaries to `reports/runs/`.
13. Run `ollama stop TAG`.
14. Capture post-unload memory and swap.
15. Remove the candidate, unless it is the 9B baseline or the user explicitly chooses to retain it.
16. Confirm disk reclamation.

### B.13.6 Repeat count

Primary protocol:

- response mode: 3 attempts per task;
- repo mode: 3 attempts per task;
- agent mode: 1 attempt per task.

Reasons:

1. One attempt cannot distinguish a stable capability from sampling noise.
2. Three attempts are the smallest practical repeat count for this suite.
3. Agent mode is more expensive and can be repeated for borderline candidates after the primary comparison.

If a candidate is within one task or 0.10 mean score of the leader, run three additional attempts for the affected tasks before making a final choice.

### B.13.7 Throughput measurement

Use the median of all completed repo attempts for the headline tokens-per-second value. Also report:

- minimum;
- maximum;
- median request time;
- first-token time when available.

Do not compare one fast warm-cache task with one cold or slow task.

### B.13.8 Disk reclamation

`ollama stop` unloads RAM but does not reclaim model disk space. The user must run both commands explicitly.

For Qwen3.8:

```sh
ollama stop qwen3.8:27b
ollama rm qwen3.8:27b
```

For Qwen3-Coder:

```sh
ollama stop qwen3-coder:30b
ollama rm qwen3-coder:30b
```

For GPT-OSS:

```sh
ollama stop gpt-oss:20b
ollama rm gpt-oss:20b
```

Then verify:

```sh
ollama list
df -h /Users/jacklee/Other/Me/Projects/local-coder
du -sh ~/.ollama/models
```

No script in the repository may execute `ollama rm` or recursively delete the Ollama store.

---

## B.14 KV-cache and memory feasibility

### B.14.1 Formula

For a transformer with:

- `L` transformer layers;
- `H_kv` key/value heads;
- head dimension `D`;
- `B` bytes per cached scalar;
- context length `C`;

the approximate KV cache is:

```text
KV bytes = 2 × L × H_kv × D × B × C
```

The factor 2 represents keys and values.

The figures below are estimates, not claimed architecture facts for models whose manifests have not yet been inspected. They use the following assumptions:

| Candidate | Assumed `L` | Assumed `H_kv` | Assumed `D` | KV bytes per token, f16 |
|---|---:|---:|---:|---:|
| Qwen3.5 9B | 48 | 8 | 128 | 196,608 |
| Qwen3.8 27B | 64 | 8 | 128 | 262,144 |
| Qwen3-Coder 30B | 48 | 4 | 128 | 98,304 |
| GPT-OSS 20B | 24 | 8 | 64 | 49,152 |

These assumptions are deliberately conservative. Verify the actual layer count, KV-head count, and KV-cache type from the downloaded Ollama manifest and server configuration.

### B.14.2 Qwen3.5 9B

Known model layer size:

```text
6,594,462,816 bytes / 2^30 = 6.14 GiB
```

Estimated f16 KV cache:

```text
32K:
196,608 × 32,768 = 6,442,450,944 bytes = 6.00 GiB

64K:
196,608 × 65,536 = 12,884,901,888 bytes = 12.00 GiB
```

Approximate total:

| Context | Weights | KV, f16 | Total before runtime overhead |
|---:|---:|---:|---:|
| 32K | 6.14 GiB | 6.00 GiB | 12.14 GiB |
| 64K | 6.14 GiB | 12.00 GiB | 18.14 GiB |

**Recommendation:** 64000. It should fit 24 GB with room for runtime overhead. A q8 KV cache would reduce the cache to about 6 GiB at 64K, but f16 is the cleaner baseline if it fits.

### B.14.3 GPT-OSS 20B

Weight estimate:

```text
14 GB decimal × 0.9313225746 = 13.04 GiB
```

Estimated f16 KV cache:

```text
32K:
49,152 × 32,768 = 1,610,612,736 bytes = 1.50 GiB

64K:
49,152 × 65,536 = 3,221,225,472 bytes = 3.00 GiB
```

Approximate total:

| Context | Weights | KV, f16 | Total before runtime overhead |
|---:|---:|---:|---:|
| 32K | 13.04 GiB | 1.50 GiB | 14.54 GiB |
| 64K | 13.04 GiB | 3.00 GiB | 16.04 GiB |

**Recommendation:** 64000. This candidate has the strongest memory margin and should be a control for whether quality and speed differ because of the model or the runtime.

### B.14.4 Qwen3-Coder 30B A3B

Weight estimate:

```text
19 GB decimal × 0.9313225746 = 17.70 GiB
```

Estimated f16 KV cache:

```text
32K:
98,304 × 32,768 = 3,221,225,472 bytes = 3.00 GiB

64K:
98,304 × 65,536 = 6,442,450,944 bytes = 6.00 GiB
```

Approximate total:

| Context | Weights | KV, f16 | Total before runtime overhead |
|---:|---:|---:|---:|
| 32K | 17.70 GiB | 3.00 GiB | 20.70 GiB |
| 64K | 17.70 GiB | 6.00 GiB | 23.70 GiB |

**Recommendation:** target 64000, but treat it as marginal with f16. Runtime buffers and the KV implementation can push it beyond the physical memory limit. If a q8 KV cache is used, the estimated 64K totals become about 20.70 GiB including weights, which is more plausible. Any q8 policy must be applied consistently to all primary local candidates and recorded.

### B.14.5 Qwen3.8 27B

Weight estimate:

```text
18 GB decimal × 0.9313225746 = 16.76 GiB
```

Estimated f16 KV cache:

```text
32K:
262,144 × 32,768 = 8,589,934,592 bytes = 8.00 GiB

64K:
262,144 × 65,536 = 17,179,869,184 bytes = 16.00 GiB
```

Approximate total:

| Context | Weights | KV, f16 | Total before runtime overhead |
|---:|---:|---:|---:|
| 32K | 16.76 GiB | 8.00 GiB | 24.76 GiB |
| 64K | 16.76 GiB | 16.00 GiB | 32.76 GiB |

Under these conservative assumptions, even 32K f16 does not fit comfortably in 24 GB, and 64K f16 is clearly infeasible. If the actual architecture has half as many KV heads, the cache is halved. If the KV cache is q8, it is also halved. Therefore:

**Recommendation:** 64000 is the required daily-use target because OpenCode requires at least 64K, but this candidate is not operationally eligible until an actual 64000-context run demonstrates acceptable memory pressure. A 32K run is diagnostic only and must not be presented as satisfying the OpenCode requirement.

Under a q8 assumption, the estimated totals are:

| Context | Weights | KV, q8 | Total before runtime overhead |
|---:|---:|---:|---:|
| 32K | 16.76 GiB | 4.00 GiB | 20.76 GiB |
| 64K | 16.76 GiB | 8.00 GiB | 24.76 GiB |

Even q8 at 64K is marginal under the conservative architecture assumption.

### B.14.6 Throughput and memory-pressure consequences

1. KV-cache memory grows linearly with context.
2. Prefill time grows with the number of input tokens.
3. Decode throughput usually declines less than prefill time because the model weights remain the dominant fixed cost, but larger KV caches increase memory bandwidth and cache pressure.
4. On unified memory, swapping is much worse than a modest reduction in raw tokens per second. A model that swaps heavily is operationally unsuitable even if its first few tokens appear fast.
5. The 9B and 20B models should sustain 64K without sustained swapping.
6. The 30B MoE model may fit at 64K only with careful KV-cache policy and low runtime overhead.
7. The dense 27B model is the highest-risk case. Its 30B parameter count does not make it automatically safer than a sparse model because all dense weights must be resident.

### B.14.7 Measurement that resolves the estimates

For each downloaded model:

1. Start the server with the intended context and KV policy.
2. Load the model with a long request that approaches the target context.
3. Capture:
   ```sh
   ollama ps
   ps -axo pid=,ppid=,rss=,command= | grep '[o]llama runner'
   sysctl vm.swapusage
   memory_pressure -Q
   ```
4. Record whether `ollama ps` shows 64000.
5. Repeat at 32768 only as a diagnostic.
6. Do not infer context feasibility from the model's advertised 256K maximum.

---

## B.15 Sequencing plan for the two-day cloud window

The cloud model is a ceiling reference, not a local-model recommendation. The priority is to finish and validate the harness while access is available.

### Hours 0 through 2: freeze the protocol

- Commit the configuration schema and all model entries.
- Define protocol version 2.
- Define the comparison key.
- Update the experiment log and selection-report structure.
- Do not download a local candidate.

### Hours 2 through 7: request, parsing, and failure handling

- Implement SSE handling.
- Implement assistant and reasoning extraction.
- Implement the balanced JSON scanner.
- Implement truncation evidence.
- Implement the closed failure taxonomy.
- Add unit tests for string content, list content, alternate fields, reasoning, fences, prose wrappers, truncation, HTTP errors, and timeouts.

### Hours 7 through 11: hidden tests and scoring

- Add the `hidden/` convention.
- Change `fixture_files()` and `suite_hash()`.
- Add withheld validation.
- Add hidden tests for all ten existing tasks.
- Implement the rubric and bulk score sheet.
- Test that omitted tasks remain null and existing reviews are not clobbered.

### Hours 11 through 15: metadata, telemetry, and report

- Implement schema version 2 metadata.
- Implement strict comparison-key validation.
- Implement sampled Ollama runner RSS.
- Implement the report sections and failure and category aggregation.
- Implement tracked export.

### Hours 15 through 18: optional repair

- Implement the optional repair loop.
- Use a fake model in tests to fail once and pass after repair.
- Verify that initial and final results remain distinct.
- Do not spend more than three hours on this P1 feature if it delays agent mode.

### Hours 18 through 25: agent mode

- Prototype the temporary OpenCode configuration.
- Verify `OPENCODE_CONFIG` behavior.
- Establish the macOS sandbox.
- Verify local Ollama access, external network denial, and home-directory isolation.
- Implement the temporary Git workspace.
- Implement transcript capture, diff capture, and validation.
- Run one cloud-model agent task.
- If the sandbox cannot be made reliable, document that blocker immediately.

### Hours 25 through 31: cloud ceiling run

Run the same frozen suite with the cloud model:

```sh
.venv/bin/python scripts/evaluate.py run \
  --model minimax_m31_flash_cloud \
  --mode response \
  --repeats 3

.venv/bin/python scripts/evaluate.py run \
  --model minimax_m31_flash_cloud \
  --mode repo \
  --repeats 3

.venv/bin/python scripts/evaluate.py run \
  --model minimax_m31_flash_cloud \
  --mode agent \
  --repeats 1
```

The cloud run must use the same suite, common generation settings, task order, and prompt versions as the later local runs.

### Hours 31 through 36: rubric calibration

1. Score the cloud repo run once.
2. Export the score sheet.
3. Score the same run again without consulting the first sheet.
4. Compare all task scores and failure categories.
5. Resolve every disagreement against the written rubric.
6. Amend the rubric and task wording before local runs.
7. If agreement is below 90 percent, repeat calibration after revising the rubric.

### Hours 36 through 42: task extension

- Add `minimal-repair`.
- Add `strict-lint`.
- Derive and review the first real-repository fixture.
- Derive and review the second real-repository fixture.
- Recompute and record the new suite hash.
- Rerun the cloud smoke test on the changed suite if the window still permits it.

### Hours 42 through 46: final cloud validation

- Run all tests.
- Run a full response, repo, and agent smoke test.
- Export the cloud summary.
- Update the experiment log.
- Update `reports/model_selection.md` with the cloud ceiling only.
- Commit all harness, suite, and documentation work.

### Must finish before the cloud window closes

- All P0 items.
- All P1 items, including bulk scoring, hidden tests, telemetry, report design, repair accounting, and agent mode.
- A successful cloud response, repo, and agent run.
- A complete cloud scoring pass.
- A repeated cloud scoring pass and documented rubric resolution.
- A stable suite hash.
- A committed harness revision.
- An exported cloud run summary.

### May wait until after the window

- P2 usability improvements.
- Additional real-repository fixtures beyond the two planned.
- More than three repeats for a stable candidate.
- Fine-tuning dataset design.
- Additional cloud prompts unrelated to the frozen suite.

---

## B.16 Final decision document

Replace `reports/model_selection.md` with this structure:

```markdown
# Local model selection

Status: {pending|complete}

## Decision summary

{One paragraph naming the recommended local model, any second model, and the
fine-tuning decision.}

## 1. Best overall model

- Model:
- Evidence:
- Majority task success:
- Mean manual score:
- Validation rate:
- Context and memory feasibility:
- Why it ranks above the alternatives:

## 2. Best model for difficult tasks

- Model:
- Difficult-task definition:
- Score:
- Validation:
- Repeated failure modes:

## 3. Best model for fast routine work

- Model:
- Routine-task definition:
- Score:
- Median tokens/sec:
- Median request time:
- Memory and disk fit:

## 4. Is maintaining two models worthwhile?

- Decision:
- Specialist and generalist:
- Portfolio gain:
- Operational cost:
- Recommendation:

## 5. Is there a repeated weakness?

- Category or task:
- Models affected:
- Number of affected tasks:
- Failure category:
- Shared root cause:
- Whether it is model quality, protocol failure, timeout, or test weakness:

## 6. Is custom fine-tuning justified?

- Decision: yes|no
- Pre-registered D rule satisfied: yes|no
- Evidence:
- If no, state which trigger was not met.
- If yes, specify the next dataset and validation work, but do not start training.

## 7. Outcome mapping

### A. Use two models

{Satisfied or not satisfied, with thresholds.}

### B. Qwen3-Coder matches Qwen3.8 but is faster

{Satisfied or not satisfied, with thresholds.}

### C. Qwen3.8 wins outright

{Satisfied or not satisfied, with thresholds.}

### D. All models fail the same task type

{Satisfied or not satisfied, with thresholds.}

## 8. Run inventory

| Model | Mode | Run IDs | Attempts | Suite hash | Context | Protocol |
|---|---|---|---:|---|---:|---|

## 9. Operational evidence

| Model | Download size | Observed context | Peak sampled RSS | Swap behavior | Disk status |
|---|---:|---:|---:|---|---|

## 10. Threats to validity

- Repeat variance:
- Manual-scoring consistency:
- Hidden-test limitations:
- Runtime or model-specific settings:
- Telemetry limitations:
- Cloud-ceiling differences:

## 11. Final recommendation

{Exact daily-use command or commands, plus the model to avoid or retain for
special cases.}
```

### B.16.1 Pre-registered task subsets

Before local runs, freeze these subsets:

- **Difficult tasks:** `cache-leak`, `retry-final`, `api-key`, and `task-loader`.
- **Routine tasks:** `result-summary`, `score-tests`, `web-search`, `java-names`, and `user-validation`.
- `config-parse` and `minimal-repair` are general implementation tasks and are included in overall results but not in either specialist subset.

The rationale must be recorded before observing model scores.

### B.16.2 Pre-registered ranking rules

For three-attempt runs:

1. A task succeeds for a model when at least two of three attempts receive score 2.
2. Overall quality is the number of majority-success tasks out of 14.
3. Mean manual score across scored attempts is the secondary quality measure.
4. Objective validation rate is reported separately.
5. First-pass success is reported separately and is not the primary quality measure.
6. If two models differ by fewer than one majority-success task and less than 0.10 mean score, the quality result is inconclusive. Speed and memory then break the operational tie, but the report must call the quality difference inconclusive.
7. Throughput ties use median completion tokens per second.
8. Memory ties use the lower sampled runner RSS.

### B.16.3 Pre-registered outcome A: use two models

Use two models only if all of these hold:

1. One model is at least two majority-success tasks better on the difficult subset.
2. The other model is no worse on the routine subset and is at least two majority-success tasks better there.
3. The union of the two models' per-task majority results improves over the best single model on at least two tasks.
4. Both models meet the 64000 context requirement.
5. Both have acceptable memory pressure and sustained throughput.
6. Keeping and switching between them is operationally acceptable after accounting for disk use.

If the models can both be kept on disk, the 9B baseline plus one larger candidate is acceptable. Two larger candidates do not fit safely under the 40 GB free-space constraint.

### B.16.4 Pre-registered outcome B: Qwen3-Coder matches Qwen3.8 but is faster

Select the single-model Qwen3-Coder outcome only if all of these hold:

1. Qwen3-Coder's majority-success count is no more than one task below Qwen3.8's.
2. Its mean manual score is no more than 0.05 below Qwen3.8's.
3. Its validation-pass rate is no more than 10 percentage points below Qwen3.8's.
4. Its median completion throughput is at least 1.5 times Qwen3.8's.
5. It sustains an observed 64000 context without sustained swapping.
6. It has no repeated requirement weakness that Qwen3.8 does not share.

### B.16.5 Pre-registered outcome C: Qwen3.8 wins outright

Select Qwen3.8 as the single overall model if either condition holds:

1. It wins at least two majority-success tasks and has at least 0.20 higher mean manual score; or
2. It wins at least three majority-success tasks and at least three category wins.

It must also meet the 64000 context and memory requirements. A quality win does not override an operational failure.

### B.16.6 Pre-registered outcome D: repeated task-type failure

D is satisfied only if:

1. The affected category contains at least three tasks.
2. At least two exact task IDs in that category fail for every evaluated local candidate.
3. On each shared task, every local candidate has the same closed manual failure category.
4. The reviewer assigns the same root-cause label to all of those failures.
5. The failures are not caused by HTTP errors, timeouts, truncation, invalid JSON, or another protocol defect.
6. The failure is not caused by an ambiguous or incorrect task.
7. If the GPT-OSS control was evaluated, it either shares the same failure or is explicitly documented as a counterexample that prevents D.

This is deliberately stricter than correlated low scores. The same generic category alone is insufficient.

### B.16.7 Fine-tuning decision

- If D is satisfied, custom fine-tuning is justified as a next experiment.
- If D is not satisfied, custom fine-tuning remains unjustified and paused.
- Protocol failures, truncation, or bad tasks trigger harness or task repair, not fine-tuning.
- A weakness in only one model is a model-selection result, not a fine-tuning trigger.
- No training is started by this decision.

---

## B.17 Experiment log requirements

### B.17.1 Required fields for each new candidate entry

Every candidate run or batch must add an entry to `docs/experiment_log.md` with:

1. Date and UTC time.
2. Git commit.
3. Whether the working tree was dirty.
4. Model key, display name, provider, and served model ID.
5. Ollama tag and model quantization if known.
6. Ollama and OpenCode versions.
7. Endpoint.
8. Requested context.
9. Observed context from `ollama ps`.
10. KV-cache type.
11. Suite path and hash.
12. Prompt version.
13. Common generation settings.
14. Model-specific reasoning settings.
15. Number of attempts.
16. Task IDs and attempt counts.
17. Agent protocol and sandbox configuration hash, for agent mode.
18. Repair policy.
19. Objective validation counts.
20. Failure-kind counts.
21. Manual score summary.
22. Requirement-failure category counts.
23. Timing summary.
24. Memory and swap observations.
25. Download size and disk observations.
26. Exported report path.
27. Observations.
28. Decision or effect on the selection.
29. Failures, interruptions, and deviations.
30. Raw run path, which remains uncommitted.

### B.17.2 Required backfill for the six 7B runs

Add one dated backfill section covering all six run directories. It must state:

- commit `bdbd2e0`;
- suite hash `8dbe038dd7c32fe5bc3ea8b89c1c12bd8624cb79ce4027033b71384dce031637`;
- generation setting `max_tokens: 1024`;
- every run has `manual.score: null`;
- no run has been manually reviewed;
- the 10-task repo run has objective validation passing for:
  - `cache-leak`;
  - `config-parse`;
  - `score-tests`;
  - `user-validation`;
- the other six repo tasks fail validation;
- none of the 10-task repo records has a non-null harness error;
- therefore the 4/10 result is an objective validation count, not a manual quality score;
- the `result-summary` and `user-validation` examples document requirement adherence and output-integrity failures;
- the 7B workflow remains a reference and not a selection candidate;
- no score should be inferred or backfilled after the fact.

List all six run IDs and their mode and task counts so the backfill is auditable.

Also update `reports/model_selection.md` to state that Qwen3.5 9B is installed and available, correcting the current statement that its weights are not installed.

---

## Part C: implementation plan

## C.1 Ordered implementation steps

| Order | Files | Change | Acceptance check | Rough effort |
|---:|---|---|---|---:|
| 1 | `config/models.json`, `scripts/evaluate.py`, `tests/test_evaluate.py` | Add schema version, exact model fields, and all six model entries. | Config validation accepts the supplied file; endpoint and model IDs are exact; no model requires Python edits. | 0.5 day |
| 2 | `scripts/evaluate.py`, `tests/test_evaluate.py` | Add streaming endpoint handling, robust assistant extraction, reasoning separation, timeout handling, and the closed failure taxonomy. | Unit tests cover string and list content, alternate fields, SSE, HTTP errors, timeouts, and every failure kind. | 1.5 days |
| 3 | `scripts/evaluate.py`, `tests/test_evaluate.py` | Implement the balanced JSON extractor and truncation rules. | Three worked malformed-but-recoverable examples parse; truncated JSON is not labeled unparseable; invalid JSON remains unparseable. | 1 day |
| 4 | `scripts/evaluate.py`, `tests/test_evaluate.py` | Add schema-v2 metadata, exact comparison key, protocol version, and actionable incompatibility errors. | Old/new protocol mismatch names the differing fields; legacy runs are not silently compared. | 1 day |
| 5 | `scripts/evaluate.py`, `tests/test_evaluate.py` | Add timing, usage, sampled Ollama RSS, and runtime metadata. | Fake SSE usage produces correct tokens/sec; sampled RSS is labeled approximate; cloud memory is null with a reason. | 1 day |
| 6 | `tasks/core.json`, `scripts/evaluate.py`, `tests/test_evaluate.py` | Add hidden-file convention, `withheld_validation`, and hidden-inclusive suite hashing. | A sentinel in a hidden file never appears in a prompt; changing a hidden file changes the suite hash; hidden tests run after changes are applied. | 1 day |
| 7 | `tests/test_evaluate.py`, new hidden fixture files, `tasks/core.json` | Add withheld tests for all ten existing tasks. | Every existing task has at least one hidden edge case and all public and hidden tests pass against a known-good implementation. | 1.5 days |
| 8 | `scripts/evaluate.py`, `tests/test_evaluate.py`, `docs/evaluation_method.md` | Implement the rubric, closed failure categories, bulk score sheets, and nullable correction counts. | Omitted tasks stay null; invalid categories fail validation; `--replace` is required to overwrite a review. | 1 day |
| 9 | `scripts/evaluate.py`, `tests/test_evaluate.py` | Add the optional, bounded repair loop. | A fake model can fail then pass; initial and final scores remain separate; attempt count and prompt count are recorded. | 1 day |
| 10 | `scripts/evaluate.py`, `tests/test_evaluate.py` | Add agent mode, temporary OpenCode configuration, sandbox preflight, Git diff capture, transcript capture, and agent validation. | Agent changes stay in the temp workspace; hidden files are absent during the run; source fixtures are unchanged; no `--auto` is used. | 2.5 days |
| 11 | `scripts/evaluate.py`, `tests/test_evaluate.py` | Rewrite `compare()` around the new metadata, repeated attempts, categories, failure modes, diff scope, and outcome rules. | Response mode has no validation row; repo and agent modes remain separate; incompatible runs fail clearly. | 1.5 days |
| 12 | `scripts/evaluate.py`, `tests/test_evaluate.py` | Add tracked export of run summaries and patch files. | Export creates `summary.json`, `summary.md`, and `changes.patch`; raw results remain ignored. | 0.5 day |
| 13 | `tasks/core.json`, new fixture directories | Add `minimal-repair`, `strict-lint`, and two sanitized real-repository tasks. | Fourteen tasks load; all public and hidden validations pass against reference solutions; no sensitive or licence-sensitive content remains. | 2.5 days |
| 14 | `README.md`, `docs/evaluation_method.md`, `docs/experiment_log.md`, `reports/model_selection.md` | Document the new commands, modes, scoring, operational procedure, cloud calibration, and six-run backfill. | A new operator can complete pull, serve, evaluate, score, export, compare, and reclaim disk without hidden steps. | 1 day |
| 15 | `scripts/evaluate.py`, `tests/test_evaluate.py`, `docs/experiment_log.md`, `reports/model_selection.md` | Run the cloud end-to-end calibration and record the observed results. | Cloud response, repo, and agent runs exist; scores are exported; repeated-review agreement is documented. | 1 day |

The order matters. Do not begin real candidate scoring until steps 1 through 14 are complete.

## C.2 Proposed commit sequence

The user must run these commands. The environment does not permit the assistant to commit.

### Commit 1: model configuration

```sh
git add config/models.json scripts/evaluate.py tests/test_evaluate.py
git commit -m "Configure local and cloud evaluation models"
```

### Commit 2: response protocol and failures

```sh
git add scripts/evaluate.py tests/test_evaluate.py
git commit -m "Handle reasoning responses and structured failures"
```

### Commit 3: comparable metadata and telemetry

```sh
git add scripts/evaluate.py tests/test_evaluate.py
git commit -m "Record comparable run metadata and telemetry"
```

### Commit 4: withheld tests

```sh
git add tasks/core.json tasks/fixtures scripts/evaluate.py tests/test_evaluate.py
git commit -m "Add withheld fixture tests"
```

### Commit 5: scoring workflow

```sh
git add scripts/evaluate.py tests/test_evaluate.py docs/evaluation_method.md
git commit -m "Add bulk scoring and review rubric"
```

### Commit 6: repair loop

```sh
git add scripts/evaluate.py tests/test_evaluate.py
git commit -m "Add optional repository repair attempts"
```

### Commit 7: agent mode

```sh
git add scripts/evaluate.py tests/test_evaluate.py
git commit -m "Add sandboxed OpenCode repository mode"
```

### Commit 8: reporting and export

```sh
git add scripts/evaluate.py tests/test_evaluate.py
git commit -m "Expand model comparison reports and run exports"
```

### Commit 9: task extension

```sh
git add tasks/core.json tasks/fixtures
git commit -m "Extend practical model selection task suite"
```

### Commit 10: documentation and runbook

```sh
git add README.md docs/evaluation_method.md docs/experiment_log.md reports/model_selection.md
git commit -m "Document candidate evaluation and decision protocol"
```

### Commit 11: cloud calibration, only after the run exists

```sh
git add reports/runs docs/experiment_log.md reports/model_selection.md
git commit -m "Record cloud model calibration results"
```

### Commit 12: local decision, only after all local runs and scores exist

```sh
git add reports/runs reports/model_selection.md docs/experiment_log.md
git commit -m "Record local model selection decision"
```

Before each commit, run:

```sh
.venv/bin/python -m unittest discover -s tests -v
git diff --check
git status --short
```

Do not use `git add -f results/`. Raw results remain ignored.

## C.3 Risk register

| Risk | What you would notice | Cheapest mitigation |
|---|---|---|
| The proposed Ollama tag is absent or has a different served ID. | `ollama pull` or a request returns a model-not-found error. | Correct only `config/models.json`; do not add model-specific Python. |
| The running server ignores `OLLAMA_CONTEXT_LENGTH=64000`. | `ollama ps` shows 4K or 32K. | Stop the incorrectly configured server and restart it. Exclude the run until context is observed. |
| The 27B dense model swaps heavily at 64K. | Swap rises, memory pressure is high, throughput collapses, or the request times out. | Do not force it. Test q8 KV only as a consistently applied policy, or mark the candidate operationally ineligible. |
| The 30B MoE model is marginal at 64K. | `ollama ps` shows the right context but memory pressure or swap is high. | Use the measured q8 or 32K diagnostic result, but do not present 32K as OpenCode-compliant. |
| Disk fills during a pull. | `df -h` free space drops unexpectedly. | Keep only the 9B baseline and one new candidate. Stop and reclaim before the next pull. |
| Reasoning text corrupts JSON extraction. | `unparseable` rises despite otherwise valid answers. | Use the balanced scanner, inspect raw responses, and adjust only the prompt or model-specific reasoning fields. |
| A valid JSON patch is truncated after parsing. | `finish_reason=length` and unexpected truncation despite a valid `files` map. | Treat the parsed map as valid, record the finish reason, and rerun the whole comparison at a higher token budget if the answer was semantically incomplete. |
| Streaming or `stream_options` is unsupported by another compatible server. | HTTP 400 or malformed SSE. | Remove the unsupported field in configuration or endpoint request policy. Do not silently change model behavior. |
| The evaluator times out during a long reasoning response. | `failure.kind=timeout` and a 3600-second wall time. | Inspect token rate and context. Do not automatically retry or classify it as quality 0. |
| Hidden tests leak into prompts. | A hidden sentinel appears in `prompt` or `response_raw` before the model runs. | Keep `include_hidden=False` as the default and add a regression test. |
| The suite hash ignores hidden changes. | Two materially different suites produce the same hash. | Include namespace-marked hidden bytes in `suite_hash()` and test the hash change. |
| The agent reaches the network or private files. | Sandbox preflight fails or an unexpected child request is observed. | Disable agent mode. Do not use an unsandboxed fallback. |
| OpenCode's global plugins or permissions leak into the run. | Unexpected tools or plugins appear in the transcript. | Use a verified isolated `OPENCODE_CONFIG`, `plugin: []`, and the OS sandbox. |
| The model modifies visible tests or unrelated files. | `unexpected_paths` is non-empty or the diff includes test edits. | Classify as `disallowed_path` and apply `unrelated_refactor` or `invented_file_or_api` during review. |
| Reviewer scoring is inconsistent. | Cloud double-scoring agreement is below 90 percent. | Revise the rubric and task wording before local runs. |
| One attempt gives a misleading quality result. | Repeated attempts have mixed scores. | Use three attempts and report majority success and instability. |
| A protocol change invalidates old runs. | Comparison reports a protocol mismatch. | Increment the protocol version and rerun candidates. Never force an incompatible comparison. |
| Peak memory is overstated by shared RSS. | Sampled RSS is higher than Ollama's reported size. | Label it as an approximate upper bound and show `ollama ps` separately. |
| A model requires an unsupported reasoning field. | HTTP 400 or ignored field. | Set the field to null in configuration and use model defaults. Record the actual settings. |
| A repair loop hides first-pass weakness. | Final score is 2 but initial score is 0. | Report initial and final results separately. Primary comparison uses repair disabled. |
| A real fixture contains sensitive or licence-sensitive data. | Redaction or licence review finds a problem. | Do not commit the fixture. Recreate the task from abstract behavior. |
| Raw results are lost before export. | `results/` is missing or ignored. | Export `summary.json`, `summary.md`, and `changes.patch` immediately after scoring. |
| The cloud window closes mid-implementation. | The cloud model starts returning an access or quota error. | Prioritize P0 and agent-mode work first, keep each change committed, and stop cloud experimentation before harness completion. |

---

## Part D: open questions

The recommended defaults are sufficient to begin implementation. These are the points that still require explicit confirmation.

## D.0 Findings from live probes on 2026-10-21

The following were measured directly on this machine while the `minimax-m3.1-flash:cloud`
window was open. They supersede the assumptions recorded elsewhere in this document where
they conflict. Each probe is reproducible with the scripts in `docs/cloud_run/`.

### D.0.1 The local Ollama endpoint ignores `think` and always returns a `reasoning` field

Measured with `docs/cloud_run/probe_reasoning.py` and `docs/cloud_run/probe_endpoint.py`
against `http://127.0.0.1:11434/v1/chat/completions`:

| Model | Request | Message keys returned | Reasoning characters |
|---|---|---|---:|
| `minimax-m3.1-flash:cloud` | no extra fields | `content`, `role` | none |
| `minimax-m3.1-flash:cloud` | `think: true` | `content`, `role` | none |
| `minimax-m3.1-flash:cloud` | `think: false` | `content`, `role` | none |
| `minimax-m3.1-flash:cloud` | `reasoning_effort: high` | `content`, `reasoning`, `role` | 44 |
| `qwen3.5:9b` | no extra fields | `content`, `reasoning`, `role` | 3,548 |
| `qwen3.5:9b` | `think: false` | `content`, `reasoning`, `role` | 511 |
| `qwen3.5:9b` | `reasoning_effort: high` | `content`, `reasoning`, `role` | 112 |

Conclusions that the implementation must respect:

1. **`think` is not a supported request parameter on this endpoint.** It is accepted
   without an error but has no effect. The harness must not send it and must not record
   it as a setting that was applied.
2. **`reasoning_effort` is accepted and is the only reasoning control that changes
   behaviour.** For `qwen3.5:9b` it reduced the reasoning output from 3,548 characters to
   112, a 31-fold reduction, while `think: false` only reduced it to 511. On the cloud
   model, `reasoning_effort` is what causes a `reasoning` field to appear at all.
3. **A `reasoning` field is present on some responses and absent on others, with no
   reliable pattern.** The extractor must treat its absence as normal, and must never
   require it. It must never be concatenated into `content`.
4. **`options.num_ctx` in the request body has no effect on the served context**, as
   expected, because the OpenAI-compatible endpoint exposes no per-request context
   control. The context must be set server-side. The `num_ctx` value in
   `config/models.json` is a declaration of the intended server setting, and it is
   evidence of nothing until `ollama ps` confirms it.

### D.0.2 The `qwen3.5:9b` context is already 262,144, not the 4K or 32K the VRAM default implies

`ollama ps` and `GET /api/ps` on this machine, with no `OLLAMA_CONTEXT_LENGTH` set:

```text
NAME          ID              SIZE     PROCESSOR    CONTEXT    RUNNER      UNTIL
qwen3.5:9b    c97eb11d70b1    15 GB    100% GPU     262144     llamacpp    3 minutes from now
```

```json
{"name":"qwen3.5:9b","size":15280436673,"details":{"family":"qwen35","parameter_size":"9.7B",
 "quantization_level":"Q4_K_M"},"size_vram":15280436673,"context_length":262144,"runner":"llamacpp"}
```

This contradicts the assumption in section 2.3 of the originating prompt that the default
would land on 4K or 32K. The observed value is the model's native 256K context. Two
consequences:

1. The harness must **read the served context from `ollama ps` or `/api/ps` and record
   it**, not assume it. A run whose observed context is below the model configuration's
   required context is operationally non-compliant and must be marked as such, exactly as
   section 3.2 of the original brief requires.
2. The 9B baseline is already far more viable on this machine than the brief assumed.

### D.0.3 The 9B model's VRAM footprint is roughly double its download size

The 6.6 GB on-disk model occupies **15,280,436,673 bytes (14.23 GiB) of VRAM**, not 6.6 GB.
The difference is the KV cache allocated for the 262,144-token context. This is a
first-order finding for the memory feasibility analysis in section B.14, and it is the
same mechanism that makes the 27B candidate fail on comparable hardware.

The rule this establishes: **for a long-context model on a 24 GB Mac, the context length
dominates the memory budget, and the weights are a minority of it.** Any candidate that
fits at 4K may fail at 64K. The evaluation protocol must therefore treat context length
as a first-class variable, not a fixed setting.

### D.0.4 `sandbox-exec` is available

`/usr/bin/sandbox-exec` is present and executable on this machine. Agent-mode isolation
does not need to be abandoned. The remaining requirement is a working profile that permits
the local Ollama connection while denying writes outside the temporary workspace, which
is a design task, not a feasibility question.

### D.0.5 `OLLAMA_KV_CACHE_TYPE` is supported

`ollama serve --help` on this machine lists `OLLAMA_KV_CACHE_TYPE` with the default `f16`,
alongside `OLLAMA_FLASH_ATTENTION`, `OLLAMA_CONTEXT_LENGTH`, `OLLAMA_NUM_PARALLEL`,
`OLLAMA_KEEP_ALIVE`, and `OLLAMA_MAX_LOADED_MODELS`. The `q8_0` and `q4_0` values must
still be confirmed by one measurement each, but the knob exists.

### D.0.6 The exact registry tags remain unconfirmed from this machine

`registry.ollama.ai` was not reachable from the execution sandbox, so the tags for
`qwen3.8:27b`, `qwen3-coder:30b`, and `gpt-oss:20b` could not be confirmed by querying
the registry directly. The proposed tags remain unverified. A single `ollama pull` attempt
remains the cheapest verification, and the spec's default already covers the failure case:
if a pull returns model-not-found, correct `config/models.json` only and record it.

### D.0.7 Independent evidence changes the candidate ranking

An independent measurement on a different 24 GB Apple Silicon machine reports that
`qwen3.8:27b` **runs out of GPU memory when a 20K-token prompt arrives**, and that
`gpt-oss:20b` loads fully onto the GPU. This is not a measurement from this machine and
must be re-verified here, but it is a strong prior that the dense 27B candidate is the
most likely of the three to be ineligible on this hardware, while `gpt-oss:20b` is the
most likely to fit.

The practical consequence for sequencing: **test `gpt-oss:20b` first**, not last. It is
the smallest of the new downloads at 14 GB, it is the most likely to fit at the 64K context
that OpenCode requires, and it is the candidate most likely to be usable for daily work.
`qwen3.8:27b` should be attempted only after the harness is proven, and its failure mode
on 24 GB hardware is a foreseeable memory-limit result rather than a quality result.

This also changes the interpretation of the "Qwen3.8 clearly wins difficult tasks"
outcome in the original plan. On this hardware, a 27B model that cannot hold a 64K
context is not a candidate for daily OpenCode use at all, regardless of its benchmark
quality. Quality ranking and operational eligibility must be reported as two separate
axes, and a model that is ineligible on the second axis is excluded from the first.

### D.0.8 `OPENCODE_CONFIG` is additive, and a filtered model query is the isolation mechanism

Measured with `opencode models` on this machine, OpenCode v1.18.35:

| Test | Result |
|---|---|
| `opencode models probe-only-provider` with no `OPENCODE_CONFIG` | `Error: Provider not found: probe-only-provider` |
| `opencode models probe-only-provider` with `OPENCODE_CONFIG` set to a temp file | `probe-only-provider/qwen3.5:9b` |
| `opencode models` with `OPENCODE_CONFIG` set to a temp file | 91 models; the temp provider is **absent**, but `ollama-local/qwen3.5:9b` and all five `featherless` models are **present** |

Conclusions:

1. **`OPENCODE_CONFIG` is honoured.** A provider defined only in the temp file is usable
   when the variable is set.
2. **It is additive, not a replacement.** The temp provider is merged with the user's
   global config, so `ollama-local` and `featherless` remain reachable. The spec's
   earlier assumption of replacement semantics was wrong.
3. **The full unfiltered listing is not a reliable indicator of what is loaded.** The
   temp provider is absent from the 91-model list yet resolvable by name. The listing is
   evidently assembled from a different source than the provider registry the filtered
   query uses. The harness must therefore verify a model by **resolving it explicitly**
   and confirming that a request succeeds, never by checking that it appears in a
   listing.
4. **Agent mode can target one model deterministically** by passing
   `opencode run --model probe-only-provider/qwen3.5:9b` with `OPENCODE_CONFIG` pointing
   at a generated config, and by selecting the model with a filtered query. This is
   sufficient for a controlled evaluation. It is **not** sufficient for isolation, because
   the user's other providers remain configured and reachable.
5. **`"plugin": []` was accepted** in the temp config without error. The user's global
   `tokentracker.js` plugin, which shells out to
   `/Users/jacklee/.tokentracker/bin/notify.cjs` on every `session.updated` event, sits in
   the global plugin directory and therefore still loads. The harness must not rely on
   `"plugin": []` in an `OPENCODE_CONFIG` file to suppress global plugins. Isolation of
   the global plugin directory requires running OpenCode with a redirected
   `XDG_CONFIG_HOME` or an equivalent, which remains to be verified. Until that is
   verified, agent mode must record that global plugins are active.

The remaining agent-mode risk is therefore narrower than the spec assumed: model
targeting is solved, sandboxing is available, and only global plugin and config
directory isolation remain unverified.

### D.0.9 The cloud ceiling reference: 10/10 validation passing

The full ten-task repo suite was run against `minimax-m3.1-flash:cloud` on 2026-10-21,
using the existing `evaluate.make_prompt` and `evaluate.execute_repo` functions unchanged.
One attempt per task, `max_tokens: 8192`, no repair loop, no manual scoring. Raw results
are in `docs/cloud_run/ceiling_suite.json`; the driver is `docs/cloud_run/ceiling_suite.py`.

| Task | Category | Validation | Seconds | Content chars | Reasoning chars |
|---|---|---|---:|---:|---:|
| `config-parse` | python_implementation | pass | 46.2 | 1,644 | 11,415 |
| `result-summary` | python_implementation | pass | 47.8 | 596 | 9,673 |
| `cache-leak` | python_debugging | pass | 52.7 | 238 | 18,288 |
| `retry-final` | python_debugging | pass | 15.4 | 366 | 2,082 |
| `score-tests` | unit_testing | pass | 35.2 | 1,247 | 14,248 |
| `web-search` | typescript_web | pass | 38.9 | 1,011 | 10,002 |
| `java-names` | java | pass | 12.8 | 757 | 1,290 |
| `api-key` | multi_file | pass | 9.8 | 204 | 816 |
| `user-validation` | refactoring | pass | 15.4 | 535 | 1,090 |
| `task-loader` | implementation_document | pass | 96.9 | 2,416 | 22,250 |

**10/10 objective validation passing, every category at 1/1, zero parse failures, zero
timeouts, and every `finish_reason` of `stop`.**

For comparison, the historical Qwen2.5-Coder-7B run in `results/qwen25_7b` passed 4/10 on
the same suite with `max_tokens: 1024`. The gap between 4/10 and 10/10 is therefore
attributable to model capability, not to the suite being mis-specified, and the suite is
capable of distinguishing a weak model from a strong one.

Three conclusions for the implementation:

1. **The suite is not saturated and not broken.** A strong model scores full marks, so a
   candidate scoring lower is genuinely weaker on these tasks. This validates the
   ceiling-reference role the spec assigned to the cloud model.
2. **`max_tokens: 1024` is the binding constraint on the 7B run, not just the model.**
   Every task in the ceiling run needed between 238 and 3,602 completion tokens, and the
   reasoning channel alone ran to 22,250 characters. The harness default of 1024 is
   below the requirement for at least half the suite. A candidate evaluated at 1024
   tokens must never be compared against one evaluated at 8192, and the comparison key
   must treat `max_tokens` as a first-class incompatible field, exactly as section B.5.3
   requires. **Every local candidate must be evaluated at the same generous budget**, and
   that budget must be recorded.
3. **The reasoning channel is not separable from the answer budget.** On the hardest task
   the reasoning was roughly nine times longer than the answer. If a harness discards
   reasoning but charges it against `max_tokens`, a thinking model can exhaust its budget
   before emitting any answer, which is exactly the "truncated" failure mode that section
   B.2.6 is designed to detect. The harness must record reasoning length separately so a
   truncation caused by reasoning exhaustion is distinguishable from a truncation caused
   by an over-long answer.

This run is calibration evidence, not a candidate result. It is a cloud model, so it
establishes the ceiling and the rubric calibration, and it says nothing about which local
model is best. The manual 0/1/2 scores for this run are still null, and a reviewer must
supply them before the ceiling is used as a rubric anchor.

### D.0.10 Agent-driven repository mode is feasible and works end to end

The single largest unknown in this specification was whether agent mode could be built at
all on this machine. It can. A full agent-mode run was executed on 2026-10-21 using
`minimax-m3.1-flash:cloud` as both the harness model and the OpenCode model, against a
temporary copy of the `result-summary` fixture. The driver is
`docs/cloud_run/agent_probe.py` and the transcript is
`docs/cloud_run/ocprobe/agent_result-summary.log`.

| Observation | Result |
|---|---|
| `opencode run` exit code | 0 |
| Wall clock | 447.6 seconds for one task |
| Harness validation after the agent finished | `python3 -m unittest discover -s tests -v` exit 0, **passing** |
| Files changed relative to the fixture | `summary.py` modified, nothing else created or touched |
| Tool calls in the transcript | 6 `bash`, 2 `read`, 1 `write` |
| Token accounting in the transcript | `tokens` with `input`, `output`, `reasoning`, and `cache.write` / `cache.read` present in the JSON stream |
| `cost` field in the transcript | 0, for the cloud model |

The agent's own narration confirms it behaved like a developer rather than a text
completer. It began by exploring the directory, read both the implementation and the
test file, stated "Now I understand the requirements", implemented the function, then
discovered that `unittest discover` did not work in this layout and said so: "No pytest
and `tests/` isn't a package. Let me run the test file directly". It then ran the tests,
confirmed they passed, and proceeded to verify additional edge cases before reporting the
implementation. Only `summary.py` was modified.

This settles three design questions that section B.8 had to specify blind:

1. **Model targeting works.** The agent used the provider generated into
   `docs/cloud_run/ocprobe/agent_opencode.json` and addressed it as
   `probe-only-provider/minimax-m3.1-flash:cloud`, exactly as section D.0.8 established.
2. **The transcript format is sufficient.** `opencode run --format json` emits text
   events, tool events, file events, and a `tokens` object per message, including
   `cache.read` and `cache.write`. The token accounting the spec wanted for agent mode
   is therefore available without a custom telemetry mechanism, and `cost` is present
   for models that report it.
3. **The allowlist enforcement point works.** Comparing the workspace tree against the
   fixture after the run identified exactly one modified file and no new files, so a
   whole-tree comparison against the pristine fixture is sufficient to enforce the
   allowlist in agent mode. This is the check section B.8.6 calls for.

Two limits remain, and they are not defects in agent mode itself:

- **A single agent task took 447.6 seconds**, against a JSON repo-mode attempt of 47.8
  seconds for the same task. Agent mode is roughly an order of magnitude slower, because
  it makes many round trips and re-reads context. A full ten-task agent run therefore
  costs far more wall clock than a JSON run, and the protocol must budget for that. On a
  local 27B model, which is slower still, a full agent suite may not complete in a
  reasonable time, which is a reason to keep agent mode to a representative subset of
  tasks rather than the whole suite.
- **The agent discovered a real environment quirk** (`unittest discover` not working
  against `tests/` without a package marker) and adapted its command. A future harness
  must capture the agent's *actual* commands, not assume it ran the task's declared
  validation command, or the two may diverge. The declared validation command remains
  the authority for the pass or fail verdict.

## D.1 Must be answered before implementation or the first candidate pull

| Question | Recommended default |
|---|---|
| Are `qwen3.8:27b` and `qwen3-coder:30b` the exact registry tags and served IDs? | **Still open.** The registry was unreachable from the sandbox (see D.0.6). Use the supplied proposed tags. If a pull returns model-not-found, update `config/models.json` only and record the correction. |
| Does OpenCode v1.18.35 honor `OPENCODE_CONFIG` as a replacement or additive config source? | **Resolved** by measurement (see D.0.8). It is honoured and is **additive**. A temp config supplies a target provider but does not remove the user's existing providers or global plugins. Model targeting is solved; directory isolation is not. |
| Is `/usr/bin/sandbox-exec` available and usable for local Ollama access plus home isolation on this machine? | **Partly resolved.** The binary is present and executable (see D.0.4). A working profile is still required. If no profile can permit the local Ollama connection while denying writes outside the workspace, do not run an unsandboxed automated agent mode. |
| Which reasoning fields are actually accepted by the Ollama OpenAI-compatible endpoint for each model? | **Resolved** by measurement (see D.0.1). `think` is accepted and ignored. `reasoning_effort` is the only control that changes behaviour. `options.num_ctx` in the request body is ignored. Set only `reasoning_effort`, and only where a measurement shows it helps. |
| Should the primary local comparison use f16 or q8 KV cache? | **Partly resolved.** The `OLLAMA_KV_CACHE_TYPE` knob exists with default `f16` (see D.0.5). Start with the server default and record it. If q8 is needed for 64K feasibility, use q8 for every primary local candidate and label the policy. |
| Is the local OpenCode provider name guaranteed to remain `ollama-local`? | Keep the existing name and generate a temporary provider with the same name from `config/models.json`. |
| Should tracked run exports include complete patches? | Yes, because the fixtures are small and the patches are needed for review. Do not track raw model responses by default. |

## D.2 Can be decided later

| Question | Recommended default |
|---|---|
| Which two real repositories should supply the new tasks? | Prefer Auto Trader plus Dynamic Task Router if their licences permit; otherwise choose by the redaction and isolation checklist. |
| Should the cloud model receive a separate score-weighting role? | No. Treat it only as a ceiling and agent-mode reference. |
| Should response mode receive three attempts? | Yes, because it is inexpensive relative to local inference and reveals answer stability. |
| Should agent mode receive three attempts? | No initially. Run one, then add three attempts only for candidates within the quality tie band. |
| How long should raw local results be retained locally? | Until the final decision is committed, then archive them outside the repository if desired. Do not commit raw responses automatically. |
| What dataset would be used if fine-tuning is triggered? | Do not design it during model selection. First document the shared root cause and write a pre-registered dataset and evaluation plan. |
| Should the 9B baseline remain installed after selection? | Keep it if it is the routine fallback or useful cloud-outage fallback. Its disk cost is modest compared with the larger candidates. |
| Should the final report include raw cloud transcripts? | No by default. Commit summaries, scores, and patches. Keep transcripts local unless they are needed to resolve a disputed result. |

With those defaults accepted, implementation can begin without further design decisions, and the large-model pull can wait until the P0 and P1 release gate is complete.
