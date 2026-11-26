# Goldfish Annotated Review Report: Stage 9 Round 2

Status: resolved (2026-11-24). Auto accept applied Q1–Q19 and the 14 batched nits; 2 nits declined.

**Target:** `docs/designs/heritage_short_pipeline.md`, lines 753–1249 (Detailed
Implementation Plan). A few fixes also touch matching lines in the Technical
Plan, lines 1–752.

**Source:** `implementation_readiness_report_r2.md`, from three reviewers:

*   IR: implementation readiness
*   CD: codebase details
*   SY: style

**Counts:** ESCALATE 0, PROPOSE FIX 19 (Q1–Q19), CONTEST 0, DECLINE 2,
PROPOSE FIX (nits, batched) 14.

All 19 Blocker and Major findings are valid. For each one, I checked the
cited lines against the reviewer's claim and the claim held. Three of them
were caused by my round 1 rewrite:

*   Q1: the step order
*   Q3: swapped labels
*   Q6: a hard-coded value

None of the 19 needs an architecture decision. The four author decisions
(D1–D4) stay as they are.

--------------------------------------------------------------------------------

## Blocker

### [Q1] [IR, CD]: A clean clone without `kaggle.json` crashes. Severity: Blocker

*   **Scope:** Kaggle cycle, steps 1–2 (Technical Plan); file 23
    (`kaggle_runner.py`); Verification, CUJ 1.
*   **AI suggestion:** PROPOSE FIX.
*   **Justification:** The cycle runs Recover before Plan. Importing `kaggle`
    authenticates as it loads, so it raises an error when no credentials
    exist. CUJ 1 is a promise the design makes, and this breaks it.
*   **Proposed edit:**
    *   Reorder the cycle so Plan runs before Recover. If no job is missing,
        return before importing `kaggle`.
    *   Recover runs only when jobs are missing.
    *   Import `kaggle` inside `run_stage`.
    *   Add a test to `tests/test_runner.py`: with a full cache and
        `KAGGLE_CONFIG_DIR` pointing at an empty folder, `run_stage` returns
        and `kaggle` is absent from `sys.modules`.

## Major

### [Q2] [IR]: The floor film needs `shots.py`, which is scheduled after the cut line. Severity: Major

*   **AI suggestion:** PROPOSE FIX.
*   **Proposed edit:**
    *   Split file 28. Group 3a gets `shots.py` with `clip_job`, which exits
        0 and contacts Kaggle for nothing when no shot is animated.
    *   Group 3b adds the Kaggle push and `--smoke` to the same file.

### [Q3] [IR, CD, SY]: The cut-line labels are swapped. Severity: Major

*   **AI suggestion:** PROPOSE FIX.
*   **Proposed edit:** Group 3a heading: "floor, before the cut line".
    Group 3b heading: "after the cut line".

### [Q4] [IR]: The first run of a Kaggle stage is undefined. Severity: Major

*   **AI suggestion:** PROPOSE FIX.
*   **Proposed edit:**
    *   Recover treats a 404 from `kernels_status` as "no previous version".
    *   Upload treats a 404 from `dataset_status` as "create with
        `dataset_create_new`".
    *   Both cases are handled before `with_retry` classifies errors. Add both
        to `tests/test_runner.py`.

### [Q5] [IR, CD]: Wan asserts that FlashAttention is installed, and the T4 has no bf16. Severity: Major

*   **AI suggestion:** PROPOSE FIX.
*   **Proposed edit:** In file 27, after the clone:
    *   Install with `grep -v flash_attn requirements.txt | pip install -r
        /dev/stdin`.
    *   Patch `wan/modules/attention.py` so `flash_attention()` calls
        `torch.nn.functional.scaled_dot_product_attention`. The patch is a
        `sed` that replaces the function body, kept in
        `kaggle/wan/patch_attention.py` and run before generation.
    *   Force fp16 by setting the config's `param_dtype` to `torch.float16`
        in the same patch file.
    *   Add a Risks line: if the patched runtime still fails, the film ships
        on Ken Burns and FAILURES.md records why.

### [Q6] [IR, CD, SY]: `--frame_num 121` is hard-coded. Severity: Major

*   **AI suggestion:** PROPOSE FIX.
*   **Proposed edit:**
    *   Pass `--frame_num <frames>`, taken from the job.
    *   Build the command as a `subprocess.run([...])` argument list, so the
        prompt is not shell-quoted.
    *   `validate.py` checks that `frames % 4 == 1`.

### [Q7] [CD]: `zoompan` output size and expressions are missing. Severity: Major

*   **AI suggestion:** PROPOSE FIX.
*   **Proposed edit:** In Assembly step 2:
    *   Upscale the still with `scale=2*W:2*H`.
    *   Then apply `zoompan=z='zf+(zt-zf)*on/(d-1)':d=D:fps=24:s=2*Wx2*H` with
        integer `D=round(24*length)`.
    *   Choose x and y by pan direction:
        *   `none`: `x=(iw-iw/zoom)/2`
        *   `right`: `x=(iw-iw/zoom)*on/(d-1)`
        *   `left`: `x=(iw-iw/zoom)*(1-on/(d-1))`
        *   `down`: same as `right`, on y
        *   `up`: same as `left`, on y
        *   In every case, the other axis stays centred.
    *   Then apply `scale=W:H`.
    *   Read the still as a single frame, without `-loop 1`.

