import argparse
import json
import subprocess
import sys
from pathlib import Path

from pipeline.common import OUTPUTS, ROOT, load_storyboard, wrap_subtitle

END_CARD_S = 3.0
VOICE_LEAD_S = 0.3
VOICE_TAIL_S = 0.3
DRAFT_MISSING_S = 2.5
LINE_GAP_S = 0.35
MIN_CUE_S = 1.5
FILM_MIN_S, FILM_MAX_S = 60.0, 90.0
FPS = 24
PLACEHOLDER = ROOT / "assets" / "placeholder_music.wav"
FINAL = OUTPUTS / "final"
TMP = OUTPUTS / "assemble" / "tmp"
# Starting values; tuned by ear and logged in EXPERIMENTS.md.
DUCK = "threshold=0.02:ratio=6:attack=100:release=1500"
VOICE_LUFS, MUSIC_LUFS, MASTER_LUFS, MASTER_TP = -16, -24, -14, -1.5


class TimelineError(ValueError):
    pass


def build_timeline(sb: dict, durations: dict[str, list[float]], strict: bool = True) -> dict:
    """Shots in order, each line placed after the previous one, then the message cards and the AI card."""
    shots, start = [], 0.0
    for shot in sb["shots"]:
        seconds = durations.get(shot["id"], [])
        lines, cursor = [], start + VOICE_LEAD_S
        for line, s in zip(shot["lines"], seconds):
            lines.append({"start_s": round(cursor, 3), "seconds": round(s, 3), "subtitle_en": line["subtitle_en"],
                          "speaker": line["speaker"], "text": line["text"]})
            cursor += s + LINE_GAP_S
        spoken = VOICE_LEAD_S + sum(seconds) + LINE_GAP_S * max(len(seconds) - 1, 0) + VOICE_TAIL_S
        length = max(shot["duration_s"], spoken) if seconds else shot["duration_s"]
        shots.append({"shot_id": shot["id"], "start_s": round(start, 3), "length_s": round(length, 3), "lines": lines})
        start += length
    cards = []
    for card in sb["end_cards"]:
        cards.append({"start_s": round(start, 3), "length_s": card["duration_s"], "text": card["text"],
                      "subtitle_en": card["subtitle_en"]})
        start += card["duration_s"]
    total = start + END_CARD_S
    if not FILM_MIN_S <= total <= FILM_MAX_S:
        if not strict:
            print(f"WARNING (draft): {total:.1f}s is outside {FILM_MIN_S:g}-{FILM_MAX_S:g}s")
            return {"shots": shots, "cards": cards, "ai_card_start_s": round(start, 3), "total_s": round(total, 3)}
        overruns = ", ".join(f"{t['shot_id']} +{t['length_s'] - s['duration_s']:.1f}s"
                             for t, s in zip(shots, sb["shots"]) if t["length_s"] > s["duration_s"])
        raise TimelineError(f"film would be {total:.1f}s with the end cards, outside {FILM_MIN_S:g}-{FILM_MAX_S:g}s. "
                            f"Shots stretched by dialogue: {overruns or 'none'}")
    return {"shots": shots, "cards": cards, "ai_card_start_s": round(start, 3), "total_s": round(total, 3)}


def _srt_time(seconds: float) -> str:
    ms = round(seconds * 1000)
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def srt_text(timeline: dict) -> str:
    """One cue per spoken line, held at least MIN_CUE_S but never into the next line; one per message card."""
    spans = [(l["start_s"], l["seconds"], l["subtitle_en"]) for t in timeline["shots"] for l in t["lines"]]
    cues = []
    for i, (start, seconds, text) in enumerate(spans):
        end = start + max(seconds, MIN_CUE_S)
        if i + 1 < len(spans):
            end = min(end, spans[i + 1][0] - 0.05)
        cues.append((start, end, text))
    cues += [(c["start_s"], c["start_s"] + c["length_s"], c["subtitle_en"]) for c in timeline["cards"]]
    return "\n\n".join(f"{n}\n{_srt_time(a)} --> {_srt_time(b)}\n" + "\n".join(wrap_subtitle(text))
                        for n, (a, b, text) in enumerate(cues, 1)) + "\n"


def pick_music(sb: dict, candidates: list) -> tuple[Path, str]:
    """candidates is aligned with music.seeds; an entry is None until that seed is generated."""
    music = sb["music"]
    if music["use_placeholder"]:
        return PLACEHOLDER, "placeholder track (use_placeholder is set; the spec asks for an original score)"
    if music["chosen"] is not None:
        if candidates[music["chosen"]] is None:
            raise FileNotFoundError(f"music.chosen = {music['chosen']} but that candidate is not generated")
        return candidates[music["chosen"]], f"candidate {music['chosen']}"
    first = next(i for i, c in enumerate(candidates) if c is not None)
    return candidates[first], f"candidate {first} (WARNING: set music.chosen and music.chosen_reason)"


