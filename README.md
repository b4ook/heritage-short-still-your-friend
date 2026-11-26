# አሁንም ጓደኛህ ነኝ: Still Your Friend

A 60–90 second Amharic short film about two lifelong friends, Abebe and
Kassa. Kassa has dementia. The film is made entirely by a code pipeline from
one file, `storyboard.json`. One command rebuilds both exports:

*   `outputs/final/film_9x16.mp4`
*   `outputs/final/film_16x9.mp4`

Each has Amharic dialogue, English subtitles, an original score, Amharic
closing messages and a "Made with AI" card. All characters, faces and voices
are fictional and generated.

Made for the 10 Academy challenge "AI-Content Generation: The Heritage
Short".

*   Requirements summary: [docs/references/module_5399.md](docs/references/module_5399.md).
*   Design: [docs/designs/heritage_short_pipeline.md](docs/designs/heritage_short_pipeline.md).

## Run it

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env        # add GEMINI_API_KEY, CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN
make film
```

A clean clone that includes `outputs/` rebuilds the film entirely from the
cache. In that case every new line in `runs.jsonl` is `cache_hit` and no
model is called.

API keys and a Kaggle token are needed only when an output is missing and
must be regenerated:

*   Save the Kaggle API token to `~/.kaggle/access_token`.
*   The Kaggle account needs phone verification before it gets a GPU.

## Requirements

*   **Python 3.11 or later.** It was developed on 3.14.
*   **FFmpeg built with libass and freetype**, for subtitles and on-screen
    text. On macOS, run `brew install ffmpeg-full`. That build is keg-only,
    and the pipeline finds it at `/opt/homebrew/opt/ffmpeg-full/bin`.
    `make smoke` checks for the filters it needs.
*   **An Ethiopic font** for the Amharic cards:
    *   `assets/fonts/NotoSansEthiopic-Regular.ttf` if present;
    *   otherwise macOS's built-in Kefa III.
*   **Accounts:**
    *   Gemini API key (free tier);
    *   Cloudflare Workers AI (free allowance);
    *   phone-verified Kaggle account (T4 GPU).

## Commands

| Command | What it does |
| --- | --- |
| `make smoke` | One call per provider (Gemini text and TTS, Cloudflare FLUX, Kaggle T4, FFmpeg filters) |
| `make validate` | Checks `storyboard.json` against the schema and the code rules |
| `make radio` / `make radio-draft` | Dialogue over a placeholder track on black, the audio prototype for user test 1. The draft leaves missing lines silent. |
| `make film` | Validate, keyframes, dialogue, music, shots, assembly, both ratios |
| `make test` | Unit tests (no network) |
| `make costs` | Rebuilds the measured table in COSTS.md from `runs.jsonl` |
| `make prune` | Deletes cached files the current storyboard no longer uses (run before release) |

`python -m pipeline.assemble --draft --ratio 9x16` renders one ratio, with
silence for any missing line and the placeholder track if no score exists.

## First run on a new storyboard

1.  `make film` generates one reference portrait per character, then stops.
2.  View the portraits in `outputs/keyframes/`. Set each character's
    `golden_reference` in `storyboard.json` to the path the run printed, then
    run `make film` again.
3.  Listen to the three score candidates. Set `music.chosen` and
    `music.chosen_reason`. Until you do, assembly uses the first candidate
    and prints a warning.

## Version two

`storyboard_v2.json` tells the same story with reworded dialogue and depth
parallax motion (EXPERIMENTS.md E11). It reuses version one's keyframes and
score through the cache. Six unchanged lines reuse their audio, and ten new
lines cost ten TTS calls. Select it with the `STORYBOARD` variable:

```bash
STORYBOARD=storyboard_v2.json make film
```

Its films are written as `outputs/final/film_16x9_v2.mp4` and
`film_9x16_v2.mp4`. `make prune` keeps every file that any `storyboard*.json`
uses.

## Change one shot

Edit that shot's `image_prompt` (or one `lines[].text`) in
`storyboard.json`, then run `make film`. Every output is stored under a hash
of the exact request that made it, so only that shot's keyframes (or that
one line) are regenerated. Everything else is a `cache_hit` in
`runs.jsonl`.

## What it costs

Everything runs on free tiers. The binding limit is Gemini TTS, at 10
requests per day per model. See [COSTS.md](COSTS.md) for the measured
calls, latency and GPU minutes per stage.

## Repository map

| Path | Contents |
| --- | --- |
| `storyboard.json` | The contract: characters, voices, shots, dialogue lines, music, end cards |
| `schema/` | JSON Schema for the storyboard |
| `pipeline/` | One module per stage, plus `common.py` (cache keys, log, retries), `tts.py`, `cloudflare.py`, `kaggle_runner.py` |
| `kaggle/` | Kaggle kernels for the GPU stages (`smoke`, `music`, `wan`) |
| `tests/` | Unit tests and the fixture storyboard |
| `outputs/` | Cached outputs by stage, plus `final/` for the films and subtitles |
| `runs.jsonl` | One line per stage output event |
| `DESIGN.md`, `ARCHITECTURE.md`, `EXPERIMENTS.md`, `FAILURES.md`, `COSTS.md`, `ETHICS.md` | The written evidence |
| `docs/designs/`, `docs/reviews/` | The design document and its multi-stage review reports |
| `docs/references/` | The challenge requirements summary |

## Links

*   Film (9:16): _to add_
*   Film (16:9): _to add_
*   Public post: _to add_
