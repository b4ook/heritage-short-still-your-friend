"""Minimal Kaggle push, poll and pull for the smoke test.

kaggle_runner.py (Group 3a) replaces this for real stages.
"""
import json
import shutil
import tempfile
import time
from pathlib import Path

from pipeline.common import ROOT

KERNEL_DIR = ROOT / "kaggle" / "smoke"
POLL_S = 30
DEADLINE_S = 20 * 60
RUNNING = {"queued", "running", "new_script"}


def normalise(status) -> str:
    return str(getattr(status, "status", status)).split(".")[-1].lower()


def build(kernel_dir: Path, username: str) -> Path:
    build_dir = kernel_dir / "build"
    if build_dir.exists():
        shutil.rmtree(build_dir)
    shutil.copytree(kernel_dir, build_dir, ignore=shutil.ignore_patterns("build", "*.template.json"))
    meta = (kernel_dir / "kernel-metadata.template.json").read_text().replace("<user>", username)
    (build_dir / "kernel-metadata.json").write_text(meta)
    return build_dir


def run() -> dict:
    from kaggle.api.kaggle_api_extended import KaggleApi

    api = KaggleApi()
    api.authenticate()
    username = api.get_config_value("username")
    build_dir = build(KERNEL_DIR, username)
    slug = json.loads((build_dir / "kernel-metadata.json").read_text())["id"]

    started = time.monotonic()
    api.kernels_push(str(build_dir))
    status = "queued"
    while status in RUNNING and time.monotonic() - started < DEADLINE_S:
        time.sleep(POLL_S)
        status = normalise(api.kernels_status(slug))

    result = {"kernel": slug, "status": status, "seconds": round(time.monotonic() - started, 1)}
    if status in RUNNING:
        result["error"] = f"still {status} after {DEADLINE_S // 60} min"
        return result
    with tempfile.TemporaryDirectory() as tmp:
        api.kernels_output(slug, tmp)
        gpu = Path(tmp) / "gpu.txt"
        result["gpu"] = gpu.read_text() if gpu.exists() else None
    result["is_t4"] = bool(result["gpu"] and "Tesla T4" in result["gpu"])
    return result
