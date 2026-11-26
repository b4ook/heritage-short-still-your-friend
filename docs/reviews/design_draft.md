# Heritage Short: Storyboard-Driven Film Pipeline

*   **Author:** b4ook
*   **Status:** Proposed (revised after Goldfish review)
*   **Date:** 2026-11-24

--------------------------------------------------------------------------------

## Overview

This repository builds a 60–90 second short film about a person, place or story
that is important to the author's family. Narration is in a language the
author chooses. The film has English subtitles, an original score and an
AI-disclosure end card. It is exported natively in vertical (9:16) and
horizontal (16:9).

The film is not edited by hand. One file, `storyboard.json`, describes every
shot: duration, image prompt, motion prompt, narration line and music cue.
Five stage scripts read that file and write their outputs to `outputs/`. The
stages match the module's list: keyframes, shots, music, narration and
assembly.

The repository is designed so that:

*   a stranger can clone it, run one command, and regenerate the film from the
    storyboard;
*   changing one shot in the storyboard regenerates only that shot.

The work is the 10 Academy challenge "AI-Content Generation: The Heritage
Short" (module 5399). The requirements, rubric and deadline are summarised in
[module_5399.md](../references/module_5399.md). There are two graded
submissions, both due **Thursday 26 November 2026, 23:59 EAT**:

1.  **Codebase and report.** Graded by reading code, text, logs and written
    documents only. No audio, image or video file is opened.
2.  **Film, walkthrough video and public post.** Graded by hand.

Terms used below:

*   **Floor**: the required work every trainee must finish.
*   **Ceiling work**: optional extras judged on insight.
*   **Phase 1, 2, 3**: the module's three checkpoints. They are story and
    radio cut; pictures and music; edit and release.

## The Problem

A single model call is straightforward. Producing a coherent film from many
models is not, for four reasons:

1.  **No memory between calls.** Image and video models do not remember earlier
    outputs. The same character drifts from shot to shot unless every call gets
    the same reference image, style text and seed.
2.  **Scarce, unreliable compute.** The free video and music models run on
    Kaggle T4 GPUs with about 30 GPU hours a week, session limits and queues.
    A 5-second 720p Wan 2.2 clip takes many minutes on a T4. If a quota runs out
    or a session dies, the run must not lose finished work.
3.  **Several providers, each with its own limits.** Gemini (text and speech),
    Cloudflare Workers AI (images), Kaggle (video and music) and local FFmpeg
    each have different failure modes, rate limits and data terms.
4.  **The graders cannot see the media.** Assignment 1 reads only text. Every
    claim about quality, cost, consistency or audience reaction needs written
    evidence in logs and documents.

The proposed solution is a pipeline with explicit stage contracts:

*   The storyboard is validated against a JSON Schema before any model is
    called.
*   Each stage stores its outputs under a hash of the exact request that
    produced them.
*   Each stage retries temporary failures.
*   Each stage appends one line per output event to `runs.jsonl`.
*   The documents (DESIGN, ARCHITECTURE, EXPERIMENTS, FAILURES, COSTS, ETHICS)
    are written alongside the code, not after it.

**Time is the binding constraint.** Drafting starts on 24 November, which
leaves about 2.5 days, not the three the module plans for. The design therefore
treats a narrated, scored, subtitled sequence of stills with a slow pan and
zoom (the Ken Burns effect, called Ken Burns below) as the guaranteed film.
Wan 2.2 clips replace stills one shot at a time, as GPU quota allows. A
schedule with a cut line (Detailed Implementation Plan) keeps that order.

## Goals

*   **G1: One-command rebuild.** From a clean clone with keys in `.env`, one
    documented command (`make film`) does the following:
    *   validates the storyboard;
    *   runs every stage, pushing any missing GPU jobs to Kaggle itself and
        reusing cached outputs otherwise;
    *   writes `outputs/final/film_9x16.mp4` and
        `outputs/final/film_16x9.mp4`.

    The two manual choices on a first run are described in CUJ 0.
*   **G2: Only changed shots regenerate.** Editing one shot's image prompt or
    narration line and re-running produces new model-call lines (`ok`, `retry`
    or `failed`) in `runs.jsonl` for that shot only. Everything else is a
    `cache_hit`. The walkthrough video demonstrates this.
*   **G3: Validated contract.** `storyboard.json` passes
    `schema/storyboard.schema.json` and the code checks in `validate.py` before
    any stage runs. It must have 8–12 shots and a planned total of 60–87 s
    plus a 3 s end card. A failure stops the run before any model is called.
*   **G4: Complete log.** Every stage output event appends one JSON line to
    `runs.jsonl`. The fields are listed in the Technical Plan, under Call log.
*   **G5: Film meets the spec.**
    *   The actual length, including the end card, is 60–90 s.
    *   Narration is in the chosen language.
    *   English subtitles are burned in: at most 2 lines of 40 characters,
        inside the 9:16 safe area.
    *   The score is ducked under the voice.
    *   Integrated loudness is −14 LUFS ±1 and true peak is ≤ −1 dBTP.
    *   There is a visible AI end card.
*   **G6: Character consistency.** One front-view reference image per
    character is generated and approved first. Every keyframe that shows the
    character passes that image to the image model as an input image. Every
    keyframe also carries the same style block.
*   **G7: The picture always ships.** Any shot without a Wan clip uses Ken
    Burns over its keyframe, so assembly completes. This goal covers pictures
    only. Missing narration or music stops the run (see Risks & Mitigations).
*   **G8: Written evidence for the graders.** The repository contains:
    *   DESIGN.md: audience, intent, two user tests of at least three people
        each, what changed, and a reason for every shot;
    *   EXPERIMENTS.md: at least ten hypothesis → change → result entries;
    *   FAILURES.md;
    *   COSTS.md: measured latency and GPU minutes per stage, and a
        list-price equivalent;
    *   ETHICS.md: consent, licences, labelling and the data sent to each
        provider.
*   **G9: Consent before generation.** If a real person's face, likeness or
    voice appears, their recorded consent is in ETHICS.md before anything of
    them is generated. `validate.py` enforces this (see the schema rule
    `real_person`). Without consent the film scores zero.
*   **G10: No secrets in git.** Keys live in `.env` (gitignored) and
    `~/.kaggle/kaggle.json`. GitHub push protection is on for the repository.

## Non-Goals

*   **Paid models in the main path.** Paid frontier models are used only as a
    comparison experiment, and only if the cohort is given a shared
    organisation key.
*   **A moving clip for every shot.** Wan clips are an upgrade over Ken Burns,
    and the 9:16 export gets them first.
*   **A 720p re-render pass.** Every Wan clip is rendered once, at the
    resolution fixed in the storyboard.
*   **Generic multi-user tooling.** There is no web app, MCP server or packaged
    CLI. These are possible ceiling work (see Future Improvements).
*   **LoRA training.** Consistency comes from reference images, seeds and a
    fixed style block.
*   **Voice cloning of a real person.** Narration uses a stock Gemini TTS
    voice.
*   **Automatic upload to social platforms.** Posting with the AI label on is a
    manual step.
*   **Hand editing in a GUI editor.** Every edit decision lives in the
    storyboard or in the assembly code.

## Open Questions

*   **Story, subject and language.** Who or what is the film about, and which
    language is the narration in? Gemini TTS quality varies by language.
    Amharic is listed as supported; Afaan Oromo, Tigrinya and Somali are not
    confirmed.
*   **Consent.** Will a real person's face or voice appear? If so, who records
    their consent, and when? Does the family agree to their story text going
    to free-tier Gemini (see Risks & Mitigations, privacy)?
*   **Audience.** Who are the at least three people for each user test?
    *   User test 1 (radio cut) is planned for the evening of 24 Nov or the
        morning of 25 Nov.
    *   User test 2 (near-final cut) is planned for the afternoon of 26 Nov.
*   **Accounts.** Are the Gemini key, the Cloudflare account and the
    phone-verified Kaggle account already set up?

The smoke test (`make smoke`) answers each of the following and records the
answer in COSTS.md or FAILURES.md:

*   **FLUX.2 klein on Workers AI.** Is `@cf/black-forest-labs/flux-2-klein-4b`
    available? Does it accept `width`, `height`, `seed` and `input_image_0`
    as multipart form fields, and what is the response format?
*   **Kaggle accelerator.** Does `machine_shape: "NvidiaTeslaT4"` in the kernel
    metadata give a T4? The smoke kernel prints `nvidia-smi` to check.
*   **Wan on a T4.** Does the official Wan 2.2 repository run TI2V-5B at
    704×1280 on a T4? The T4 has no native bf16 and no FlashAttention-2, with
    the attention and dtype patch in item 28. How long does one 121-frame clip take? `make smoke-wan` answers this.
