"""Shots stage: Wan 2.2 image-to-video clips on Kaggle.

Group 3a (floor): only the clip keys, so assembly can find cached clips; with no shot
animated this stage contacts nothing. The Kaggle push arrives in Group 3b.
"""
import sys

from pipeline.common import ROOT, cache_key, file_hash, load_storyboard, output_path

STAGE = "shots"
WAN_MODEL = "Wan-AI/Wan2.2-TI2V-5B"
WAN_KERNEL = ROOT / "kaggle" / "wan" / "wan_kernel.py"
SIZE_KEY = {"9x16": "size_9x16", "16x9": "size_16x9"}


def animated_ratios(shot: dict) -> tuple[str, ...]:
    return {"none": (), "9x16": ("9x16",), "both": ("9x16", "16x9")}[shot["animate"]]


def clip_job(sb: dict, shot: dict, ratio: str) -> dict:
    from pipeline import keyframes

    return {"stage": STAGE, "model": WAN_MODEL,
            "payload": {"prompt": shot["motion_prompt"], "seed": shot["motion_seed"],
                        "size": sb["wan"][SIZE_KEY[ratio]], "frames": sb["wan"]["frames"]},
            "inputs": {"keyframe": file_hash(keyframes.keyframe_file(sb, shot, ratio))},
            "code": file_hash(WAN_KERNEL) if WAN_KERNEL.exists() else None}


def clip_file(sb: dict, shot: dict, ratio: str):
    """Cached clip for this shot and ratio, or None (assembly then uses Ken Burns)."""
    if ratio not in animated_ratios(shot):
        return None
    path = output_path(STAGE, cache_key(clip_job(sb, shot, ratio)), "mp4")
    return path if path.exists() else None


def main(argv):
    sb = load_storyboard()
    wanted = [(s["id"], r) for s in sb["shots"] for r in animated_ratios(s)]
    if not wanted:
        print("shots: no shot is animated; every shot uses Ken Burns")
        return 0
    print(f"shots: {len(wanted)} clips requested; the Kaggle push arrives in Group 3b, so they use Ken Burns for now")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
