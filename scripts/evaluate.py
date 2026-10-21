"""Small local-model evaluator for response, repository, and agent repository tasks."""

import argparse
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import evalcore
import evalcompare
import evalrepair
import evalreport
from evalcore import (
    EvaluationError,
    ModelFailure,
    PROTOCOL_VERSION,
    PROMPT_VERSION,
    REQUIREMENT_FAILURES,
    SCHEMA_VERSION,
    FAILURE_KINDS,
)

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "tasks/core.json"
MODELS = ROOT / "config/models.json"
SUITES = ROOT / "config/suites.json"
RESULTS = ROOT / "results"
HIDDEN_DIR = "hidden"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def safe_name(value):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", value):
        raise EvaluationError(f"Invalid name: {value}")
    return value


def safe_file(value):
    path = Path(value)
    if path.is_absolute() or not path.parts or any(part in (".", "..") for part in path.parts):
        raise EvaluationError(f"Unsafe fixture path: {value}")
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


def load_suites():
    data = evalcore.read_json(SUITES)
    version = data.get("schema_version")
    if version != 1:
        raise EvaluationError(
            f"Unsupported suites schema_version {version!r}. This harness supports version 1."
        )
    suites = data.get("suites")
    if not isinstance(suites, dict) or not suites:
        raise EvaluationError("config/suites.json must contain a 'suites' object")
    return suites


def resolve_suite(name, tasks):
    """Return the tasks in a named suite, preserving the suite's declared order."""
    suites = load_suites()
    if name not in suites:
        known = ", ".join(sorted(suites))
        raise EvaluationError(f"Unknown suite {name!r}. Available suites: {known}")
    entry = suites[name]
    wanted = entry.get("tasks") or []
    if "*" in wanted:
        return list(tasks)
    available = {task["id"] for task in tasks}
    missing = [task_id for task_id in wanted if task_id not in available]
    if missing:
        raise EvaluationError(
            f"Suite {name!r} refers to tasks that do not exist: {', '.join(missing)}"
        )
    by_id = {task["id"]: task for task in tasks}
    return [by_id[task_id] for task_id in wanted]


def suite_hash(tasks):
    digest = hashlib.sha256(SUITE.read_bytes())
    for task in tasks:
        for namespace, include_hidden in (("public", False), ("hidden", True)):
            for name, body in fixture_files(task, include_hidden=include_hidden).items():
                digest.update(task["id"].encode())
                digest.update(namespace.encode())
                digest.update(name.encode())
                digest.update(body.encode())
    return digest.hexdigest()


def fixture_files(task, include_hidden=False):
    fixture = ROOT / "tasks/fixtures" / task["id"]
    files = {}
    for path in sorted(fixture.rglob("*")):
        if "__pycache__" in path.parts or path.suffix in (".pyc", ".class"):
            continue
        relative = path.relative_to(fixture)
        if not include_hidden and relative.parts and relative.parts[0] == HIDDEN_DIR:
            continue
        if path.is_symlink():
            raise ValueError(f"Symlink in fixture: {path}")
        if path.is_file():
            files[str(relative)] = path.read_text(encoding="utf-8")
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
    """A configured model, reachable through either MLX or an OpenAI-compatible endpoint."""

    def __init__(self, config):
        self.config = config
        self.loaded = None
        if config["provider"] == "mlx":
            path = Path(config["path"])
            if not path.is_absolute():
                path = ROOT / path
            if not (path / "config.json").is_file():
                raise EvaluationError(f"Local model unavailable: {path}")
            from mlx_lm import load
            self.loaded = load(str(path))

    def generate(self, prompt, common, model_settings, timeout_seconds):
        """Return (answer, reasoning, timings). Raises ModelFailure on a classified failure."""
        if self.loaded:
            from mlx_lm import generate

            start = time.perf_counter()
            model, tokenizer = self.loaded
            chat = tokenizer.apply_chat_template(
                [{"role": "user", "content": prompt}], tokenize=False, add_generation_prompt=True
            )
            answer = generate(
                model, tokenizer, chat, max_tokens=common["max_tokens"], verbose=False
            )
            elapsed = time.perf_counter() - start
            tokens = len(tokenizer.encode(answer))
            timings = {
                "generation_seconds": round(elapsed, 3),
                "first_token_seconds": None,
                "tokens_generated": tokens,
                "prompt_tokens": None,
                "tokens_per_second": round(tokens / elapsed, 2) if tokens and elapsed else None,
                "reasoning_chars": 0,
                "answer_chars": len(answer),
                "finish_reason": None,
                "timeout_seconds": timeout_seconds,
                "peak_memory_bytes": None,
                "warning": "MLX path applies max_tokens only; temperature and top_p are not applied",
            }
            return answer, "", timings
        return evalcore.call_endpoint(
            self.config, common, model_settings, prompt, timeout_seconds
        )


