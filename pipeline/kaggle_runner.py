"""Push GPU jobs to a Kaggle kernel, wait, and collect outputs into the cache.

Cycle per stage per run: Plan (no Kaggle contact if nothing is missing), Recover
(collect a previous version's outputs), Upload inputs, Build, Push and poll.
"""
import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from pipeline.common import ROOT, _status, log_call, with_retry

POLL_S = 60
RUNNING = {"queued", "running", "new_script"}
INPUTS_DIR = ROOT / "kaggle" / "inputs"
INPUTS_SLUG = "heritage-inputs"
DATASET_READY_S = 600


def normalise(status) -> str:
    return str(getattr(status, "status", status)).split(".")[-1].lower()


def _valid(path: Path) -> bool:
    if path.stat().st_size == 0:
        return False
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                            str(path)], capture_output=True, text=True)
    return probe.returncode == 0 and probe.stdout.strip() not in ("", "N/A")


def _api():
    from kaggle.api.kaggle_api_extended import KaggleApi  # imported only when a job is missing

    api = KaggleApi()
    api.authenticate()
    return api


def _call(fn, stage, what):
    return with_retry(fn, {"stage": stage, "provider": "kaggle", "params": {"call": what}})


def collect(api, slug: str, out_dir: Path, ext: str, stage: str) -> dict[str, str]:
    """Download the kernel's latest output and move valid files listed in its manifest into the cache."""
    statuses = {}
    with tempfile.TemporaryDirectory() as tmp:
        _call(lambda: api.kernels_output(slug, tmp), stage, "kernels_output")
        manifest = Path(tmp) / "manifest.jsonl"
        if not manifest.exists():
            return statuses
        out_dir.mkdir(parents=True, exist_ok=True)
        for raw in manifest.read_text().splitlines():
            entry = json.loads(raw)
            if entry.get("key") == "kernel":
                log_call(stage=stage, provider="kaggle", model=slug, status="ok", gpu_s=entry.get("seconds"),
                         params={"kernel_total": True, "gpu": entry.get("gpu")})
                continue
            produced = Path(tmp) / f"{entry['key']}.{ext}"
            if entry.get("status") == "ok" and produced.exists() and _valid(produced):
                target = out_dir / produced.name
                shutil.move(str(produced), str(target))
                statuses[entry["key"]] = "ok"
                log_call(stage=stage, provider="kaggle", model=slug, cache_key=entry["key"], status="ok",
                         seed=entry.get("seed"), gpu_s=entry.get("seconds"), output_path=target)
            else:
                statuses[entry["key"]] = "failed"
                log_call(stage=stage, provider="kaggle", model=slug, cache_key=entry["key"], status="failed",
                         error=str(entry.get("error"))[:500])
    return statuses


def _never_pushed(exc) -> bool:
    """Kaggle answers 404, or 403 'kernels.get was denied', for a kernel that does not exist yet."""
    text = str(exc).lower()
    return _status(exc) in (403, 404) or "404" in text or "not found" in text or "was denied" in text


def _latest_status(api, slug, stage):
    try:
        return normalise(api.kernels_status(slug))
    except Exception as exc:
        if _never_pushed(exc):
            return None
        raise


def upload_inputs(api, username: str, inputs: dict[str, Path], stage: str) -> bool:
    INPUTS_DIR.mkdir(parents=True, exist_ok=True)
    for name, src in inputs.items():
        dst = INPUTS_DIR / name
        if not dst.exists():
            shutil.copy2(src, dst)
    slug = f"{username}/{INPUTS_SLUG}"
    (INPUTS_DIR / "dataset-metadata.json").write_text(json.dumps(
        {"id": slug, "title": INPUTS_SLUG, "licenses": [{"name": "CC0-1.0"}]}))
    try:
        api.dataset_status(slug)
        exists = True
    except Exception as exc:
        if not (_status(exc) == 404 or "404" in str(exc) or "not found" in str(exc).lower()):
            raise
        exists = False
    if exists:
        _call(lambda: api.dataset_create_version(str(INPUTS_DIR), version_notes=f"run {time.strftime('%Y%m%dT%H%M%S')}",
                                                 dir_mode="skip"), stage, "dataset_create_version")
    else:
        _call(lambda: api.dataset_create_new(str(INPUTS_DIR), public=False, dir_mode="skip"), stage,
              "dataset_create_new")
    deadline = time.monotonic() + DATASET_READY_S
    while time.monotonic() < deadline:
        if "ready" in str(api.dataset_status(slug)).lower():
            return True
        time.sleep(15)
    return False


