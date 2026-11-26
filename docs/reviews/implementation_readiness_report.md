# Stage 9: Implementation Readiness Test (Round 1)

*   **Target**: `docs/designs/heritage_short_pipeline.md`, DetailedRange
    lines 508–870 (read with lines 1–507 as background)
*   **Standard**: `implementation-readiness-standard.md`
*   **Context**: `docs/references/module_5399.md`
*   **Reviewers**: each ran in a fresh context, and all completed.
    *   Implementation Readiness (IR): 3 Blockers, 16 Majors, 8 Nits
    *   Codebase Details (CD), which checked the named external APIs and tools:
        4 Blockers, 14 Majors, 12 Nits
    *   Style (SY): 7 Majors, 13 Nits
*   **Verdict**: **FAIL** against the Zero-Decision Rule. After deduplication:
    5 Blockers, 14 Majors and 16 Nits. The file list and the shape of each
    stage are sound. The plan leaves decisions open where risk is highest: the
    Wan and ACE-Step kernels, the Cloudflare model, Kaggle's failure handling,
    and assembly's numbers and formats. CD also found two outright technical
    errors (R1, R2).
*   **Tags**:
    *   *(gone if S8 triage adopted)* marks an item that disappears if you adopt
        the Stage 8 triage in `intermediate_zoom_out_report.md`.
    *   *(also C#/S5 M#)* marks an item an earlier stage already raised.

--------------------------------------------------------------------------------

## Blockers

### R1. Gemini TTS returns raw PCM, not WAV (CD-B1; IR-N2). Confidence: high

*   **Problem**: The bytes arrive with no header (`audio/L16`, 24 kHz, mono,
    16-bit). Saved straight to `.wav`, they cannot be read by ffprobe or
    FFmpeg, so assembly fails.
*   **Fix**:
    *   Wrap the bytes with stdlib `wave` (1 channel, sample width 2, 24000 Hz).
    *   Compute the duration as `len(pcm) / 48000`. This drops the ffprobe call
        and the duration sidecar file.
    *   Gemini TTS has no style parameter. The style instruction is prepended to
        the prompt text, so state that.

### R2. The Cloudflare FLUX model is not chosen, and the likely model cannot do what the plan assumes (IR-B2, CD-B3) *(also C13, S5 M6)*. Confidence: medium-high

*   **Problem**:
    *   `flux-1-schnell` takes only `prompt` and `steps`. It has no
        width/height, no seed and no reference image, and it returns a square
        JPEG as base64 inside JSON.
    *   The FLUX.2 models on Workers AI take multipart form data with `width`,
        `height`, `seed` and `input_image_0..n`.
    *   The request encoding, the native ratios, the seed in the cache key and
        golden-reference conditioning (G6) all depend on which model is chosen.
    *   The output is saved as `.png`, but schnell returns JPEG.
*   **Fix**:
    *   Name the model id. CD suggests `@cf/black-forest-labs/flux-2-klein-4b`
        (Apache 2.0); the 9B variant is non-commercial.
    *   State the request and response format, the pixel sizes for each ratio,
        and the output format.
    *   Assign the crop fallback to a specific file.

### R3. The Wan kernel is a design gap, not an instruction (IR-B1, CD-M5) *(also C6, S5 M2)*

*   **Undecided**:
    *   whether to use the official repo's `generate.py` or diffusers
        `WanImageToVideoPipeline`
    *   the Hugging Face repo id
    *   dtype (T4 has no bf16, so fp16) and the offload mode
    *   how the 2× T4 is used
    *   `frames`, which is part of the cache key but has no value anywhere
    *   the hold rule when a clip is shorter than its shot
*   **Technical errors**:
    *   The official `generate.py` accepts only `1280*704` and `704*1280` for
        ti2v-5B, so 832×480 is rejected there.
    *   Frame counts must be 4n+1 (for example, 121 frames is about 5 s at
        24 fps).
    *   A T4 has no FlashAttention-2.
    *   A 720p clip on a T4 is likely to take tens of minutes, so 6 clips per
        90-minute batch is very unlikely.
*   **Fix**: Give the install commands, model id, pipeline call, dtype, offload
    flags, sizes and frames, the GPU strategy, the per-clip time assumption and
    the hold rule.
*   **Note**: The Stage 8 Z2 proposal (fix 480p, drop 720p) conflicts with the
    official runtime's size limits. Under Z2, the runtime would have to be
    diffusers, or the fixed resolution would have to be 704×1280 / 1280×704.

### R4. The reference stage's cache keys collide, and the golden reference is ambiguous per ratio (IR-B3, CD-B2) *(gone if S8 Z4 adopted)*

*   **Problem**:
    *   The reference key has no `view` field, so the front, three-quarter and
        side views all get the same key. Two of the three become false cache
        hits or overwrite each other.
    *   `golden_reference` is a single path, but references are generated in
        both ratios.
*   **Fix**: Add `view` to the key and to the prompt, and make the golden
    reference either per ratio or one image for both. Alternatively, drop
    stage 0 as Stage 8 Z4 proposes.

### R5. The Kaggle failure path does not deliver CUJ 3 (IR-M3, CD-B4) *(also C7, S5 M4)*. Confidence: medium-high

*   **Problem**:
    *   When the local deadline is reached, the kernel is still running.
        `kaggle kernels output` returns nothing for an unfinished version, so
        "clips that finished are kept" is false.
    *   The kernel keeps spending quota.
    *   The next push to the same slug replaces the earlier version's output.
    *   It is unverified whether output survives an `error` status, such as a
        CUDA out-of-memory kill.
    *   The verification step that sets a 1-minute deadline leaves an orphan
        GPU run behind.
*   **Fix**:
    *   Before pushing, check the previous version. If it is still running,
        skip the push. If it is complete, pull its output first (as Stage 8
        proposed).
    *   State whether batches run one after another.
    *   Replace the 1-minute test with one that cannot leave a run behind.

--------------------------------------------------------------------------------

## Major

| # | Finding | Fix | Sources |
| --- | --- | --- | --- |
| R6 | **Kaggle CLI details are wrong.** <ul><li>The status values are `queued / running / complete / error / cancelRequested / cancelAcknowledged`; there is no `cancelled`.</li><li>The CLI prints human-readable text, not JSON.</li><li>`kernel-metadata.json` needs a `title` whose slug matches its `id`.</li><li>Dataset privacy is set when you run `datasets create`; it is not a metadata field.</li><li>`datasets version` needs `-m`.</li><li>The template file has to be renamed to `kernel-metadata.json`.</li><li>Nothing says how to detect the first run, when `create` must be used instead of `version`.</li></ul> | Use the `KaggleApi` Python class, or state exactly how output is parsed. Fix the metadata. | IR-M3, IR-M5, CD-M1, CD-M3 |
| R7 | **Dataset propagation race.** `datasets version` returns before the new version is processed, so the run-id guard fails every batch. | Poll `datasets status` until `ready`, or embed the job list in the kernel source (S8 triage), which removes the race. | IR-M4, CD-M2 *(gone if S8 adopted; also S5 M5)* |
| R8 | **The accelerator choice is deferred to a smoke test that cannot answer it.** `enable_gpu: true` has historically defaulted to a P100. | Decide now, or add a tiny GPU push that runs `nvidia-smi` to the smoke test. | IR-M4, CD-M4, SY-2 |
| R9 | **The ACE-Step kernel is unspecified.** No install, model id, inference API, output sample rate or format, or GPU settings. The licence is cited as MIT without a source; ACE-Step v1 was Apache 2.0. | Specify these as in R3, and cite the model card. | IR-M6, IR-N8, CD-N, SY-4 |
| R10 | **Job, manifest and templating contracts are undefined.** <ul><li>There is no `jobs.json` schema for either kernel.</li><li>There is no manifest line schema.</li><li>Nothing says how `RUN_ID` and `BATCH_ID` are substituted.</li><li>Both kernels share the dataset slug, and the plan does not say so.</li><li>`(shot_id, ratio)` tuples cannot be JSON keys.</li></ul> | Define the schemas and placeholder tokens, and use keys like `"s04/9x16"`. | IR-M5, IR-N3, CD-Nit |
| R11 | **Resolution lives in `.env`, so CUJ 1 breaks and there is no per-shot 720p.** | Move it into `storyboard.json`. Stage 8 Z2 fixes it at a single value. | IR-M2, CD-M6 *(also S5 M1, C4)* |
| R12 | **Keyframe key misses the character description**, and the order and separator used to join the prompt are not stated. | Key on the fully built prompt or payload. | IR-M1 *(also C8)* |
| R13 | **Final length can exceed 90 s.** Narration extension plus the 3 s end card can push a planned 88 s film past 90 s. Nothing says whether the end card counts. | Assert the actual timeline length in assembly. | IR-M10, CD-M7 *(also C10)* |
| R14 | **The audio mix graph is incomplete.** <ul><li>There is no `asplit` of the voice, which must feed both the sidechain and the mix.</li><li>There is no `amix` of voice and ducked music.</li><li>There is no resample from 24 kHz.</li><li>The loudness-match method is not stated.</li><li>Single-pass `loudnorm` is not reliable.</li><li>A 300 ms attack is slow for speech.</li></ul> | Spell out the filter graph. Keep single-pass `loudnorm` with a measurement afterwards, as Stage 8 proposed. | IR-M8, CD-M8 |
| R15 | **Music length against the timeline is undefined.** It could loop, trim or fade. Behaviour under the end card is also undefined. | Trim and fade with `atrim`/`afade` to the timeline (S8). | IR-M7, CD-M11 *(also C10)* |
| R16 | **Output geometry is unspecified.** <ul><li>There is no final size for the 16:9 film.</li><li>There is no scale, crop or pad rule for Wan and FLUX sizes.</li><li>The `zoompan` expressions are missing (`d`, `fps`, x/y for each pan value; upscale before `zoompan` to avoid jitter).</li><li>The hold filter is not named (`tpad=stop_mode=clone`).</li><li>The end card text, font and layout are missing; `drawtext` does not wrap.</li><li>When narration starts within a shot is not stated.</li><li>The radio cut's processing is not defined.</li></ul> | Give exact values. | IR-M8, CD-M9, CD-Nit |
| R17 | **Subtitles.** <ul><li>Nothing says what happens to text over 80 characters.</li><li>The filters need `fontsdir` and `force_style`, and the margin value is missing.</li><li>The project path contains spaces and a curly apostrophe, which will break filter-graph escaping unless FFmpeg runs from the repo root with relative paths.</li><li>Neither the libass nor the freetype build requirement is checked.</li></ul> | Set `maxLength: 80` (S8). Run FFmpeg with the repo root as working directory. Have the smoke test check `ffmpeg -filters` for `subtitles`, `drawtext`, `zoompan` and `sidechaincompress`. | IR-M9, CD-M10, SY-14 *(also C14)* |
| R18 | **Schema and retry contracts are too loose to write code from.** <ul><li>Required and nullable fields are not stated.</li><li>The id pattern, value ranges and `seeds` length are missing.</li><li>`with_retry` says 3 attempts but lists 4 backoff delays.</li><li>The error types `fn` raises from `requests` and `google-genai` are not given.</li><li>`retry` log lines lack the stage, shot and ratio they belong to.</li><li>The Kaggle CLI is not retried.</li><li>Gemini `response_schema` rejects `additionalProperties`; use `response_json_schema` or a simpler schema.</li></ul> | Pin all of these down. | IR-M11, IR-M13, CD-Nit |
| R19 | **Tests and phasing.** <ul><li>All tests land in Group 4, so `make test` fails in Groups 1–3 (pytest exits with code 5).</li><li>Test 37 needs per-stage key functions that are never defined.</li><li>There are no tests for `with_retry`, `log_call`, runner manifest parsing, the placeholder path or the music length.</li><li>The JSON path format is undefined.</li><li>The fixtures are not named.</li><li>"Pinned to exact versions" gives no versions.</li></ul> | Move each test next to its code. Name the key functions. Pin the versions. | IR-M12, IR-M14, IR-M16, CD-M12, CD-M14, SY-10 |

**Also Major (verification and privacy):**

*   **R20. Privacy contradiction** *(also C12)* (IR-M15). `script.py` sends the
    family treatment to free-tier Gemini, and narration sends the story text
    there too. Decide on scrubbing, paid billing, or a documented acceptance
    in ETHICS.md.
*   **R21. The verification steps cannot be measured** (SY-6, SY-7, SY-18,
    CD-M13, CD-Nit).
    *   **Loudness check**: no tolerance is given, and the command
        `ffmpeg -i <file> -af loudnorm=print_format=json -f null -` is
        incomplete as written.
    *   **End card**: no method is given for checking it.
    *   **Fallback check**: nothing defines its start state.
    *   **CUJ 1**: the evidence should be that every new line is `cache_hit`.
    *   **CUJ 2**: the check fails if any earlier fallbacks are still pending.
        Add the precondition "no outstanding fallbacks".

--------------------------------------------------------------------------------

## Nits

*   `RUN_ID` must be `export RUN_ID := $(shell …)` in the Makefile.
    Behaviour when it is unset is not defined. (IR-N1, CD)
*   Cloudflare API tokens have no fixed prefix, so the secret grep needs a
    real regex. Consider the Kaggle key too. Stage 8 Z5 replaces this check
    with GitHub push protection. (IR-N4, CD, SY-9)
*   `outputs/assemble/tmp/` and `storyboard.draft.json` are not gitignored.
    The 95 MB rule is reactive. (IR-N5, CD)
*   There is no FFmpeg command for the placeholder track and no source for the
    Noto font. Nothing says whether `use_placeholder` skips Kaggle. (IR-N6)
*   `KAGGLE_USERNAME` duplicates `kaggle.json`. Nothing says where the
    deadline variable is read. (IR-N7)
*   The Gemini TTS free-tier daily limit may be in the low tens of requests.
    Record it in the smoke test or COSTS.md. (CD-Nit, medium-low confidence)
*   "Each group ends in something playable" is true only of Groups 2 and 3,
    and the "Edit" heading in Group 4 has no editing files. (SY-1)
*   The music fallback sentence contradicts itself. (SY-3)
*   The "six required sections" of the report: the module does not number
    them, "and its solution" is missing, and "ceiling work" and "next steps"
    are merged. (SY-5)
*   Wording:
    *   "paid-in-quota"
    *   "hand-owned contract"
    *   "the aspect Open Question"
    *   "four providers" should be "four checks"
    *   "longer than what"
    *   "dBTP"
    *   test entries missing the "Type / Scope" line
    *   a redundant clause in file 20

    (SY-8, SY-11 to SY-13, SY-15 to SY-17, SY-19, SY-20)

--------------------------------------------------------------------------------

## Effect of the Stage 8 triage on this report

If the Stage 8 triage is adopted (drop stage 0, fix the resolution in the
storyboard, embed jobs in the kernel source, check the previous kernel before
pushing, payload hashing, length assert, `maxLength`):

*   **Removed**: R4 and R7.
*   **Mostly resolved**: R5, R11, R12, R13, R15 and the subtitle-length part
    of R17.
*   **Still needing written decisions**: R1, R2, R3, R6, R8, R9, R10, R14, R16,
    R18, R19, R20 and R21.
    *   All of them pin down values, model ids or commands.
    *   None of them adds new architecture.