def parse_changes(answer, editable):
    """Return the changes map, raising ModelFailure with a classified kind."""
    files, first_object = evalcore.find_files_object(answer)
    if files is None:
        if first_object is not None:
            raise ModelFailure("protocol_violation", "Response JSON has no 'files' key")
        raise ModelFailure("unparseable", "No JSON object could be recovered from the response")
    if not isinstance(files, dict) or not files:
        raise ModelFailure("protocol_violation", "Response has no changed files")
    for name, body in files.items():
        if name not in editable:
            raise ModelFailure("disallowed_path", f"Response changed a disallowed path: {name}")
        if not isinstance(body, str):
            raise ModelFailure("protocol_violation", f"File body for {name} is not a string")
    return files


def run_validation(commands, workspace):
    """Run the given validation commands in the workspace and collect their results."""
    checks = []
    for command in commands:
        try:
            process = subprocess.run(
                command,
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=120,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )
            checks.append(
                {
                    "command": command,
                    "exit_code": process.returncode,
                    "output": (process.stdout + process.stderr)[-16000:],
                }
            )
        except (OSError, subprocess.SubprocessError) as exc:
            checks.append({"command": command, "exit_code": None, "output": str(exc)})
    return checks


def execute_repo(task, answer, timings=None):
    """Apply the response to a temporary fixture copy and validate it."""
    changes = parse_changes(answer, set(task["editable"]))
    fixture = ROOT / "tasks/fixtures" / task["id"]
    with tempfile.TemporaryDirectory(prefix="local-coder-eval-") as directory:
        workspace = Path(directory) / "repo"
        shutil.copytree(
            fixture,
            workspace,
            symlinks=False,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.class"),
        )
        before = {name: (workspace / name).read_text(encoding="utf-8") for name in changes}
        for name, body in changes.items():
            (workspace / name).write_text(body, encoding="utf-8")
        diff = "".join(
            "".join(
                difflib.unified_diff(
                    before[name].splitlines(keepends=True),
                    body.splitlines(keepends=True),
                    fromfile="a/" + name,
                    tofile="b/" + name,
                )
            )
            for name, body in changes.items()
        )
        public = run_validation(task.get("validation") or [], workspace)
        withheld = run_validation(task.get("withheld_validation") or [], workspace)
        checks = public + withheld
        passed = bool(checks) and all(check["exit_code"] == 0 for check in checks)
        return {
            "changes": changes,
            "diff": diff,
            "validation": public,
            "withheld_validation": withheld,
            "validation_passed": passed,
        }


def build_agent_config(config, path):
    """Write a temporary OpenCode config that targets one specific model."""
    opencode = config.get("opencode") or {}
    provider_name = opencode.get("provider") or "ollama-local"
    served = opencode.get("model") or config.get("model")
    payload = {
        "$schema": "https://opencode.ai/config.json",
        "provider": {
            provider_name: {
                "npm": "@ai-sdk/openai-compatible",
                "name": f"Evaluation Provider {provider_name}",
                "options": {"baseURL": config["base_url"]},
                "models": {served: {"name": served}},
            }
        },
    }
    Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return f"{provider_name}/{served}"


