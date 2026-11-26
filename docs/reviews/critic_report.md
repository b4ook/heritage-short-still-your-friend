# Stage 7: Critic Review (Round 1)

*   **Target**: `docs/designs/heritage_short_pipeline.md`, FeatureRange lines
    1–507
*   **Standard**: `feature-spec-standard.md` (design, structural); persona
    rules (style)
*   **Context**: `docs/references/module_5399.md`
*   **Reviewers** (all completed, each in a fresh context): Design Critic (DC),
    Structural (ST), Style (SY)
*   **Raw counts**: DC 13 Major / 11 Nit; ST 6 Major / 9 Nit; SY 6 Major / 16
    Nit
*   **Consolidated**: 0 Blocker, 15 Major, 17 Nit
*   **Verdict**: Revise before implementation. Three Majors break the
    feature-spec standard outright (C1–C3). The rest are assumptions that have
    not been verified or rules that nothing enforces.
*   **Overlap with earlier stages**: items marked *(also S5 Mx / S6 #y)* were
    raised by Stage 5 or Stage 6. Fixing them once clears all of them.

--------------------------------------------------------------------------------

## Major

### C1. No Risks & Mitigations section (DC-M1, ST-1)

*   **Problem**: The standard requires a section that sets out each risk with
    its mitigation. Here, risk material is scattered across The Problem, Open
    Questions, CUJ 3 and the NFRs, and none of it pairs a risk with a
    mitigation. Several of the largest risks are not stated at all:
    *   the deadline as a schedule risk;
    *   free-tier quotas;
    *   Wan running on a T4;
    *   Kaggle as the only GPU host;
    *   TTS quality in the chosen language;
    *   the consent gate.
*   **Proposed fix**: Add `## Risks & Mitigations` as a table with columns for
    risk, likelihood, impact and mitigation. Fold in C4–C10 and the Open
    Questions that carry risk.

### C2. Rejections are attributed to the author with no link, and C and D are rejected on preference (DC-M2, ST-2)

*   **Problem**: The Alternatives Rule forbids attributing a rejection to a
    maintainer without a link to their issue, discussion or PR. All five
    alternatives say "Rejected by author". Alternatives C and D give an
    opinion where a trade-off belongs.
*   **Proposed fix**: Replace each rationale with the trade-off that decided
    it. For example, A: "the manual notebook step fails the one-command
    requirement of the 20-point software-engineering criterion". For C and D,
    state the framing loss against the GPU and image cost, with numbers.

### C3. The decision labels "choice A / choice 3" cannot be traced, and "A" clashes with Alternative A (DC-M2, ST-3, SY-2) *(also S6 #1)*

*   **Problem**: "Choice A" (adopted) reads as "Alternative A" (rejected),
    which is the opposite decision. "Choice 3" refers to an option list that
    does not appear in the document.
*   **Proposed fix**: Remove the labels. Write "chosen over Alternatives A and
    B" and "chosen over Alternatives C and D".

### C4. Native dual-ratio output has no budget behind it, and the 720p pass falls on deadline day (DC-M3) *(also S5 M1, M8)*

*   **Problem**:
    *   The plan needs 24 clips and more than 24 keyframes per pass, and no
        budget supports that.
    *   The sizes of the 6-clip batches and the 90-minute deadline are not
        reconciled.
    *   Re-rendering at 720p after the second user test lands on 26 Nov, the
        deadline day.
*   **Proposed fix**:
    *   Add a per-stage budget table covering images per day, TTS requests per
        day, GPU minutes per pass and wall-clock time per batch, filled from
        smoke-test numbers.
    *   Add a cut-down rule, such as animating 9:16 only or animating only the
        N most important shots.
    *   Either drop the 720p re-render or schedule it before the second user
        test.

### C5. Free-tier quotas are not verified, and running out of quota is treated as a transient error (DC-M4) *(related S5 M7)*

*   **Problem**:
    *   Cloudflare allows roughly 50–170 images a day. One keyframe pass plus
        the reference sheets plus experiments can use a day's allowance.
    *   The Gemini TTS limits are not stated.
    *   A 429 that comes from an exhausted daily quota burns three retries and
        then stops the run.
*   **Proposed fix**:
    *   Record the quota numbers verified by the smoke test.
    *   Log `quota_exhausted` as its own status, separate from a transient 429.
    *   Define what happens when a quota runs out mid-run.

### C6. Wan on a T4 is unverified (DC-M5) *(also S5 M2)*

*   **Problem**:
    *   TI2V-5B is published as a 720p model, so 480p support and quality need
        checking.
    *   A T4 has 16 GB of memory and no bf16 support, so it may run out of
        memory at 720p.
    *   The second T4 sits unused unless the kernel runs one worker per GPU.
*   **Proposed fix**:
    *   Have the smoke test render one clip at each resolution and record time,
        memory use and quality.
    *   Decide whether to run one worker per GPU.
    *   Name HunyuanVideo 1.5 or Colab as the fallback.

### C7. Kaggle is a single point of failure, and its behaviour is unverified (DC-M6) *(also S5 M3, M4, M5)*

*   **Problem**:
    *   It is unknown whether partial output can be retrieved after an error,
        a cancel or a local timeout.
    *   The remote kernel keeps running after the local deadline, and the next
        push may replace it.
    *   Nothing says what happens after a stale-version refusal.
    *   Nothing says whether shots and music run one after the other or at
        the same time.
    *   The Kaggle CLI calls have no retry rules.
    *   Colab, listed as a backup in the module, is not mentioned.
*   **Proposed fix**:
    *   Add a smoke-test item for partial output.
    *   Cancel or wait for the remote kernel when the deadline passes.
    *   Define the behaviour after a refusal.
    *   State the order in which the Kaggle stages run.
    *   Add retry rules for the Kaggle CLI.
    *   Document Colab or Ken Burns as the mitigation when Kaggle is down.

### C8. Cache keys leave out inputs (DC-M7, ST-6)

*   **Problem**:
    *   The keyframe key omits the character description, which is part of
        the prompt. Editing a description therefore serves stale keyframes,
        which breaks G2 and G6.
    *   The shot key omits the sampler settings (steps, guidance, fps) and the
        kernel script version.
    *   The `model` field holds a name, not a pinned revision.
*   **Proposed fix**:
    *   Hash the exact request payload sent to each model.
    *   Include the kernel script and its settings in the key.
    *   Pin the revision of every Hugging Face weight.

### C9. "The file exists" counts as a cache hit, so a bad output is reused for good (DC-M8)

*   **Problem**: An interrupted write, a truncated download, or a blank or
    safety-filtered image all become permanent cache hits.
*   **Proposed fix**:
    *   Write to a temporary file, then rename it into place.
    *   Validate each output before caching it: it decodes, has the expected
        duration and size, and is not blank.
    *   Log the output hash.

### C10. Final length is not guaranteed to be 60–90 s (DC-M9)

*   **Problem**:
    *   Validation checks only the sum of the planned durations. Narration can
        stretch shots, and a 3 s end card is added on top, so an 88 s plan can
        come out at 95 s or more.
    *   The music length is fixed and is not tied to the timeline.
    *   The module says "cut to the music", but the design cuts to the
        narration.
*   **Proposed fix**:
    *   After narration, assert that the measured timeline plus the end card
        is within 60–90 s.
    *   Say whether the end card counts toward the length.
    *   Derive the music length from the timeline, or define trim and fade.
    *   Note that the edit is cut to the narration, and why.

### C11. A music failure contradicts G7, "the film always ships" (DC-M10, ST-1) *(also S5 M7)*

*   **Problem**:
    *   Only the Wan stage has a fallback. A music or narration failure stops
        the run.
    *   A placeholder score fails the requirement for an original score.
*   **Proposed fix**:
    *   Fall back to the placeholder automatically and log it as `fallback`.
    *   State that a placeholder in the final film breaks the spec.
    *   Narrow G7, or extend it to cover narration.

### C12. The privacy policy conflicts with the chosen providers, and publishing intermediates is not covered by consent (DC-M11) *(related S5 N4, N5)*

*   **Problem**:
    *   The family narration must go to free-tier Gemini TTS, so the rule to
        "keep details out of prompts" cannot be followed.
    *   A relative's photo used as a reference image would go to free
        endpoints.
    *   Committing all of `outputs/` publishes every rejected likeness.
*   **Proposed fix**:
    *   State what text reaches each provider.
    *   Extend consent to cover publishing intermediates, or commit only the
        outputs the current storyboard references.
    *   Add a prune step and a size budget.

### C13. FLUX reference conditioning is assumed (DC-M12) *(also S5 M6)*

*   **Problem**: G6 says every keyframe is conditioned on the reference
    image, but the Technical Plan hedges with "where the model supports it".
    FLUX.1 schnell is text-only, and FLUX.2 klein's support for image input on
    Workers AI is unconfirmed.
*   **Proposed fix**:
    *   Add an Open Question and a smoke-test item.
    *   Define a fallback model, and say what G6 becomes without one.

### C14. Subtitle limits are not enforced (DC-M13)

*   **Problem**: Each shot gets one subtitle cue capped at 2 lines of 40
    characters, about 80 characters in all. The schema sets no limit on
    `subtitle_en`.
*   **Proposed fix**: Add a `maxLength` to `subtitle_en`, or define how a long
    line splits into several timed cues.

### C15. The document contradicts itself on stages, the call log and prerequisites (ST-4, ST-5, SY-5, SY-6) *(also S6 #7)*

*   **Stage count**: The Overview says five stages, but the diagram numbers
    six ([0]–[5]). The module's "script" stage is neither adopted nor
    rejected. The validation and reference stages are both numbered 0 in
    different places.
*   **Narration**: The Technical Plan has no narration subsection. Narration
    drives the timeline, yet its output format, how its duration is measured,
    the behaviour for unsupported languages, and what "reduced stage 5" means
    for `make radio` are all undocumented.
*   **Call log**: `runs.jsonl` is defined as one line per model call, but it
    also holds `cache_hit` and `fallback` lines. G4's field names (input hash,
    retry count, estimated cost) do not match the field list (`cache_key`,
    `attempt`, `cost_usd_est`).