*   **Free-tier daily limits.** What are the actual daily limits for
    Cloudflare images and Gemini TTS requests?
*   **ACE-Step 1.5.** What are the repository URL, model id and licence? They
    are recorded from the model card at install.

## Critical User Journeys (CUJs)

### CUJ 0: Author's first run

*   **Given**: A clone with `.env` and `kaggle.json` set up, and a
    `storyboard.json` with every `golden_reference` set to `null` and
    `music.chosen` set to `null`.
*   **When**: The author runs `make film`.
*   **Then**:
    1.  The reference images are generated. The run stops with a message that
        lists their paths and asks the author to set
        `characters[].golden_reference`.
    2.  The author views the images, sets the fields, and runs `make film`
        again.
    3.  The keyframes, narration and three music candidates are generated.
        Assembly uses candidate 0 and prints a warning until `music.chosen` and
        `music.chosen_reason` are set.
    4.  The author listens, sets both fields, and runs `make film` again. Only
        assembly re-runs.

### CUJ 1: Stranger rebuilds the film from a clean clone

*   **Given**: A clean clone, Python 3.11, and FFmpeg ≥ 6 built with libass
    and freetype. They have run `pip install -r requirements.txt` and set up a
    `.env` with `GEMINI_API_KEY`, `CLOUDFLARE_ACCOUNT_ID` and
    `CLOUDFLARE_API_TOKEN`. The committed `outputs/` cache is present. A
    Kaggle credential is needed only if a cache entry is missing.
*   **When**: They run `make film`.
*   **Then**: The storyboard validates. Every stage finds its outputs in the
    cache, and assembly writes both MP4s. Every new `runs.jsonl` line for the
    printed `RUN_ID` has `status: cache_hit`. The `kaggle` package is never
    imported, so no credential is needed.

### CUJ 2: Author changes one shot (the walkthrough demo)

*   **Given**: A complete previous run. No shot has `animate` set to a ratio
    whose clip is missing.
*   **When**: The author edits shot `s04`'s `image_prompt` and runs
    `make film`.
*   **Then**:
    *   Shot `s04`'s two keyframes regenerate.
    *   If `s04` is animated, only its clip jobs are pushed to Kaggle.
    *   `runs.jsonl` shows model-call lines for `s04` only, and assembly
        re-runs.
    *   If the author instead edits `s04`'s narration line, only `s04`'s
        narration regenerates and no Kaggle job is pushed.

### CUJ 3: Kaggle fails or runs late

*   **Given**: A run in which the Wan kernel errors, runs past the local
    deadline, or finds the weekly GPU quota exhausted.
*   **When**: `make film` reaches the shots stage.
*   **Then**:
    *   Every shot without a cached clip uses Ken Burns. Assembly writes both
        films.
    *   Each missing clip is logged once with `status: fallback`.
    *   On the next `make film`, the runner first collects any clips the
        earlier kernel finished, even ones finished after the local deadline.
        It then pushes only the clips that are still missing.
    *   While the earlier kernel is still running, nothing new is pushed.

### CUJ 4: Invalid storyboard

*   **Given**: A storyboard with 13 shots, a shot missing `narration`, or a
    `subtitle_en` that wraps to three lines.
*   **When**: The author runs `make film`.
*   **Then**: Validation prints each failing JSON path (for example
    `$.shots[3].narration`) and exits non-zero before any model call.
    `runs.jsonl` is unchanged.

## Technical Plan (Architecture)

### Decisions taken

*   **Kaggle orchestration**, chosen over Alternatives A and B. `make film`
    pushes the GPU stages to Kaggle itself, collects their outputs, and falls
    back to Ken Burns for pictures. There is no manual notebook step.
*   **Aspect ratios**, chosen over Alternatives C and D. Every keyframe is
    generated natively in both 9:16 and 16:9. Wan clips are generated
    natively too, per the shot's `animate` field: `none`, `9x16` or `both`.
    9:16 jobs are pushed first, because the 9:16 film is the main submission.
*   **Wan runtime.** The official Wan 2.2 repository's `generate.py`, task
    `ti2v-5B`, at its supported sizes of 704×1280 and 1280×704, 121 frames
    (about 5 s at 24 fps). Model offloading is on. The kernel patches
    attention to PyTorch SDPA and the dtype to fp16, because the T4 has
    neither FlashAttention-2 nor native bf16. There is no second render pass.
*   **Image model.** Cloudflare Workers AI
    `@cf/black-forest-labs/flux-2-klein-4b` (Apache 2.0). It is called with one
    approved reference image per character as an input image.
*   **Privacy.** The free Gemini tier is used for narration. The text sent, and
    the family's agreement to it, are recorded in ETHICS.md. No other family
    text goes to a free endpoint.
*   **Tooling.**
    *   Python 3.11 for every stage. The Kaggle kernels are Python too, so one
        language covers local and remote code.
    *   `make` is the entry point and FFmpeg does assembly.
    *   Dependencies: `jsonschema`, `google-genai`, `requests`, `kaggle`,
        `python-dotenv` and `pytest`.

### Stages and run order

`make film` runs these steps in this order. Each step is one Python module.

```text
 storyboard.json
       │
       ▼
 [validate]  schema + code checks ── fail ──► stop, no model calls
       │
       ▼
 [keyframes] Cloudflare FLUX.2 klein (local API call)
       │      a. one front reference per character → wait for approval (CUJ 0)
       │      b. per shot × {9x16, 16x9}, reference passed as input_image_0
       ▼
 [narration] Gemini TTS (local API call), one WAV per shot
       │
       ▼
 [music]     ACE-Step 1.5 on Kaggle, 3 candidates; author picks one
       │
       ▼
 [shots]     Wan 2.2 TI2V-5B on Kaggle, only shots with animate ≠ none,
       │      all 9x16 jobs first; missing clips → Ken Burns in assembly
       ▼
 [assemble]  FFmpeg (local): timeline from narration → per-shot picture
              (clip or Ken Burns) → concat → end card → voice + ducked
              music → loudnorm → subtitles → film_9x16.mp4, film_16x9.mp4

 Every stage reads storyboard.json and writes outputs/<stage>/<key>.<ext>.
 Every output event appends one line to runs.jsonl.
```

Music runs before shots. The score is part of the guaranteed film and the Wan
clips are not, so the score's Kaggle job must not wait behind hours of Wan
work.

The **radio cut** (`make radio`) is the Phase 1 prototype. It runs validation,
narration and a reduced assembly: narration on the timeline over the
placeholder track, on a black 1080×1920 picture, ducked and loudness-normalised,
with no subtitles. The **near-final cut** is the full `make film` output, with
every Wan clip that was ready by then. It is shown in user test 2.

### The contract: `storyboard.json`

Top-level fields:

*   `title` (string) and `language`, a non-empty BCP-47 code such as
    `am-ET`.
*   `style_block` (string): fixed text appended to every image prompt.
*   `wan`: `{"size_9x16": "704*1280", "size_16x9": "1280*704", "frames": 121}`.
    *   All three values are part of every clip's cache key, so they live in
        the contract and not in `.env`.
    *   `frames` must be 4n+1, which Wan requires.
*   `characters[]`:
    *   `id`, `description`, `reference_prompt`, `seed`.
    *   `golden_reference`: a path, or `null` until approved.
    *   `real_person` (bool).
    *   `consent_ref`: a string or `null`. When `real_person` is true it must
        be a string that names a heading in ETHICS.md.
*   `voice`: `tts_model`, `voice_name`, `style_instruction`. All are
    non-empty strings.
*   `music`:
    *   `caption`
    *   `bpm`: 40–200
    *   `key`: a string such as `"D minor"`
    *   `duration_s`: 30–240
    *   `seeds`: exactly 3
    *   `chosen`: 0–2, or `null`
    *   `chosen_reason`: a string, or `null`
    *   `use_placeholder` (bool)

    The score is always instrumental. With `use_placeholder: true`, the
    placeholder track replaces the score as an explicit, logged choice, and
    the music stage does not call Kaggle.
*   `shots[]` (8–12 items). Each shot has:
    *   `id`: matches `^s(0[1-9]|1[0-2])$`.
    *   `purpose`: the stated reason for the shot.
    *   `shot_size`: one of `extreme_wide`, `wide`, `medium`, `medium_close`,
        `close`, `extreme_close`, `insert`.
    *   `duration_s`: the planned length, 3–10.
    *   `characters[]`: at most 4 ids from `characters`. FLUX.2 accepts at
        most 4 input images.
    *   `image_prompt` and `image_seed`.
    *   `motion_prompt` and `motion_seed`.
    *   `animate`: `"none"`, `"9x16"` or `"both"`.
    *   `ken_burns`:
        *   `zoom_from` and `zoom_to`: 1.0–1.5.
        *   `pan`: one of `none`, `left`, `right`, `up`, `down`.
    *   `narration`:
        *   `text`: native language. It may be an empty string for a silent
            shot.
        *   `subtitle_en`: `maxLength` 80.
    *   `music_cue`: free text for the cue list.

