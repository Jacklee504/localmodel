"""Shared primitives for the local-model evaluator.

Configuration, endpoint access, response extraction, failure classification, and
result schema live here so that `evaluate.py` stays a readable command surface.
"""

import json
import os
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SCHEMA_VERSION = 2
PROTOCOL_VERSION = 2
PROMPT_VERSION = "repo-json-v2"

FAILURE_KINDS = (
    "http_error",
    "timeout",
    "truncated",
    "unparseable",
    "protocol_violation",
    "disallowed_path",
    "validation_failed",
    "none",
)

REQUIREMENT_FAILURES = (
    "ignored_requirement",
    "unnecessary_dependency",
    "public_api_changed",
    "unrelated_refactor",
    "invented_file_or_api",
    "excessive_complexity",
    "incomplete_implementation",
    "output_corrupted",
)

MODEL_FIELDS = {
    "name", "provider", "base_url", "model", "api_key_env", "path", "quantization",
    "runtime", "generation", "context", "download_size", "ollama", "opencode", "notes",
}
GENERATION_COMMON_FIELDS = {"max_tokens", "temperature", "top_p"}
GENERATION_MODEL_FIELDS = {"reasoning_effort", "think", "preserve_thinking"}
CONTEXT_FIELDS = {"num_ctx", "model_max", "kv_cache_type"}
OLLAMA_FIELDS = {"pull_command", "launch_command", "serve_command"}
OPENCODE_FIELDS = {"provider", "model"}


class EvaluationError(Exception):
    """A condition the operator must fix before a run can be meaningful."""


class ModelFailure(Exception):
    """A classified per-task failure."""

    def __init__(self, kind, message):
        super().__init__(message)
        if kind not in FAILURE_KINDS:
            raise ValueError(f"Unknown failure kind: {kind}")
        self.kind = kind
        self.message = message


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_model_config(path, key):
    data = read_json(path)
    version = data.get("schema_version")
    if version != 1:
        raise EvaluationError(
            f"Unsupported config schema_version {version!r}. This harness supports version 1."
        )
    models = data.get("models")
    if not isinstance(models, dict):
        raise EvaluationError("config/models.json must contain a 'models' object")
    if key not in models:
        known = ", ".join(sorted(models))
        raise EvaluationError(f"Unknown model {key!r}. Configured models: {known}")
    config = models[key]
    validate_model_config(config, key)
    return config


def validate_model_config(config, key):
    unknown = set(config) - MODEL_FIELDS
    if unknown:
        raise EvaluationError(f"Model {key!r} has unknown fields: {', '.join(sorted(unknown))}")
    provider = config.get("provider")
    if provider not in ("mlx", "openai_compatible"):
        raise EvaluationError(f"Model {key!r} has unsupported provider {provider!r}")
    if provider == "mlx":
        if not config.get("path"):
            raise EvaluationError(f"Model {key!r} uses provider 'mlx' and requires a 'path'")
        if config.get("base_url") or config.get("model"):
            raise EvaluationError(
                f"Model {key!r} uses provider 'mlx' and must not set base_url or model"
            )
    else:
        for required in ("base_url", "model"):
            if not config.get(required):
                raise EvaluationError(
                    f"Model {key!r} uses provider 'openai_compatible' and requires {required!r}"
                )
        if config.get("path"):
            raise EvaluationError(
                f"Model {key!r} uses provider 'openai_compatible' and must not set 'path'"
            )
        if not str(config["base_url"]).startswith(("http://", "https://")):
            raise EvaluationError(f"Model {key!r} base_url must be an absolute http or https URL")

    generation = config.get("generation") or {}
    if set(generation) - {"common", "model"}:
        raise EvaluationError(f"Model {key!r} generation has unknown sections")
    common = generation.get("common") or {}
    if set(common) - GENERATION_COMMON_FIELDS:
        raise EvaluationError(f"Model {key!r} generation.common has unknown fields")
    model_settings = generation.get("model") or {}
    if set(model_settings) - GENERATION_MODEL_FIELDS:
        raise EvaluationError(f"Model {key!r} generation.model has unknown fields")
    if "max_tokens" in common and common["max_tokens"] < 1:
        raise EvaluationError(f"Model {key!r} generation.common.max_tokens must be positive")
    for name in ("temperature", "top_p"):
        if name in common and common[name] is not None:
            upper = 2 if name == "temperature" else 1
            if not 0 <= common[name] <= upper:
                raise EvaluationError(
                    f"Model {key!r} generation.common.{name} must be between 0 and {upper}"
                )
    effort = model_settings.get("reasoning_effort")
    if effort is not None and effort not in ("low", "medium", "high"):
        raise EvaluationError(f"Model {key!r} reasoning_effort must be low, medium, high, or null")

    context = config.get("context") or {}
    if set(context) - CONTEXT_FIELDS:
        raise EvaluationError(f"Model {key!r} context has unknown fields")
    for name in ("num_ctx", "model_max"):
        if context.get(name) is not None and context[name] < 1:
            raise EvaluationError(f"Model {key!r} context.{name} must be positive")

    ollama = config.get("ollama") or {}
    if set(ollama) - OLLAMA_FIELDS:
        raise EvaluationError(f"Model {key!r} ollama has unknown fields")
    opencode = config.get("opencode") or {}
    if set(opencode) - OPENCODE_FIELDS:
        raise EvaluationError(f"Model {key!r} opencode has unknown fields")


