# Stage 8: Intermediate Zoom Out Review

*   **Target**: `docs/designs/heritage_short_pipeline.md` (full file, not yet
    edited since Stages 5–7)
*   **Standard**: `zoom-out-standard.md`
*   **Context**: `docs/references/module_5399.md`, `zoom_out_report.md`,
    `comprehension_report.md`, `critic_report.md`
*   **Reviewer**: Skeptical Architect (zoom-out), run in a fresh context.
    Completed.
*   **Verdict**: No Blockers; 3 Major and 3 Nit new findings, plus a triage of
    every fix proposed so far.
    *   Stages 6 and 7 propose about 30 fixes. Adopting all of them would add
        roughly a day of work to the Kaggle code, which is already the riskiest
        part. That would push the build past 2.5 days.
    *   If you adopt the triage below, the design gets smaller than it is now.

--------------------------------------------------------------------------------

## A. New high-altitude findings

### Z1. The review is hardening a 20-point criterion while the other 80 points have no schedule (Major)

*   **Scope**: Detailed Implementation Plan, Groups 1–4; the rubric in the
    module.
*   **Points at stake**:
    *   Written evidence earns 60 of Assignment 1's 100 points: design and user
        tests 10, experiments 10, troubleshooting 10, measurement 5, consent 5,
        report 30. Documentation is worth another 10.
    *   All of Assignment 2 is the film, the walkthrough and the post.
    *   Almost every fix proposed in Stages 5–7, and most of Group 3, serves
        only the 20-point software-engineering criterion.
*   **Missing from the plan**:
    *   No time is set aside for recruiting two user tests of 3+ people each.
    *   No time is set aside for the ten experiments, which draw on the same
        Cloudflare and Kaggle quota as production.
    *   No time is set aside for the report, the walkthrough or the post.
    *   Group 4 puts all of these on deadline day.
*   **Fix**: Add a time-boxed schedule with a cut line.
    *   **By end of 25 Nov**: the Ken Burns film with the real score, plus user
        test 1, are locked.
    *   **26 Nov**: documents, user test 2, walkthrough.
    *   **Above the cut line**: Wan and every Kaggle hardening item. They are
        built only once the floor is done.
    *   This schedule covers most of what C1, C4 and C7 are after.

### Z2. Drop the 720p re-render pass entirely (Major; revises Stage 5 M1)

*   **Scope**: lines 361–366, `WAN_RESOLUTION` (line 552); also Stage 5 M1,
    Stage 6 #4, Stage 7 C4/C6.
*   **Why**: The 720p pass falls on deadline day and may run out of memory on a
    T4.
*   **Fix**: Fix Wan at 480p as one top-level storyboard constant, and upscale
    in FFmpeg at export.
*   **This deletes**:
    *   the env var
    *   the 720p → 480p → Ken Burns lookup chain that Stage 5 proposed
    *   the 720p memory risk
    *   the mechanism for choosing which shots survive to 720p
*   720p moves to Future Improvements.

### Z3. Drop the one-time weights upload (Nit; revises Stage 5 M3)

*   **Why**: With a kernel that keeps rendering until its time budget runs out,
    a full pass needs one or two sessions, not four. Downloading the weights
    then costs only minutes per session. Uploading several GB as a dataset, and
    adding a licence note for redistributing them, costs the author more time
    than it saves.
*   **Fix**: Keep the time-budget kernel, which also removes the 6-clip
    batching. Drop the weights upload.

### Z4. Cut stage 0 by default (Nit; strengthens Stage 5 M6 / Stage 7 C13)

*   **Why**: The reference sheet, its approval gate and its hash only help if
    Workers AI FLUX accepts an image input, which is unconfirmed. The gate is
    also one of the two hidden manual steps in "one command".
*   **Fix**: Plan around the style block, the seed and the character text. Add
    stage 0 back only if the smoke test shows image input works.

### Z5. Use GitHub push protection instead of the `git grep` check (Nit; supersedes Stage 7 n10)

*   **Why**: Push protection is a platform feature, needs no code, and actually
    blocks a leaked key. A pre-commit hook would be new code for no extra
    benefit.

--------------------------------------------------------------------------------

## B. Triage of proposed fixes (Stages 5–7)

### Adopt: cheap, or removes code