### [Q8] [IR, CD]: Subtitle style values are in script units, not pixels. Severity: Major

*   **AI suggestion:** PROPOSE FIX.
*   **Proposed edit:**
    *   Add `original_size=1080x1920` (or `1920x1080`) to the `subtitles`
        filter, so `FontSize` and `MarginV` are in output pixels.
    *   9:16: `FontSize=48, MarginV=260`. 16:9: `FontSize=44, MarginV=60`.
    *   Verify with one frame grab, and record any change in EXPERIMENTS.md.

### [Q9] [IR, CD]: The schnell fallback drops the seed; model location and reference pass rule are missing. Severity: Major

*   **AI suggestion:** PROPOSE FIX.
*   **Proposed edit:**
    *   The schnell request sends `seed`.
    *   Add a `KEYFRAME_MODEL` constant in `keyframes.py`. It is part of the
        cache key because it is in the job's `model`.
    *   Add a pass rule to the smoke test. Generate one shot with and without
        its reference, at the same seed. The author records in
        EXPERIMENTS.md whether the face matches the reference. If it does
        not, switch `KEYFRAME_MODEL` to schnell.

### [Q10] [IR, CD]: The daily-limit rule matches neither provider. Severity: Major

*   **AI suggestion:** PROPOSE FIX.
*   **Proposed edit:**
    *   Use the predicate: body matches the case-insensitive regex
        `per_?day|daily`.
    *   Add test fixtures with a Gemini-shaped `..._per_day` body and a
        Cloudflare-shaped "daily free allocation" body.
    *   The smoke test records any real body it sees.

### [Q11] [IR]: The `machine_shape` field has no fallback, and there is no GPU check. Severity: Major

*   **AI suggestion:** PROPOSE FIX.
*   **Proposed edit:**
    *   The Wan and music kernels start by reading `nvidia-smi`. If the GPU
        is not a T4, they write `status: error, error: "gpu <name>"` for every
        job and exit.
    *   Fallback: the author selects the T4 accelerator once on the kernel's
        Kaggle page, which later pushes keep. Record this in FAILURES.md if
        needed.

### [Q12] [IR, CD]: Recover depends on unverified behaviour of outputs after an error. Severity: Major

*   **AI suggestion:** PROPOSE FIX.
*   **Proposed edit:**
    *   The kernel body runs inside `try/except BaseException`. Any failure
        is written to the manifest, and the kernel exits 0. Every version
        therefore ends `complete`, and `kernels_output` returns its files.
    *   Remove the Open Question "Kaggle output after an error" and the smoke
        claim that went with it.

### [Q13] [IR, CD]: The time budget has no value; deadline variable names and status handling disagree. Severity: Major

*   **AI suggestion:** PROPOSE FIX.
*   **Proposed edit:**
    *   The runner writes `TIME_BUDGET_MIN = <n>` beside `JOBS`: 170 for
        Wan and 25 for music.
    *   Use the environment variables `KAGGLE_DEADLINE_MIN_MUSIC` (default
        30) and `KAGGLE_DEADLINE_MIN_SHOTS` (default 180), with the defaults
        in code. The Technical Plan uses the same names.
    *   Normalise the status with
        `str(status).split(".")[-1].lower()`.
    *   `cancelrequested`, `cancelacknowledged` and `error` are treated as
        complete-for-collection. `new_script` and `queued` are treated as
        running.

### [Q14] [IR, CD]: The inputs dataset is not append-only, and staging is undefined. Severity: Major

*   **AI suggestion:** PROPOSE FIX.
*   **Proposed edit:**
    *   `kaggle/inputs/` is the upload folder. It keeps every keyframe ever
        uploaded, so each new version is a superset of the last.
    *   It holds `dataset-metadata.json`: `{"id": "<user>/heritage-inputs",
        "title": "heritage-inputs", "licenses": [{"name": "CC0-1.0"}]}`.
    *   A version is created with `version_notes=<run_id>`.
    *   Wait up to 10 minutes for `ready`. On timeout, every job falls back
        to Ken Burns.
    *   Rewrite the Technical Plan sentence about old versions to match.

### [Q15] [CD]: Kernel metadata is incomplete. Severity: Major

*   **AI suggestion:** PROPOSE FIX.
*   **Proposed edit:** List the template fields in item 9: `id`
    (`<user>/heritage-<name>`), `title` (`heritage-<name>`), `code_file`,
    `language: "python"`, `kernel_type: "script"`, `is_private: true`,
    `enable_gpu: true`, `enable_internet`, `machine_shape:
    "NvidiaTeslaT4"`, and `dataset_sources` (Wan only).

