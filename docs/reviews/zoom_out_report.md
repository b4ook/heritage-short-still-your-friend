# Stage 5: Initial Zoom Out Review

*   **Target**: `docs/designs/heritage_short_pipeline.md` (full file, 870 lines)
*   **Standard**: `zoom-out-standard.md`
*   **Context**: `docs/references/module_5399.md`
*   **Reviewers**: Skeptical Architect (zoom-out, ZO), Inventive Catalyst (IC),
    each run in a fresh context
*   **Verdict**: No Blockers. 8 Major and 10 Nit findings after
    deduplication. Both reviewers judged the context sufficient and the core
    shape sound: one contract file, content-addressed stage outputs, and a
    pan-and-zoom (Ken Burns) fallback. The risk is concentrated in the Kaggle
    orchestration and in one cache input that sits outside the contract.

--------------------------------------------------------------------------------

## Major

### M1. Wan resolution is outside the contract, which breaks CUJ 1 and the 720p pass (ZO-1, IC-1)

*   **Scope**: lines 286, 361–366, 552; CUJ 1 (151–160).
*   **Problem**: `WAN_RESOLUTION` comes from `.env`, but it is part of the
    shots cache key. This causes three problems:
    *   Setting it to 720p re-renders every animated shot, not only those that
        survived user test 2.
    *   A stranger copying `.env.example` (480p) computes keys that miss a
        committed 720p cache. `make film` then pushes Kaggle jobs, so CUJ 1
        ("zero model calls") fails.
    *   If the 720p pass fails on deadline day, shots that already had 480p
        clips fall back to Ken Burns instead of keeping those clips.
*   **Proposed fix**:
    *   Move resolution into `storyboard.json` (per shot or top level) and
        remove `WAN_RESOLUTION`.
    *   At assembly, look clips up in order: 720p key, then 480p key, then
        Ken Burns. Log which one was used for each shot.
*   **Cost**: Mixed resolutions in one film. The tier used must be logged.

### M2. Render time on the T4 is unmeasured, yet batch size and deadline are fixed (ZO-2)

*   **Scope**: file 7 `smoke.py` (575–582); lines 332–333, 345–347.
*   **Problem**:
    *   The Kaggle smoke check is only `kaggle kernels list`, which checks
        authentication.
    *   The 6-clip batch and 90-minute deadline are guesses. At 12–15 minutes
        per clip plus setup, every batch overruns the deadline.
    *   The module asks for a smoke test that calls each provider once and
        logs latency.
*   **Proposed fix**: Make one timed 480p Wan clip part of the smoke test, and
    derive the batch or time budget from it.

### M3. Every batch downloads the model weights again and renders in series (ZO-3, IC-3)

*   **Scope**: Kaggle cycle (320–353); files 22–24.
*   **Problem**:
    *   Every push reinstalls the Wan requirements and downloads several GB of
        TI2V-5B weights from Hugging Face, using GPU quota.
    *   There is one kernel slug, so batches run one after another. 24 clips
        means 4 batches, which at 90 minutes each could block `make film`
        for up to 6 hours.
*   **Proposed fix**:
    *   Attach the weights once as a Kaggle Model or Dataset source.
    *   Give the kernel a time budget: it keeps taking jobs until it nears the
        deadline, then exits cleanly. The per-clip manifest already limits any
        loss to one clip, so the batch size can go.
    *   Add an Open Question: does `kaggle kernels output` return partial
        `/kaggle/working` files after an error or timeout?
*   **Cost**: A one-time upload of several GB, a licence note for the
    redistributed Apache 2.0 weights, and time-budget logic in the kernel.

### M4. The local deadline does not stop the remote kernel (ZO-4)

*   **Scope**: CUJ 3 (176–181); lines 345–347, 351–353.
*   **Problem**:
    *   After `make film` gives up, the kernel may keep running and using
        quota.
    *   The next run pushes the same jobs to the same slug, possibly while the
        old run is still going.
*   **Proposed fix**: Before planning new jobs, check the previous kernel
    version. If it is still running, refuse to push. If it has finished,
    collect its outputs first. This also recovers clips that finished after
    the deadline.

### M5. The stale-dataset guard can be removed by restructuring the upload (ZO-5, IC-4)

*   **Scope**: lines 324–344; file 22; Open Question 144–147.
*   **Problem**: The design detects a stale dataset version with a run id
    check, which wastes a whole session when it fires. It does not prevent
    the staleness.
*   **Proposed fix**:
    *   Embed the job list in the kernel source, which is already templated
        and is pushed in one step with the kernel.
    *   Make the dataset an append-only folder of keyframe PNGs named by hash.
    *   Have the kernel check that each job's input file exists. If one is
        missing, only that job fails.
    *   The run/batch id guard and the propagation Open Question then go away.

### M6. Consistency depends on an unverified reference-image capability (ZO-6)

