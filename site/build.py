"""Build the public showcase into site/dist from the repository's own outputs.

Reads storyboard.json for every line, subtitle and shot purpose, and copies the real
films and keyframes, so the page can never drift from the film. Run: python site/build.py
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline import keyframes  # noqa: E402
from pipeline.common import load_storyboard  # noqa: E402

SRC = ROOT / "site" / "src"
DIST = ROOT / "site" / "dist"
MEDIA = DIST / "media"


def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-y", *map(str, args)], check=True)


def still(src: Path, dst: Path, width: int):
    ffmpeg("-i", src, "-vf", f"scale={width}:-2", "-quality", "82", dst)


def main():
    sb = load_storyboard()
    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(SRC, DIST)
    MEDIA.mkdir()

    films = {}
    for ratio in ("16x9", "9x16"):
        film = ROOT / "outputs" / "final" / f"film_{ratio}.mp4"
        shutil.copy2(film, MEDIA / film.name)
        films[ratio] = f"media/{film.name}"
    ffmpeg("-ss", "57", "-i", MEDIA / "film_16x9.mp4", "-frames:v", "1", "-vf", "scale=1920:-2", "-quality", "82",
           MEDIA / "poster_16x9.webp")
    ffmpeg("-ss", "57", "-i", MEDIA / "film_9x16.mp4", "-frames:v", "1", "-vf", "scale=1080:-2", "-quality", "82",
           MEDIA / "poster_9x16.webp")

    characters = []
    for c in sb["characters"]:
        name = f"portrait_{c['id']}.webp"
        still(ROOT / c["golden_reference"], MEDIA / name, 720)
        characters.append({"id": c["id"], "description": c["description"], "voice": c["voice"],
                           "image": f"media/{name}"})

    shots = []
    for shot in sb["shots"]:
        for ratio, width in (("16x9", 1344), ("9x16", 640)):
            still(keyframes.keyframe_file(sb, shot, ratio), MEDIA / f"{shot['id']}_{ratio}.webp", width)
        shots.append({"id": shot["id"], "purpose": shot["purpose"], "size": shot["shot_size"].replace("_", " "), "duration": shot["duration_s"],
                      "image": f"media/{shot['id']}_16x9.webp", "imageTall": f"media/{shot['id']}_9x16.webp",
                      "lines": [{"speaker": l["speaker"], "text": l["text"], "en": l["subtitle_en"]}
                                for l in shot["lines"]]})

    data = {"title": sb["title"], "films": films, "characters": characters, "shots": shots,
            "endCards": [{"text": c["text"], "en": c["subtitle_en"]} for c in sb["end_cards"]],
            "music": {"caption": sb["music"]["caption"], "reason": sb["music"]["chosen_reason"]}}
    (DIST / "data.js").write_text("window.FILM = " + json.dumps(data, ensure_ascii=False) + ";\n", encoding="utf-8")
    size = sum(p.stat().st_size for p in DIST.rglob("*") if p.is_file()) / 1e6
    print(f"site/dist built: {len(shots)} shots, {len(characters)} portraits, {size:.1f} MB")


if __name__ == "__main__":
    main()