Every seed is an integer from 0 to 2147483647. Every object has
`additionalProperties: false`. Every field is required. The nullable fields
named above take `null` when unset.

`validate.py` adds the checks that JSON Schema cannot express:

*   Shot ids are unique, and every character id resolves.
*   The planned total plus 3 s is 60–90 s.
*   `music.duration_s` is at least the planned total plus 3 s.
*   `wan.frames % 4 == 1`.
*   If `pan` is not `none`, then `zoom_from` is at least 1.1, so the pan has
    room.
*   Each `subtitle_en`, wrapped by `common.wrap_subtitle()`, fits in at most
    2 lines.
*   Every `consent_ref` exists as a heading in ETHICS.md.

### Caching

Every stage output is stored at `outputs/<stage>/<key>.<ext>`. The key is the
first 16 hex characters of SHA-256 over canonical JSON (sorted keys, no
whitespace) of this object:

```text
{ "stage":   "<stage name>",
  "model":   "<model id>",
  "payload": { ...exactly the parameters sent to the provider, including
               the fully built prompt... },
  "inputs":  { "<input name>": "<SHA-256 of the input file's bytes>", ... },
  "code":    "<SHA-256 of the Kaggle kernel script, before templating>" | null }
```

Each stage has one job-builder function that returns this object for a shot
and ratio. The stage uses it to call the provider. Assembly uses it to find
outputs again. The key therefore covers every input by construction, with no
hand-kept list of key fields.

An input file hash in the key means a change propagates downstream. A new
reference image changes the keyframe keys. A new keyframe changes its clip
keys.

Writes are atomic: an output is written to `<path>.tmp` and moved into place
with `os.replace`, so an interrupted write never becomes a cache entry. A
Kaggle output is kept only if it is non-empty and `ffprobe` decodes it. A stage
skips any output whose file exists and logs a `cache_hit`. Assembly is not
cached: it is deterministic and local.

`outputs/` is committed, except `outputs/assemble/tmp/`, so a stranger's clone
starts with a full cache (CUJ 1). Before the release commit, `make prune`
deletes every file in `keyframes/`, `narration/`, `music/` and `shots/`
that the current storyboard's keys do not reference. It never touches
`final/` or `assemble/`.
This keeps rejected images of family members out of the public repository.
Earlier versions stay in git history.

### Call log: `runs.jsonl`

`runs.jsonl` has one JSON line per stage output event. All lines come from one
shared helper, `log_call`.

| Field | Meaning |
| --- | --- |
| `ts` | UTC timestamp |
| `run_id` | Set once per `make` invocation; `adhoc` when run outside make |
| `stage`, `shot_id`, `ratio` | What the line is about (`shot_id`/`ratio` null where not applicable) |
| `provider`, `model` | e.g. `cloudflare`, `@cf/black-forest-labs/flux-2-klein-4b` |
| `params` | The payload, without prompt text over 200 characters (truncated) |
| `seed` | Seed used |
| `cache_key` | Key of the output |
| `status` | `ok`, `retry`, `failed` (real model calls); `cache_hit`, `fallback` (no call) |
| `attempt` | 1 for the first try |
| `latency_s` | Wall-clock seconds of the call |
| `gpu_s` | Kaggle stages only, from the kernel's manifest |
| `cost_usd_est` | List-price equivalent from the price table in COSTS.md (dated) |
| `output_path`, `error` | Output file; error text on failure |

Each Kaggle push also logs one line with `shot_id: null`, `status: ok` and
`gpu_s` equal to the kernel's total wall time, so setup time counts.
Assembly writes no lines. COSTS.md is produced by summing this file per stage.

### Retries

Local calls to Gemini, Cloudflare and the Kaggle API all go through
`with_retry`. It makes the first attempt, then up to 3 retries. It waits 2, 8
and 30 s between attempts, or the `Retry-After` value when the response gives
one.

*   **Retried:** HTTP 429, 5xx, `requests.Timeout` and connection errors.
*   **Not retried, fails at once:**
    *   any other 4xx;
    *   a 429 whose body matches the case-insensitive regex `per_?day|daily`.
        This is a daily quota: Gemini names its metrics `..._per_day`, and
        Cloudflare reports a daily free allocation.

After the final failure the stage logs `failed` and the run stops. The one
exception is the shots stage, where a missing clip becomes Ken Burns.

### Narration

*   **One TTS call per shot** through the Gemini Interactions API
    (`client.interactions.create`, model `gemini-3.8-flash-tts`), in
    `pipeline/tts.py`. The narration text is sent as a verbatim transcript.
    The voice's `style_instruction` goes in a `speech_metadata.style`
    annotation, so it shapes delivery without being read aloud. The older
    `generateContent` call with `speech_config` is rejected by the API (smoke
    test, 25 Nov).
*   **Audio format.** A unary request returns a complete WAV (24 kHz, mono,
    16-bit), written as is. Its duration is read from the WAV header.
*   **Silent shots.** A shot with empty narration text gets no TTS call.
*   **Unsupported language.** If TTS handles the chosen language badly, that is
    recorded in FAILURES.md, and the author changes the language or the
    wording.

### Kaggle orchestration (music and shots)

Each Kaggle stage has its own kernel folder, `kaggle/music/` and
`kaggle/wan/`. Each folder holds a script and `kernel-metadata.template.json`.
The runner, `pipeline/kaggle_runner.py`, uses the `KaggleApi` Python class
rather than parsing CLI text. It imports `kaggle` only after it knows there is
work to send. Importing `kaggle` signs in as a side effect, and that raises an
error on a machine with no credentials.

Status values are normalised with `str(status).split(".")[-1].lower()`:

*   `queued`, `running` and `new_script` count as **running**.
*   `complete`, `error`, `cancelrequested` and `cancelacknowledged` count as
    **finished**, and their output can be collected.

The runner goes through this cycle once per stage per run:

1.  **Plan.** Build the job object for every needed output and keep only those
    whose cache file is missing. If none remain, return. No Kaggle import, no
    network call. This is why a stranger's rebuild needs no credentials
    (CUJ 1).
2.  **Recover.** Import `kaggle`, authenticate, and read the status of the
    kernel's latest version.
    *   **404:** no version exists yet. Skip to step 3.
    *   **Running:** push nothing this run. For shots, every missing clip falls
        back to Ken Burns. For music, stop with a message, because there is no
        automatic score fallback.
    *   **Finished:**
        1.  Download that version's output.
        2.  Move every file listed in its `manifest.jsonl` that passes
            validation into the cache.
        3.  Plan again.

        This collects outputs that finished after an earlier local deadline.
3.  **Upload inputs (shots only).**
    *   `kaggle/inputs/` is the upload folder. It keeps every keyframe ever
        uploaded, as `<key>.png`, plus `dataset-metadata.json`:

        ```json
        {"id": "<user>/heritage-inputs", "title": "heritage-inputs", "licenses": [{"name": "CC0-1.0"}]}
        ```

    *   Copy in the needed keyframes.
    *   If `dataset_status` returns 404, call `dataset_create_new`. It creates
        a private dataset by default. Otherwise call `dataset_create_version`
        with `version_notes=<run_id>`.
    *   Wait up to 10 minutes for status `ready`. On timeout, every shot job
        falls back to Ken Burns.

    Each new version is a superset of the last, so a job's input is always in
    the newest version.
4.  **Build.** Copy the kernel folder to `kaggle/<name>/build/`, which is
    gitignored.
    *   Replace the line `# __JOBS__` in the copy with two lines:
        `JOBS = [...]` (the planned jobs as JSON) and
        `TIME_BUDGET_MIN = <n>` (170 for Wan, 25 for music).
    *   Write `kernel-metadata.json` from the template.

    The jobs travel inside the pushed script, so they cannot be stale. The
    cache key's `code` hash is taken from the script before this templating.
5.  **Push and poll.** Push with `kernels_push`, then check the status every
    60 s. Stop when the status is finished or the local deadline passes. The
    deadlines are `KAGGLE_DEADLINE_MIN_MUSIC` (default 30) and
    `KAGGLE_DEADLINE_MIN_SHOTS` (default 180).
    *   **Finished:** collect the output as in step 2.
    *   **Deadline passed:** leave the kernel running and log each missing
        output as `fallback`. The next run collects it in step 2.

On the kernel side:

*   The whole kernel body runs inside `try/except BaseException`. Any failure
    is written to the manifest and the kernel exits 0. Every version therefore
    ends `complete`, and its output can always be downloaded.
