# Goldfish Annotated Review Report

Status: resolved (2026-11-24). Auto accept applied all 34 PROPOSE FIX items. Author decisions: D1 = (b) official Wan repo at 720p; D2 = (a) one reference per character with FLUX.2 klein 4B; D3 = (a) animate none|9x16|both; D4 = (a) accept and document free-tier Gemini, cut script.py. CONTEST (4) and DECLINE (6) items were not applied.

**Target:** `docs/designs/heritage_short_pipeline.md` (full file, lines 1–870)

**Sources:**

*   `zoom_out_report.md` (S5)
*   `comprehension_report.md` (S6)
*   `critic_report.md` (C)
*   `intermediate_zoom_out_report.md` (S8)
*   `implementation_readiness_report.md` (R)

Findings that several reports raised are merged into one item here. The
consolidated ids from each report are listed against each item.

**Counts:**

| Category | Items | What it means |
| --- | --- | --- |
| ESCALATE (author decision) | 4 | Each needs your choice before its edits can be written |
| PROPOSE FIX | 34 | |
| CONTEST | 4 | |
| DECLINE | 6 | |

--------------------------------------------------------------------------------

## Part 1: Author decisions (ESCALATE)

The reviewers raised these as valid gaps, and each has more than one answer
that holds up. I do not pick one. The fixes in Part 2 that depend on a
decision are marked "per D#".

### [D1] Wan runtime and resolution. Sources: R3 (Blocker), S5 M1, S8 Z2, C6, R11. Severity: Blocker

*   **Problem:** Several Wan settings are undefined, and the planned 480p
    size is invalid:
    *   The runtime, model id, dtype, frame count and hold rule are not
        specified.
    *   The official `generate.py` accepts only 1280×704 and 704×1280 for
        TI2V-5B, so the plan's 832×480 is invalid there.
    *   S8 proposes fixing one resolution and dropping the 720p re-render
        pass.
*   **Options** (unranked):
    *   **(a) Diffusers at 480p.** Use `WanImageToVideoPipeline` with
        `Wan-AI/Wan2.2-TI2V-5B-Diffusers`, fp16 and CPU offload, at 832×480
        and 480×832. Upscale in FFmpeg at export.
        *   Trade-off: fastest on a T4. 480p is below the model's native
            resolution, so quality is unverified.
        *   Fails when the smoke clip at 480p comes out broken or blurry.
    *   **(b) Official repo at 720p.** Use `generate.py` at 1280×704 and
        704×1280, fp16, with `--offload_model True`.
        *   Trade-off: this is the supported path and gives native quality.
        *   Likely to take tens of minutes per clip on a T4, so only a few
            shots get animated.
        *   Fails when memory or time runs out.
    *   **(c) Diffusers at 720p.** As (a), but at 1280×704 and 704×1280.
        *   Trade-off: native quality without the official repo's install
            steps.
        *   Has the same speed risk as (b).
*   **Applies to every option:**
    *   Resolution lives in `storyboard.json` as one value, not in `.env`.
    *   There is no 720p re-render pass.
    *   Frames are 121 (4n+1, about 5 s at 24 fps).
    *   A shot longer than its clip is held with `tpad=stop_mode=clone`, up to
        1.5 s. Beyond that, the shot switches to Ken Burns.
    *   The smoke test renders one timed clip.

### [D2] Keyframe model and the reference stage. Sources: R2 (Blocker), R4 (Blocker), C13, S5 M6, S8 Z4. Severity: Blocker

*   **Problem:**
    *   No FLUX model is named.
    *   FLUX.1 schnell takes no size, seed or reference image.
    *   The reviewer reports that FLUX.2 klein 4B on Workers AI takes
        multipart form data with `width`, `height`, `seed` and
        `input_image_0..n`, under Apache 2.0. Confidence is medium-high, so
        the smoke test must confirm it.
    *   Stage 0's three views share one cache key.
*   **Options** (unranked):
    *   **(a) Klein 4B with a small reference stage.** Use
        `@cf/black-forest-labs/flux-2-klein-4b`. Stage 0 makes one front
        reference per character, not three views and two ratios. That image
        is passed as `input_image_0` for both ratios.
        *   Trade-off: this is the only route to real conditioning across
            shots. It keeps one manual approval step.
        *   Fails if the smoke test shows image input is unavailable or
            ignored.
    *   **(b) Klein 4B with no reference stage.** Same model, but consistency
        comes from the style block, the seed and the character text only.
        *   Trade-off: one stage, one gate and one manual step fewer.
        *   Character drift across shots is likely. G6 becomes "same text and
            seed", not "conditioned on a reference".