def run_agent_task(task, config, timeout_seconds):
    """Run the agent on a fixture copy, then validate exactly as repo mode does."""
    fixture = ROOT / "tasks/fixtures" / task["id"]
    with tempfile.TemporaryDirectory(prefix="local-coder-agent-") as directory:
        workspace = Path(directory) / "repo"
        shutil.copytree(
            fixture,
            workspace,
            symlinks=False,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.class", HIDDEN_DIR),
        )
        agent = execute_agent(task, config, workspace, timeout_seconds)
        editable = set(task["editable"])
        before = {}
        for name in task["editable"]:
            source = fixture / name
            before[name] = source.read_text(encoding="utf-8") if source.is_file() else ""
        changes = {}
        for name in task["editable"]:
            target = workspace / name
            if target.is_file():
                changes[name] = target.read_text(encoding="utf-8", errors="replace")
        modified = []
        unexpected = []
        for path in sorted(workspace.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            relative = str(path.relative_to(workspace))
            if relative.startswith("."):
                continue
            source = fixture / relative
            current = path.read_text(encoding="utf-8", errors="replace")
            if not source.is_file():
                unexpected.append(relative)
            elif source.read_text(encoding="utf-8", errors="replace") != current:
                modified.append(relative)
        for name in list(modified):
            if name not in editable:
                modified.remove(name)
                unexpected.append(name)
        unexpected = [name for name in unexpected if name not in editable]
        untouched = sorted(editable - set(modified))
        diff = "".join(
            "".join(
                difflib.unified_diff(
                    before[name].splitlines(keepends=True),
                    changes.get(name, "").splitlines(keepends=True),
                    fromfile="a/" + name,
                    tofile="b/" + name,
                )
            )
            for name in task["editable"]
        )
        public = run_validation(task.get("validation") or [], workspace)
        hidden_source = fixture / HIDDEN_DIR
        if hidden_source.is_dir():
            shutil.copytree(hidden_source, workspace / HIDDEN_DIR, symlinks=False)
        withheld = run_validation(task.get("withheld_validation") or [], workspace)
        checks = public + withheld
        passed = bool(checks) and all(check["exit_code"] == 0 for check in checks)
        agent.update(
            {
                "changes": changes,
                "diff": diff,
                "modified_files": modified,
                "untouched_files": untouched,
                "unexpected_paths": unexpected,
                "validation": public,
                "withheld_validation": withheld,
                "validation_passed": passed,
            }
        )
        if unexpected:
            agent["failure_kind"] = "disallowed_path"
            agent["error"] = "Agent changed paths outside the allowlist: " + ", ".join(unexpected)
        return agent


def execute_agent(task, config, workspace, timeout_seconds):
    """Run the coding agent against a fixture copy and capture what it changed."""
    with tempfile.TemporaryDirectory(prefix="local-coder-agent-") as directory:
        agent_config = Path(directory) / "opencode.json"
        reference = build_agent_config(config, agent_config)
        message = (
            task["prompt"]
            + "\n\nWork directly in this directory. Edit only these files: "
            + ", ".join(task["editable"])
            + ". Make the change and run the tests yourself to confirm it works."
        )
        environment = {**os.environ, "OPENCODE_CONFIG": str(agent_config)}
        started = time.perf_counter()
        process = subprocess.run(
            [
                "opencode", "run", message,
                "--model", reference,
                "--dir", str(workspace),
                "--format", "json",
            ],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env=environment,
            cwd=str(workspace),
        )
        elapsed = round(time.perf_counter() - started, 3)
        transcript = process.stdout
        changes = {}
        for path in sorted(workspace.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            relative = str(path.relative_to(workspace))
            if relative.startswith("."):
                continue
            changes[relative] = path.read_text(encoding="utf-8", errors="replace")
        return {
            "exit_code": process.returncode,
            "agent_seconds": elapsed,
            "transcript_chars": len(transcript),
            "transcript": transcript[-40000:],
            "workspace_files": sorted(changes),
            "stderr": process.stderr[-4000:],
        }


def git_commit():
    return evalcore.git_state()[0]


def list_models(only=None):
    """Print the configured models and the commands needed to start each one."""
    data = read_json(MODELS)
    models = data.get("models", {})
    for key in sorted(models):
        if only and key != only:
            continue
        config = models[key]
        print(f"{key}: {config.get('name')}")
        print(f"  provider   {config.get('provider')}")
        served = config.get("model") or config.get("path")
        print(f"  served     {served}")
        context = config.get("context") or {}
        print(f"  context    {context.get('num_ctx') or 'server default'}"
              f" (model max {context.get('model_max') or 'unknown'})")
        generation = (config.get("generation") or {}).get("common") or {}
        print(f"  max_tokens {generation.get('max_tokens', 4096)}")
        for command_name in ("pull_command", "serve_command", "launch_command"):
            command = (config.get("ollama") or {}).get(command_name)
            if command:
                print(f"  {command_name.replace('_command', ''):11} {command}")
        if config.get("notes"):
            print(f"  notes      {config['notes']}")
        print()


def build_comparison_key(mode, task_ids, suite_digest, common, context_requirement, repair_attempts):
    """The strict key that decides whether two runs may be compared."""
    return {
        "protocol_version": PROTOCOL_VERSION,
        "mode": mode,
        "suite_sha256": suite_digest,
        "task_ids": list(task_ids),
        "prompt_version": PROMPT_VERSION,
        "generation": {
            "max_tokens": common["max_tokens"],
            "temperature": common.get("temperature"),
            "top_p": common.get("top_p"),
        },
        "context_requirement": context_requirement,
        "repair_attempts": repair_attempts,
    }


def build_metadata(args, config, common, model_settings, tasks, suite_digest, attempt_index, batch_id):
    commit, dirty = evalcore.git_state()
    required_context = (config.get("context") or {}).get("num_ctx")
    observed = {"observed_context_tokens": None, "source": "not observed"}
    if config["provider"] == "openai_compatible":
        observed = evalcore.observe_ollama(config["base_url"], config["model"])
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": args._run_id,
        "batch_id": batch_id,
        "attempt_index": attempt_index,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": commit,
        "git_dirty": dirty,
        "model_key": args.model,
        "model_config": config,
        "mode": args.mode,
        "suite": {
            "path": str(SUITE.relative_to(ROOT)),
            "sha256": suite_digest,
            "task_ids": [task["id"] for task in tasks],
        },
        "comparison_key": build_comparison_key(
            args.mode,
            [task["id"] for task in tasks],
            suite_digest,
            common,
            required_context,
            args.repair_attempts,
        ),
        "invocation": {"model": model_settings},
        "runtime": {
            "endpoint": config["base_url"].rstrip("/") + "/chat/completions"
            if config["provider"] == "openai_compatible"
            else None,
            "served_model": config.get("model"),
            "runtime_version": config.get("runtime"),
            "requested_context_tokens": required_context,
            "observed_context_tokens": observed.get("observed_context_tokens"),
            "context_source": observed.get("source"),
            "size_vram_bytes": observed.get("size_vram_bytes"),
            "kv_cache_type": (config.get("context") or {}).get("kv_cache_type") or "server_default",
        },
        "environment": {
            "disk_free_bytes": evalcore.disk_free_bytes(),
        },
    }


def run_attempt(args, config, tasks, suite_digest, attempt_index, batch_id):
    common, model_settings = evalcore.resolve_generation(config, args.max_tokens)
    directory = RESULTS / args.model / args._run_id
    directory.mkdir(parents=True, exist_ok=False)
    metadata = build_metadata(
        args, config, common, model_settings, tasks, suite_digest, attempt_index, batch_id
    )
    write_json(directory / "metadata.json", metadata)
    try:
        model = Model(config)
    except ImportError as exc:
        raise EvaluationError(f"Model runtime unavailable: {exc}") from exc

    for index, task in enumerate(tasks, 1):
        prompt = make_prompt(task, args.mode)
        started = time.perf_counter()
        record = {
            "id": task["id"],
            "category": task["category"],
            "mode": args.mode,
            "prompt": prompt,
            "response": None,
            "reasoning": None,
            "timings": None,
            "repo": None,
            "error": None,
            "failure_kind": "none",
            "manual": {
                "score": None,
                "notes": "",
                "requirement_failures": [],
                "failure_details": [],
                "additional_prompts": None,
                "reviewer": None,
            },
        }
        try:
            if args.mode == "agent":
                record["agent"] = run_agent_task(task, config, args.timeout_seconds)
                record["timings"] = {
                    "generation_seconds": record["agent"]["agent_seconds"],
                    "first_token_seconds": None,
                    "tokens_generated": None,
                    "prompt_tokens": None,
                    "tokens_per_second": None,
                    "reasoning_chars": 0,
                    "answer_chars": record["agent"]["transcript_chars"],
                    "finish_reason": None,
                    "timeout_seconds": args.timeout_seconds,
                    "peak_memory_bytes": None,
                    "warning": None,
                }
                if not record["agent"]["validation_passed"]:
                    record["failure_kind"] = record["agent"].get(
                        "failure_kind", "validation_failed"
                    )
                    if record["failure_kind"] == "disallowed_path":
                        record["error"] = record["agent"].get("error")
                    else:
                        record["failure_kind"] = "validation_failed"
            else:
                answer, reasoning, timings = model.generate(
                    prompt, common, model_settings, args.timeout_seconds
                )
                record["response"] = answer
                record["reasoning"] = reasoning or None
                record["timings"] = timings
                if args.mode == "repo":
                    record["repo"] = execute_repo(task, answer, timings)
                    if not record["repo"]["validation_passed"]:
                        record["failure_kind"] = "validation_failed"
        except ModelFailure as failure:
            record["failure_kind"] = failure.kind
            record["error"] = failure.message
        except subprocess.TimeoutExpired:
            record["failure_kind"] = "timeout"
            record["error"] = f"Agent exceeded {args.timeout_seconds}s"
        except subprocess.SubprocessError as exc:
            record["failure_kind"] = "http_error"
            record["error"] = f"Agent invocation failed: {exc}"
        record["wall_seconds"] = round(time.perf_counter() - started, 3)
        if (
            args.mode == "repo"
            and args.repair_attempts
            and record["failure_kind"] in ("validation_failed", "unparseable", "protocol_violation")
        ):
            attempts = evalrepair.run_repair_loop(
                task, model, common, model_settings, args.timeout_seconds,
                args.repair_attempts, record,
            )
            record["repair"] = {"attempt_count": len(attempts), "attempts": attempts}
            final = attempts[-1] if attempts else None
            if final and final["failure_kind"] == "none":
                record["response"] = final.get("answer") or record.get("response")
                record["repo"] = final.get("repo")
                record["failure_kind"] = "none"
                record["error"] = None
                record["timings"] = final.get("timings") or record.get("timings")
            elif final:
                record["failure_kind"] = final["failure_kind"]
                record["error"] = final.get("error")
        write_json(directory / (task["id"] + ".json"), record)
        status = record["failure_kind"] if record["failure_kind"] != "none" else "saved"
        print(f"{index}/{len(tasks)} {task['id']}: {status}", flush=True)
    return directory


def run(args):
    tasks = load_tasks()
    if args.suite:
        tasks = resolve_suite(args.suite, tasks)
    if args.task:
        tasks = [task for task in tasks if task["id"] == args.task]
        if not tasks:
            raise EvaluationError(f"Unknown task: {args.task}")
    config = evalcore.load_model_config(MODELS, args.model)
    suite_digest = suite_hash(tasks)
    batch_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directories = []
    for attempt in range(1, args.repeats + 1):
        args._run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        directories.append(run_attempt(args, config, tasks, suite_digest, attempt, batch_id))
    if len(directories) > 1:
        write_json(
            RESULTS / args.model / ("batch-" + batch_id) / "batch.json",
            {
                "batch_id": batch_id,
                "model_key": args.model,
                "mode": args.mode,
                "attempts": [str(path) for path in directories],
            },
        )
    for directory in directories:
        print(directory)


def score(args):
    path = Path(args.run) / (safe_name(args.task) + ".json")
    record = read_json(path)
    for failure in args.failure or []:
        if failure not in REQUIREMENT_FAILURES:
            raise EvaluationError(
                f"Unknown requirement failure {failure!r}. Valid values: "
                + ", ".join(REQUIREMENT_FAILURES)
            )
    manual = record.get("manual") or {}
    manual.update(
        {
            "score": args.score,
            "notes": args.notes,
            "requirement_failures": args.failure or [],
            "failure_details": args.failure_detail or [],
            "additional_prompts": args.additional_prompts,
            "reviewer": args.reviewer,
        }
    )
    record["manual"] = manual
    write_json(path, record)


def summarize(directory):
    meta = read_json(directory / "metadata.json")
    task_ids = meta.get("task_ids") or meta.get("suite", {}).get("task_ids") or []
    rows = [read_json(directory / (task_id + ".json")) for task_id in task_ids]
    return meta, rows


def compare(args):
    runs = [summarize(Path(name)) for name in args.runs]
    first = runs[0][0]
    if getattr(args, "legacy", False):
        return compare_legacy(runs, args)
    check_comparable(first, [meta for meta, _ in runs[1:]])
    return evalcompare.build_report(runs, args.output)


def compare_old(args):
    """The previous single-table report, kept for reference."""
    runs = [summarize(Path(name)) for name in args.runs]
    first = runs[0][0]
    lines = [f"# Local model comparison ({first['mode']})", ""]
    lines += ["## Run identity", "", "| Field | " + " | ".join(
        meta["model_key"] for meta, _ in runs) + " |", "|---|" + "---:|" * len(runs)]

    def identity(label, function):
        lines.append("| " + label + " | " + " | ".join(function(meta) for meta, _ in runs) + " |")

    identity("Model", lambda meta: meta.get("model_config", {}).get("name", "n/a"))
    identity("Served model", lambda meta: meta.get("runtime", {}).get("served_model") or "n/a")
    identity("Max tokens", lambda meta: str(
        meta.get("comparison_key", {}).get("generation", {}).get("max_tokens", "n/a")))
    identity("Context required", lambda meta: str(
        meta.get("comparison_key", {}).get("context_requirement")
        or ("n/a (remote)" if is_remote(meta) else "not configured")))
    identity("Context observed", lambda meta: str(
        meta.get("runtime", {}).get("observed_context_tokens", "n/a")))
    identity("Reasoning effort", lambda meta: str(
        meta.get("invocation", {}).get("model", {}).get("reasoning_effort", "n/a")))
    identity("Think", lambda meta: str(
        meta.get("invocation", {}).get("model", {}).get("think", "n/a")))
    identity("Context compliant", lambda meta: context_compliant(meta))
    lines += ["", "## Scores", "", "| Metric | " + " | ".join(
        meta["model_key"] for meta, _ in runs) + " |", "|---|" + "---:|" * len(runs)]

    def metric(label, function):
        lines.append("| " + label + " | " + " | ".join(function(rows) for _, rows in runs) + " |")
    metric("Manually successful (score 2)", lambda rows: str(sum(r["manual"]["score"] == 2 for r in rows)) + f"/{len(rows)}")
    metric("Unscored", lambda rows: str(sum(r["manual"]["score"] is None for r in rows)))
    metric("First pass success", lambda rows: str(sum(
        r["manual"]["score"] == 2 and r["manual"].get("additional_prompts") == 0 for r in rows)))
    if first["mode"] in ("repo", "agent"):
        metric("Validation passing", lambda rows: str(sum(bool(r["repo"] and r["repo"]["validation_passed"]) for r in rows)) + f"/{len(rows)}")
        metric("Withheld tests passing", lambda rows: str(sum(
            bool(r["repo"] and r["repo"].get("withheld_validation")
                 and all(c["exit_code"] == 0 for c in r["repo"]["withheld_validation"]))
            for r in rows)) + f"/{len(rows)}")
    metric("Transport valid", lambda rows: str(sum(
        r.get("failure_kind") not in ("http_error", "timeout") for r in rows)) + f"/{len(rows)}")
    metric("Protocol success", lambda rows: str(sum(
        r.get("failure_kind") in ("none", "validation_failed") for r in rows)) + f"/{len(rows)}")
    metric("Requirement failures", lambda rows: str(sum(len(r["manual"]["requirement_failures"]) for r in rows)))
    metric("Average additional prompts", lambda rows: average(
        [r["manual"].get("additional_prompts") for r in rows]))
    metric("Average generation seconds", lambda rows: average([r["timings"]["generation_seconds"] for r in rows if r["timings"]]))
    metric("Average tokens/sec", lambda rows: average([r["timings"]["tokens_per_second"] for r in rows if r["timings"]]))
    metric("Average reasoning chars", lambda rows: average(
        [r["timings"].get("reasoning_chars") for r in rows if r["timings"]]))

    lines += ["", "## Failure modes", "", "| Failure kind | " + " | ".join(
        meta["model_key"] for meta, _ in runs) + " |", "|---|" + "---:|" * len(runs)]
    for kind in FAILURE_KINDS:
        lines.append("| " + kind + " | " + " | ".join(
            str(sum(r.get("failure_kind") == kind for r in rows)) for _, rows in runs) + " |")

    lines += ["", "## Category breakdown", "", "| Category | " + " | ".join(
        meta["model_key"] for meta, _ in runs) + " |", "|---|" + "---:|" * len(runs)]
    categories = []
    for _, rows in runs:
        for row in rows:
            if row["category"] not in categories:
                categories.append(row["category"])
    for category in categories:
        def category_value(rows, category=category):
            matching = [r for r in rows if r["category"] == category]
            passed = sum(bool(r["repo"] and r["repo"]["validation_passed"]) for r in matching)
            return f"{passed}/{len(matching)}"
        lines.append("| " + category + " | " + " | ".join(
            category_value(rows) for _, rows in runs) + " |")

    lines += ["", "## Per-task observations", ""]
    for task_id in first.get("comparison_key", {}).get("task_ids", []):
        lines.append(f"### {task_id}")
        for meta, rows in runs:
            row = next(r for r in rows if r["id"] == task_id)
            manual = row["manual"]
            validation = row["repo"]["validation_passed"] if row["repo"] else "n/a"
            lines.append(
                f"- {meta['model_key']}: score {manual['score']}, validation {validation}, "
                f"failure {row.get('failure_kind', 'none')}; "
                f"{manual['notes'] or row['error'] or 'No review note.'}"
            )
        lines.append("")
    output = "\n".join(lines) + "\n"
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output, end="")