def resolve_generation(config, max_tokens_override=None):
    """Return (common, model_settings) with the effective values applied."""
    generation = config.get("generation") or {}
    common = dict(generation.get("common") or {})
    model_settings = dict(generation.get("model") or {})
    if max_tokens_override is not None:
        common["max_tokens"] = max_tokens_override
    common.setdefault("max_tokens", 4096)
    common.setdefault("temperature", 0.2)
    common.setdefault("top_p", 0.9)
    return common, model_settings


# --------------------------------------------------------------------------
# Response extraction
# --------------------------------------------------------------------------

REASONING_BLOCK = re.compile(r"<(think|thinking)\b[^>]*>.*?</\1\s*>", re.IGNORECASE | re.DOTALL)
LEADING_REASONING_BLOCK = re.compile(r"^\s*<(think|thinking)\b[^>]*>.*", re.IGNORECASE | re.DOTALL)


def text_from_parts(parts):
    """Concatenate the text of a content part list without adding separators."""
    if isinstance(parts, str):
        return parts
    if not isinstance(parts, list):
        return ""
    pieces = []
    for part in parts:
        if isinstance(part, str):
            pieces.append(part)
        elif isinstance(part, dict):
            if isinstance(part.get("text"), str):
                pieces.append(part["text"])
            elif part.get("type") in ("text", "output_text", "input_text"):
                if isinstance(part.get("value"), str):
                    pieces.append(part["value"])
    return "".join(pieces)


def extract_content(message):
    """Return the answer text from an assistant message, or an empty string."""
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if isinstance(content, str):
        return content
    text = text_from_parts(content)
    if text:
        return text
    for field in ("output_text", "answer", "response"):
        value = message.get(field)
        if isinstance(value, str) and value:
            return value
        if isinstance(value, list):
            text = text_from_parts(value)
            if text:
                return text
    nested = message.get("message")
    if isinstance(nested, dict):
        return extract_content(nested)
    return ""


def extract_reasoning(message):
    """Return the reasoning text from an assistant message, or an empty string."""
    if not isinstance(message, dict):
        return ""
    for field in ("reasoning_content", "reasoning", "thinking"):
        value = message.get(field)
        if isinstance(value, str) and value:
            return value
        if isinstance(value, list):
            text = text_from_parts(value)
            if text:
                return text
    return ""


def strip_reasoning(text):
    """Remove complete and leading reasoning blocks, preserving everything else."""
    cleaned = REASONING_BLOCK.sub("", text)
    cleaned = LEADING_REASONING_BLOCK.sub("", cleaned)
    return cleaned.strip()


def balanced_spans(text):
    """Return the outermost balanced {...} spans, ignoring braces inside JSON strings."""
    spans = []
    depth = 0
    start = None
    in_string = False
    escaped = False
    for index, character in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
        elif character == "{":
            if depth == 0:
                start = index
            depth += 1
        elif character == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start is not None:
                    spans.append(text[start:index + 1])
                    start = None
    return spans


def strip_code_fence(text):
    """Remove a single outer code fence including an optional language tag."""
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    match = re.match(r"^```[A-Za-z0-9_+-]*\s*\n(.*?)\n?```\s*$", stripped, re.DOTALL)
    if match:
        return match.group(1)
    return re.sub(r"^```[A-Za-z0-9_+-]*\s*", "", stripped)


