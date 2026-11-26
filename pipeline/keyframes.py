"""Keyframes stage: one reference portrait per character, then one still per shot and ratio.

Exit code 2 means references exist but are not approved yet: view them, set
characters[].golden_reference in storyboard.json, and run again.
"""
import sys
import time
from pathlib import Path

from pipeline import cloudflare
from pipeline.common import (ROOT, cache_key, cost_usd, file_hash, load_env, load_storyboard, log_call, output_path,
                             with_retry, write_atomic)

STAGE = "keyframes"
KEYFRAME_MODEL = cloudflare.KLEIN
REFERENCE_SIZE = (1024, 1024)
SIZES = {"9x16": (768, 1344), "16x9": (1344, 768)}
RATIOS = tuple(SIZES)


def _characters(sb):
    return {c["id"]: c for c in sb["characters"]}


def reference_job(sb: dict, character: dict) -> dict:
    prompt = ". ".join([character["reference_prompt"], character["description"], sb["style_block"],
                        "front view, head and shoulders, neutral background"])
    width, height = REFERENCE_SIZE
    return {"stage": STAGE, "model": KEYFRAME_MODEL,
            "payload": {"prompt": prompt, "seed": character["seed"], "width": width, "height": height},
            "inputs": {}, "code": None}


def golden_path(character: dict) -> Path:
    return ROOT / character["golden_reference"]


def keyframe_job(sb: dict, shot: dict, ratio: str) -> dict:
    chars = _characters(sb)
    cast = [chars[c] for c in shot["characters"]]
    prompt = ". ".join([shot["image_prompt"], *[c["description"] for c in cast], sb["style_block"]])
    width, height = SIZES[ratio]
    return {"stage": STAGE, "model": KEYFRAME_MODEL,
            "payload": {"prompt": prompt, "seed": shot["image_seed"], "width": width, "height": height},
            "inputs": {c["id"]: file_hash(golden_path(c)) for c in cast} if shot["use_references"] else {},
            "code": None}


def keyframe_file(sb: dict, shot: dict, ratio: str) -> Path:
    return output_path(STAGE, cache_key(keyframe_job(sb, shot, ratio)), "png")


def _generate(job: dict, inputs: list[Path], log_base: dict) -> Path:
    key = cache_key(job)
    path = output_path(STAGE, key, "png")
    base = {**log_base, "stage": STAGE, "provider": "cloudflare", "model": job["model"],
            "params": job["payload"], "seed": job["payload"]["seed"], "cache_key": key}
    if path.exists():
        log_call(**base, status="cache_hit", output_path=path)
        return path
    p = job["payload"]
    start = time.monotonic()
    try:
        png = with_retry(lambda: cloudflare.generate_image(job["model"], p["prompt"], p["seed"], p["width"],
                                                           p["height"], inputs), base)
    except Exception as exc:
        log_call(**base, status="failed", attempt=1, error=f"{type(exc).__name__}: {exc}"[:500])
        raise
    write_atomic(path, png)
    log_call(**base, status="ok", attempt=1, latency_s=round(time.monotonic() - start, 2),
             cost_usd_est=cost_usd(job["model"], 1), output_path=path)
    print(f"{log_base.get('shot_id') or log_base.get('ratio')}: {path.relative_to(ROOT)}")
    return path


def run_references(sb: dict) -> list[tuple[str, Path]]:
    return [(c["id"], _generate(reference_job(sb, c), [], {"shot_id": f"ref:{c['id']}"})) for c in sb["characters"]]


def run(sb: dict) -> int:
    refs = run_references(sb)
    unapproved = [(cid, path) for cid, path in refs if not _characters(sb)[cid]["golden_reference"]]
    if unapproved:
        print("\nApprove the references: set characters[].golden_reference in storyboard.json, then run again.")
        for cid, path in unapproved:
            print(f"  {cid}: \"golden_reference\": \"{path.relative_to(ROOT)}\"")
        return 2
    chars = _characters(sb)
    for shot in sb["shots"]:
        # Front-facing reference portraits also pull the framing towards a posed portrait, so wide,
        # candid or from-behind shots set use_references false and rely on the text descriptions.
        inputs = [golden_path(chars[c]) for c in shot["characters"]] if shot["use_references"] else []
        for ratio in RATIOS:
            _generate(keyframe_job(sb, shot, ratio), inputs, {"shot_id": shot["id"], "ratio": ratio})
    return 0


def main():
    load_env()
    return run(load_storyboard())


if __name__ == "__main__":
    sys.exit(main())