def audio_graph(voices: list[tuple[Path, float]], total: float) -> str:
    """Filter graph: inputs 0..n-1 are narration WAVs, input n is the music. Output label [out]."""
    stereo = "aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo"
    parts = [f"[{i}:a]{stereo},adelay=delays={round(start * 1000)}:all=1[v{i}]" for i, (_, start) in enumerate(voices)]
    labels = "".join(f"[v{i}]" for i in range(len(voices)))
    parts.append(f"{labels}amix=inputs={len(voices)}:normalize=0:duration=longest,apad=whole_dur={total},"
                 f"atrim=0:{total},loudnorm=I={VOICE_LUFS}:TP=-1.5,aresample=48000[voice]")
    parts.append(f"[{len(voices)}:a]{stereo},atrim=0:{total},apad=whole_dur={total},loudnorm=I={MUSIC_LUFS},"
                 f"aresample=48000,afade=t=out:st={max(total - 2, 0)}:d=2[music]")
    parts.append("[voice]asplit=2[vkey][vmix]")
    parts.append(f"[music][vkey]sidechaincompress={DUCK}[ducked]")
    parts.append("[vmix][ducked]amix=inputs=2:normalize=0:duration=first[out]")
    return ";".join(parts)


def master_filter(mix: Path) -> str:
    """Two-pass loudnorm: measure the mix, then normalise linearly to the G5 target."""
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", _rel(mix), "-af",
         f"loudnorm=I={MASTER_LUFS}:TP={MASTER_TP}:print_format=json", "-f", "null", "-"],
        cwd=ROOT, capture_output=True, text=True, check=True)
    m = json.loads(result.stderr[result.stderr.rindex("{"):result.stderr.rindex("}") + 1])
    return (f"loudnorm=I={MASTER_LUFS}:TP={MASTER_TP}:linear=true:measured_I={m['input_i']}:"
            f"measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:"
            f"offset={m['target_offset']},aresample=48000")


def _rel(path: Path) -> str:
    """FFmpeg runs from the repo root; the project path has spaces and a curly apostrophe."""
    return str(Path(path).resolve().relative_to(ROOT))


def ffmpeg(args: list[str]) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-y", *args], cwd=ROOT, check=True)


def render_mix(voices: list[tuple[Path, float]], music: Path, total: float, name: str) -> Path:
    if not voices:
        raise ValueError("needs at least one spoken line")
    mix = TMP / f"{name}_mix.wav"
    mix.parent.mkdir(parents=True, exist_ok=True)
    args = []
    for path, _ in voices:
        args += ["-i", _rel(path)]
    ffmpeg([*args, "-i", _rel(music), "-filter_complex", audio_graph(voices, total), "-map", "[out]",
            "-t", str(total), "-c:a", "pcm_s24le", _rel(mix)])
    return mix


ENCODE = ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
          "-movflags", "+faststart"]