*   It first reads `nvidia-smi`. If the GPU is not a Tesla T4, it writes
    `status: error, error: "gpu <name>"` for every job and stops.
*   It runs jobs in `JOBS` order: all `9x16` jobs, then the `16x9` jobs.
*   It checks each job's input file. If the file is missing, only that job
    fails.
*   After each output it appends one line to `manifest.jsonl`: `key`,
    `status`, `seconds`, `seed`, `error`. It also writes one `kernel` line
    with the total wall time, so install and download time count in GPU
    minutes.
*   It stops taking new jobs once 80 % of `TIME_BUDGET_MIN` has passed.

Kernel metadata fields:

*   `id`: `<user>/heritage-<name>`
*   `title`: `heritage-<name>`
*   `code_file`
*   `language: "python"`
*   `kernel_type: "script"`
*   `is_private: true`
*   `enable_gpu: true`
*   `enable_internet: true`, needed to download weights and packages
*   `machine_shape: "NvidiaTeslaT4"`
*   `dataset_sources: ["<user>/heritage-inputs"]` (Wan only)

If the smoke test shows that `machine_shape` is ignored, the author selects
the T4 accelerator once on each kernel's Kaggle page. Later pushes keep it.

Kaggle sessions have fixed overheads: install, weight download, and a model
reload per clip, because `generate.py` runs once per job. `make smoke-wan`
measures them on 25 Nov. If the reload dominates, an EXPERIMENTS.md entry
tests calling the model in-process instead.

**GPU budget and cut-down rule.** A 720p clip on a T4 is expected to take
many minutes, so only some shots can move.

1.  The author first sets `animate: "9x16"` on the shots whose `purpose` most
    needs motion.
2.  The author widens that to `"both"`, or to more shots, only as the measured
    time allows.
3.  `shots.py` warns before pushing any shot longer than 6 s. A 5 s clip plus
    a 1.5 s hold cannot cover a longer shot, so its GPU time would be wasted.
4.  Before the release commit, every shot whose clip is still missing is set
    to `"none"`. A stranger's rebuild then makes no Kaggle call (CUJ 1).
5.  DESIGN.md explains every shot that moves in 9:16 but not in 16:9.

### Keyframes and consistency

The image model is the constant `KEYFRAME_MODEL` in `keyframes.py`. It
defaults to `@cf/black-forest-labs/flux-2-klein-4b`. The model id is part of
every keyframe's cache key.

1.  **Reference.**
    *   For each character, generate one front-view image at 1024×1024 using
        the character's seed. The prompt is: `reference_prompt`, then the
        character description, then `style_block`, then "front view, neutral
        background".
    *   The author views the image and sets `golden_reference`.
    *   `keyframes.py` refuses to generate a shot's keyframes until every
        character in that shot has a golden reference.
2.  **Keyframes.**
    *   Generate one keyframe per shot per ratio: 768×1344 for 9:16 and
        1344×768 for 16:9.
    *   The prompt is `image_prompt`, then each character's description, then
        `style_block`, joined with ". ".
    *   Each character's golden reference is downscaled to 512×512 and sent as
        `input_image_0`, `input_image_1` and so on, up to 4.
    *   Both ratios share the prompt, the references and `image_seed`. A seed
        does not give the same composition at two resolutions, so consistency
        comes from the prompt and the references.
3.  **Pass rule.** The smoke test checks whether the reference images are
    honoured:
    *   It generates one shot twice with the same seed, once with its
        reference and once without.
    *   The author records in EXPERIMENTS.md whether the face matches the
        reference.
4.  **Fallback.** Switch `KEYFRAME_MODEL` to
    `@cf/black-forest-labs/flux-1-schnell` if the smoke test shows either of
    these:
    *   klein is unavailable;
    *   the pass rule fails.

    schnell takes a JSON body of `prompt`, `steps: 8` and `seed`. It returns a
    square base64 image, which `cloudflare.py` centre-crops to each ratio. G6
    then weakens to "same text and seed", and FAILURES.md records why.

### Assembly

Assembly is pure FFmpeg, driven from Python, and runs once per ratio. W×H is
the output size: 1080×1920 for 9:16, 1920×1080 for 16:9.

Every FFmpeg call runs with the repository root as its working directory and
uses relative paths. The project path contains spaces and a curly apostrophe,
and FFmpeg filter strings cannot take those unescaped.

Assembly writes no `runs.jsonl` lines, because it calls no model. Its
fallbacks are printed in an end-of-run summary and written to
`outputs/final/fallbacks.txt`.

1.  **Timeline.** `build_timeline(sb, durations)` takes the narration
    durations as a dict, so it can be tested without audio files.
    *   Each shot's narration starts 0.3 s into the shot.
    *   The shot lasts `max(duration_s, 0.3 + narration_s + 0.5)`.
    *   Assembly checks that the total plus the 3 s end card is 60–90 s. If
        not, it fails and lists each shot's overrun.
    *   The edit is cut to the narration, not the music. Professionals cut
        picture to the voice track, and the score is fitted to the timeline
        in step 4.
2.  **Picture per shot.**
    *   **With a Wan clip:**
        *   Trim 0.25 s from each end.
        *   If the shot is longer than the clip, hold the last frame for up to
            1.5 s with `tpad=stop_mode=clone`.
        *   If the shot is longer still, it uses Ken Burns instead, and the
            fallback is listed.
    *   **With Ken Burns:** read the keyframe as a single frame, without
        `-loop 1`, then apply:

        ```text
        scale=2W:2H,
        zoompan=z='zf+(zt-zf)*on/(d-1)':x=X:y=Y:d=D:fps=24:s=2Wx2H,
        scale=W:H
        ```

        *   `D = round(24 × shot length)`.
        *   `zf` and `zt` are `zoom_from` and `zoom_to`.
        *   X and Y come from `pan`. The axis the pan does not move stays
            centred at `(iw-iw/zoom)/2`, or `(ih-ih/zoom)/2` for y.

            | `pan` | Expression |
            | --- | --- |
            | `none` | both axes centred |
            | `right` | `x=(iw-iw/zoom)*on/(d-1)` |
            | `left` | `x=(iw-iw/zoom)*(1-on/(d-1))` |
            | `down` | the `right` expression on y |
            | `up` | the `left` expression on y |
    *   Every picture is scaled to cover W×H, then centre-cropped:
        `scale=W:H:force_original_aspect_ratio=increase,crop=W:H`.
3.  **Join.** Join the shots with the concat demuxer. Add a 3 s end card: a
    black background with two `drawtext` lines in white Noto Sans at 64 px,
    using `fontfile=assets/fonts/NotoSans-Regular.ttf`. The lines are "Made
    with AI" and the list of models, fixed in code.
4.  **Audio.**
    1.  Resample every source to 48 kHz stereo.
    2.  Place each narration WAV at its timeline position with `adelay`,
        then mix them into one voice track.
    3.  Bring the voice to about −16 LUFS and the music to about −24 LUFS
        before mixing.
    4.  Trim the music to the timeline with `atrim`, and fade it out over the
        last 2 s with `afade`. If the score is shorter, pad it with silence
        and print a warning.
    5.  `asplit` the voice into two copies. One copy is the sidechain key for
        `sidechaincompress` on the music. The other is mixed with the ducked
        music in `amix=inputs=2:normalize=0`.
    6.  Ducking starts at threshold 0.02, ratio 6, attack 100 ms and release
        1500 ms. These values are tuned by ear and logged in EXPERIMENTS.md.
    7.  Render the mix to a WAV, measure it with `loudnorm`, then normalise
        it with a second, linear `loudnorm` pass at I = −14 and TP = −1.5
        while encoding to AAC. A single pass measured −15.2 LUFS on a 67 s
        test cut, outside G5. Two passes measured −14.7 LUFS and −1.34 dBTP.
5.  **Subtitles.**
    *   Write `outputs/final/subtitles_en.srt` with one cue per narrated shot,
        from narration start to narration end, at least 1.5 s. Text is wrapped
        by `common.wrap_subtitle()` (`textwrap.wrap(width=40)`), the same
        function `validate.py` uses.
    *   Burn in with `subtitles=outputs/final/subtitles_en.srt:fontsdir=assets/fonts:force_style='PlayResX=W,PlayResY=H,FontName=Noto Sans,FontSize=F,MarginV=M,Outline=3'`.
        Setting `PlayResX`/`PlayResY` to the output size makes F and M pixels.
        `original_size` does not: SRT input keeps libass's 288-line canvas,
        and a test frame rendered the text off the top of a 9:16 frame
        (25 Nov). With PlayRes set, frame grabs at both ratios showed two
        lines low in the frame:

        | Ratio | F | M |
        | --- | --- | --- |
        | 9:16 | 56 | 260 |
        | 16:9 | 56 | 60 |

    *   Check one frame grab, and record any change in EXPERIMENTS.md.
