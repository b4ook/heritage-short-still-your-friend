import json
import re
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

from pipeline.common import ROOT, load_storyboard, wrap_subtitle

SCHEMA = ROOT / "schema" / "storyboard.schema.json"
ETHICS = ROOT / "ETHICS.md"
END_CARD_S = 3
FILM_MIN_S, FILM_MAX_S = 60, 90


def json_path(parts) -> str:
    return "$" + "".join(f"[{p}]" if isinstance(p, int) else f".{p}" for p in parts)


def ethics_headings(path=ETHICS) -> set[str]:
    if not Path(path).exists():
        return set()
    return {m.group(1).strip() for m in re.finditer(r"^#+\s+(.+)$", Path(path).read_text(encoding="utf-8"), re.M)}


def code_checks(sb: dict, headings: set[str]) -> list[tuple[str, str]]:
    errors = []
    ids = [s["id"] for s in sb["shots"]]
    for dup in sorted({i for i in ids if ids.count(i) > 1}):
        errors.append(("$.shots", f"duplicate shot id {dup}"))

    characters = {c["id"]: c for c in sb["characters"]}
    for i, shot in enumerate(sb["shots"]):
        for j, cid in enumerate(shot["characters"]):
            if cid not in characters:
                errors.append((f"$.shots[{i}].characters[{j}]", f"unknown character {cid!r}"))
        kb = shot["ken_burns"]
        if kb["pan"] != "none" and kb["zoom_from"] < 1.1:
            errors.append((f"$.shots[{i}].ken_burns.zoom_from", "a pan needs zoom_from >= 1.1 to have room"))
        for j, line in enumerate(shot["lines"]):
            where = f"$.shots[{i}].lines[{j}]"
            speaker = characters.get(line["speaker"])
            if speaker is None:
                errors.append((f"{where}.speaker", f"unknown speaker {line['speaker']!r}"))
            elif not speaker["voice"]:
                errors.append((f"{where}.speaker", f"character {line['speaker']!r} has no voice"))
            if len(wrap_subtitle(line["subtitle_en"])) > 2:
                errors.append((f"{where}.subtitle_en", "wraps to more than 2 lines of 40 characters"))
    for i, card in enumerate(sb["end_cards"]):
        if len(wrap_subtitle(card["subtitle_en"])) > 2:
            errors.append((f"$.end_cards[{i}].subtitle_en", "wraps to more than 2 lines of 40 characters"))

    planned = sum(s["duration_s"] for s in sb["shots"]) + sum(c["duration_s"] for c in sb["end_cards"]) + END_CARD_S
    if not FILM_MIN_S <= planned <= FILM_MAX_S:
        errors.append(("$.shots", f"planned length {planned:g}s (with {END_CARD_S}s end card) is outside "
                                  f"{FILM_MIN_S}-{FILM_MAX_S}s"))
    if sb["music"]["duration_s"] < planned:
        errors.append(("$.music.duration_s", f"score is shorter than the planned {planned:g}s"))
    if sb["wan"]["frames"] % 4 != 1:
        errors.append(("$.wan.frames", "Wan needs 4n+1 frames"))

    for i, c in enumerate(sb["characters"]):
        if c["real_person"] and c["consent_ref"] not in headings:
            errors.append((f"$.characters[{i}].consent_ref",
                           f"no heading {c['consent_ref']!r} in ETHICS.md; record consent before generating"))
    return errors


def validate(sb: dict, headings=None) -> list[tuple[str, str]]:
    validator = Draft202012Validator(json.loads(SCHEMA.read_text()))
    schema_errors = sorted(validator.iter_errors(sb), key=lambda e: list(e.absolute_path))
    errors = [(json_path(e.absolute_path), e.message) for e in schema_errors]
    if errors:
        return errors
    return code_checks(sb, ethics_headings() if headings is None else headings)


def main(argv):
    path = argv[0] if argv else ROOT / "storyboard.json"
    errors = validate(load_storyboard(path))
    for where, message in errors:
        print(f"{where}: {message}")
    if not errors:
        print(f"{path}: valid")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