def render_radio(voices: list[tuple[Path, float]], music: Path, total: float, out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    mix = render_mix(voices, music, total, out.stem)
    ffmpeg(["-f", "lavfi", "-i", f"color=c=black:s=1080x1920:r={FPS}:d={total}", "-i", _rel(mix),
            "-af", master_filter(mix), "-map", "0:v", "-map", "1:a", *ENCODE, "-t", str(total), _rel(out)])
    return out


def placed_voices(sb: dict, timeline: dict) -> tuple[list[tuple[Path, float]], list[str]]:
    from pipeline import narration

    voices, missing = [], []
    for t, shot in zip(timeline["shots"], sb["shots"]):
        for placed, line in zip(t["lines"], shot["lines"]):
            path = narration.line_file(sb, line)
            if path.exists():
                voices.append((path, placed["start_s"]))
            else:
                missing.append(f"{shot['id']} {line['text']}")
    return voices, missing


def radio(sb: dict, draft: bool = False) -> Path:
    """Dialogue over the placeholder track on black. A draft leaves missing lines silent and only warns on length."""
    from pipeline import narration

    timeline = build_timeline(sb, narration.durations(sb, DRAFT_MISSING_S if draft else None), strict=not draft)
    total = timeline["total_s"]
    voices, missing = placed_voices(sb, timeline)
    name = "radio_cut_draft" if draft else "radio_cut"
    out = render_radio(voices, PLACEHOLDER, total, FINAL / f"{name}.mp4")
    (FINAL / f"{name}.srt").write_text(srt_text(timeline), encoding="utf-8")
    print(f"{name}: {total:.1f}s, {len(voices)} lines -> {out}")
    if missing:
        print(f"silent (not generated yet, {DRAFT_MISSING_S:g}s each): " + "; ".join(missing))
    return out


# ---- pictures -------------------------------------------------------------

SIZES = {"9x16": (1080, 1920), "16x9": (1920, 1080)}
SUBTITLE_STYLE = {"9x16": (56, 260), "16x9": (56, 60)}
CARD_FONT_SIZE = {"9x16": 54, "16x9": 60}
CARD_WRAP = {"9x16": 22, "16x9": 40}
TRIM_S, HOLD_MAX_S = 0.25, 1.5
def ai_card_lines(sb: dict, used_music: bool, used_clips: bool) -> list[str]:
    """The disclosure card names only the models that made something in this cut."""
    lines = ["Made with AI", "Voices: Gemini 3.8 TTS", "Images: FLUX.2 klein"]
    if used_music:
        lines.append("Music: ACE-Step 1.5")
    if used_clips:
        lines.append("Motion: Wan 2.2")
    return lines


def _font(names: list[str]) -> Path:
    for candidate in names:
        path = Path(candidate) if candidate.startswith("/") else ROOT / "assets" / "fonts" / candidate
        if path.exists():
            return path
    raise FileNotFoundError(f"none of these fonts exist: {names}")


def amharic_font() -> Path:
    return _font(["NotoSansEthiopic-Regular.ttf", "/System/Library/Fonts/Supplemental/KefaIII.ttf"])


def latin_font() -> Path:
    return _font(["NotoSans-Regular.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf"])


def cover(w: int, h: int) -> str:
    return f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}"


def ken_burns_filter(kb: dict, length: float, w: int, h: int) -> str:
    frames = max(round(FPS * length), 2)
    zf, zt = kb["zoom_from"], kb["zoom_to"]
    progress = f"on/{frames - 1}"
    cx, cy = "(iw-iw/zoom)/2", "(ih-ih/zoom)/2"
    x, y = {"none": (cx, cy),
            "right": (f"(iw-iw/zoom)*{progress}", cy),
            "left": (f"(iw-iw/zoom)*(1-{progress})", cy),
            "down": (cx, f"(ih-ih/zoom)*{progress}"),
            "up": (cx, f"(ih-ih/zoom)*(1-{progress})")}[kb["pan"]]
    return (f"{cover(2 * w, 2 * h)},zoompan=z='{zf}+({zt}-{zf})*{progress}':x='{x}':y='{y}':d={frames}:"
            f"s={2 * w}x{2 * h}:fps={FPS},scale={w}:{h},setsar=1")