*   **Prerequisites**: CUJ 1 requires a Kaggle credential even when the cache
    is full, and the reason given for rejecting Alternative B implies none is
    needed. *(also DC-N3)*
*   **Proposed fix**:
    *   Use one stage numbering throughout.
    *   Add a Narration subsection.
    *   Define the log as one line per stage output event, list which statuses
        mean a model was actually called, and use the real field names in G4.
    *   State that the Kaggle credential is needed only when the cache is
        incomplete.

--------------------------------------------------------------------------------

## Nits

| # | Finding | Source |
| --- | --- | --- |
| n1 | G1 says the GPU boundary is "decided in the Technical Plan". It is already decided. | SY-1 *(S5 N6)* |
| n2 | "Future Improvements, to be drafted" is stale. The section exists, and it sits as an H3 under the NFRs; make it its own H2. | DC-N1, ST-7, ST-8, SY-13 *(S5 N6, S6 #9)* |
| n3 | "The cohort's frontier lane", Nano Banana, Omni Flash and Lyria 3.5 are undefined. Say "paid frontier models", or define them. | SY-3 *(S6 #6)* |
| n4 | The ducking values read as already tuned. Mark them "initial values". | SY-4 *(S5 N3)* |
| n5 | "Share the seed, so their composition stays close" does not hold across resolutions, because the noise shape changes with resolution. | DC-N2 |
| n6 | Claims that assembly takes "under a minute", that the run is "dominated by FFmpeg" and that it "finishes in minutes" are unmeasured. | DC-N4, SY-14 |
| n7 | Single-pass `loudnorm` misses its target. Use two passes and measure after encoding. Write "−1 dBTP" and give a tolerance in G5, for example −14 ±1 LUFS. | DC-N5, SY-11 |
| n8 | Holding a 5 s clip's last frame for a long shot looks frozen. Define a rule for the overrun. | DC-N6 *(S5 N8)* |
| n9 | Templating the run id rewrites tracked kernel files. Generate them in a gitignored build folder, and point to that from the Kaggle section. | DC-N7 *(S6 #11)* |
| n10 | A `git grep` in `make test` prevents nothing. Use a pre-commit hook or GitHub push protection, and word the claim accurately. | DC-N8, SY-20 |
| n11 | Nothing enforces the consent gate. Add a `real_person` flag that requires a consent reference before generation. | DC-N9 |
| n12 | `cost_usd_est` has no source or date for its prices. | DC-N10 |
| n13 | Calling TTS once per shot risks prosody drift between lines. Log it as an experiment. | DC-N11 |
| n14 | The `outputs/final/` exclusion is ambiguous, and 100 MB conflicts with the 95 MB stated elsewhere. | ST-14, SY-16 *(S6 #10)* |
| n15 | The diagram has a misaligned border and an unlabelled branch. The cross-reference "Technical Plan, Keyframes" does not match the heading. The `runs.jsonl` fields should be a table. | ST-9, ST-10, ST-11, ST-13 |
| n16 | There are no links. Link `docs/references/module_5399.md` from the Overview. Use horizontal rules consistently. | ST-15 *(S6 #5)* |
| n17 | Wording: <ul><li>"Easy" is subjective.</li><li>The Overview states behaviour as fact; say "is designed so that".</li><li>"From the author's family" and "own language" drift from the module's wording.</li><li>"Markdown documents only" should be "written documents".</li><li>"Shows live" should be "demonstrates".</li><li>"Pan-and-zoom" and "Ken Burns" both appear; pick one.</li><li>The user-test dates are vague.</li><li>A tautology about batch size.</li><li>Unclear budget for the final pass.</li><li>"This is a fallback, not the plan" is redundant.</li><li>"May read as a shortcut" is speculative.</li><li>"Evidence the module rewards" overstates the module, which treats it as optional.</li></ul> | SY-7–SY-10, SY-12, SY-15, SY-17–SY-19, SY-21, SY-22 |

--------------------------------------------------------------------------------

## Traceability

| Raw | Consolidated |
| --- | --- |
| DC-M1, ST-1 | C1, C11 |
| DC-M2, ST-2 | C2 |
| DC-M2, ST-3, SY-2 | C3 |
| DC-M3 | C4 |
| DC-M4 | C5 |
| DC-M5 | C6 |
| DC-M6 | C7 |
| DC-M7, ST-6 | C8 |
| DC-M8 | C9 |
| DC-M9 | C10 |
| DC-M10 | C11 |
| DC-M11 | C12 |
| DC-M12 | C13 |
| DC-M13 | C14 |
| ST-4, ST-5, ST-12, SY-5, SY-6, DC-N3 | C15 |
| DC-N1…N11, ST-7…ST-15, SY-1, SY-3, SY-4, SY-7…SY-22 | n1–n17 |
