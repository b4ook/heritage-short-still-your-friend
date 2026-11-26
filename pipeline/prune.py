"""Delete cached outputs the current storyboard no longer references (run before the release commit).

Only the four content-addressed cache folders are touched; final/ and assemble/ never are.
All three music candidates are kept.
"""
import sys
from pathlib import Path

from pipeline.common import OUTPUTS, ROOT, cache_key, load_storyboard

PRUNED = ("keyframes", "narration", "music", "shots")


def referenced(sb: dict) -> set[Path]:
    from pipeline import keyframes, music, narration, shots

    keep = {(ROOT / c["golden_reference"]).resolve() for c in sb["characters"] if c["golden_reference"]}
    keep |= {keyframes.keyframe_file(sb, s, r).resolve() for s in sb["shots"] for r in keyframes.RATIOS
             if all(c["golden_reference"] for c in sb["characters"])}
    keep |= {narration.line_file(sb, line).resolve() for s in sb["shots"] for line in s["lines"]}
    keep |= {(OUTPUTS / "music" / f"{cache_key(music.music_job(sb, seed))}.wav").resolve()
             for seed in sb["music"]["seeds"]}
    for s in sb["shots"]:
        for r in shots.animated_ratios(s):
            clip = shots.clip_file(sb, s, r)
            if clip:
                keep.add(clip.resolve())
    return keep


def prune(sb: dict, outputs: Path = OUTPUTS, dry_run: bool = False) -> list[Path]:
    keep = referenced(sb)
    removed = []
    for stage in PRUNED:
        folder = outputs / stage
        if not folder.is_dir():
            continue
        for path in sorted(folder.iterdir()):
            if path.is_file() and path.resolve() not in keep:
                removed.append(path)
                if not dry_run:
                    path.unlink()
    return removed


def main(argv):
    dry = "--dry-run" in argv
    removed = prune(load_storyboard(), dry_run=dry)
    for path in removed:
        print(("would delete " if dry else "deleted ") + str(path.relative_to(ROOT)))
    print(f"{len(removed)} file(s) {'to delete' if dry else 'deleted'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