def find_files_object(text):
    """Return (files_dict, object_dict) parsed from an answer, or (None, None)."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")
    cleaned = strip_reasoning(normalized)
    candidates = [
        normalized,
        strip_code_fence(normalized),
        cleaned,
        strip_code_fence(cleaned),
    ]
    candidates.extend(balanced_spans(cleaned))
    candidates.extend(balanced_spans(normalized))

    first_object = None
    for candidate in candidates:
        candidate = candidate.strip()
        if not candidate:
            continue
        try:
            parsed = json.loads(candidate)
        except (ValueError, TypeError):
            continue
        if not isinstance(parsed, dict):
            continue
        if first_object is None:
            first_object = parsed
        if "files" in parsed:
            return parsed["files"], parsed
    return None, first_object


# --------------------------------------------------------------------------
# Endpoint access
# --------------------------------------------------------------------------

def build_request_body(config, common, model_settings, prompt, stream=True):
    body = {
        "model": config["model"],
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": common["max_tokens"],
        "stream": stream,
    }
    if stream:
        body["stream_options"] = {"include_usage": True}
    for name in ("temperature", "top_p"):
        if common.get(name) is not None:
            body[name] = common[name]
    for name in ("reasoning_effort", "think", "preserve_thinking"):
        if model_settings.get(name) is not None:
            body[name] = model_settings[name]
    return body


def request_headers(config):
    headers = {"Content-Type": "application/json"}
    api_key_env = config.get("api_key_env")
    if api_key_env:
        if api_key_env not in os.environ:
            raise EvaluationError(f"Environment variable {api_key_env!r} is not set")
        headers["Authorization"] = "Bearer " + os.environ[api_key_env]
    return headers


def call_endpoint(config, common, model_settings, prompt, timeout_seconds):
    """Call the endpoint and return (answer, reasoning, timings)."""
    url = config["base_url"].rstrip("/") + "/chat/completions"
    body = json.dumps(build_request_body(config, common, model_settings, prompt)).encode()
    headers = request_headers(config)
    headers["Accept"] = "text/event-stream"
    request = urllib.request.Request(url, body, headers)

    started = time.perf_counter()
    first_token = None
    answer_parts = []
    reasoning_parts = []
    finish_reason = None
    usage = None
    warning = None

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            content_type = response.headers.get("Content-Type", "")
            if "text/event-stream" in content_type:
                for raw_line in response:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line or not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if payload == "[DONE]":
                        break
                    try:
                        event = json.loads(payload)
                    except ValueError:
                        warning = "Ignored a malformed server-sent event"
                        continue
                    for choice in event.get("choices") or []:
                        delta = choice.get("delta") or {}
                        text = extract_content(delta)
                        thought = extract_reasoning(delta)
                        if text:
                            answer_parts.append(text)
                            if first_token is None:
                                first_token = time.perf_counter() - started
                        if thought:
                            reasoning_parts.append(thought)
                            if first_token is None:
                                first_token = time.perf_counter() - started
                        if choice.get("finish_reason"):
                            finish_reason = choice["finish_reason"]
                    if event.get("usage"):
                        usage = event["usage"]
            else:
                result = json.load(response)
                choices = result.get("choices") or [{}]
                message = choices[0].get("message") or {}
                answer_parts.append(extract_content(message))
                reasoning_parts.append(extract_reasoning(message))
                finish_reason = choices[0].get("finish_reason")
                usage = result.get("usage")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        raise ModelFailure("http_error", f"HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, TimeoutError):
            raise ModelFailure("timeout", f"Request exceeded {timeout_seconds}s") from exc
        raise ModelFailure("http_error", f"Connection failed: {exc.reason}") from exc
    except TimeoutError as exc:
        raise ModelFailure("timeout", f"Request exceeded {timeout_seconds}s") from exc
    except OSError as exc:
        raise ModelFailure("http_error", f"Transport failure: {exc}") from exc

    elapsed = time.perf_counter() - started
    answer = "".join(answer_parts)
    reasoning = "".join(reasoning_parts)
    completion_tokens = (usage or {}).get("completion_tokens")
    prompt_tokens = (usage or {}).get("prompt_tokens")
    timings = {
        "generation_seconds": round(elapsed, 3),
        "first_token_seconds": round(first_token, 3) if first_token is not None else None,
        "tokens_generated": completion_tokens,
        "prompt_tokens": prompt_tokens,
        "tokens_per_second": (
            round(completion_tokens / elapsed, 2) if completion_tokens and elapsed else None
        ),
        "reasoning_chars": len(reasoning),
        "answer_chars": len(answer),
        "finish_reason": finish_reason,
        "timeout_seconds": timeout_seconds,
        "peak_memory_bytes": None,
        "warning": warning,
    }
    return answer, reasoning, timings


def observe_ollama(base_url, served_model):
    """Read the served context and VRAM from the local Ollama server."""
    root = base_url.rstrip("/")
    for suffix in ("/../api/ps", "/api/ps"):
        try:
            request = urllib.request.Request(
                root + suffix, headers={"Accept": "application/json"}
            )
            with urllib.request.urlopen(request, timeout=10) as response:
                payload = json.load(response)
        except Exception:
            continue
        for entry in payload.get("models") or []:
            if entry.get("name") == served_model or entry.get("model") == served_model:
                return {
                    "observed_context_tokens": entry.get("context_length"),
                    "size_vram_bytes": entry.get("size_vram"),
                    "size_bytes": entry.get("size"),
                    "runner": entry.get("runner"),
                    "quantization_level": (entry.get("details") or {}).get("quantization_level"),
                    "source": "ollama api/ps",
                }
    return {"observed_context_tokens": None, "source": "ollama api/ps (model not resident)"}


def git_state():
    def run(*args):
        try:
            result = subprocess.run(
                ["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=30
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except (OSError, subprocess.SubprocessError):
            return None
    commit = run("rev-parse", "HEAD")
    dirty = run("status", "--porcelain")
    return commit, bool(dirty)


def disk_free_bytes():
    try:
        return shutil.disk_usage(ROOT).free
    except OSError:
        return None