def context_compliant(meta):
    """True when the observed served context meets the required context."""
    required = meta.get("comparison_key", {}).get("context_requirement")
    observed = meta.get("runtime", {}).get("observed_context_tokens")
    if not required:
        return "n/a (remote)" if is_remote(meta) else "not configured"
    if observed is None:
        return "n/a (remote)" if is_remote(meta) else "not observed"
    return "yes" if observed >= required else f"no ({observed} < {required})"


def is_remote(meta):
    """True when the run used a cloud model, which has no local context requirement."""
    config = meta.get("model_config") or {}
    context = config.get("context") or {}
    served = config.get("model") or ""
    if context.get("num_ctx"):
        return False
    return ":cloud" in served or served.endswith("-cloud")


def compare_legacy(runs, args):
    """Summarize pre-schema-2 runs without comparing them to current ones."""
    lines = [
        "# Legacy run summary",
        "",
        "These runs predate the current comparison key. They are shown for reference only "
        "and are not comparable with current runs.",
        "",
    ]
    for meta, rows in runs:
        lines.append(
            f"## {meta.get('model_key', 'unknown')} "
            f"({meta.get('mode', 'unknown')}, {meta.get('created_utc', 'unknown')})"
        )
        lines.append("")
        lines.append(f"- git commit {meta.get('git_commit', 'unknown')}")
        lines.append(f"- suite sha256 {meta.get('suite_sha256', 'unknown')}")
        lines.append(f"- generation {meta.get('generation', 'unknown')}")
        passed = sum(
            bool(row.get("repo") and row["repo"].get("validation_passed")) for row in rows
        )
        lines.append(f"- validation passing {passed}/{len(rows)}")
        scored = sum(row["manual"]["score"] is not None for row in rows)
        lines.append(f"- manually scored {scored}/{len(rows)}")
        lines.append("")
    output = "\n".join(lines) + "\n"
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output, end="")


