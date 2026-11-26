### What this proposes

The document proposes a batch pipeline built around a single storyboard file.
It turns a hand-written `storyboard.json` (8–12 shots, 60–90 s) into a
narrated, scored and subtitled short film about the author's family. The film
is exported natively at 9:16 and 16:9 by one command, `make film`. Every stage
writes its output to a file named by a hash of the stage's inputs. Editing one
shot therefore regenerates only that shot, and a fresh clone that includes the
committed cache can rebuild the film without calling any model. The film that
is always produced is a slow pan-and-zoom (Ken Burns) over each still image.
Wan 2.2 video clips rendered on Kaggle replace those stills one shot at a time,
as free GPU quota allows. Every model call is logged to `runs.jsonl`, because
the graders can only read text.

### How the existing system works, per this document

Nothing exists yet: every file in the plan is marked Create. The setting is a
10 Academy challenge with two graded submissions due on 26 Nov. The providers
are a free stack:

*   Gemini for text and speech
*   Cloudflare Workers AI FLUX for images
*   Kaggle T4 GPUs (about 30 h a week) for Wan video and ACE-Step music
*   local FFmpeg

The document describes each provider's limits and failure modes. It mentions
the grading rubric only in passing.

--------------------------------------------------------------------------------

# Stage 6: Comprehension Test

*   **Target**: `docs/designs/heritage_short_pipeline.md`. FeatureRange is
    lines 1–507 and DetailedRange is lines 508–870.
*   **Reviewer**: Comprehension Goldfish, run in a fresh context. It had the
    document only, with no Goldfish context and no standard.
*   **Overall**: Both ranges could be paraphrased, and the document is mostly
    self-contained. The main gaps are findings 1–4. Findings 5–6 come from
    relying on a rubric the document never links.

## Findings

1.  **Major. Decision labels point to an option list the reader never sees.**
    *   **Scope**: Lines 194–198 ("author choice A", "author choice 3") and
        lines 417–430 (the rejected "Alternative A").
    *   **Problem**: "Author choice A" is the adopted Kaggle push.
        "Alternative A" is the rejected manual notebook. A reader will
        conclude the author picked an option the document then rejects.
        Label each decision by what it is.
2.  **Major. "One command" hides two manual steps.**
    *   **Scope**: G1 (66–71), CUJ 1–2 (151–170), lines 355–359 and 370–373,
        and file 20 (686–691).
    *   **Problem**: `keyframes.py` refuses to run until the author fills in
        `characters[].golden_reference` by hand, and the author also sets
        `music.chosen` by hand. On a first run, `make film` stops partway and
        needs an edit and a re-run. No user journey describes this first-run
        sequence.
3.  **Major. A clean-clone rebuild conflicts with retrying fallback shots.**
    *   **Scope**: CUJ 1 (158–160) against lines 329–331, 351–353 and file 27
        (752–756).
    *   **Problem**: A shot with `animate: true` and no cached clip is pushed
        to Kaggle again on every run. If the committed cache holds even one
        fallback shot, a stranger's `make film` calls Kaggle. That breaks
        CUJ 1's promise of no model calls. The document does not say how the
        committed state prevents this, for example by setting `animate: false`
        on shots that fell back.
4.  **Major. The clip's resolution and frame count have no stated source.**
    *   **Scope**: Lines 361–366, 286 and 335 (`resolution`, `frames`), and
        line 552 (`WAN_RESOLUTION`).
    *   **Resolution**: It looks like a global environment variable. The
        design says the 720p pass re-renders only the shots that survived the
        near-final user test, but no field or mechanism selects those shots.
        Changing the variable changes every clip's cache key.
    *   **Frame count**: It is never tied to anything, and no mapping from
        `duration_s` to frames is given.
5.  **Major. Decisions are justified by a rubric that is neither linked nor
    summarised.**
    *   **Scope**: Lines 23–29, 112–113, 426, 461, 477, 510, 820, and "Phase 1"
        at lines 241 and 577.
    *   **Problem**: The document refers to the following without linking or
        explaining them:
        *   "the software-engineering criterion"
        *   "the film criterion"
        *   "the open-vs-frontier evidence the module rewards"
        *   "floor" and "ceiling work"
        *   "the module's checkpoints"
        *   "Phase 1"
        *   "the six required sections"

        A reader cannot check the rejection reasons that rest on them. Link
        the brief or summarise the rubric.
6.  **Major. "The cohort's frontier lane" is undefined.**
    *   **Scope**: Lines 107 and 502.
    *   **Problem**: This term decides when paid models may be used, but the
        document never says what the lane is or what "opens" means.
7.  **Nit. Stage numbering is inconsistent.**
    *   **Scope**: The diagram (212–231), line 596 and line 686.
    *   **Problem**:
        *   The diagram makes the reference stage [0] and gives validation no
            number.
        *   The plan calls validation "Stage 0" and the reference stage
            "Stage 0b".
        *   The `make film` order (line 522) differs from both.

        Use one numbering scheme throughout.
8.  **Nit. "Radio cut" and "near-final cut" are not defined where they first
    appear.**
    *   **Scope**: Line 133.
    *   **Problem**: "Radio cut" is used before its definition at line 240.
        "Near-final cut" is never defined: the document does not say which
        stages it includes or at what quality.
9.  **Nit. A stale cross-reference.**
    *   **Scope**: Line 113.
    *   **Problem**: It says "see Future Improvements, to be drafted", but that
        section exists at line 497.
10. **Nit. Two size limits disagree.**
    *   **Scope**: Line 296 (100 MB) against line 544 (95 MB).
    *   **Problem**: Two different thresholds are given for leaving files in
        `outputs/final/` out of git.
11. **Nit. How the run id reaches the kernel is explained too late.**
    *   **Scope**: Lines 340–342.
    *   **Problem**: The Technical Plan does not say how the run id gets into
        the kernel's source. The answer, templating into
        `kaggle/<name>/build/`, appears only at line 711. Add a pointer.
12. **Nit. It is unclear whether there is one golden reference per character
    or one per ratio.**
    *   **Scope**: Lines 372 and 285.
    *   **Problem**: The reference sheet is generated in both ratios, but the
        author approves "one image per character", and the cache key mentions
        "reference image file hashes".
13. **Nit. No rule for when the music and timeline lengths differ.**
    *   **Scope**: Lines 254 and 388.
    *   **Problem**: The score has a fixed `duration_s`, but narration can
        stretch the timeline past the planned durations. The document does not
        say whether the score is trimmed, looped or faded.
14. **Nit. `script.py` is called a "stage" but is not one.**
    *   **Scope**: Line 606 against line 610.
    *   **Problem**: It is not part of `make film` and is not in the stage
        list. Call it the drafting helper.
15. **Nit. Shot ids use two formats.**
    *   **Scope**: Lines 165–170 ("shot 04") against line 259 (`s01`…`s12`).
    *   **Problem**: This matters for the `grep` check at line 858.