| Fix | Minimal form | Rejected parts |
| --- | --- | --- |
| C8 cache-key gaps | One `cache_key(payload)` over the exact dict sent to the model. This replaces the per-stage key table and fixes the missing character description. Add the kernel script's file hash to the shot and music keys. | Pinning HF weight revisions (the weights won't change in 2 days) |
| C9 bad outputs cached | Write to a temporary file and rename it into place. At Kaggle pull, check the file is non-empty and that `ffprobe` can decode it. | Blank or safety-filter detection (the author views every keyframe); output-hash logging (the name is already a hash) |
| C10 final length | Assert that timeline plus end card is 60–90 s. Trim and fade the music to the timeline with `atrim`/`afade`. State in one sentence that the edit is cut to the narration. | — |
| C14 subtitle length | `maxLength: 80` on `subtitle_en` | Logic to split one line across several cues |
| S5 M2 / C6 render time | One timed 480p Wan clip in the smoke test | One worker per GPU; naming HunyuanVideo or Colab as a fallback (Ken Burns is the fallback) |
| S5 M5 stale dataset | Embed the job list in the kernel source. This deletes the run/batch id guard, the propagation question and the refusal behaviour. | — |
| S5 M4 / C7 orphan kernel | Before pushing, check `kaggle kernels status`. If still running, skip the push and use Ken Burns. If finished, pull its outputs first. | Cancel logic; separate CLI retry rules; documenting Colab |
| S5 M8 / S6 #3 per-ratio animate | One field, `animate: none \| 9x16 \| both`. Set it to `none` on shots that fell back before committing, which keeps CUJ 1 at zero calls. | Per-ratio object |
| S6 #2 first-run manual steps | With Z4 adopted, only `music.chosen` is left, and it defaults to candidate 0. Add one CUJ or a README sentence. | — |

### Adopt: document text only

*   **C2, C3, S6 #1**: rename the decision labels, and state the trade-off
    behind each rejection.
*   **C15**: use one stage numbering; add a short Narration subsection; use the
    real field names in G4; state that the Kaggle credential is needed only
    when the cache is incomplete.
*   **S6 #5–#15**, plus the Stage 7 nits that are wording only.
*   **C1**: add Risks & Mitigations as a short bullet list that points each
    risk to its existing mitigation. Do not use a likelihood/impact table.

### Reject or defer: over-engineering for this deadline

| Fix | Decision | Why |
| --- | --- | --- |
| C4 per-stage budget table | Reject | Every cell is a guess until the smoke test runs, and COSTS.md holds the measured numbers. Keep only the cut-down rule (9:16 first, then the N shots with the clearest `purpose`), plus Z2. |
| C5 `quota_exhausted` status | Reject | The cache makes a re-run the next day cheap. Record quota numbers in COSTS.md. At most, don't retry a 429 whose body names a daily limit. |
| n11 `real_person` consent flag | Defer | If no real face or voice appears, it guards nothing. If one does, ETHICS.md (Group 2) already comes before any generation. Add one `consent_ref` only if needed. |
| C11 / S5 M7 automatic placeholder score | Reject (revises S5 M7) | An automatic placeholder would hide a breach of the "original score" requirement. The manual `use_placeholder` flag is more honest. Keep "run music first" so failures surface on 25 Nov. |
| n7 two-pass `loudnorm` | Defer | Measure after export. Add the second pass only if the result misses −14 ±1 LUFS. |
| C12 cache size budget | Partly reject | Keep one prune step before release, because rejected likenesses must not be published. Drop the size budget. |

--------------------------------------------------------------------------------

## C. Net effect if the triage is adopted

*   **Deleted**:
    *   stage 0
    *   6-clip batching
    *   the run/batch id guard
    *   the 720p pass
    *   `WAN_RESOLUTION`
    *   the per-stage key table
    *   the dataset-propagation Open Question
*   **Added**:
    *   one length assertion
    *   one schema `maxLength`
    *   atomic writes
    *   a check of the previous kernel before pushing
    *   one `animate` enum
    *   one timed smoke clip
    *   a schedule with a cut line
    *   a short Risks section
*   **Note on author decisions**:
    *   The `animate` enum keeps decision 3 (both ratios framed natively). It
        only changes which ratio gets motion first.
    *   Z2 keeps native dual-ratio output but fixes it at 480p.