*   **Applies to both options:**
    *   Name the model id, the multipart request, the sizes (768×1344 for
        9:16 and 1344×768 for 16:9) and the decode step.
    *   If the smoke test shows klein is unavailable, fall back to
        `flux-1-schnell` with square output, then a centre crop. That crop
        lives in `cloudflare.py`.

### [D3] Which ratio gets motion. Sources: S5 M8, S6 #3, S8 triage. Severity: Major

*   **Problem:**
    *   Every fallback shot is pushed to Kaggle again on every run, which
        breaks CUJ 1's promise of zero model calls.
    *   Dual-ratio Wan runs double the GPU time.
*   **Options** (unranked):
    *   **(a) One field per shot,
        `animate: "none" | "9x16" | "both"`.** Push all 9:16 jobs before any
        16:9 jobs. Before committing, set shots that fell back to `none`.
        *   Trade-off: half the GPU time for the main submission.
        *   The two exports can differ in motion, so DESIGN.md must say so.
    *   **(b) Keep `animate: bool` for both ratios.** Add only the step of
        setting fallen-back shots to `false` before committing.
        *   Trade-off: the two exports match.
        *   Uses double the GPU time.
        *   Fails when the quota covers fewer shots than planned.
*   **Note:** both options keep decision 3, native framing for both ratios.

### [D4] Free-tier privacy. Sources: C12, R20, S5 N5. Severity: Major

*   **Problem:**
    *   The design says private family details stay out of free endpoints.
    *   The narration is the family story, and it must go to free-tier Gemini
        TTS. Free-tier inputs may be used for training.
    *   `script.py` would also send the treatment there.
*   **Options** (unranked):
    *   **(a) Accept the risk and document it.** Keep the free tier. Record in
        ETHICS.md which text reaches which provider, and that the family
        agreed. Cut `script.py`, since it is not a required stage.
        *   Trade-off: no cost.
        *   Fails if the family does not agree.
    *   **(b) Attach billing for Gemini calls.** On the paid tier, inputs are
        not used for training. Keep `script.py`.
        *   Trade-off: needs a payment card, which the module says most
            trainees cannot attach.
    *   **(c) Write narration that leaves out private details.** Leave out
        names, places and other identifying details. Cut `script.py`.
        *   Trade-off: no cost and no data concern.
        *   The story becomes less specific.

--------------------------------------------------------------------------------

## Part 2: PROPOSE FIX

The edits are listed in the order they will be applied.

### Structure and standard compliance

**[F1] Add a `## Risks & Mitigations` section** (C1, Major; DC/ST)

*   **Justification:** The feature-spec standard requires this section.
*   **Edit:** After Alternatives Considered, add a short list of risks. Each
    risk points to its mitigation:
    *   Deadline: mitigated by the schedule (F2).
    *   Cloudflare and Gemini daily quotas: the cache and smoke-test numbers
        in COSTS.md.
    *   Wan on a T4: D1 and the smoke clip.
    *   Kaggle as the only GPU host: the Ken Burns fallback and F12.
    *   TTS quality in the chosen language: the native-speaker check and
        FAILURES.md.
    *   The consent gate: F20.
    *   Privacy: D4.
    *   Write no likelihood or impact table (S8).

**[F2] Add a schedule with a cut line** (S8 Z1, Major)

*   **Justification:** The schedule protects the 80 points that are not
    software engineering.
*   **Edit:** At the top of the Detailed Implementation Plan, add the
    schedule:
    *   24 Nov: Groups 1 and 2 and the radio cut.
    *   By end of 25 Nov: user test 1, plus a Ken Burns film with the real
        score.
    *   26 Nov: documents, user test 2, walkthrough, post and report.
    *   Wan clips sit above the cut line. They are started only once the
        floor film plays.
    *   Rename Group 4 so its heading no longer says "Edit" (SY-1).

**[F3] Replace "choice A" and "choice 3" with plain labels** (C3, S6 #1,
Major)

*   **Edit:** Change line 194 to "chosen over Alternatives A and B". Change
    line 197 to "chosen over Alternatives C and D".

**[F4] Rewrite each rejection as its trade-off** (C2, Major)