def render_shot(sb: dict, shot: dict, ratio: str, length: float, out: Path) -> str:
    """One shot's picture: its Wan clip if cached and long enough, otherwise Ken Burns over the keyframe."""
    from pipeline import keyframes, shots

    w, h = SIZES[ratio]
    clip = shots.clip_file(sb, shot, ratio)
    if clip is not None:
        clip_s = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                       "csv=p=0", str(clip)], capture_output=True, text=True, check=True).stdout)
        usable = clip_s - 2 * TRIM_S
        if length <= usable + HOLD_MAX_S:
            hold = max(length - usable, 0)
            ffmpeg(["-ss", str(TRIM_S), "-i", _rel(clip), "-an", "-vf",
                    f"{cover(w, h)},fps={FPS},tpad=stop_mode=clone:stop_duration={hold},setsar=1",
                    "-t", str(length), "-c:v", "libx264", "-pix_fmt", "yuv420p", _rel(out)])
            return "clip"
    still = keyframes.keyframe_file(sb, shot, ratio)
    if not still.exists():
        raise FileNotFoundError(f"keyframe for {shot['id']} {ratio} missing; run the keyframes stage")
    ffmpeg(["-i", _rel(still), "-vf", ken_burns_filter(shot["ken_burns"], length, w, h), "-t", str(length),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", _rel(out)])
    return "ken_burns" if clip is None and shot["animate"] == "none" else "ken_burns (fallback)"


def render_card(lines: list[str], font: Path, size: int, length: float, ratio: str, out: Path) -> None:
    w, h = SIZES[ratio]
    step = round(size * 1.6)
    top = h // 2 - step * len(lines) // 2
    draws = []
    for i, text in enumerate(lines):
        txt = out.with_name(f"{out.stem}_{i}.txt")
        txt.write_text(text, encoding="utf-8")
        draws.append(f"drawtext=fontfile={font}:textfile={_rel(txt)}:fontcolor=white:fontsize={size}:"
                     f"x=(w-tw)/2:y={top + i * step}")
    ffmpeg(["-f", "lavfi", "-i", f"color=c=black:s={w}x{h}:r={FPS}:d={length}", "-vf", ",".join(draws),
            "-t", str(length), "-c:v", "libx264", "-pix_fmt", "yuv420p", _rel(out)])


def film(sb: dict, ratio: str, draft: bool = False) -> Path:
    import textwrap

    from pipeline import music, narration

    timeline = build_timeline(sb, narration.durations(sb, DRAFT_MISSING_S if draft else None), strict=not draft)
    total = timeline["total_s"]
    work = TMP / f"film_{ratio}"
    work.mkdir(parents=True, exist_ok=True)
    segments, report = [], []
    for t, shot in zip(timeline["shots"], sb["shots"]):
        seg = work / f"{shot['id']}.mp4"
        report.append(f"{shot['id']}: {render_shot(sb, shot, ratio, t['length_s'], seg)}")
        segments.append(seg)
    for i, card in enumerate(timeline["cards"]):
        seg = work / f"card{i}.mp4"
        render_card(textwrap.wrap(card["text"], CARD_WRAP[ratio]), amharic_font(), CARD_FONT_SIZE[ratio],
                    card["length_s"], ratio, seg)
        segments.append(seg)

    candidates = music.candidate_files(sb)
    if not sb["music"]["use_placeholder"] and not any(candidates):
        if not draft:
            raise FileNotFoundError("no score yet; run the music stage or set music.use_placeholder")
        score, note = PLACEHOLDER, "placeholder (draft: no score generated yet)"
    else:
        score, note = pick_music(sb, candidates)
    seg = work / "ai_card.mp4"
    render_card(ai_card_lines(sb, score != PLACEHOLDER, any(r.endswith(": clip") for r in report)), latin_font(),
                CARD_FONT_SIZE[ratio], END_CARD_S, ratio, seg)
    segments.append(seg)
    concat = work / "concat.txt"
    concat.write_text("".join(f"file '{s.name}'\n" for s in segments), encoding="utf-8")
    picture = work / "picture.mp4"
    ffmpeg(["-f", "concat", "-safe", "0", "-i", _rel(concat), "-c", "copy", _rel(picture)])

    voices, missing = placed_voices(sb, timeline)
    mix = render_mix(voices, score, total, f"film_{ratio}")

    srt = FINAL / ("film_draft.srt" if draft else "subtitles_en.srt")
    srt.parent.mkdir(parents=True, exist_ok=True)
    srt.write_text(srt_text(timeline), encoding="utf-8")
    w, h = SIZES[ratio]
    font_size, margin = SUBTITLE_STYLE[ratio]
    subs = (f"subtitles={_rel(srt)}:fontsdir=assets/fonts:force_style='PlayResX={w},PlayResY={h},"
            f"FontName=Arial,FontSize={font_size},MarginV={margin},Outline=3'")
    out = FINAL / (f"film_{ratio}_draft.mp4" if draft else f"film_{ratio}.mp4")
    ffmpeg(["-i", _rel(picture), "-i", _rel(mix), "-vf", subs, "-af", master_filter(mix),
            "-map", "0:v", "-map", "1:a", *ENCODE, "-t", str(total), _rel(out)])
    fallbacks = [r for r in report if "fallback" in r]
    (FINAL / "fallbacks.txt").write_text("\n".join(fallbacks + [f"music: {note}"] +
                                         [f"silent line: {m}" for m in missing]) + "\n", encoding="utf-8")
    print(f"film {ratio}: {total:.1f}s, score {note} -> {out}")
    for line in report:
        print("  " + line)
    if missing:
        print("  silent lines (draft): " + "; ".join(missing))
    return out


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--radio", action="store_true", help="dialogue over the placeholder track on black")
    parser.add_argument("--draft", action="store_true", help="leave missing lines silent and warn on length")
    parser.add_argument("--ratio", choices=[*SIZES, "both"], default="both")
    args = parser.parse_args(argv)
    sb = load_storyboard()
    if args.radio:
        radio(sb, draft=args.draft)
        return 0
    for ratio in (SIZES if args.ratio == "both" else [args.ratio]):
        film(sb, ratio, draft=args.draft)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
