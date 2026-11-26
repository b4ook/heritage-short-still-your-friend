"""ACE-Step 1.5 score candidates on a Kaggle T4. JOBS and TIME_BUDGET_MIN are injected at build time.

Kaggle's image runs Python 3.13 and ACE-Step needs 3.11-3.12, so the kernel builds the repo's own
uv environment on Python 3.12 and runs generation there as a subprocess.
"""
import json
import subprocess
import time
import traceback
from pathlib import Path

# __JOBS__

WORK = Path("/kaggle/working")
REPO = Path("/kaggle/temp/ACE-Step-1.5")
MANIFEST = WORK / "manifest.jsonl"
STARTED = time.monotonic()

GENERATE = r'''
import inspect, json, shutil, sys, time, traceback
from pathlib import Path
jobs, budget_s, started = json.loads(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3])
work, repo = Path("/kaggle/working"), Path("/kaggle/temp/ACE-Step-1.5")

def record(**e):
    with (work / "manifest.jsonl").open("a") as f:
        f.write(json.dumps(e) + "\n")

def call(fn, **kw):
    ps = inspect.signature(fn).parameters
    if any(p.kind == p.VAR_KEYWORD for p in ps.values()):
        return fn(**kw)
    return fn(**{k: v for k, v in kw.items() if k in ps})

from acestep.handler import AceStepHandler
from acestep.inference import GenerationConfig, GenerationParams, generate_music
dit = AceStepHandler()
call(dit.initialize_service, project_root=str(repo), config_path="acestep-v15-turbo", device="cuda",
     offload_to_cpu=True, quantization=None)

def to_fp32():
    """T4 has no bf16, so ACE-Step picks fp16, which can overflow to NaN; float32 is slower but stable."""
    import torch
    dit.dtype = torch.float32
    for value in list(vars(dit).values()):
        if isinstance(value, torch.nn.Module):
            value.float()
    print("switched DiT to float32", flush=True)
llm = None
try:
    from acestep.llm_inference import LLMHandler
    llm = LLMHandler()
    call(llm.initialize, checkpoint_dir=str(repo / "checkpoints"), lm_model_path="acestep-5Hz-lm-0.6B",
         backend="pt", device="cuda")
except Exception:
    print("LM planner unavailable, continuing without it:\n" + traceback.format_exc(), flush=True)
    llm = None
for job in jobs:
    if time.time() - started > budget_s:
        break
    t0 = time.time()
    try:
        params = call(GenerationParams, caption=job["caption"], lyrics="[Instrumental]", instrumental=True,
                      duration=job["duration_s"], bpm=job["bpm"], keyscale=job["keyscale"], seed=job["seed"],
                      inference_steps=8, shift=3.0)
        config = call(GenerationConfig, batch_size=1, audio_format="wav", use_random_seed=False, seeds=[job["seed"]])
        out = work / ("tmp_" + job["key"])
        result = generate_music(dit, llm, params, config, save_dir=str(out))
        failure = str(getattr(result, "error", "")) if not result.success or not result.audios else ""
        if "NaN" in failure and str(dit.dtype) != "torch.float32":
            to_fp32()
            result = generate_music(dit, llm, params, config, save_dir=str(out))
            failure = str(getattr(result, "error", "")) if not result.success or not result.audios else ""
        if failure or not result.audios:
            raise RuntimeError("generation failed: " + (failure or str(result))[:800])
        shutil.move(result.audios[0]["path"], work / (job["key"] + ".wav"))
        shutil.rmtree(out, ignore_errors=True)
        record(key=job["key"], status="ok", seconds=round(time.time() - t0, 1), seed=job["seed"])
    except Exception as exc:
        record(key=job["key"], status="error", seconds=round(time.time() - t0, 1),
               error=(type(exc).__name__ + ": " + str(exc))[:1500])
'''


def record(**entry):
    with MANIFEST.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def sh(cmd, cwd=None):
    print("$", cmd, flush=True)
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    with (WORK / "setup.log").open("a") as log:
        log.write(f"$ {cmd}\n{result.stdout[-6000:]}\n{result.stderr[-6000:]}\n")
    if result.returncode != 0:
        raise RuntimeError(f"{cmd} failed (exit {result.returncode}); see setup.log: {result.stderr[-600:]}")


def gpu_name():
    out = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], capture_output=True, text=True)
    return out.stdout.strip() or "none"


def main():
    gpu = gpu_name()
    if "T4" not in gpu:
        for job in JOBS:
            record(key=job["key"], status="error", error=f"gpu {gpu}")
        return
    if not REPO.exists():
        sh(f"git clone --depth 1 https://github.com/ace-step/ACE-Step-1.5.git {REPO}")
    sh("pip install -q uv")
    sh("uv sync --python 3.12", cwd=REPO)
    script = WORK / "generate.py"
    script.write_text(GENERATE)
    budget_s = 0.8 * TIME_BUDGET_MIN * 60
    started_wall = time.time() - (time.monotonic() - STARTED)
    sh(f"{REPO}/.venv/bin/python {script} '{json.dumps(JOBS)}' {budget_s} {started_wall}", cwd=REPO)
    script.unlink()


try:
    main()
except BaseException:
    for job in JOBS:
        if not (WORK / f"{job['key']}.wav").exists():
            record(key=job["key"], status="error", error=traceback.format_exc()[-1500:])
finally:
    record(key="kernel", status="ok", seconds=round(time.monotonic() - STARTED, 1), gpu=gpu_name())
