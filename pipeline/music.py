"""Music stage: three ACE-Step 1.5 instrumental candidates on Kaggle; the author picks one."""
import os
import sys

from pipeline import kaggle_runner
from pipeline.common import OUTPUTS, ROOT, cache_key, file_hash, load_env, load_storyboard

STAGE = "music"
MODEL = "ACE-Step/acestep-v15-turbo"
KERNEL_DIR = ROOT / "kaggle" / "music"
TIME_BUDGET_MIN = 25


def music_job(sb: dict, seed: int) -> dict:
    m = sb["music"]
    return {"stage": STAGE, "model": MODEL,
            "payload": {"caption": m["caption"], "duration_s": m["duration_s"], "bpm": m["bpm"],
                        "keyscale": m["key"], "seed": seed, "instrumental": True},
            "inputs": {}, "code": file_hash(KERNEL_DIR / "music_kernel.py")}


def candidate_files(sb: dict) -> list:
    """One entry per seed, in storyboard order: the cached WAV, or None if not generated yet."""
    paths = [OUTPUTS / STAGE / f"{cache_key(music_job(sb, seed))}.wav" for seed in sb["music"]["seeds"]]
    return [p if p.exists() else None for p in paths]


def run(sb: dict) -> int:
    if sb["music"]["use_placeholder"]:
        print("music: use_placeholder is set; skipping ACE-Step")
        return 0
    jobs = []
    for seed in sb["music"]["seeds"]:
        job = music_job(sb, seed)
        p = job["payload"]
        jobs.append({"key": cache_key(job), "caption": p["caption"], "duration_s": p["duration_s"], "bpm": p["bpm"],
                     "keyscale": p["keyscale"], "seed": seed})
    statuses = kaggle_runner.run_stage(KERNEL_DIR, jobs, OUTPUTS / STAGE, "wav", STAGE,
                                       deadline_min=float(os.environ.get("KAGGLE_DEADLINE_MIN_MUSIC", 30)),
                                       time_budget_min=TIME_BUDGET_MIN)
    for seed, job in zip(sb["music"]["seeds"], jobs):
        print(f"music seed {seed}: {statuses.get(job['key'])}")
    if not any(candidate_files(sb)):
        print("music: no candidate exists. Check kaggle/music/build and the kernel log, or set "
              "music.use_placeholder to finish with the placeholder track.")
        return 1
    return 0


def main():
    load_env()
    return run(load_storyboard())


if __name__ == "__main__":
    sys.exit(main())