*   **Scope**: lines 370–382; G6 (87–89); file 19; stage 0 (684–691).
*   **Problem**:
    *   Stage 0, the golden-reference approval gate and the reference hash in
        the keyframe key all assume Workers AI FLUX accepts a reference image.
    *   FLUX.1 schnell is likely text-only. If so, stage 0 is wasted work, and
        the gate blocks keyframes for no benefit.
*   **Proposed fix**:
    *   Add this as an Open Question and a smoke-test item.
    *   If FLUX has no reference input, drop stage 0 and the gate, and rely on
        the style block, the seed and the character description.

### M7. Music, not Wan, puts the Kaggle runner on the critical path; failure handling is uneven (ZO-7, IC-5)

*   **Scope**: Group 3 order (674–765); file 28 (762–765); retries (316–318);
    G7.
*   **Problem**:
    *   The only path to an original score goes through `kaggle_runner.py`,
        and a music failure stops the run until the storyboard is edited by
        hand.
    *   A final keyframe failure, such as the Cloudflare daily cap running
        out, kills the whole film over one shot.
*   **Proposed fix**:
    *   Build the runner with music as its first user.
    *   Get a full Ken Burns film with the real score working, then add Wan.
    *   Fall back to the placeholder score automatically, logged as
        `fallback`.
    *   Keep the last good keyframe per (shot, ratio) and use it if a new one
        fails.
    *   Print a summary of every fallback at the end of the run.

### M8. Dual-ratio animation is all-or-nothing when it could be set per shot (IC-2, ZO-7)

*   **Scope**: lines 196–199, 363–364; Alternative D (463–464).
*   **Problem**:
    *   Native both-ratio generation doubles Wan jobs. It also doubles
        Cloudflare images, against a daily cap of roughly 50–170.
    *   The trade-off is set once for the whole film.
*   **Proposed fix**:
    *   Keep keyframes native in both ratios.
    *   Make `animate` per ratio (for example `["9x16"]`) and push all 9:16
        clips first, since 9:16 is the main submission.
    *   A 16:9 shot without a clip uses Ken Burns over its own native
        keyframe.
*   **Cost**: The two exports can differ in motion. This has to be explained
    in DESIGN.md.
*   **Note**: This refines author decision 3 (native framing for both ratios).
    It keeps native framing and changes only which ratio gets motion first.

--------------------------------------------------------------------------------

## Nits

*   **N1. Reference sheet in both ratios (ZO-8)**: Identity does not depend on
    aspect ratio. Generate the sheet once per character and drop `ratio` from
    the reference key.
*   **N2. Index and sidecar files duplicate what can be derived (ZO-9)**:
    `keyframes/index.json` and the narration duration JSON can go stale.
    Compute keys in `common.py` instead. Keep `shots/index.json` only as the
    record of fallbacks. (IC-5 wants a keyframe index for last-good fallback.
    Resolve the two together.)
*   **N3. Tuning numbers in the architecture section (ZO-10)**: The 0.6 s pad,
    0.25 s trim, ducking parameters and backoff values belong in code and
    EXPERIMENTS.md.
*   **N4. Committed cache grows without limit (ZO-11, IC-8)**:
    `outputs/assemble/tmp/` is committed. Add a `make prune-unreferenced`
    before release; git history keeps old files for rollback.
*   **N5. `script.py` sends the family treatment to the free Gemini tier
    (ZO-12)**: This conflicts with the privacy rule, and it is not one of the
    required stages. Cut it, or record in ETHICS.md what is sent.
*   **N6. Stale references (ZO-13)**: G1 says the GPU boundary is "decided in
    the Technical Plan" (it is decided). Non-Goals says Future Improvements is
    "to be drafted" (it exists).
*   **N7. `costs.py` extras (ZO-14)**: The p90 latency and the in-place marker
    rewrite are the first things to cut if time is short.
*   **N8. Clips frozen to fill narration length (IC-6)**: When narration runs
    longer than the clip, the last frame is held. Either derive `frames` from
    `duration_s`, or slow the clip down by up to 1.25× (`setpts`) or continue
    with a zoompan, instead of a static hold. Keep narration out of the shot
    key.
*   **N9. Music runs after shots (IC-7)**: Run the small music job first, so
    the candidates can be heard while Wan renders.
*   **N10. Concurrent Kaggle sessions (IC-7)**: Whether the account can run
    two GPU sessions at once is unverified. Add it to the smoke test if it is
    wanted.

--------------------------------------------------------------------------------

## Traceability

| Raw finding | Consolidated |
| --- | --- |
| ZO-1, IC-1 | M1 |
| ZO-2 | M2 |
| ZO-3, IC-3 | M3 |
| ZO-4 | M4 |
| ZO-5, IC-4 | M5 |
| ZO-6 | M6 |
| ZO-7, IC-5 | M7 |
| IC-2, ZO-7 (ratio ordering) | M8 |
| ZO-8 | N1 |
| ZO-9 | N2 |
| ZO-10 | N3 |
| ZO-11, IC-8 | N4 |
| ZO-12 | N5 |
| ZO-13 | N6 |
| ZO-14 | N7 |
| IC-6 | N8 |
| IC-7 | N9, N10 |
