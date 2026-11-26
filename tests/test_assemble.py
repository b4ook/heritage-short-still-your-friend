import copy
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from pipeline import assemble

VALID = json.loads((Path(__file__).parent / "fixtures" / "storyboard_valid.json").read_text())
SHOTS = {s["id"]: s for s in VALID["shots"]}


def durations(per_line=1.0, **overrides):
    return {sid: overrides.get(sid, [per_line] * len(s["lines"])) for sid, s in SHOTS.items()}


def test_short_lines_keep_planned_lengths():
    tl = assemble.build_timeline(VALID, durations())
    planned = [s["duration_s"] for s in VALID["shots"]]
    assert [t["length_s"] for t in tl["shots"]] == planned
    cards = sum(c["duration_s"] for c in VALID["end_cards"])
    assert tl["total_s"] == pytest.approx(sum(planned) + cards + assemble.END_CARD_S)


def test_lines_are_sequential_within_a_shot():
    tl = assemble.build_timeline(VALID, durations(s11=[2.0, 1.5, 1.0, 3.0]))
    s11 = next(t for t in tl["shots"] if t["shot_id"] == "s11")
    starts = [l["start_s"] for l in s11["lines"]]
    gap = assemble.LINE_GAP_S
    assert starts == pytest.approx([s11["start_s"] + 0.3, s11["start_s"] + 0.3 + 2.0 + gap,
                                    s11["start_s"] + 0.3 + 3.5 + 2 * gap, s11["start_s"] + 0.3 + 4.5 + 3 * gap])


def test_long_dialogue_stretches_only_its_shot():
    tl = assemble.build_timeline(VALID, durations(s02=[6.0]))
    by_id = {t["shot_id"]: t for t in tl["shots"]}
    assert by_id["s02"]["length_s"] == pytest.approx(0.3 + 6.0 + assemble.VOICE_TAIL_S)
    assert by_id["s03"]["start_s"] == pytest.approx(next(s["duration_s"] for s in VALID["shots"] if s["id"] == "s01") + 0.3 + 6.0 + assemble.VOICE_TAIL_S)


def test_total_outside_range_names_stretched_shot():
    with pytest.raises(assemble.TimelineError, match="s11"):
        assemble.build_timeline(VALID, durations(s11=[10.0, 10.0, 10.0, 1.0]))


def test_end_cards_follow_shots():
    tl = assemble.build_timeline(VALID, durations())
    shots_end = tl["shots"][-1]["start_s"] + tl["shots"][-1]["length_s"]
    assert tl["cards"][0]["start_s"] == pytest.approx(shots_end)
    assert tl["ai_card_start_s"] == pytest.approx(tl["total_s"] - assemble.END_CARD_S)


def test_srt_cues_never_overlap_and_wrap():
    srt = assemble.srt_text(assemble.build_timeline(VALID, durations(0.4)))
    blocks = [b.splitlines() for b in srt.strip().split("\n\n")]
    spoken = sum(len(s["lines"]) for s in VALID["shots"])
    assert len(blocks) == spoken + len(VALID["end_cards"])

    def secs(t):
        h, m, rest = t.split(":")
        s, ms = rest.split(",")
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000

    spans = [tuple(map(secs, b[1].split(" --> "))) for b in blocks]
    assert all(a < b for a, b in spans)
    assert all(spans[i][1] <= spans[i + 1][0] for i in range(len(spans) - 1))
    assert all(len(line) <= 40 for b in blocks for line in b[2:]) and all(len(b) - 2 <= 2 for b in blocks)


def test_pick_music_cases():
    candidates = [Path("c0.wav"), Path("c1.wav"), Path("c2.wav")]
    sb = copy.deepcopy(VALID)
    sb["music"].update(chosen=None, use_placeholder=False)
    assert assemble.pick_music(sb, candidates)[0] == candidates[0]
    assert assemble.pick_music(sb, [None, candidates[1], None])[0] == candidates[1]
    sb["music"]["chosen"] = 2
    assert assemble.pick_music(sb, candidates)[0] == candidates[2]
    sb["music"]["use_placeholder"] = True
    assert assemble.pick_music(sb, candidates)[0] == assemble.PLACEHOLDER


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
def test_radio_mix_renders_full_length():
    work = assemble.TMP / "pytest"
    work.mkdir(parents=True, exist_ok=True)
    voices = []
    for i, start in enumerate([0.3, 8.3]):
        path = work / f"voice{i}.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=440:d=3",
                        "-ar", "24000", "-ac", "1", str(path)], check=True)
        voices.append((path, start))
    out = assemble.render_radio(voices, assemble.PLACEHOLDER, 20.0, work / "radio.mp4")
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "csv=p=0", str(out)], capture_output=True, text=True, check=True)
    assert float(probe.stdout) == pytest.approx(20.0, abs=0.1)
    shutil.rmtree(work)
