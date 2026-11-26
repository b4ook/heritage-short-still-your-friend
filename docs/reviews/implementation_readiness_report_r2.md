# Stage 9: Implementation Readiness Test, Round 2 (Re-audit)

*   **Target**: `docs/designs/heritage_short_pipeline.md`, DetailedRange
    lines 753–1249 (revised after round 1)
*   **Standard**: `implementation-readiness-standard.md`
*   **Context**: `docs/references/module_5399.md`
*   **Reviewers**: all completed, each in a fresh context.
    *   Implementation Readiness (IR): 1 Blocker, 15 Major, 16 Nit
    *   Codebase Details (CD): 1 Blocker, 15 Major, 15 Nit
    *   Style (SY): 4 Major, 14 Nit
*   **After deduplication**: 1 Blocker, 17 Major, 16 Nit
*   **Verdict**: **NOT READY, but much closer.**
    *   The round 1 Blockers are fixed. CD confirmed these as correct:
        *   the Wan flags and sizes;
        *   the FLUX.2 multipart fields and the Apache 2.0 licence;
        *   the raw PCM from Gemini TTS;
        *   the `KaggleApi` method names;
        *   `tpad`;
        *   the Makefile syntax.
    *   The new Blocker is a step-order bug that the revision introduced.
    *   The Majors are mostly missing values plus three test steps that
        cannot run.
*   **Re-audit cap**: This was Stage 9's one allowed re-audit. Findings can
    still be resolved, but a third audit will not run.

--------------------------------------------------------------------------------

## Blocker

### Q1. A clean-clone rebuild (CUJ 1) crashes without `kaggle.json` (IR-B1, CD-B1). Confidence: high

*   **Problem**:
    *   The cycle runs *Recover* (`kernels_status`) before *Plan*, so every
        run contacts Kaggle even when the cache is full.
    *   Importing `kaggle` authenticates as a side effect and raises
        `OSError` when no credentials exist.
    *   A stranger's credentials could not read the author's private kernel
        anyway.
*   **Fix**:
    *   Run *Plan* first, and return before any Kaggle contact when no job is
        missing.
    *   Import `kaggle` lazily inside `run_stage`.
    *   Add a test: full cache and no credentials means no `kaggle` import.

--------------------------------------------------------------------------------

## Major

