"""Build the public showcase into site/dist from the repository's own outputs.

Reads storyboard.json (and storyboard_v2.json, if its films exist) for every line, subtitle and shot purpose, and copies the real
films and keyframes, so the page can never drift from the film. Run: python site/build.py
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline import assemble, keyframes, narration  # noqa: E402
from pipeline.common import load_storyboard  # noqa: E402

SRC = ROOT / "site" / "src"
DIST = ROOT / "site" / "dist"
MEDIA = DIST / "media"
WEB_MAX_BYTES = 24 * 1024 * 1024


def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-y", *map(str, args)], check=True)


def still(src: Path, dst: Path, width: int):
    ffmpeg("-i", src, "-vf", f"scale={width}:-2", "-quality", "82", dst)


VERSIONS = [  # storyboard file, file-name tag, label, one-line note shown under the film
    ("storyboard.json", "", "Version one", "The first cut: slow zooms on each frame, straight cuts."),
    ("storyboard_v2.json", "_v2", "Version two",
     "Reworded dialogue, depth-parallax camera moves and soft dissolves between shots."),
]


def camera_move(kb: dict, motion: str) -> str:
    """Plain words for a shot's move, e.g. 'Parallax · slide right' or 'Zoom · push in'."""
    zf, zt, pan = kb["zoom_from"], kb["zoom_to"], kb["pan"]
    move = f"slide {pan}" if pan != "none" else ("push in" if zt > zf else "pull back" if zt < zf else "hold")
    return f"{'Parallax' if motion == 'parallax' else 'Zoom'} · {move}"


def version_data(n: int, file: str, tag: str, label: str, note: str, base: dict) -> dict:
    """base is version one's storyboard: a line counts as reworded when its text differs from it."""
    sb = load_storyboard(ROOT / file)
    timeline = assemble.build_timeline(sb, narration.durations(sb))
    reworded = [[l["text"] != b["text"] for l, b in zip(shot["lines"], bshot["lines"])]
                for shot, bshot in zip(sb["shots"], base["shots"])]
    cast = {}
    for c in sb["characters"]:
        spoken = [(l, reworded[i][j]) for i, shot in enumerate(sb["shots"])
                  for j, l in enumerate(shot["lines"]) if l["speaker"] == c["id"]]
        first = spoken[0][0] if spoken else None
        cast[c["id"]] = {"lines": len(spoken), "reworded": sum(r for _, r in spoken),
                         "sample": {"text": first["text"], "en": first["subtitle_en"]} if first else None}
    films, posters = {}, {}
    for ratio, width in (("16x9", 1920), ("9x16", 1080)):
        film = ROOT / "outputs" / "final" / f"film_{ratio}{tag}.mp4"
        if film.stat().st_size <= WEB_MAX_BYTES:
            shutil.copy2(film, MEDIA / film.name)
        else:  # Cloudflare serves at most 25 MiB per file; the master in outputs/final is left as it is
            ffmpeg("-i", film, "-c:v", "libx264", "-preset", "slow", "-b:v", "1.8M", "-maxrate", "2.4M",
                   "-bufsize", "4M", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart",
                   MEDIA / film.name)
        films[ratio] = f"media/{film.name}"
        poster = MEDIA / f"poster_{ratio}{tag}.webp"
        ffmpeg("-ss", "57", "-i", MEDIA / film.name, "-frames:v", "1", "-vf", f"scale={width}:-2", "-quality", "82",
               poster)
        posters[ratio] = f"media/{poster.name}"
    return {"id": n, "label": label, "note": note, "films": films, "posters": posters,
            "lines": [[{"speaker": l["speaker"], "text": l["text"], "en": l["subtitle_en"], "reworded": reworded[i][j]}
                       for j, l in enumerate(shot["lines"])] for i, shot in enumerate(sb["shots"])],
            "shots": [{"start": t["start_s"], "length": t["length_s"], "move": camera_move(shot["ken_burns"], sb.get("motion"))}
                      for t, shot in zip(timeline["shots"], sb["shots"])],
            "cast": cast, "newLines": sum(map(sum, reworded)), "total": timeline["total_s"],
            "endCards": [{"text": c["text"], "en": c["subtitle_en"]} for c in sb["end_cards"]]}


def main():
    sb = load_storyboard(ROOT / "storyboard.json")
    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(SRC, DIST)
    MEDIA.mkdir()

    versions = [version_data(n, *v, base=sb) for n, v in enumerate(VERSIONS, 1)
                if (ROOT / v[0]).exists() and (ROOT / "outputs" / "final" / f"film_16x9{v[1]}.mp4").exists()]
    films = versions[0]["films"]

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

    data = {"title": sb["title"], "films": films, "versions": versions, "characters": characters, "shots": shots,
            "endCards": [{"text": c["text"], "en": c["subtitle_en"]} for c in sb["end_cards"]],
            "music": {"caption": sb["music"]["caption"], "reason": sb["music"]["chosen_reason"]}}
    (DIST / "data.js").write_text("window.FILM = " + json.dumps(data, ensure_ascii=False) + ";\n", encoding="utf-8")
    size = sum(p.stat().st_size for p in DIST.rglob("*") if p.is_file()) / 1e6
    print(f"site/dist built: {len(versions)} versions, {len(shots)} shots, {len(characters)} portraits, {size:.1f} MB")


if __name__ == "__main__":
    main()