6.  **Export.** H.264, `yuv420p`, 24 fps, AAC 48 kHz and `+faststart`, to
    `outputs/final/film_9x16.mp4` and `outputs/final/film_16x9.mp4`.

### Secrets and data handling

*   Keys come only from `.env` and `~/.kaggle/kaggle.json`, and both stay out
    of git.
*   GitHub push protection is turned on for the repository.
*   The Kaggle inputs dataset is private, which is the default for
    `datasets create`.
*   Free-tier Gemini may use inputs to improve its products. Only narration
    lines are sent to it. ETHICS.md lists, for each provider, exactly what is
    sent:
    *   Gemini: narration text;
    *   Cloudflare: image prompts and reference images;
    *   Kaggle: keyframes and motion prompts.

    It also records that the family agreed to this.

## Alternatives Considered

### Alternative A: Cache-only `make film` with a manual GPU notebook

*   **Mechanism**: The author runs the Kaggle notebook by hand, and it saves
    hash-named outputs. `make film` downloads whatever matches and uses Ken
    Burns for the rest.
*   **Pros**: Least orchestration code. A stranger needs no Kaggle account.
*   **Cons**: `make film` cannot produce a new clip. If the notebook and the
    local code compute keys differently, every clip silently drops to Ken
    Burns.
*   **Reason for rejection**: A manual GPU step fails the module's requirement
    that one documented command runs the pipeline end to end. That requirement
    is part of the 20-point software-engineering criterion.

### Alternative B: Cache-only default plus a separate `make gpu` target

*   **Mechanism**: `make film` behaves as in Alternative A. A second target,
    `make gpu`, pushes jobs for missing outputs.
*   **Pros**: A stranger can always rebuild, and the author still gets a
    remote run with logs.
*   **Cons**: Two entry points to build, test and document in about 2.5 days.
*   **Reason for rejection**: The committed cache already lets a stranger
    rebuild with one command (CUJ 1), so the second target adds work without
    adding a capability.

### Alternative C: 16:9 master with a centre crop for 9:16

*   **Mechanism**: Generate everything in landscape. The vertical cut keeps
    the centre 56 % of the width.
*   **Pros**: Half the keyframes and clips.
*   **Cons**: The main 9:16 submission loses 44 % of every frame's width. Any
    off-centre subject or sideways camera move leaves the frame.
*   **Reason for rejection**: The main submission's framing matters more than
    the saved generation. Keyframes are cheap, and clips are limited by the
    `animate` field.

### Alternative D: 9:16 master with a blurred pillarbox for 16:9

*   **Mechanism**: Generate in portrait. The 16:9 cut places the frame over a
    blurred, enlarged copy of itself.
*   **Pros**: Half the keyframes and clips, and full framing for 9:16.
*   **Cons**: The 16:9 export never fills its frame, and wide establishing
    shots lose their sense of place.
*   **Reason for rejection**: Both exports are graded. Native 16:9 keyframes
    cost one extra image per shot, and a 16:9 shot without a clip still uses
    Ken Burns over its own native keyframe.

### Alternative E: Recraft for keyframes and image-to-video

*   **Mechanism**: Call Recraft's API, on a paid plan the author holds, in
    place of Cloudflare FLUX and Kaggle Wan.
*   **Pros**: Removes the Kaggle queue and T4 render time from the critical
    path.
*   **Cons**:
    *   A paid key means a stranger cannot regenerate those stages at zero
        cost.
    *   It is unconfirmed whether app credits cover API use.
    *   The credit cost per video clip is unmeasured.
*   **Reason for rejection**: The pipeline stays on the free stack so a
    stranger can reproduce it. An open-vs-paid comparison remains possible as
    optional ceiling work.

## Risks & Mitigations

*   **Deadline (about 2.5 days).** The schedule and cut line in the Detailed
    Implementation Plan come first. The floor film (Ken Burns, real score,
    subtitles) is locked by the end of 25 Nov, and Wan work starts only after
    that.
*   **Wan 2.2 at 720p on a T4.** The T4 has no native bf16 and no
    FlashAttention-2. Each clip takes many minutes, or may run out of memory.
    *   Mitigations: the kernel patches attention to PyTorch SDPA and the
        dtype to fp16; `make smoke-wan` measures one clip before any shot is
        planned to move; `animate` limits the clip count; Ken Burns covers
        every shot without a clip.
    *   If the runtime does not run at all, that is recorded in FAILURES.md
        and the film ships on Ken Burns.
*   **Kaggle is the only GPU host.** The recover step collects late outputs,
    and the kernel's time budget saves partial work. Music runs first, so a
    Kaggle failure shows up on 25 Nov.
*   **No score if ACE-Step fails.** Stage order surfaces the failure early. The
    explicit `use_placeholder` flag ships the film with a recorded spec breach
    rather than a hidden one.
*   **Free-tier daily limits (Cloudflare about 50–170 images, Gemini TTS).**
    *   Mitigations: the cache means no image or line is generated twice; a
        429 that names a daily limit is not retried; the smoke test records
        the real limits in COSTS.md; experiments use fixed seeds and few
        shots.
*   **FLUX.2 klein unavailable, or ignoring the reference image.** Fall back to
    schnell with crops, as described in Keyframes and consistency, and record
    it.
*   **TTS quality in the chosen language.** A native speaker listens once to
    the radio cut. Failures are recorded in FAILURES.md.
*   **Consent.** `validate.py` refuses a real person without a consent heading
    in ETHICS.md.
*   **Privacy.** Only narration text goes to free-tier Gemini, with the
    family's recorded agreement. `make prune` keeps rejected likenesses out of
    the public repository.
*   **Leaked keys.** GitHub push protection, and `.env` is gitignored.

## Non-Functional Requirements

*   **Security and privacy**: see Secrets and data handling, and Risks &
    Mitigations.
*   **Performance**:
    *   GPU time is the limit. There is one Wan render per clip at the
        storyboard's fixed size, one kernel push per stage per run, and a
        kernel time budget.
    *   Local stages are bounded by API latency.
    *   Assembly time is estimated at a few minutes per ratio and is measured
        into COSTS.md.
*   **Rollback**: Every output is content-addressed. Reverting
    `storyboard.json` (and, after a prune, `outputs/`) in git and re-running
    restores the earlier film from cache with no model calls.

## Future Improvements

*   **720p everywhere, or a faster GPU.** Animate every shot in both ratios if
    a larger GPU becomes available.
*   **Second language.** A parallel storyboard in Afaan Oromo or Tigrinya, with
    the TTS failures recorded.
*   **Open vs paid benchmark.** The same shot through Wan and a paid model,
    with a blind test of at least 5 people.
*   **Packaged tool.** The pipeline as a CLI another person can point at their
    own storyboard.

--------------------------------------------------------------------------------

## Detailed Implementation Plan

### Schedule and cut line

| When | Work | Ends with |
| --- | --- | --- |
| 24 Nov | Group 1 (skeleton, smoke test) and Group 2 (contract, narration, radio cut) | `make radio` plays; user test 1 booked |
| 25 Nov morning | User test 1; storyboard changes; Group 3a (keyframes, music runner, minimal shots stage) | DESIGN.md test 1 notes |
| 25 Nov evening | **Floor film**: `make film` with every shot on Ken Burns and the chosen score | Both MP4s play end to end |
| **cut line** | Everything after this row starts only once the floor film plays | |
| 25 Nov night – 26 Nov | Group 3b (`make smoke-wan`, Wan kernel, shots push), as quota allows | At least one 9:16 shot uses a Wan clip; the count is recorded in COSTS.md |
| 26 Nov | Group 4 (docs, measurement, report); user test 2; walkthrough; post | Both assignments submitted by 23:59 EAT |

### Group 1: Skeleton and smoke test (24 Nov)

#### 1. `Makefile` (Create)

*   **Type / Scope**: Build entry point.
*   **Proposed Changes**:
    *   At the top: `export RUN_ID := $(shell date -u +%Y%m%dT%H%M%S)-$(shell openssl rand -hex 3)`.
        Every recipe line then sees the same value.
    *   Targets:
        *   `film`: prints `RUN_ID=$(RUN_ID)`, then runs `validate`,
            `keyframes`, `narration`, `music`, `shots`, `assemble`. Each is a
            separate `python -m pipeline.<stage>` call, so a failure names its
            stage.
        *   `smoke`: `python -m pipeline.smoke`.
        *   `smoke-wan`: `python -m pipeline.shots --smoke` (Group 3b).
        *   `validate`: `python -m pipeline.validate storyboard.json`.
        *   `radio`: `validate`, `narration`, then `assemble --radio`.
        *   `costs`: `python -m pipeline.costs`.
        *   `prune`: `python -m pipeline.prune`.
        *   `test`: `python -m pytest tests`.
    *   There is no `clean` target. Wiping the cache would spend free-tier
        quota regenerating every output.

