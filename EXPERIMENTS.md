# Experiments

Each entry records the hypothesis, the change, the measured result and the
decision. Unless noted, the evidence is in `runs.jsonl`, in the files named
in the entry, and in FAILURES.md.

## E1. One loudness pass is enough (25 Nov). Rejected

*   **Hypothesis:** a single `loudnorm` pass at I = −14 lands inside
    −14 ±1 LUFS.
*   **Change:** rendered a 67 s test cut from the real TTS clip, once with a
    single pass, then again with two passes (measure first, then normalise
    linearly).
*   **Result:**
    *   Single pass: −15.22 LUFS, outside the target.
    *   Two passes: −14.72 LUFS, true peak −1.34 dBTP.
    *   The full 95.3 s draft later measured −14.04 LUFS and −1.10 dBTP.
*   **Decision:** two passes (`assemble.master_filter`).

## E2. `original_size` makes subtitle sizes pixels (25 Nov). Rejected

*   **Hypothesis:** `subtitles=...:original_size=1080x1920` with
    `FontSize=48` gives 48 px text.
*   **Change:** compared one test frame with `original_size` against one with
    `force_style='PlayResX=1080,PlayResY=1920,...'`.
*   **Result:**
    *   With `original_size`, the text was wider than the frame and sat at the
        top, because SRT keeps libass's 288-line canvas.
    *   With PlayRes, there were two 56 px lines near the bottom, at both
        ratios.
*   **Decision:** PlayRes (FAILURES.md F4).

## E3. Prompt wording can undo posed reference framing (25 Nov). Rejected

*   **Hypothesis:** adding "candid moment, not looking at the camera" and
    putting the action first fixes s07, s11 and s12, which came out as posed
    portraits.
*   **Change:** rewrote those prompts and kept the reference images. Seeds
    were unchanged.
*   **Result:**
    *   s07, s11 and s12 were still front-facing standing portraits.
    *   s11 gained a duplicated third man and no photograph.
    *   Only s01 improved, to black and white, though it still showed one
        young man.
*   **Decision:** the reference images, not the wording, set the framing.
    Next test: E4.

## E4. Reference images on or off per shot (25 Nov). Adopted

*   **Hypothesis:** the front-facing reference portraits pull every keyframe
    towards a posed portrait. With references off, the text descriptions
    alone keep the characters recognisable in wide, candid and from-behind
    shots.
*   **Change:** added `use_references` per shot. Set it to false for s01,
    s07, s11 and s12, with the same seeds and prompts.
*   **Result:** all four now show the intended action:
    *   s01: two young friends in a black-and-white photo.
    *   s07: seated in profile in the stands.
    *   s11: Abebe showing Kassa a photograph.
    *   s12: seen from behind in the empty stadium.

    The flat cap with grey beard, and the white hair with cream shawl, stay
    recognisable. Close-ups keep references for face identity.
*   **Decision:** adopted. Wide and candid shots go without references;
    close-ups use them.

## E5. Wording the description fixes ethnicity drift and props (25 Nov). Adopted

*   **Hypothesis:** the first reference portraits read as lighter-skinned and
    not clearly Ethiopian, and young Abebe held an American football. Adding
    "dark brown skin, Ethiopian Habesha features", "round black-and-white
    leather soccer ball" and "alone in the frame" fixes all three.
*   **Change:** edited the four character descriptions and regenerated the
    references (4 images).
*   **Result:**
    *   The faces read as Habesha.
    *   The ball is a soccer ball.
    *   Each portrait shows one person.
    *   Approved by the author.
*   **Decision:** adopted. The descriptions are also appended to every shot
    prompt.

## E6. Voice choice for two elderly Amharic speakers (25 Nov). Author decision

*   **Hypothesis:** a non-Amharic studio voice can sound natural enough in
    Amharic, because the Voice Library has only one Amharic male voice (a
    man in his late 20s).
*   **Change:** rendered one Abebe line in five voices: `am-et-assistant-1`,
    Gacrux, Algenib, Charon and Schedar.
*   **Result:** 4.5–5.5 s for the same line. The author preferred
    `am-et-assistant-1` and Algenib.
*   **Decision:** Kassa uses `am-et-assistant-1`, Abebe uses Algenib.
*   **Lesson:** five auditions used half of a day's TTS quota (E8).

## E7. Flash and Flash-Lite TTS sound alike for the same speaker (25 Nov). Accepted

*   **Hypothesis:** lines from `gemini-3.8-flash-lite-tts` match the Flash
    lines closely enough to mix in one film.
*   **Change:** rendered Kassa's s07 line on Lite and compared it with his
    s03 line on Flash.
*   **Result:** the author judged them close enough. 5 lines are on Flash
    and 11 on Lite. Each line records its model, so any line can be moved
    back.
*   **Decision:** mixed, recorded per line in `tts_model`.

## E8. A delivery style changes line length (25–26 Nov). Confirmed

*   **Hypothesis:** delivery styles change duration a lot.
*   **Change:** none yet. This is an observation from `runs.jsonl`
    durations.
*   **Result:**
    *   s05.1 with "laughing softly" ran 11.0 s for a 13-word line.
    *   Comparable lines ran 3–6 s.
    *   s03.0 ("Okay... who are you?") ran 4.4 s with "uncertain and gentle".
*   **Retake (26 Nov, 02:15 EAT):** s05.1 regenerated with "warm, a little
    amused" on Flash-Lite, same text and voice. Result: **5.5 s**, down from
    11.0 s.
*   **Decision:** keep the calmer take. With it and the three new photo-scene
    lines, the estimated length is **89.0 s** (from 95.3 s), counting the
    last missing line at 1.1 s. It now fits under 90 s with no script cut.
*   **Final (26 Nov):** the last line, "አሁንም ነኝ።", came out at 1.1 s.
    `make film` built both exports at exactly **89.0 s**: −14.03 LUFS and
    −1.41 dBTP for both, with no fallbacks.

## E9. Pacing can absorb length without script cuts (25 Nov). Partly

*   **Hypothesis:** shortening the tail after each line (0.5 → 0.3 s), the
    wordless shots (s01, s06, s10) and the end cards (14 → 12 s) brings the
    estimate under 90 s.
*   **Change:** applied all three. No new TTS calls.
*   **Result:** 100.6 s → 95.3 s, still 5.3 s over.
*   **Decision:** keep the changes. Fix the rest with the E8 retake. If that
    is not enough, the author picks the next cut.

## E10. Int8 quantization is safe on a T4 for ACE-Step (25 Nov). Rejected

*   **Hypothesis:** `quantization="int8_weight_only"` (recommended for GPUs
    under 20 GB) lets ACE-Step 1.5 turbo run safely on a 16 GB T4.
*   **Change:** compared int8 in fp16 against no quantization in fp16, with
    a float32 fallback.
*   **Result:**
    *   Int8: all 3 jobs returned NaN latents.
    *   No quantization: all 3 tracks fine (90 s, 48 kHz stereo,
        −13.8 to −14.1 LUFS, 7–8 LU range) at 14.5–18.3 s each. The float32
        fallback never ran.
*   **Decision:** no quantization (FAILURES.md F8).