*   **Edit:** Remove "Rejected by author:" everywhere. Use these reasons:
    *   A: "A manual GPU step fails the one-command requirement."
    *   B: "Two entry points to build and document in 2.5 days, and the
        committed cache already covers a stranger's rebuild."
    *   C: "Centre-cropping the main 9:16 submission loses the edges of the
        frame for every shot."
    *   D: "The 16:9 export never fills its frame."
    *   E: "Needs a paid key, so a stranger cannot regenerate the film at zero
        cost. Video credit cost is unmeasured."

**[F5] Make the stage list consistent and add a Narration subsection** (C15,
S6 #7, ST-4/5, Major)

*   **Edit:**
    *   Number validation as step V, not a stage.
    *   Number the stages 1–5 to match the module: keyframes, shots, music,
        narration, assembly.
    *   Treat the reference sheet as part of keyframes (per D2).
    *   Call `script.py` "the drafting helper" (S6 #14).
    *   Add a "### Narration" subsection with:
        *   one TTS call per shot;
        *   the style instruction prepended to the text;
        *   the PCM-to-WAV wrap (F9);
        *   duration computed as `len(pcm)/48000`;
        *   for an unsupported language, log the failure in FAILURES.md and
            follow D4 or change the language;
        *   a definition of the radio cut: narration placed on the timeline
            over the placeholder track on black, with ducking and loudnorm
            but no subtitles.

**[F6] Define the call log once** (C15, SY-5, Major)

*   **Edit:**
    *   Define `runs.jsonl` as one line per stage output event.
    *   Only `ok`, `retry` and `failed` lines are real model calls.
    *   In G4, use the field names from the list: `cache_key`, `attempt`,
        `cost_usd_est`.
    *   Turn the field list into a table (ST-13).
    *   `cost_usd_est` cites the price table and its date in COSTS.md (n12).

**[F7] Fix the Kaggle prerequisite for a stranger's rebuild** (C15, SY-6,
DC-N3, Major)

*   **Edit:** CUJ 1 says `kaggle.json` is needed only if a cache entry is
    missing. Verification step CUJ 1 becomes: every new `runs.jsonl` line for
    this `run_id` is `cache_hit`. Add `pip install` to that step's setup.

**[F8] Link and summarise the brief** (S6 #5, S6 #6, ST-15, Major)

*   **Edit:**
    *   Link `../references/module_5399.md` from the Overview.
    *   Replace "frontier lane", "Nano Banana", "Omni Flash" and "Lyria 3.5"
        with "paid frontier models, which the cohort may share through an
        organisation key".
    *   Define "floor", "Phase 1" and the report's required sections by
        pointing to the module summary.

### Technical errors

**[F9] Wrap Gemini TTS output as WAV** (R1, Blocker)

*   **Edit:** File 13 says: wrap the raw `audio/L16` 24 kHz mono PCM with the
    stdlib `wave` module (1 channel, sample width 2, 24000 Hz). Compute the
    duration from the byte length. Remove the duration sidecar and the
    ffprobe call (S5 N2).

**[F10] Kaggle CLI facts** (R6, Major)

*   **Edit:**
    *   Use the `KaggleApi` Python class, not CLI text parsing.
    *   The statuses are `queued`, `running`, `complete`, `error`,
        `cancelRequested` and `cancelAcknowledged`.
    *   Kernel metadata needs a `title` whose slug matches its `id`.
    *   Dataset privacy is set by `datasets create` (private by default).
        `dataset-metadata.json` holds `id`, `title` and `licenses`.
    *   Detect the first run by checking whether the dataset exists.
    *   The build step renames `kernel-metadata.template.json` to
        `kernel-metadata.json`.

**[F11] Embed the job list in the kernel source; make the dataset
content-addressed** (S5 M5, C7, R7, R10, S8, Major)

*   **Edit:**
    *   The runner writes `JOBS = [...]` into the build copy of the kernel
        script, replacing a `# __JOBS__` placeholder line.
    *   The dataset `heritage-inputs` is append-only and holds `<key>.png`
        keyframes.
    *   Each kernel job checks that its input exists. A missing input fails
        that job only.
    *   Delete the run and batch id guard, the dataset-propagation Open
        Question, and `jobs.json`.
    *   Define the `JOBS` entry schema for Wan and for music, and the
        `manifest.jsonl` line schema (`key`, `status`, `seconds`, `seed`,
        `error`).
    *   Before pushing, poll `datasets status` until it reports `ready`.

**[F12] Check the previous kernel before pushing; give the kernel a time
budget** (S5 M3/M4, C7, R5, S8, Blocker)

*   **Edit:**
    *   The runner first reads the status of the previous kernel version:
        *   `running` or `queued`: do not push. This run uses Ken Burns.
        *   `complete` or `error`: pull its output and cache whatever the
            manifest lists, then plan the new jobs.
    *   The kernel stops taking jobs once 80 % of its time budget has passed,
        and exits cleanly so `/kaggle/working` is saved.
    *   Remove the 6-clip batches. One push per stage per run.
    *   Run music before shots (S5 N9).
    *   The weights still download from Hugging Face (S8 Z3).
    *   Wrap Kaggle API calls in `with_retry`.
    *   CUJ 3 changes to match: clips that finish after the local deadline
        are collected on the next run.
    *   Replace the 1-minute deadline test with a kernel that has a 2-job
        list, one job of which has a missing input. Expect one `ok` line and
        one `fallback` line.

**[F13] Fix the accelerator setting in metadata** (R8, Major)

*   **Edit:** Add `"machine_shape": "NvidiaTeslaT4"` to the template, a
    medium-confidence field name. The smoke test pushes a 1-minute kernel
    that prints `nvidia-smi` and confirms the GPU type. This answers the Open
    Question.

**[F14] Specify the ACE-Step kernel** (R9, Major)

*   **Edit:**
    *   Install from the official ACE-Step 1.5 repository with pip.
    *   Use the model id from its model card, fp16, and one GPU.
    *   Output is 48 kHz stereo WAV.
    *   One job per seed.
    *   Change the licence text to "per the model card (to be confirmed at
        install)" and remove the unsourced "MIT" (SY-4, N8).

### Cache and contract

**[F15] Use one cache key: the hash of the exact request** (C8, R12, S8,
Major)

*   **Edit:**
    *   Replace the per-stage key table with: key =
        `cache_key({"stage", "model", "payload", "inputs": {name: file_hash},
        "code": file_hash(kernel script)})`.
    *   The payload is the dict sent to the provider, which includes the fully
        built prompt.
    *   Define one `*_job(storyboard, shot, ratio)` builder per stage in that
        stage's module. Test 37 uses these builders.

**[F16] Make cache writes atomic and validate outputs** (C9, S8, Major)

*   **Edit:**
    *   Write to `<path>.tmp`, then `os.replace`.
    *   When pulling from Kaggle, keep a file only if it is non-zero in size
        and `ffprobe` decodes it.

**[F17] Assert the final length; fit the music to the timeline** (C10, R13,
R15, Major)

*   **Edit:**
    *   After the timeline is built, assert that 60 ≤ total + 3 s end card
        ≤ 90. If not, fail with the per-shot overruns.
    *   The end card counts toward the length.
    *   Trim the music to the timeline with `atrim`, and add a 2 s `afade`
        out that ends with the end card.
    *   A shorter score is padded with silence and logged as a warning.
    *   Add a sentence saying the edit is cut to the narration, and
        explaining why.

**[F18] Tighten the schema** (R18, C14, Major)

*   **Edit:** In file 8, list:
    *   required fields;
    *   nullable fields (`golden_reference`, `chosen`, `chosen_reason`);
    *   id pattern `^s(0[1-9]|1[0-2])$`;
    *   `zoom_from` and `zoom_to` between 1.0 and 1.5;
    *   `bpm` between 40 and 200;
    *   `seeds` length 3;
    *   `subtitle_en` `maxLength` 80;
    *   `narration.text` may be an empty string for a silent shot;
    *   the D3 `animate` field;
    *   one top-level `wan` object `{resolution, frames}` per D1.

**[F19] Define the retry contract** (R18, C5 partial, Major)

*   **Edit:**
    *   `with_retry(fn, ctx)`: 1 attempt plus 3 retries, with backoff of 2, 8
        and 30 s.
    *   `fn` raises `requests.HTTPError` or `google.genai.errors.APIError`.
        Both expose a status code.
    *   `ctx` carries the stage, shot and ratio for the `retry` log line.
    *   A 429 whose body names a daily or per-day limit is not retried.

**[F20] Add a minimal consent check** (n11, Nit; fix proposed because the
gate zeroes the film)

*   **Edit:**
    *   Add `characters[].real_person: bool`.
    *   When it is true, require `consent_ref`, a heading in ETHICS.md.
    *   `validate.py` checks that the heading exists in ETHICS.md.

**[F21] Fix the Gemini structured-output schema** (R18, Major)

*   **Edit:** The drafting helper (if kept, per D4) uses
    `response_json_schema`, because `response_schema` rejects
    `additionalProperties`. It validates locally afterwards.

### Assembly

**[F22] Spell out the audio graph** (R14, Major)

*   **Edit:**
    *   Resample everything to 48 kHz.
    *   `asplit` the voice into two copies: one is the sidechain, the other
        goes to `amix`.
    *   `[music][voice_sc] sidechaincompress` produces the ducked music, then
        `amix` the voice and the ducked music.
    *   Before mixing, normalise the voice to −16 LUFS and the music to
        −24 LUFS.
    *   Finish with a single-pass `loudnorm` at I=−14, TP=−1, then measure
        (S8).
    *   Label the ducking values as starting values (n4), with a 100 ms
        attack.

**[F23] Fix the output geometry** (R16, Major)

*   **Edit:**
    *   Final sizes are 1080×1920 and 1920×1080 at 24 fps.
    *   Clips and keyframes are scaled to cover the frame, then centre-cropped
        (`scale=...:force_original_aspect_ratio=increase,crop`).
    *   Ken Burns: upscale the keyframe to 2× the output size first. Then
        `zoompan` with `d=24*length`, `fps=24`, z rising linearly from
        `zoom_from` to `zoom_to`. The x and y expressions move up to 10 % of
        the frame in the chosen pan direction.
    *   The hold rule follows D1.
    *   Narration starts 0.3 s into each shot.
    *   End card: black background, white Noto Sans at 64 px, two
        `drawtext` lines with fixed text ("Made with AI" and the list of
        models).

**[F24] Subtitle rendering** (R17, Major)

*   **Edit:**
    *   Use `subtitles=...:fontsdir=assets/fonts:force_style='FontName=Noto
        Sans,FontSize=14,MarginV=120'` for 9:16 and `MarginV=40` for 16:9.
    *   Run FFmpeg with the repo root as the working directory and relative
        paths, because the project path contains spaces and a curly
        apostrophe.
    *   The smoke test checks `ffmpeg -filters` for `subtitles`, `drawtext`,
        `zoompan` and `sidechaincompress`.
    *   The README names libass and freetype as requirements.

### Plan, tests and docs

**[F25] Put tests in the same group as their code** (R19, Major)

*   **Edit:**
    *   `test_validate` and its fixtures move to Group 2.
    *   `test_timeline` moves to Group 2.
    *   `test_cache_keys` moves to Group 3.
    *   `make test` tolerates an empty test folder in Group 1
        (`pytest || [ $$? -eq 5 ]`).
    *   Add tests for `with_retry` and for runner manifest parsing.
    *   Name the fixture files.
    *   The JSON path format is `$.shots[3].narration`.

**[F26] Pin dependency versions** (R19, IR-M16, Major)

*   **Edit:** State that `requirements.txt` is written with
    `pip freeze` after the smoke test passes. The README lists FFmpeg ≥ 6
    with libass and freetype.

**[F27] Remove the user-test dates from the CUJs; check the Makefile
`RUN_ID`** (IR-N1)

*   **Edit:** Use `export RUN_ID := $(shell date -u +%Y%m%dT%H%M%S)-$(shell
    openssl rand -hex 3)`. `log_call` uses `adhoc` when the variable is unset.

**[F28] Secret protection** (S8 Z5, n10, Nit)

*   **Edit:** Replace the `git grep` claim with GitHub push protection,
    turned on for the repo, plus a grep of the actual `.env` values.

**[F29] Gitignore and prune** (S5 N4, C12 partial, N5)

*   **Edit:**
    *   Ignore `outputs/assemble/tmp/` and `storyboard.draft.json`.
    *   Add `make prune`, which deletes cached files not referenced by the
        current storyboard's keys. Run it before the release commit.
    *   Set one size rule: a file over 95 MB is listed by name in
        `.gitignore`.

**[F30] Make the verification checks measurable** (R21, Major)

*   **Edit:** Each check gets a pass rule:
    *   Loudness: `ffmpeg -i <file> -af loudnorm=print_format=json -f null -`
        must give I between −15 and −13 LUFS, and TP ≤ −1 dBTP.
    *   End card: `ffmpeg -sseof -1 -i <file> -frames:v 1 end.png`, then
        inspect the frame.
    *   CUJ 2 starts with the precondition "no fallback entries outstanding".

**[F31] Fix stale references and loose claims** (S5 N6, S6 #8–12, #15,
SY-1–22, ST-7–11, IR/CD nits)

*   **Edit:** The fixes are text only:
    *   G1 boundary text.
    *   Remove "to be drafted".
    *   Move Future Improvements to an H2.
    *   Define "radio cut" and "near-final cut" at their first use.
    *   Make the 100 MB and 95 MB size rules agree.
    *   Use `s04` for the shot id in the CUJs.
    *   Change "the shots share the seed, so composition stays close" to "the
        shots share the prompt and reference" (n5).
    *   Mark assembly times as estimates.
    *   Write "dBTP".
    *   Give G5 tolerances.
    *   Align the cross-reference to "Keyframes and consistency".
    *   Fix the diagram border, and label the branch that goes straight to
        assembly.
    *   Note that `drawtext` needs `fontfile` and `subtitles` needs
        `fontsdir`.
    *   Wording: "is designed so that", "written documents", "demonstrates",
        use "Ken Burns" after its first definition, and remove the
        tautologies.
    *   Rewrite the music fallback sentence.
    *   Fix the report-section list: no count, add "and its solution", and
        follow the module's order.
    *   Change "four providers" to "four checks".
    *   Give the `index.json` key format as `"s04/9x16"`.
    *   Remove `KAGGLE_USERNAME` (it is read from `kaggle.json`).

**[F32] Record a quota and experiment note** (C5, CD-Nit)

*   **Edit:** The smoke test records the daily limits for Cloudflare and
    Gemini TTS in COSTS.md. Add "one TTS call per shot vs one call split by
    timestamps" as a candidate entry in EXPERIMENTS.md (n13).

**[F33] Write the first-run sequence** (S6 #2, Major)

*   **Edit:** Add CUJ 0, "first run":
    *   `make film` stops after the reference step and asks for
        `golden_reference` (if D2 option a).
    *   Music defaults to candidate 0 with a warning until `music.chosen` is
        set.
    *   The README gets the same three steps.

**[F34] Remove the run-id templating from tracked files** (DC-N7)

*   **Edit:** This is already covered by F11. The build copy goes in the
    gitignored `kaggle/*/build/`. State this in the Technical Plan.

--------------------------------------------------------------------------------

## Part 3: CONTEST

**[X1] C4: put a per-stage budget table in the design** (DC-M3, Major)

*   **Contest:** The design already assigns measured numbers to `COSTS.md`
    (file 30) and derives them from `runs.jsonl` (file 29). A table in the
    design would be guesses that go stale. The schedule (F2) and the cut-down
    rule in D3 cover the schedule risk this finding raises.

**[X2] C11: fall back to the placeholder score automatically** (DC-M10,
S5 M7, Major)

*   **Contest:** The module requires an original score. An automatic
    placeholder would hide a breach of that requirement. The design's manual
    `music.use_placeholder` flag makes the breach an explicit, logged choice.
    F12 (music runs first) moves the risk to 25 Nov.

**[X3] S5 M3: upload the weights as a Kaggle dataset** (Major)

*   **Contest:** With F12 there is one session per stage per run. The weight
    download costs minutes per session. A one-time upload of several GB, plus
    a redistribution note, costs the author more time than it saves (S8 Z3).

**[X4] C6 and CD: one worker per GPU on 2× T4; HunyuanVideo or Colab as a
named fallback** (Major)

*   **Contest:** Ken Burns is the fallback, and the module allows it. Running
    one worker per GPU is a parallelism change made before the smoke clip has
    measured where the time goes. If the smoke clip shows GPU 1 sits idle and
    time is the limit, add this as an experiment (S8).

--------------------------------------------------------------------------------

## Part 4: DECLINE (Nits, recorded only)

*   **n7 / R14:** two-pass `loudnorm`. Measure first, and add the second
    pass only if a check misses (S8).
*   **C12:** a size budget for the committed cache. The prune step (F29) is
    enough.
*   **S5 N7:** the p90 latency and the marker rewrite in `costs.py`. Keep
    them, and cut them first if time is short.
*   **IR-N6:** the source URL for the Noto font. It is found at install
    time.
*   **R8 / C7:** documenting Colab as a backup. Same reason as X4.
*   **SY-20:** "Type / Scope" fields on the test entries. This is cosmetic.