#### 2. `requirements.txt` (Create)

*   **Type / Scope**: Python dependencies.
*   **Proposed Changes**:
    *   Packages: `jsonschema`, `google-genai`, `requests`, `kaggle`,
        `python-dotenv`, `pytest`.
    *   Versions are pinned with `pip freeze` once the smoke test passes.
    *   FFmpeg is a system requirement, named in the README.

#### 3. `.gitignore` (Create)

*   **Type / Scope**: Git config.
*   **Proposed Changes**:
    *   Ignore `.env`, `__pycache__/`, `.venv/`, `kaggle/inputs/`,
        `kaggle/*/build/` and `outputs/assemble/tmp/`.
    *   Any output file over 95 MB is added here by name. GitHub's file limit
        is 100 MB, and the 5 MB gap is a safety margin.

#### 4. `.env.example` (Create)

*   **Type / Scope**: Config template.
*   **Proposed Changes**:
    *   `GEMINI_API_KEY=`, `CLOUDFLARE_ACCOUNT_ID=`, `CLOUDFLARE_API_TOKEN=`.
    *   `KAGGLE_DEADLINE_MIN_MUSIC=30` and `KAGGLE_DEADLINE_MIN_SHOTS=180`.
        The same defaults are set in code, so a `.env` with only the first
        three lines works.
    *   The Kaggle username is read from `kaggle.json`.

#### 5. `pipeline/__init__.py` (Create)

*   **Type / Scope**: Package marker, empty.

#### 6. `pipeline/common.py` (Create)

*   **Type / Scope**: Shared helpers.
*   **Proposed Changes**:
    *   `load_storyboard(path) -> dict`.
    *   `cache_key(job: dict) -> str`: SHA-256 of canonical JSON, first 16 hex
        characters.
    *   `file_hash(path) -> str`.
    *   `output_path(stage, key, ext) -> Path`.
    *   `write_atomic(path, data: bytes)`: writes `<path>.tmp`, then
        `os.replace`.
    *   `wrap_subtitle(text) -> list[str]`: `textwrap.wrap(text, width=40)`.
    *   `log_call(**fields)`: appends one line with the fields in the Call log
        table. It reads `run_id` from `RUN_ID`, or uses `adhoc` if unset.
    *   `with_retry(fn, ctx: dict, sleep=time.sleep)`: follows the retry rules
        in the Technical Plan.
        *   The status code is read from `.response.status_code` for
            `requests.HTTPError` and Kaggle API errors, and from `.code` for
            `google.genai.errors.APIError`.
        *   `requests.Timeout` and `ConnectionError` are retried.
        *   `ctx` carries `stage`, `shot_id` and `ratio`.
    *   `PRICES`: a dict mapping model to `{unit, usd}`. The units are
        `image`, `audio_second` and `t4_gpu_hour`. Each entry's source and
        date are in COSTS.md.

#### 7. `pipeline/cloudflare.py` (Create)

*   **Type / Scope**: Provider client.
*   **Proposed Changes**:
    *   `generate_image(model, prompt, seed, width, height,
        input_images: list[Path]) -> bytes`.
    *   For `flux-2-klein-4b`, send a multipart POST to
        `https://api.cloudflare.com/client/v4/accounts/{id}/ai/run/{model}`
        with the fields `prompt`, `width`, `height`, `seed` and
        `input_image_0..3`. Each input is downscaled to 512×512 first.
    *   For `flux-1-schnell`, send a JSON POST with `prompt`, `steps: 8` and
        `seed`, then centre-crop the square result.
    *   Both decode the base64 image in the JSON response. The exact field
        name is unverified, and the smoke test reads it from the first
        response. The result is saved as PNG. If the provider returns JPEG,
        FFmpeg re-encodes it.

#### 8. `pipeline/smoke.py` and `pipeline/smoke_kaggle.py` (Create)

*   **Type / Scope**: Provider and tool smoke test (Phase 1).
*   **Proposed Changes**: Four checks. Each is logged with `stage: smoke` and
    printed as pass or fail.
    1.  **Gemini:** one Flash text call, and one TTS sentence in the chosen
        language, wrapped as WAV.
    2.  **Cloudflare:** one klein image at 768×1344 with an input image, and
        one at 1344×768. This answers the Open Question "FLUX.2 klein on
        Workers AI". It also runs the reference pass rule from Keyframes and
        consistency. If klein fails, the check reports a fallback to schnell,
        not a failure.
    3.  **Kaggle:** `smoke_kaggle.py` has its own minimal push, poll and pull
        code, because `kaggle_runner.py` arrives in Group 3a. It pushes the
        kernel from item 9, waits for it, and reads `gpu.txt`. This checks
        authentication, the GPU type and output download.
    4.  **FFmpeg:** `ffmpeg -filters` must list `subtitles`, `drawtext`,
        `zoompan` and `sidechaincompress`.

    The results go into COSTS.md and FAILURES.md: the daily limits each
    provider states, and every 429 body seen.

#### 9. `kaggle/smoke/smoke_kernel.py` and `kaggle/smoke/kernel-metadata.template.json` (Create)

*   **Type / Scope**: Kaggle kernel.
*   **Proposed Changes**:
    *   The script runs `nvidia-smi` and writes its output to
        `/kaggle/working/gpu.txt`.
    *   The metadata uses the fields listed in the Technical Plan's Kaggle
        section, with `title: heritage-smoke`, `enable_internet: false` and
        no `dataset_sources`.

#### 10. `tests/test_common.py` (Create)

*   **Type / Scope**: Unit tests. This file also creates `tests/`, so pytest
    always has a folder to collect from.
*   **Proposed Changes**:
    *   `cache_key` is stable when dict key order changes.
    *   `write_atomic` leaves no `.tmp` file behind.
    *   `wrap_subtitle` gives at most 40 characters per line.
    *   `with_retry`, using an injected no-op `sleep`:
        *   retries a 503, then succeeds;
        *   honours `Retry-After`;
        *   retries `requests.Timeout`;
        *   fails at once on a 400, on a 429 with body
            `"quota_metric": "generate_requests_per_day"`, and on a 429 with
            body `"daily free allocation"`;
        *   gives up after 4 attempts.

### Group 2: Contract, narration and radio cut (24 Nov)

#### 11. `schema/storyboard.schema.json` (Create)

*   **Type / Scope**: JSON Schema, draft 2020-12.
*   **Proposed Changes**:
    *   Exactly the fields, types, ranges, patterns, enums and nullability in
        the Technical Plan's contract section.
    *   `additionalProperties: false` on every object.
    *   An `if`/`then` on each character: `real_person: true` requires
        `consent_ref` to be a string.

#### 12. `pipeline/validate.py` (Create)

*   **Type / Scope**: Validation step.
*   **Proposed Changes**:
    *   Validates against the schema, then runs the code checks from the
        contract section.
    *   Prints each error as `<JSON path>: <message>`, using paths such as
        `$.shots[3].narration`. A code check uses the nearest path, for
        example `$.shots` for the total duration.
    *   Exits 1 on any error.

#### 13. `storyboard.json` (Create)

*   **Type / Scope**: The contract.
*   **Proposed Changes**:
    *   8–12 shots for the author's story, each with a `purpose`.
    *   The coding agent drafts it against the schema, and the author edits
        it.
    *   It changes after each user test. DESIGN.md cites each change by
        commit hash.
    *   Every shot starts with `animate: "none"`.

#### 14. `pipeline/narration.py` (Create)

*   **Type / Scope**: Narration stage.
*   **Proposed Changes**:
    *   `narration_job(sb, shot) -> dict` holds the model, the voice, the text
        with the style instruction as `speech_metadata.style`, and the language.
    *   For each missing output:
        1.  Call Gemini TTS through `with_retry`.
        2.  Write `outputs/narration/<key>.wav` atomically.
    *   `narration_seconds(path)` reads the duration from the WAV header.

#### 15. `pipeline/assemble.py` (Create)