### [Q16] [IR, CD]: The music job and kernel are underspecified. Severity: Major

*   **AI suggestion:** PROPOSE FIX.
*   **Proposed edit:**
    *   Make `instrumental` the constant `true`. The film has a score with
        no lyrics, so drop the field from the schema.
    *   The job maps `key` to `keyscale`.
    *   The implementer chooses the ACE-Step repository, model id and
        inference call inside `music_kernel.py` only, and records each choice
        in EXPERIMENTS.md and ETHICS.md.
    *   `use_placeholder` remains the fallback.

### [Q17] [IR, CD, SY]: Three verification steps cannot run as written. Severity: Major

*   **AI suggestion:** PROPOSE FIX.
*   **Proposed edit:**
    *   `make film` prints `RUN_ID=<id>` first.
    *   Checks read the latest id with `tail -1 runs.jsonl | jq -r .run_id`.
    *   The CUJ 3 check runs `pytest tests/test_runner.py::test_missing_input`,
        a job whose `input` names a key that does not exist. Expected: one
        `fallback` and assembly completes.
    *   Assembly writes no `runs.jsonl` lines. Its hold-rule fallbacks go in
        the end-of-run summary and in `outputs/final/fallbacks.txt`.

### [Q18] [IR, CD]: `prune.py` would delete the final films. Severity: Major

*   **AI suggestion:** PROPOSE FIX.
*   **Proposed edit:**
    *   Prune only `outputs/keyframes/`, `outputs/narration/`,
        `outputs/music/` and `outputs/shots/`. References live in
        `keyframes/`.
    *   Keep all three music candidates.
    *   Never touch `final/` or `assemble/`.
    *   Add `tests/test_prune.py`, which runs on a temporary directory tree.

### [Q19] [IR]: Schema test assertions are incomplete. Severity: Major

*   **AI suggestion:** PROPOSE FIX.
*   **Proposed edit:**
    *   Each fixture names its expected path, for example `$.shots` for the
        95 s fixture and `$.characters[0].consent_ref` for the consent
        fixture.
    *   Seeds are integers from 0 to 2147483647.
    *   `music.duration_s` is 30–240.
    *   `key`, `voice.*` and `language` are non-empty strings.
    *   `use_placeholder` is required.
    *   `consent_ref` is nullable. When `real_person` is true, the schema
        requires a string through `if/then`, and the code checks that the
        heading exists.

--------------------------------------------------------------------------------

## Nits

### PROPOSE FIX: applied in one batch

*   **Weights download:** use `hf download Wan-AI/Wan2.2-TI2V-5B
    --local-dir ...` and pin `huggingface_hub`.
*   **Kernel hash:** take the kernel script's hash before `JOBS` and the
    time budget are templated in.
*   **`with_retry`:**
    *   also catch `requests.Timeout` and Kaggle API exceptions;
    *   read the status from `.response.status_code` or `.code`;
    *   accept a `sleep` argument so tests can inject it.
*   **Placeholder track:** add `-ac 2`.
*   **Audio mix:**
    *   `amix=normalize=0`;
    *   `loudnorm` with TP=−1.5;
    *   add `-vn` to the loudness check.
*   **Reference images:**
    *   downscale to 512×512 before sending;
    *   a shot can show at most 4 characters, and `validate.py` checks this.
*   **Clip length:** `shots.py` warns before pushing a shot whose length is
    over 6 s.
*   **Assembly inputs:** join shots with the concat demuxer, and place
    voice lines with `adelay`.
*   **Test folder:** Group 1 creates `tests/` with `test_common.py`, so
    pytest never exits with code 4.
*   **README:** give the install command `brew install ffmpeg-full` (or a
    static build), then check `ffmpeg -filters`.
*   **Testability and logging:**
    *   `build_timeline(sb, durations)`;
    *   one shared `wrap_subtitle()` function in `common.py`;
    *   one kernel-level `runs.jsonl` line per push, so its total GPU time
        is counted;
    *   the smoke test has its own minimal push, poll and pull code.
*   **Tests:**
    *   the `golden_reference` exit-2 path;
    *   music selection in `test_timeline.py`, renamed `test_assemble.py`;
    *   units for `PRICES`.
*   **Wording:**
    *   name "the klein question";
    *   name the free agents;
    *   point "time-budget rule" and "item 9" at what they refer to;
    *   "as each group is implemented";
    *   make the schedule's last cell measurable;
    *   fix the grammar in the SRT test sentence;
    *   the costs extras are cut if Group 4 is not done by midday 26 Nov;
    *   state the 95 MB rule clearly;
    *   clarify the heading of item 19;
    *   clarify the placeholder licence line.

### DECLINE

*   **CD-N10: Wan picks its own size from the image aspect.** Assembly's
    cover-and-crop already absorbs a small difference, so no edit is needed.
*   **IR-Nit: response field name deferred.** The reviewer marked it as
    acceptable. One response read settles it.