| # | Finding | Fix | Sources |
| --- | --- | --- | --- |
| Q2 | **The floor film needs `shots.py`, which is scheduled after the cut line.** `make film` calls it, and assembly needs `clip_job` to find clips. | Move a minimal `shots.py` into Group 3a: `clip_job`, exit 0 when nothing is animated. The Kaggle push and `--smoke` stay in 3b. | IR-M2 |
| Q3 | **The cut-line labels are swapped.** The headings put 3a below the line and 3b above it, the opposite of the schedule. | Swap the two labels. | IR-M3, CD-M1, SY-1 |
| Q4 | **The first run of a Kaggle stage is undefined.** `kernels_status` returns 404 because no kernel exists yet, and the 4xx rule then stops the run. | Treat a 404 as "no previous version" and skip Recover. A missing dataset means `dataset_create_new`. Test both. | IR-M1 |
| Q5 | **Wan will likely assert on FlashAttention.** `flash_attention()` asserts FA2 is available, so leaving out `flash_attn` is not enough. `--convert_model_dtype` gives bf16, which the T4 lacks. The install mechanism is vague. | Add a patch step: replace `flash_attention` with `torch.nn.functional.scaled_dot_product_attention` and force fp16. Install with `grep -v flash_attn requirements.txt \| pip install -r /dev/stdin`. | IR-M7, CD-M4 (medium-high) |
| Q6 | **`--frame_num 121` is hard-coded**, even though the job carries `frames` and the cache key uses it. | Use `--frame_num <frames>` (must be 4n+1). Pass the command as a subprocess argument list. | IR-Nit, CD-M3, SY-2 |
| Q7 | **`zoompan` output size is never set.** It defaults to 1280×720, which squashes the 9:16 frame. The expressions and frame-count rules are missing. | Set `s=2160x3840` / `3840x2160`, then scale. Use `z='zf+(zt-zf)*on/(d-1)'`, pan x and y expressions for each direction, and integer `d=round(24*len)`. Read the still without `-loop 1`. | CD-M2, IR-Nit |
| Q8 | **Subtitle `force_style` values are in 288-line script units, not pixels.** `MarginV=120` sits near mid-frame, and `FontSize=14` is about 93 px, so lines overflow. | Set `original_size=1080x1920` / `1920x1080`, or set PlayRes in `force_style`. Give values for each ratio and check them with a frame grab. | IR-M12, CD-M12 (medium) |
| Q9 | **The schnell fallback drops the seed**, but G6's fallback promises "same text and seed". The model id has no defined location. There is no pass rule for "the reference is honoured". | Send `seed` (schnell accepts it). Add a `KEYFRAME_MODEL` constant in `keyframes.py`. Add a pass rule: a human compares one keyframe with and without the reference and records the result in EXPERIMENTS.md. | IR-M4, CD-M5 |
| Q10 | **The daily-limit 429 rule matches neither provider.** Gemini's body says `..._per_day` and Cloudflare's says "daily". | Use the case-insensitive regex `per_?day\|daily`. Use fixtures shaped like real responses. | IR-M9, CD-M6 |
| Q11 | **`machine_shape` has no fallback, and there is no GPU check.** | The kernel reads `nvidia-smi`. If the GPU is not a T4, it writes `status: error` for every job. Fallback: choose the T4 accelerator once on the kernel page, which later pushes keep. | IR-M5 |
| Q12 | **Recover depends on unverified output after an error.** The smoke test never makes a kernel error, so it cannot answer this. | Wrap the kernel body in try/except so it always exits cleanly with `complete`, and keep per-job failures only in the manifest. This removes the dependency. | IR-M6, CD-M14 |
| Q13 | **The kernel time budget has no value, and the deadline variable names disagree.** | Inject `TIME_BUDGET_MIN` next to `JOBS`: 170 for Wan and 25 for music. Use one set of names, `KAGGLE_DEADLINE_MIN_MUSIC` and `KAGGLE_DEADLINE_MIN_SHOTS`, with defaults in code. Treat cancel states like `error`. Normalise the `KernelWorkerStatus` enum, including `new_script`. | IR-M10, IR-Nit, CD-M9, CD-N2, CD-N5 |
| Q14 | **The inputs dataset is not append-only.** A new version contains only the uploaded folder, the staging folder is undefined, and `dataset-metadata.json` is missing. | `kaggle/inputs/` accumulates every uploaded keyframe and is the upload folder. `dataset-metadata.json` holds `{id, title, licenses: [{name: "CC0-1.0"}]}`. Wait at most 10 minutes for `ready`. `version_notes` carries the run id. | IR-M11, CD-M10, CD-M11 |
| Q15 | **Kernel metadata is incomplete.** | The template has `id`, `title` (its slug matches the id), `code_file`, `language: "python"`, `kernel_type: "script"`, `is_private`, `enable_gpu`, `enable_internet`, `machine_shape` and `dataset_sources`. | CD-M11, IR-Nit |
| Q16 | **The music job and kernel are underspecified.** The storyboard has `key`, but the job uses `keyscale`. `instrumental: false` has no lyrics source. The repository, model id and call are open. | Fix `instrumental` to the constant `true` (score only) and map `key` to `keyscale`. Let the implementer set the repository, model id and inference call inside the kernel only, and record each choice in EXPERIMENTS.md. `use_placeholder` remains the fallback. | IR-M8, CD-M13 |
| Q17 | **Three verification steps cannot run as written.** <ul><li>The `$RUN_ID` grep runs in the author's shell, where the variable is empty.</li><li>The CUJ 3 test deletes a file from an immutable dataset version.</li><li>CUJ 1's "all `cache_hit`" clashes with assembly logging `ok` and `fallback`.</li></ul> | Have `make film` print `RUN_ID`. Read the id with `tail -1 runs.jsonl \| jq -r .run_id`. Replace the CUJ 3 test with a test hook: a fixture job whose `input` names a key that does not exist. Assembly does not write `runs.jsonl`; its hold-rule fallbacks go in the end-of-run summary. | IR-Nit, IR-M13, CD-M7, CD-M10, CD-M15, SY-3 |
| Q18 | **`prune.py` would delete the final films.** It also has no listed scope and no test. | Prune only `keyframes/`, `narration/`, `music/` and `shots/`. Keep all three music candidates. Never touch `final/` or `assemble/`. Test it on a temporary tree. | IR-M14, CD-M8 |