def check_comparable(first, others):
    """Raise an actionable error when two runs cannot be compared."""
    first_key = first.get("comparison_key")
    if not first_key:
        raise EvaluationError(
            "This run has no comparison key, so it is a legacy result and cannot be compared "
            "with current runs. Use a separate legacy summary instead."
        )
    differences = []
    for meta in others:
        key = meta.get("comparison_key")
        if not key:
            raise EvaluationError(
                f"Run {meta.get('run_id', 'unknown')} has no comparison key and cannot be "
                "compared with current runs."
            )
        if key.get("protocol_version") != first_key.get("protocol_version"):
            raise EvaluationError(
                f"Comparison protocol {key.get('protocol_version')} is not compatible with "
                f"protocol {first_key.get('protocol_version')}. Rerun the candidates under one "
                "protocol or implement an explicit migration."
            )
        for field in sorted(set(first_key) | set(key)):
            if first_key.get(field) != key.get(field):
                differences.append(f"  {field}: {first_key.get(field)!r} != {key.get(field)!r}")
    if differences:
        raise EvaluationError(
            "Runs are not comparable:\n" + "\n".join(differences)
        )


def average(values):
    numbers = [value for value in values if value is not None]
    return f"{sum(numbers) / len(numbers):.2f}" if numbers else "n/a"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("tasks")
    commands.add_parser("suites")
    runner = commands.add_parser("run")
    runner.add_argument("--model", required=True)
    runner.add_argument("--mode", choices=("response", "repo", "agent"), required=True)
    runner.add_argument("--task")
    runner.add_argument("--suite", help="Run a named suite from config/suites.json")
    runner.add_argument("--max-tokens", type=int, default=None)
    runner.add_argument("--repeats", type=int, default=1)
    runner.add_argument("--timeout-seconds", type=int, default=3600)
    runner.add_argument("--repair-attempts", type=int, choices=(0, 1, 2), default=0)
    scoring = commands.add_parser("score")
    scoring.add_argument("run")
    scoring.add_argument("--task", required=True)
    scoring.add_argument("--score", type=int, choices=(0, 1, 2), required=True)
    scoring.add_argument("--notes", default="")
    scoring.add_argument("--failure", action="append")
    scoring.add_argument("--failure-detail", action="append")
    scoring.add_argument("--additional-prompts", type=int, default=None)
    scoring.add_argument("--reviewer", default=None)
    models = commands.add_parser("models")
    models.add_argument("--model")
    sheet = commands.add_parser("score-sheet")
    sheet.add_argument("sheet")
    sheet.add_argument("--dry-run", action="store_true")
    sheet.add_argument("--replace", action="store_true")
    export = commands.add_parser("export")
    export.add_argument("run")
    export.add_argument("--output", required=True)
    comparison = commands.add_parser("compare")
    comparison.add_argument("runs", nargs="+")
    comparison.add_argument("--output")
    comparison.add_argument("--legacy", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "tasks":
            for task in load_tasks():
                print(f"{task['id']}: {task['title']} ({task['category']})")
        elif args.command == "suites":
            suites = load_suites()
            all_tasks = load_tasks()
            for key in sorted(suites):
                entry = suites[key]
                count = len(resolve_suite(key, all_tasks))
                print(f"{key}: {entry.get('name')} ({count} tasks)")
                if entry.get("description"):
                    print(f"  {entry['description']}")
        elif args.command == "models":
            list_models(args.model)
        elif args.command == "run":
            if args.max_tokens is not None and args.max_tokens < 1:
                raise EvaluationError("max tokens must be positive")
            if args.repeats < 1:
                raise EvaluationError("repeats must be at least 1")
            if args.timeout_seconds < 1:
                raise EvaluationError("timeout-seconds must be positive")
            run(args)
        elif args.command == "score":
            score(args)
        elif args.command == "score-sheet":
            evalreport.score_sheet(args.sheet, dry_run=args.dry_run, replace=args.replace)
        elif args.command == "export":
            evalreport.export_run(args.run, args.output)
        else:
            compare(args)
    except EvaluationError as exc:
        parser.exit(1, f"Evaluation error: {exc}\n")
    except (KeyError, OSError, ValueError, json.JSONDecodeError) as exc:
        parser.exit(1, f"Evaluation error: {exc}\n")


if __name__ == "__main__":
    main()
