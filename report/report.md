# Report: "Still Your Friend" (አሁንም ጓደኛህ ነኝ)

10 Academy challenge "AI-Content Generation: The Heritage Short". Author:
b4ook.

Repository: <https://github.com/b4ook/heritage-short-still-your-friend>

Every number below comes from the repository: `runs.jsonl`, COSTS.md,
EXPERIMENTS.md (E1–E10) and FAILURES.md (F1–F8).

## 1. What I set out to make, and for whom

**The film.** An 89-second Amharic short about Abebe and Kassa, two
lifelong friends in their seventies. Kassa has dementia and no longer
recognises Abebe. Abebe keeps taking him to football. It opens as a warm
story about friendship and football. The illness shows through the
friendship, not through a lecture. Only the closing cards carry the
awareness message: learn the signs, seek help early, stay with the person.
The characters, faces and voices are all fictional.

**The audience:**
*   Ethiopian families, both young adults and older people.
*   Families caring for someone with dementia.
*   Caregivers and health workers.

The film has to work for someone who knows nothing about dementia. It is
made for phones first (9:16), with a 16:9 cut for sharing.

**The pipeline.** One file, `storyboard.json`, drives every stage, and
`make film` rebuilds both exports from it:
*   **Keyframes:** 12 shots × 2 aspect ratios with FLUX.2 klein on
    Cloudflare.
*   **Dialogue:** 16 lines with Gemini 3.8 TTS, two voices.
*   **Score:** three ACE-Step 1.5 candidates on a Kaggle T4.
*   **Assembly in FFmpeg:**
    *   ducking and two-pass loudness normalisation;
    *   burned-in English subtitles;
    *   Amharic closing cards;
    *   an AI disclosure card that names only the models used.

Every output is stored under a hash of the exact request that made it, so
editing one line regenerates only that line. The final build used no
model at all: every stage was a cache hit.

**Final measurements:**
*   Both exports are 89.0 s.
*   Loudness −14.03 LUFS, true peak −1.41 dBTP.
*   16 lines, score candidate 1, and no shot fell back to an unplanned
    still.

## 2. What I learned from my audience

> **To fill in from DESIGN.md before submitting. Do not submit with these
> placeholders.**

*   **User test 1, the radio cut** (dialogue over a placeholder track on
    black, 25 Nov).
    *   Who: _at least 3 people from the audience, and how you reached them._
    *   What they said: _quotes or close paraphrase._
    *   What changed: _the storyboard edits it caused, with the commit._
*   **User test 2, the near-final cut** (version one of the film).
    *   What they said: one tester found the video motion a bit laggy. The
        others said the narration should change, because the AI voice
        didn't sound right.
    *   What changed: I made version two (commit `7813f7e`). The stepped
        Ken Burns moves became eased depth parallax with dissolves between
        shots (E11). Ten of the 16 lines were reworded and their delivery
        styles rewritten. I could not swap the voices: Gemini has one
        Amharic male voice, and the free tier allows about 20 lines a day
        (E6, F5). Both versions are on the site for comparison.

**Changes the evidence forced before any audience heard it.** The first
complete script was 20 lines. The measured TTS durations put it at about
100.6 s, against a 90 s limit (E9).

*   I trimmed it to 16 lines. I cut "where are we going?" from the walk and
    merged "every week… with whom?… with me, for fifty years" into "Yes.
    With me. For fifty years."
