# Architecture

The full design, with alternatives and review history, is in
[docs/designs/heritage_short_pipeline.md](docs/designs/heritage_short_pipeline.md).
This page describes the pipeline as built.

## Stages and run order

```text
storyboard.json ──► validate ──► keyframes ──► narration ──► music ──► shots ──► assemble
                    schema +     Cloudflare    Gemini TTS    ACE-Step   Wan 2.2    FFmpeg
                    code rules   FLUX.2 klein  per line      on Kaggle  on Kaggle  per ratio
```

*   **validate.** Runs the JSON Schema, then the code rules:
    *   speakers resolve and have a voice;
    *   subtitles fit in two lines;
    *   planned length is 60–90 s;
    *   `frames` is 4n+1;
    *   a real person needs a consent heading in ETHICS.md.

    It prints the JSON path of every error and exits 1 before any model is
    called.
*   **keyframes.** First, one front reference portrait per character. The
    stage stops (exit 2) until the author sets each `golden_reference`. Then
    one still per shot and ratio, at 768×1344 and 1344×768.
    *   Shots with `use_references: true` send the characters' golden
        references as `input_image_0..3`.
    *   Wide, candid or from-behind shots turn references off, because
        front-facing references force a posed framing (EXPERIMENTS.md E4).
*   **narration.** One Gemini TTS call per dialogue line, through the
    Interactions API (`pipeline/tts.py`).
    *   The text is sent verbatim.
    *   The character's `voice_style` plus the line's `style` go in a
        `speech_metadata.style` annotation, so they are not read aloud.
    *   Each line can override the model (`tts_model`).
    *   The output is a complete 24 kHz WAV.
*   **music.** Three ACE-Step 1.5 turbo candidates (instrumental, 90 s) on a
    Kaggle T4. The kernel builds the repo's own uv environment on Python
    3.12, because Kaggle's Python is 3.13, and runs in fp16 without
    quantization (E10).
*   **shots.** Wan 2.2 TI2V-5B image-to-video on Kaggle for shots whose
    `animate` is `9x16` or `both`. Until a clip exists, assembly uses Ken
    Burns.
*   **assemble.** Per ratio:
    1.  Timeline from the measured dialogue durations.
    2.  Each shot is its Wan clip, or a Ken Burns `zoompan` over the
        keyframe.
    3.  The Amharic end cards (`drawtext`, Ethiopic font).
    4.  The AI card, which names only the models used in that cut.
    5.  Concatenate.
    6.  Dialogue placed with `adelay`; the score trimmed and faded to the
        timeline and ducked under the voices with `sidechaincompress`.
    7.  Two-pass `loudnorm` to −14 LUFS and −1.5 dBTP.
    8.  Burned-in English subtitles.

## The contract

`storyboard.json` is the only input. It holds:

*   **Characters:** description, seed, golden reference, voice, voice style,
    `real_person` and `consent_ref`.
*   **Shots (8–12):** purpose, size, planned duration, characters,
    `use_references`, image and motion prompts with seeds, `animate`, Ken
    Burns zoom and pan, and dialogue `lines`. Each line has a speaker, the
    Amharic text, an English subtitle, a style and an optional TTS model.
*   **Music:** caption, bpm, key, duration, 3 seeds, the chosen candidate
    and the reason.
*   **End cards:** the closing messages in Amharic, each with an English
    subtitle.

The schema is `schema/storyboard.schema.json`.

## Caching

Every output is stored at `outputs/<stage>/<key>.<ext>`. The key is the
first 16 hex characters of SHA-256 over canonical JSON of four things:

*   the stage;
*   the model;
*   the exact payload sent to the provider, including the fully built
    prompt;
*   the SHA-256 of every input file, plus the Kaggle kernel script's hash.

A changed reference image therefore changes every keyframe built from it.
A changed keyframe changes its clip. A changed line regenerates only that
line.

*   **Atomic writes:** a file is written to `<path>.tmp`, then
    `os.replace`d, so an interrupted run never leaves a half file in the
    cache.
*   **Kaggle outputs** are cached only if they are non-empty and `ffprobe`
    can read them.

## Call log

`runs.jsonl` has one line per stage output event. The fields are `ts`,
`run_id`, `stage`, `shot_id`, `ratio`, `provider`, `model`, `params`,
`seed`, `cache_key`, `status`, `attempt`, `latency_s`, `gpu_s`,
`cost_usd_est`, `output_path` and `error`.

*   **Statuses:** `ok`, `retry` and `failed` are real model calls.
    `cache_hit` and `fallback` are not.
*   **Kaggle runs** add one kernel-level line with total GPU wall time.
*   **Assembly** writes no lines. Its fallbacks go to
    `outputs/final/fallbacks.txt`.

## Failure handling

*   **Retries.** `common.with_retry` makes the first attempt plus 3 retries
    (waits of 2, 8 and 30 s, or `Retry-After`).
    *   It retries 429, 5xx, timeouts and connection errors.
    *   It never retries a 429 whose body names a daily limit
        (`per[ _]?day|daily`), because those last until the next day.
    *   The Gemini SDK's own silent retries are turned off, so every failure
        is visible (FAILURES.md F5).
*   **Kaggle cycle** (`kaggle_runner.run_stage`):
    1.  Plan. If nothing is missing, return without importing `kaggle`, so
        a stranger needs no credentials.
    2.  Recover. If the previous kernel version is still running, push
        nothing. If it finished, collect its outputs first.
    3.  Upload keyframes to a private, append-only dataset.
    4.  Build. The job list is written into the kernel source.
    5.  Push, then poll every 60 s up to a deadline.
    6.  Collect the outputs listed in the kernel's `manifest.jsonl`.

    The kernel wraps everything in `try`/`except` and always exits cleanly,
    so its outputs can always be downloaded. It checks for a T4 first and
    stops taking jobs at 80 % of its time budget.
*   **Fallbacks:**
    *   A missing clip becomes Ken Burns.
    *   A missing score stops `make film`. Drafts use the placeholder track.
        `music.use_placeholder` makes that an explicit, logged choice.
*   **Length.** Assembly refuses a film outside 60–90 s. Drafts only warn.
