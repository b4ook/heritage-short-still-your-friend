import copy
import json
from pathlib import Path

import pytest

from pipeline.validate import validate

VALID = json.loads((Path(__file__).parent / "fixtures" / "storyboard_valid.json").read_text())


def mutated(fn):
    sb = copy.deepcopy(VALID)
    fn(sb)
    return sb


def paths(sb, headings=frozenset()):
    return [where for where, _ in validate(sb, set(headings))]


def test_valid_fixture_passes():
    assert validate(VALID, set()) == []


def add_shots(sb, n):
    sb["shots"] += [dict(sb["shots"][0], id=f"s{9 + i:02}") for i in range(n)]


@pytest.mark.parametrize("mutate, expected", [
    (lambda sb: add_shots(sb, 5), "$.shots"),
    (lambda sb: sb["shots"][0].pop("lines"), "$.shots[0]"),
    (lambda sb: sb["shots"][0].__setitem__("characters", ["ghost"]), "$.shots[0].characters[0]"),
    (lambda sb: [s.__setitem__("duration_s", 10) for s in sb["shots"]] and None, "$.shots"),
    (lambda sb: sb["shots"][1]["lines"][0].__setitem__("subtitle_en", "x" * 81), "$.shots[1].lines[0].subtitle_en"),
    (lambda sb: sb["shots"][1]["lines"][0].__setitem__("speaker", "ghost"), "$.shots[1].lines[0].speaker"),
    (lambda sb: sb["shots"][1]["lines"][0].__setitem__("speaker", "young_abebe"), "$.shots[1].lines[0].speaker"),
    (lambda sb: sb["end_cards"][0].__setitem__("duration_s", 1), "$.end_cards[0].duration_s"),
    (lambda sb: sb["wan"].__setitem__("frames", 120), "$.wan.frames"),
    (lambda sb: sb["shots"][0].__setitem__("id", "s13"), "$.shots[0].id"),
    (lambda sb: sb["music"].__setitem__("seeds", [1, 2]), "$.music.seeds"),
    (lambda sb: sb["shots"][0].__setitem__("extra", 1), "$.shots[0]"),
])
def test_invalid_storyboards_fail_at_path(mutate, expected):
    assert expected in paths(mutated(mutate))


def test_three_line_subtitle_fails():
    three_lines = " ".join(["a" * 21] * 3)
    sb = mutated(lambda sb: sb["shots"][1]["lines"][0].__setitem__("subtitle_en", three_lines))
    assert "$.shots[1].lines[0].subtitle_en" in paths(sb)


def test_pan_needs_zoom_room():
    sb = mutated(lambda sb: sb["shots"][0]["ken_burns"].update(zoom_from=1.0, pan="left"))
    assert "$.shots[0].ken_burns.zoom_from" in paths(sb)


def test_real_person_requires_consent_ref():
    sb = mutated(lambda sb: sb["characters"][0].update(real_person=True))
    assert "$.characters[0].consent_ref" in paths(sb)


def test_real_person_consent_heading_must_exist():
    sb = mutated(lambda sb: sb["characters"][0].update(real_person=True, consent_ref="Consent: grandmother"))
    assert "$.characters[0].consent_ref" in paths(sb)
    assert paths(sb, {"Consent: grandmother"}) == []