*   I kept the full photograph exchange that ends on "አሁንም ነኝ።" ("I still
    am"), because that exchange is the film.

## 3. The hardest problem and how I solved it

**The narration stage hung, with no error.** Three runs stalled for more
than ten minutes on the same line, and nothing reached the log. Adding
client and per-call timeouts did not stop it.

**The decisive step was to stop guessing and get evidence:**
1.  I re-ran that one line with a stack dump after 60 s.
2.  The dump showed the call sleeping inside the Gemini SDK's own retry
    loop.
3.  With the SDK's retries turned off, the real error appeared: `429 Rate
    limit exceeded … (limit: 10 requests per day on Free Tier)`.

The SDK had been silently retrying a daily quota error. My own daily-limit
check also missed it, because it matched `per_day` but not "per day"
(F5).

**Fixes:**
*   SDK retries are off, so every failure reaches the pipeline's own retry
    helper and the log.
*   The daily-limit pattern now matches both spellings, with a test using
    the real message.

**The consequence shaped the rest of the project.** Free TTS allows about
20 lines a day across two models, and auditions spend the same budget.

*   Each line records which model made it, so the script could mix Flash
    and Flash-Lite after I compared one character across both (E7).
*   Changing one delivery style from "laughing softly" to "warm, a little
    amused" cut a line from 11.0 s to 5.5 s (E8). Together with tighter
    pacing (E9), the film fell from 100.6 s to 89.0 s with no further
    script cuts.
*   Flash-Lite's quota turned out to reset on a rolling window, which let
    the last lines through hours before the daily reset (F6).

**The runner-up was the music.** ACE-Step 1.5 failed twice on Kaggle:
*   **F7:** Kaggle runs Python 3.13, and ACE-Step needs 3.11–3.12. Fixed by
    running the repo's own `uv sync --python 3.12`.
*   **F8:** generation returned NaN audio. The cause was the int8
    quantization I had requested, not fp16 itself: without quantization,
    all three tracks rendered in 14–18 s each (E10).

## 4. Suggested practices, tested honestly

**A practice that beat my instinct: a JSON contract between stages, with
cached outputs keyed by the exact request.** My instinct was to script
each stage directly and regenerate when something changed. The contract
paid off repeatedly:
*   Trimming the script and retaking shot 5 regenerated only the changed
    lines. The other dialogue lines stayed cached.
*   Turning reference images off for four shots regenerated only those 8
    keyframes, not all 24.
*   The final `make film` produced both films with no model calls.

`runs.jsonl` shows it: the final build (run `20261126T095120-f553d3`) logged
28 keyframe and 16 dialogue `cache_hit` lines, and nothing else.

**A practice that did not work as suggested: generate a reference sheet
first and condition every keyframe on it.** The reference portraits did
hold identity: the same cap and beard, and the same shawl and white hair,
in every shot. But FLUX.2 klein also copied their framing. Every
conditioned shot came out as a posed, front-facing portrait. In s11, the
key "show the old photograph" moment, there was no photograph and a
duplicated third man.

*   Rewording the prompts ("candid", "not looking at the camera") did not
    help (E3).
*   What worked was turning references off per shot for wide, candid and
    from-behind shots (`use_references: false`), and keeping them for
    close-ups (E4). All four broken shots then showed the intended action,
    and the text descriptions alone kept the men recognisable.

The suggested practice holds for faces. It does not hold for composition.

## 5. Curiosity beyond the floor

I did not reach the listed ceiling items: no Wan motion, no blind test and
no second language. The extra work I did do is measurement that the next
person on a free stack can use:

*   **Free-tier limits.** 10 TTS requests per day per Gemini model, as
    separate quotas, with Flash-Lite resetting on a rolling window. No
    Cloudflare limit was hit at about 44 images in a day. All recorded in
    COSTS.md.
*   **Amharic voice supply.** Gemini's voice library has exactly one
    Amharic male voice (late 20s). I tested whether non-Amharic studio
    voices could carry Amharic dialogue for two elderly men (E6), and cast
    one of each.
*   **ACE-Step 1.5 on a T4.** It runs, if you use Python 3.12 through uv
    and no quantization. The kernel takes about 210 s including setup, and
    each 90 s track about 15 s. That is two failures someone else no
    longer has to hit.
*   **Text in the film.** FFmpeg subtitle sizes are wrong unless you set
    the canvas with `PlayResX`/`PlayResY` (E2). macOS's Kefa III renders
    Ge'ez script for the Amharic cards.

## 6. What I would build next

1.  **A native-speaker review of the Amharic.** End card 2 uses "የአእምሮ
    መታወክ", which can read as "mental disorder" and may stigmatise.
    "የመርሳት በሽታ" may be gentler. ETHICS.md records this.
2.  **Wan 2.2 motion for 9:16 close-ups.** The time-budgeted Kaggle runner
    and the clip cache are built and tested. The Wan kernel is the
    remaining piece.
3.  **A Tigrinya version.** Gemini TTS lists Tigrinya, and the storyboard
    format already supports it. Document where it fails.
4.  **A blind preference test** of the two TTS models with five listeners,
    to replace my own judgement in E7.

## Tools

I used Claude Code, a paid coding agent, rather than the free agents the
module suggests (Gemini or free Claude models through Antigravity CLI or
OpenCode). I directed the design, reviewed it through a multi-stage review
(`docs/reviews/`), and made the creative and casting decisions. The agent
wrote most of the code under that direction.
