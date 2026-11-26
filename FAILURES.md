# Failures

## F1. Gemini TTS: old `generateContent` speech call rejected (25 Nov)

*   **What broke:** `make smoke` TTS check. Every model returned
    `400 Invalid JSON payload received. Unknown name "speechConfig"`.
*   **Tried:** six model ids, including `gemini-3.8-flash-tts`; same error.
*   **Cause:** Gemini 3.8 TTS moved to the Interactions API
    (`client.interactions.create`), with style in a `speech_metadata`
    annotation and WAV output by default.
*   **Fix:** `pipeline/tts.py` uses the Interactions API. Smoke check passes.

## F2. Kaggle kernel ran without a GPU (25 Nov)

*   **What broke:** smoke kernel finished with `nvidia-smi` not found.
*   **Cause:** the Kaggle account was not phone-verified, so no accelerator
    was granted.
*   **Fix:** phone verification on kaggle.com. The rerun confirmed a Tesla T4
    in 32 s with `machine_shape: "NvidiaTeslaT4"`.

## F3. FFmpeg missing `subtitles` and `drawtext` (25 Nov)

*   **What broke:** smoke FFmpeg check; Homebrew's default `ffmpeg` lacks
    libass and freetype.
*   **Tried:** `brew install ffmpeg-full`. The first attempt stalled in
    Homebrew's self-update (git fetch from GitHub).
*   **Fix:** installed with `HOMEBREW_NO_AUTO_UPDATE=1`. It is keg-only, so
    `pipeline/common.py` prepends its bin folder to PATH for the pipeline.

## F4. Subtitles rendered huge and off-frame (25 Nov)

*   **What broke:** a test frame with `original_size=1080x1920` and
    `FontSize=48` drew text larger than the frame width at the top.
*   **Cause:** SRT input keeps libass's 288-line canvas; `original_size` does
    not change it.
*   **Fix:** `force_style='PlayResX=W,PlayResY=H,...'`. Frame grabs at both
    ratios showed two 56 px lines near the bottom.

## F5. Narration stage hung for 10+ minutes on one line (25 Nov)

*   **What broke:** `make` narration stalled three times on shot s07's first
    line, with nothing in `runs.jsonl`.
*   **Tried:**
    1.  A 120 s client timeout: no effect.
    2.  A 90 s per-call timeout: no effect.
    3.  A stack dump after 60 s showed the call sleeping inside the SDK's
        own retry loop (`retry_with_attempt_count_backoff`).
*   **Cause:** with SDK retries disabled, the real error appeared:
    `429 Rate limit exceeded for model gemini-3.8-flash-tts (limit: 10
    requests per day on Free Tier)`. The SDK was silently retrying a daily
    quota error with backoff. Our own daily-limit check also missed the
    message, because its pattern matched `per_day` but not "per day".
*   **Fix:**
    *   `tts.client()` sets `retry_options={"attempts": 1}`, so every failure
        reaches `common.with_retry` and is logged.
    *   The daily-limit pattern is now `per[ _]?day|daily`, with a test using
        the real message.
*   **Open:** 10 TTS requests per day cannot cover a 21-line script by the
    deadline. See the decision in DESIGN.md / COSTS.md.

## F6. Flash-Lite TTS has the same 10-a-day limit (25 Nov)

*   **What broke:** after switching the remaining 11 lines to
    `gemini-3.8-flash-lite-tts`, generation stopped after 7 lines with
    `429 ... (limit: 10 requests per day on Free Tier)`.
*   **Effect:** 12 of 16 lines exist. Missing: s11.2, s11.3, s12.0, s12.1.
    Both free TTS quotas reset at about 08:00 UTC (11:00 EAT) on 26 Nov.
*   **Also found:** with the trimmed script, the estimated length (missing
    lines at 2.5 s each) is 100.6 s, against a 90 s limit. The largest
    stretch is s05.1 (Abebe, "laughing softly"), at 11.0 s for a 13-word
    line.
*   **Resolved (26 Nov):** Flash-Lite's quota turned out to be a rolling
    window. At 02:15 EAT it allowed 4 more lines, and at 12:51 EAT the last
    one. All 16 lines exist, and the final films are 89.0 s.
*   **Lesson:** the free TTS budget is about 20 lines a day across both
    models. Auditions and probes spend the same budget as production lines,
    so test with one line, not five.

## F7. ACE-Step 1.5 does not install on Kaggle's Python (25 Nov)

*   **What broke:** all three music jobs failed in about 60 s. From the
    kernel's `setup.log`: `Package 'ace-step' requires a different Python:
    3.13.16 not in '<3.13,>=3.11'`.
*   **Tried:** `pip install -e .` into the Kaggle image's Python 3.13.
*   **Fix:** the kernel now runs `uv sync --python 3.12`, the repo's own
    install route. It runs generation as a subprocess with that
    environment's Python, so there is no forced install against the wrong
    interpreter.
*   **Also fixed:** Kaggle answers `403 ... kernels.get was denied` (not 404)
    for a kernel that was never pushed. The runner now treats that as "no
    previous version".

## F8. ACE-Step produced NaN latents on the T4 (25 Nov)

*   **What broke:** after the uv fix, all three jobs failed with
    `Generation produced NaN or Inf latents (... dtype=torch.float16 ...)`
    after a 195 s kernel run.
*   **Cause:** the T4 has no bf16, so ACE-Step runs in fp16. Its own loader
    notes that fp16 can overflow on pre-Ampere GPUs. The int8 weight
    quantization I had requested added more precision loss.
*   **Fix:** no quantization. If a job still returns NaN, the kernel
    converts the DiT to float32 and retries that job.
*   **Result:** all three candidates generated in fp16, at 14.5–18.3 s of
    GPU each and 210 s for the whole kernel. The float32 fallback never ran,
    so the int8 quantization caused the NaN, not fp16 itself.