**Also Major: schema test assertions (IR-M15).**

*   **Problem**: The fixtures have no expected paths, and several fields have
    no stated types.
*   **Fix**:
    *   Give each fixture its expected path. A code check uses the nearest
        path, for example `$.shots` for the total duration.
    *   Seeds are integers from 0 to 2³¹−1.
    *   `music.duration_s` is a number from 30 to 240.
    *   `key` is a string such as `"D minor"`.
    *   `voice.*` and `language` are non-empty strings.
    *   `use_placeholder` is required (drop the word "default").
    *   `consent_ref` is nullable. When `real_person` is true, the schema
        requires it to be a string, using `if/then`, and the code checks that
        the heading exists.

--------------------------------------------------------------------------------

## Nits

*   Use `hf download` instead of the deprecated `huggingface-cli`.
    (CD-N1, medium)
*   Hash the kernel script before templating `JOBS`. Otherwise every key
    changes whenever the job set changes. (CD-N3)
*   The `with_retry` exception contract:
    *   add `requests.Timeout` and Kaggle exceptions;
    *   say how each error type exposes its status code;
    *   make the sleep injectable for tests.

    (CD-N4, IR-Nit)
*   The placeholder track comes out mono, so add `-ac 2`. (CD-N6)
*   Set `normalize=0` on `amix`. Use TP=−1.5 to leave margin for the AAC
    encode. Add `-vn` to the loudness check. (CD-N7, N8, IR-Nit)
*   Cloudflare FLUX.2 takes at most 4 input images, possibly with a size
    cap, so downscale references to 512². (CD-N9, low-medium)
*   Wan TI2V may change the output size slightly to follow the image aspect;
    cover/crop absorbs that. (CD-N10, low-medium)
*   A shot longer than about 6 s cannot use its clip. `shots.py` should warn
    before pushing it. (CD-N11)
*   Specify the concat method (concat demuxer) and how voice lines are
    positioned (`adelay`). (CD-N12)
*   If `tests/` is missing, pytest exits 4. Create `tests/` in Group 1.
    (CD-N15)
*   Homebrew may need `ffmpeg-full` to get drawtext and libass. Give the
    install command. (CD-N14, low-medium)
*   `build_timeline` should take a dict of durations so it can be tested.
    `validate` and the SRT writer should share one wrap function
    (`textwrap.wrap(width=40)`). (IR-Nit)
*   Log one kernel-level line for each push, so install and download time
    counts in GPU minutes. (IR-Nit)
*   The Group 1 smoke test has its own minimal push, poll and pull code,
    because `kaggle_runner.py` does not exist until Group 3a. (IR-Nit)
*   Missing tests: the `golden_reference` exit-2 path, and music selection.
    State the `PRICES` units. (IR-Nit)
*   Wording:
    *   name "the klein question";
    *   name the free agents;
    *   point "time-budget rule" and "as in file 9" at what they refer to;
    *   use "as each group is implemented";
    *   make the schedule's last step measurable ("at least one 9:16 shot
        uses a Wan clip");
    *   fix the grammar in the SRT test;
    *   set a concrete trigger for cutting `costs.py` extras ("by midday
        26 Nov");
    *   write the 95 MB / 100 MB rule clearly;
    *   phrase the heading for file 19 more simply.

    (SY-4 to SY-18)
