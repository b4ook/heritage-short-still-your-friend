import json
from pathlib import Path

from pipeline import prune

VALID = json.loads((Path(__file__).parent / "fixtures" / "storyboard_valid.json").read_text())


def test_prune_only_touches_cache_folders(tmp_path, monkeypatch):
    monkeypatch.setattr(prune, "referenced", lambda sb: {(tmp_path / "keyframes" / "keep.png").resolve()})
    for rel in ["keyframes/keep.png", "keyframes/old.png", "music/old.wav", "final/film.mp4", "assemble/tmp.wav"]:
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_bytes(b"x")
    removed = prune.prune(VALID, outputs=tmp_path)
    assert sorted(p.relative_to(tmp_path).as_posix() for p in removed) == ["keyframes/old.png", "music/old.wav"]
    assert (tmp_path / "final/film.mp4").exists() and (tmp_path / "assemble/tmp.wav").exists()
    assert (tmp_path / "keyframes/keep.png").exists()