*   **Type / Scope**: Assembly stage.
*   **Proposed Changes**:
    *   `build_timeline(sb, durations)` returns
        `list[{shot_id, start_s, length_s, voice_start_s}]` and includes the
        60–90 s assertion.
    *   `write_srt(timeline, sb, path)`.
    *   `render_shot(shot, ratio, length_s) -> Path`: the clip with the hold
        rule, or Ken Burns. It uses `shots.clip_job` to find cached clips.
    *   `pick_music(sb) -> Path`, in this order:
        1.  `use_placeholder` gives the placeholder track.
        2.  `chosen` gives that candidate.
        3.  Otherwise candidate 0, with a warning.
    *   `mix_audio(timeline, music_path) -> Path`.
    *   `export(ratio)`.
    *   `--radio` writes `outputs/final/radio_cut.mp4`: black 1080×1920,
        narration over the placeholder track, ducked and loudness-normalised,
        no subtitles.
    *   Intermediates go to `outputs/assemble/tmp/`.
    *   Every FFmpeg call runs with the repository root as `cwd` and uses an
        argument list.
    *   The end-of-run fallback summary is printed and written to
        `outputs/final/fallbacks.txt`.

#### 16. `assets/placeholder_music.wav` (Create)

*   **Type / Scope**: Temp track. It is generated locally from FFmpeg's own
    signal sources, so no third-party licence applies.
*   **Proposed Changes**: Generated once with:

    ```bash
    ffmpeg -f lavfi -i "sine=f=220:d=120" -f lavfi -i "anoisesrc=d=120:a=0.02" -filter_complex "amix=inputs=2,volume=0.3" -ar 48000 -ac 2 assets/placeholder_music.wav
    ```

#### 17. `assets/fonts/NotoSans-Regular.ttf` (Create)

*   **Type / Scope**: Font, SIL Open Font License.
*   **Proposed Changes**: Downloaded from Google Fonts. `drawtext` uses it via
    `fontfile=`, and `subtitles` via `fontsdir=`.

#### 18. `DESIGN.md` (Create)

*   **Type / Scope**: Documentation.
*   **Proposed Changes**:
    *   Audience, viewing context and intended feeling.
    *   The "how might we" sentence.
    *   A reason for each shot, pointing to its `purpose`.
    *   User test 1 (radio cut) and user test 2 (near-final cut). Each records:
        who took part (at least 3 people), the date, what they said, what
        changed, and the storyboard commit hash.
    *   Why any shot moves in 9:16 but not in 16:9.

#### 19. `ETHICS.md` (Create, before any real person's likeness or voice is generated)

*   **Type / Scope**: Documentation and grading gate.
*   **Proposed Changes**:
    *   One heading per real person, used as their `consent_ref`. Under each:
        what was consented to, the date, how consent was recorded, and where
        the recording is kept outside the repository.
    *   The family's agreement that narration text goes to free-tier Gemini.
    *   The data sent to each provider, as listed in "Secrets and data
        handling".
    *   A licence table for every model and output:
        *   Wan 2.2: Apache 2.0.
        *   FLUX.2 klein 4B: Apache 2.0.
        *   ACE-Step 1.5: as stated on its model card at install.
        *   Gemini: its terms of use.
    *   The labelling plan: the end card, the platform's AI toggle, and
        watermarks left intact.

#### 20. `tests/test_validate.py` and `tests/fixtures/` (Create)

*   **Type / Scope**: Unit tests and fixtures.
*   **Proposed Changes**:
    *   `storyboard_valid.json` passes.
    *   Each invalid fixture fails at the given path:

        | Fixture | Expected path |
        | --- | --- |
        | `storyboard_13_shots.json` | `$.shots` |
        | `storyboard_no_narration.json` | `$.shots[0]` |
        | `storyboard_bad_character.json` | `$.shots[0].characters[0]` |
        | `storyboard_95s.json` | `$.shots` |
        | `storyboard_long_subtitle.json` | `$.shots[0].narration.subtitle_en` |
        | `storyboard_real_person_no_consent.json` | `$.characters[0].consent_ref` |
        | `storyboard_bad_frames.json` | `$.wan.frames` |

#### 21. `tests/test_assemble.py` (Create)

*   **Type / Scope**: Unit tests, using a dict of durations and no audio
    files.
*   **Proposed Changes**:
    *   A shot is extended when narration plus padding is longer than its
        `duration_s`.
    *   Start times are cumulative.
    *   A total outside 60–90 s raises an error.
    *   SRT text wraps at 40 characters, with at most 2 lines per cue.
    *   `pick_music` returns the placeholder, the chosen candidate, or
        candidate 0, as its three cases require.

### Group 3a: Keyframes, music and minimal shots stage (floor, before the cut line; 25 Nov)

#### 22. `pipeline/keyframes.py` (Create)

*   **Type / Scope**: Keyframes stage, including the reference step.
*   **Proposed Changes**:
    *   `KEYFRAME_MODEL` constant.
    *   `reference_job(sb, character)` and `keyframe_job(sb, shot, ratio)`,
        as described in the Technical Plan section "Keyframes and
        consistency".
    *   Generates missing references first. If any character has
        `golden_reference: null`, it prints the reference paths and exits
        with code 2, which stops `make film` (CUJ 0).
    *   Then generates missing keyframes into `outputs/keyframes/<key>.png`.
        References live in the same folder.

#### 23. `pipeline/kaggle_runner.py` (Create)

*   **Type / Scope**: Shared Kaggle cycle.
*   **Proposed Changes**:
    *   `run_stage(kernel_dir, jobs: list[dict], inputs: dict[str, Path],
        deadline_min, time_budget_min) -> dict[key, status]`.
    *   Implements the five-step cycle in the Technical Plan section "Kaggle
        orchestration", in this order: Plan, Recover, Upload, Build, Push and
        poll.
    *   `kaggle` is imported inside the function, after Plan finds missing
        jobs.
    *   `KaggleApi` calls go through `with_retry`. A 404 from `kernels_status`
        or `dataset_status` is handled before retry classification.
    *   The job entry schema:
        *   Wan: `{key, input: "<key>.png", prompt, seed, size, frames}`.
        *   Music: `{key, caption, duration_s, bpm, keyscale, seed}`, where
            `keyscale` comes from `music.key`.
    *   Logs one `runs.jsonl` line per job, with `gpu_s` from the manifest,
        plus one `kernel` line per push.

#### 24. `kaggle/music/music_kernel.py` and `kaggle/music/kernel-metadata.template.json` (Create)

*   **Type / Scope**: Kaggle kernel.
*   **Proposed Changes**:
    *   Keeps the kernel-side rules from the Technical Plan: the try/except
        wrapper, the GPU check, the manifest, and `TIME_BUDGET_MIN`.
    *   Installs ACE-Step 1.5 from its official repository with pip.
    *   For each job, renders an instrumental 48 kHz stereo WAV to
        `/kaggle/working/<key>.wav`.
    *   The repository URL, model id and inference call are chosen inside
        this file only. Each choice is recorded in EXPERIMENTS.md and
        ETHICS.md. `use_placeholder` is the fallback if ACE-Step does not run.
    *   Metadata: the fields from the Technical Plan, with
        `title: heritage-music` and no `dataset_sources`.

#### 25. `pipeline/music.py` (Create)

*   **Type / Scope**: Music stage.
*   **Proposed Changes**:
    *   `music_job(sb, seed)` builds one job per seed, then calls `run_stage`
        with `KAGGLE_DEADLINE_MIN_MUSIC` and a 25-minute budget.
    *   With `use_placeholder: true`, it skips Kaggle entirely.
    *   If no candidate exists after the run, it exits 1 with a message that
        names `use_placeholder`.

#### 26. `pipeline/shots.py` (Create, minimal part)

*   **Type / Scope**: Shots stage, the part needed by the floor film.
*   **Proposed Changes**:
    *   `clip_job(sb, shot, ratio)`: model, payload (prompt, seed, size,
        frames), keyframe file hash, and the hash of the untemplated kernel
        script.
    *   When no shot has `animate` other than `none`, it exits 0 without any
        Kaggle import.

#### 27. `tests/test_runner.py` (Create)

*   **Type / Scope**: Unit tests with no network. `KaggleApi` is replaced by
    a fake.
*   **Proposed Changes**:
    *   With a full cache and `KAGGLE_CONFIG_DIR` pointing at an empty
        folder, `run_stage` returns and `kaggle` is not in `sys.modules`.
    *   A 404 from `kernels_status` skips Recover. A 404 from
        `dataset_status` calls `dataset_create_new`.
    *   A manifest with one `ok` line and one `error` line moves only the
        `ok` file. A zero-byte output is rejected.
    *   A `running` status means nothing is pushed.
    *   `test_missing_input`: a job whose `input` names a key that does not
        exist is reported as `fallback`.
    *   Templating replaces exactly one `# __JOBS__` line. The `code` hash
        does not change when the jobs change.
    *   `keyframes.py` exits with code 2 when a golden reference is missing.

### Group 3b: Moving shots (after the cut line; 25 Nov night – 26 Nov)