def build(kernel_dir: Path, username: str, jobs: list[dict], time_budget_min: int) -> Path:
    build_dir = kernel_dir / "build"
    if build_dir.exists():
        shutil.rmtree(build_dir)
    shutil.copytree(kernel_dir, build_dir, ignore=shutil.ignore_patterns("build", "*.template.json"))
    meta = json.loads((kernel_dir / "kernel-metadata.template.json").read_text().replace("<user>", username))
    script = build_dir / meta["code_file"]
    source = script.read_text()
    if source.count("# __JOBS__") != 1:
        raise ValueError(f"{script.name} must contain exactly one '# __JOBS__' line")
    script.write_text(source.replace("# __JOBS__", f"JOBS = {json.dumps(jobs)}\nTIME_BUDGET_MIN = {time_budget_min}"))
    (build_dir / "kernel-metadata.json").write_text(json.dumps(meta, indent=2))
    return build_dir


def run_stage(kernel_dir: Path, jobs: list[dict], out_dir: Path, ext: str, stage: str,
              deadline_min: float, time_budget_min: int, inputs: dict[str, Path] | None = None) -> dict[str, str]:
    """Return {key: status} for every job: ok, cached, failed, fallback (pending on Kaggle) or running_elsewhere."""
    def missing():
        return [j for j in jobs if not (out_dir / f"{j['key']}.{ext}").exists()]

    statuses = {j["key"]: "cached" for j in jobs}
    todo = missing()
    if not todo:
        return statuses

    api = _api()
    username = api.get_config_value("username")
    meta = json.loads((kernel_dir / "kernel-metadata.template.json").read_text())
    slug = meta["id"].replace("<user>", username)

    previous = _latest_status(api, slug, stage)
    if previous in RUNNING:
        print(f"{slug} is still {previous}; not pushing. Missing outputs fall back this run.")
        return {**statuses, **{j["key"]: "running_elsewhere" for j in todo}}
    if previous is not None:
        statuses.update(collect(api, slug, out_dir, ext, stage))
        todo = missing()
        if not todo:
            return statuses

    if inputs:
        needed = {name: path for name, path in inputs.items() if any(j.get("input") == name for j in todo)}
        if not upload_inputs(api, username, needed, stage):
            print("inputs dataset not ready in time; missing outputs fall back this run")
            return {**statuses, **{j["key"]: "fallback" for j in todo}}

    build_dir = build(kernel_dir, username, todo, time_budget_min)
    _call(lambda: api.kernels_push(str(build_dir)), stage, "kernels_push")
    print(f"pushed {len(todo)} job(s) to {slug}")
    started = time.monotonic()
    status = "queued"
    while status in RUNNING and time.monotonic() - started < deadline_min * 60:
        time.sleep(POLL_S)
        status = _latest_status(api, slug, stage) or "queued"
        print(f"  {slug}: {status} after {round(time.monotonic() - started)}s", flush=True)
    if status in RUNNING:
        for j in todo:
            statuses[j["key"]] = "fallback"
            log_call(stage=stage, provider="kaggle", model=slug, cache_key=j["key"], status="fallback",
                     error=f"still {status} after {deadline_min} min; collected on a later run")
        return statuses
    statuses.update(collect(api, slug, out_dir, ext, stage))
    for j in missing():
        statuses.setdefault(j["key"], "failed")
    return statuses
