"""Check the local Apple Silicon and MLX setup without downloading anything."""

import argparse
import importlib.metadata
import os
import platform
import subprocess
import sys
from pathlib import Path

DEFAULT_MODEL = "models/qwen2.5-coder-7b-instruct-4bit"


def model_path():
    return os.environ.get("LOCAL_CODER_MODEL", DEFAULT_MODEL)


def check(model, load_model=False):
    errors = []
    print(f"macOS: {platform.mac_ver()[0] or 'unavailable'}")
    print(f"architecture: {platform.machine()}")
    try:
        chip = subprocess.check_output(
            ["sysctl", "-n", "machdep.cpu.brand_string"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        chip = "unavailable"
    print(f"chip: {chip}")
    try:
        memory = int(subprocess.check_output(
            ["sysctl", "-n", "hw.memsize"], text=True, stderr=subprocess.DEVNULL
        ))
        print(f"memory: {memory / 2**30:.1f} GiB")
    except (OSError, ValueError, subprocess.CalledProcessError):
        print("memory: unavailable")
    print(f"Python: {platform.python_version()}")
    for package in ("mlx", "mlx-lm"):
        try:
            version = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            version = "not installed"
            errors.append(f"Install {package} with: python -m pip install -r requirements.txt")
        print(f"{package}: {version}")
    print(f"model: {model}")
    local = Path(model)
    if not local.is_dir() or not (local / "config.json").is_file():
        errors.append("Use a local model directory containing config.json; set LOCAL_CODER_MODEL if needed")
    if sys.platform != "darwin" or platform.machine() != "arm64":
        errors.append("An Apple Silicon macOS host is required")
    try:
        import mlx.core as mx
        mx.array([1]).sum().item()
        print("Metal: available")
    except (ImportError, RuntimeError, OSError) as exc:
        print(f"Metal: unavailable ({exc})")
        errors.append("Run on an Apple Silicon session with Metal access")
    if load_model and not errors:
        try:
            from mlx_lm import load
            load(model)
            print("model load: successful")
        except Exception as exc:
            errors.append(f"Model load failed: {exc}")
    else:
        print("model load: skipped" if not load_model else "model load: blocked by preflight errors")
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    return not errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=model_path())
    parser.add_argument("--load-model", action="store_true", help="Actually load the weights")
    args = parser.parse_args()
    sys.exit(0 if check(args.model, args.load_model) else 1)
