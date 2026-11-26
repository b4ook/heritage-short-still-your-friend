# Costs and measurements

All of this runs on free tiers. The table below is generated from
`runs.jsonl` by `make costs`. Every number in it was measured, not
estimated.

## Measured per stage and model

<!-- costs:start -->
| Stage | Model | Calls | OK | Failed | Cache hits | Fallbacks | Mean latency (s) | GPU min | List-price USD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| keyframes | `@cf/black-forest-labs/flux-2-klein-4b` | 48 | 48 | 0 | 72 | 0 | 7.8 | n/a | n/a |
| music | `brookteweldebirhan/heritage-music` | 15 | 3 | 12 | 0 | 0 | n/a | 10.4 | n/a |
| narration | `gemini-3.8-flash-lite-tts` | 15 | 12 | 2 | 31 | 0 | 8.4 | n/a | n/a |
| narration | `gemini-3.8-flash-tts` | 7 | 7 | 0 | 30 | 0 | 4.9 | n/a | n/a |
<!-- costs:end -->

How to read the table:

*   **Calls** counts real model calls: `ok`, `retry` and `failed`.
*   **Cache hits** made no model call.
*   **GPU min** comes from each Kaggle kernel's total wall time, including
    install and download, not only generation.
*   **Music failures** count each failed job twice: once when its run
    finished, and again when the next run collected that version's output
    before pushing. That is 2 failed runs × 3 jobs × 2 (FAILURES.md F7, F8).
*   **Smoke checks** do not appear. Their log lines were deleted during
    development, before this table existed. Their results are in
    FAILURES.md F1–F3 and the timings below.

## Free-tier limits found (25 Nov 2026)

| Provider | Limit found | How it was found |
| --- | --- | --- |
| Gemini `gemini-3.8-flash-tts` | 10 requests per day | 429 body, see FAILURES.md F5 |
| Gemini `gemini-3.8-flash-lite-tts` | 10 requests per day (a separate quota) | 429 body, FAILURES.md F6 |
| Gemini `gemini-3.8-flash` (text) | Not hit; 503 "high demand" seen once | smoke test |
| Cloudflare Workers AI, FLUX.2 klein 4B | Not hit after about 44 images in one day | `runs.jsonl` |
| Kaggle GPU | About 30 h per week, phone verification required | Kaggle settings; FAILURES.md F2 |

The binding limit was TTS: 20 lines a day across both models. Auditions
and probes spend the same quota as production lines. That is why the script
was trimmed from 20 to 16 lines (DESIGN.md), and why dialogue generation was
spread over two days.

## Timings worth knowing

*   **Keyframes:** the first FLUX.2 klein call of a session took about 65 s
    (cold start). Later calls took 5–10 s each.
*   **TTS:** about 4–6 s per line. Speech runs about 5 s per short Amharic
    line in these voices, which is slower than the module's rule of thumb of
    2–2.5 words per second.
*   **Music:** ACE-Step 1.5 turbo in fp16 on a T4 took 14.5–18.3 s per 90 s
    track. The kernel took 210 s in total, mostly `uv sync` and the weight
    download.
*   **Assembly:** about 3.5 min per aspect ratio on an M-series MacBook Air.
    Most of that is `zoompan` on 2× upscaled stills.

## List-price equivalents

`PRICES` in `pipeline/common.py` is left as `None` until each price has a
source and a date. A cost column shows `n/a` rather than a guess. To fill
it, record each list price here with its URL and date, then set it in
`PRICES`:

*   Cloudflare Workers AI price per FLUX.2 klein image (neurons per image ×
    price per 1,000 neurons)
*   Gemini 3.8 Flash TTS and Flash-Lite TTS price per audio second on the
    paid tier
*   On-demand cloud price of a T4 GPU hour, to value the Kaggle GPU minutes