#### 28. `kaggle/wan/wan_kernel.py`, `kaggle/wan/patch_attention.py` and `kaggle/wan/kernel-metadata.template.json` (Create)

*   **Type / Scope**: Kaggle kernel.
*   **Proposed Changes**:
    *   Keeps the kernel-side rules from the Technical Plan.
    *   Setup:
        1.  `git clone` the official Wan2.2 repository.
        2.  Install its requirements without `flash_attn`:
            `grep -v flash_attn requirements.txt | pip install -r /dev/stdin`.
        3.  `python patch_attention.py`. This rewrites
            `flash_attention()` in `wan/modules/attention.py` to call
            `torch.nn.functional.scaled_dot_product_attention`, because the
            T4 has no FlashAttention-2. It also sets the TI2V-5B config's
            `param_dtype` to `torch.float16`, because the T4 has no native
            bf16.
        4.  `pip install "huggingface_hub==<pinned>"`, then
            `hf download Wan-AI/Wan2.2-TI2V-5B --local-dir /kaggle/temp/wan`.
    *   For each job, it runs this argument list with `subprocess.run`:
        `["python", "generate.py", "--task", "ti2v-5B", "--size", size,
        "--frame_num", str(frames), "--ckpt_dir", "/kaggle/temp/wan",
        "--offload_model", "True", "--t5_cpu", "--image", input_path,
        "--prompt", prompt, "--base_seed", str(seed), "--save_file",
        out_path]`.
    *   If the patched runtime still fails, every job records the error, the
        film ships on Ken Burns, and FAILURES.md explains why.
    *   Metadata: the fields from the Technical Plan, with
        `title: heritage-wan` and `dataset_sources: ["<user>/heritage-inputs"]`.

#### 29. `pipeline/shots.py` (Modify: add the Kaggle push)

*   **Type / Scope**: Shots stage, full version.
*   **Proposed Changes**:
    *   Builds jobs for shots with `animate` set to `9x16` or `both`: all
        9:16 jobs first, then all 16:9 jobs.
    *   Warns before pushing any shot longer than 6 s.
    *   Calls `run_stage` with `KAGGLE_DEADLINE_MIN_SHOTS` and a 170-minute
        budget.
    *   Always exits 0, so assembly runs (CUJ 3).
    *   `--smoke` pushes one 704×1280 job for the first shot and prints the
        measured time. That time sets how many shots can move.

#### 30. `tests/test_cache_keys.py` (Create)

*   **Type / Scope**: Unit tests.
*   **Proposed Changes**:
    *   Changing `s04.image_prompt` changes only `s04`'s keyframe keys.
    *   Changing a character description changes the keyframe keys of every
        shot that shows that character.
    *   Changing a keyframe file's bytes changes its clip key.
    *   Changing `wan.frames` changes every clip key.
    *   Changing narration text changes no clip key.

### Group 4: Measurement, documents and release (26 Nov)

#### 31. `pipeline/costs.py` (Create)

*   **Type / Scope**: Report generator.
*   **Proposed Changes**:
    *   Groups `runs.jsonl` by stage and model.
    *   Sums model calls, cache hits, fallbacks and failures.
    *   Reports mean latency, GPU minutes (from `kernel` lines) and
        `cost_usd_est`.
    *   Writes the table between `<!-- costs:start -->` and
        `<!-- costs:end -->` in COSTS.md.
    *   If Group 4 is not done by midday on 26 Nov, drop the p90 latency and
        the marker rewrite first.

#### 32. `pipeline/prune.py` and `tests/test_prune.py` (Create)

*   **Type / Scope**: Release helper and its test.
*   **Proposed Changes**:
    *   Computes every job key for the current storyboard, including all 3
        music candidates.
    *   Deletes files whose names are not current keys, only in
        `outputs/keyframes/`, `outputs/narration/`, `outputs/music/` and
        `outputs/shots/`.
    *   Never touches `outputs/final/` or `outputs/assemble/`.
    *   Prints what it deleted.
    *   The test runs prune on a temporary tree and checks what survives.

#### 33. `COSTS.md` (Create)

*   **Type / Scope**: Documentation.
*   **Proposed Changes**:
    *   The free-tier limits and 429 bodies found by the smoke test.
    *   The generated table.
    *   The source and date of each `PRICES` entry.
    *   How many shots were animated, and why.

#### 34. `EXPERIMENTS.md` (Create)

*   **Type / Scope**: Documentation, at least 10 entries.
*   **Proposed Changes**:
    *   Each entry records: id, date, hypothesis, change (with a fixed seed
        when comparing), result, `run_id`, and decision.
    *   Candidate entries:
        *   the reference pass rule;
        *   style block vs none;
        *   ducking settings;
        *   subtitle size check;
        *   TTS style instruction variants;
        *   one TTS call per shot vs one call split by timestamps;
        *   ACE-Step caption length and the choices made in its kernel;
        *   Ken Burns vs Wan on a static shot;
        *   Wan per-clip reload overhead.

#### 35. `FAILURES.md` (Create)

*   **Type / Scope**: Documentation.
*   **Proposed Changes**: Each entry records what broke, the error text, what
    was tried, the fix or workaround, and the linked `runs.jsonl` lines.

#### 36. `ARCHITECTURE.md` (Create)

*   **Type / Scope**: Documentation.
*   **Proposed Changes**: Adapted from this design's Technical Plan:
    *   the stage diagram and run order;
    *   the contract;
    *   cache keys and atomic writes;
    *   the log fields;
    *   the retry rules;
    *   the Kaggle cycle and its fallbacks.

#### 37. `README.md` (Create)

*   **Type / Scope**: Documentation.
*   **Proposed Changes**:
    *   What the pipeline makes.
    *   Prerequisites:
        *   Python 3.11.
        *   FFmpeg with libass and freetype, for example
            `brew install ffmpeg-full` or a static build. Then check
            `ffmpeg -filters`.
        *   The accounts.
    *   Setup:
        1.  `pip install -r requirements.txt`.
        2.  Copy `.env.example` to `.env`.
        3.  Place `kaggle.json`. This is needed only when an output is missing
            from `outputs/` and must be regenerated on Kaggle.
    *   `make film`, and the first-run steps from CUJ 0.
    *   What it costs, pointing to COSTS.md.
    *   How to change one shot.
    *   A map of the repository.
    *   Links to the film and the post.

#### 38. `report/report.md` (Create)

*   **Type / Scope**: Source of the separately submitted report, exported to
    PDF.
*   **Proposed Changes**:
    *   The items the module asks for, in its order, each citing evidence in
        the repository:
        *   what was made, and for whom;
        *   what the audience said;
        *   the hardest problem and its solution;
        *   one suggested practice that helped, and one that did not;
        *   ceiling work;
        *   next steps.
    *   It states that Claude Code, which is paid, was used instead of the
        free agents the module suggests: Gemini Flash or the free Claude
        models through Antigravity CLI or OpenCode.

### Verification Plan

*   **Unit tests:** `make test` passes. Tests are added as each group is
    implemented.
*   **Contract:** `make validate` passes on `storyboard.json`, and every
    invalid fixture fails at its listed path.
*   **Smoke:** `make smoke` reports pass, or a documented fallback, for all
    four checks. The Open Questions it covers are answered in COSTS.md or
    FAILURES.md.
*   **Selective regeneration (CUJ 2):**
    *   Precondition: the previous run logged no `fallback` lines.
    *   Edit `s04.image_prompt` and run `make film`.
    *   Then run:

        ```bash
        R=$(tail -1 runs.jsonl | jq -r .run_id); grep "\"$R\"" runs.jsonl | jq -c 'select(.status=="ok" or .status=="retry" or .status=="failed") | .shot_id' | sort -u
        ```

        It must print only `"s04"`.
*   **Kaggle fallback (CUJ 3):** `pytest tests/test_runner.py::test_missing_input`
    passes. On one real run where a clip is missing, both films are still
    written and `outputs/final/fallbacks.txt` lists the shot.
*   **Clean clone (CUJ 1):**
    1.  Clone into a new folder.
    2.  `pip install -r requirements.txt`.
    3.  Set up `.env`, with no `kaggle.json`.
    4.  Run `make film`.

    Every new `runs.jsonl` line for the printed `RUN_ID` is `cache_hit`. Both
    MP4s are produced, and no error mentions Kaggle.
*   **Film spec (G5):**
    *   `ffprobe` gives a duration of 60–90 s for both files.
    *   `ffmpeg -i <file> -vn -af loudnorm=print_format=json -f null -`
        reports `input_i` between −15 and −13, and `input_tp` ≤ −1.
    *   `ffmpeg -sseof -1 -i <file> -frames:v 1 outputs/assemble/tmp/end.png`
        shows the end card.

--------------------------------------------------------------------------------

*Drafted with EGM*
