# Module 5399 requirements: AI-Content Generation, "The Heritage Short"

Source: https://tenx.10academy.org/trainee/module/5399, read on 2026-11-24.
This is a requirements summary in our own words, not a copy of the page. The
glossary and tips appendices are left out.

## Deadline

Both assignments are due Thursday 26 November 2026, 23:59 East Africa Time. The
module plans for three days of work.

## What to build

*   **Film**: 60–90 seconds about a person, place or story important to the
    author's family. Narration is in a language the author chooses. It needs
    English subtitles, an original score ducked under the voice, and a visible
    end card saying it was made with AI. It is exported in 9:16 and 16:9.
*   **Pipeline**: a public repository in which `storyboard.json` is the
    contract between stages. Each stage is a script that reads the storyboard
    and writes its output. There are five stages: keyframes, moving shots,
    music, narration and assembly. Changing one shot should regenerate only
    that shot. A stranger should be able to clone the repo, run one command,
    and regenerate the film.

## Software expectations

*   Clear stage boundaries, a JSON Schema for the storyboard validated before
    every run, retries, and caching keyed by a hash of inputs so re-runs only
    regenerate what changed.
*   No secrets in the repository.
*   One line per model call in `runs.jsonl`: model, parameters, seed, latency,
    cost.
*   One documented command (`make film` or equivalent) runs the whole pipeline
    from a clean clone.

## Suggested repository shape (may be improved on)

`README.md`, `storyboard.json`, `schema/`, `pipeline/` (one script per stage:
script, keyframes, shots, music, narration, assemble), `runs.jsonl`,
`outputs/` (kept for inspection), `DESIGN.md`, `ARCHITECTURE.md`,
`EXPERIMENTS.md` (about ten hypothesis → change → result entries),
`FAILURES.md`, `COSTS.md` (measured latency and GPU minutes per stage, list-price
equivalent), `ETHICS.md` (consent, licences, labelling).

Assignment 1 grading reads only code, text, logs and documents. Audio, image and
video files in the repo are not opened, so evidence must be in writing.

## Suggested free stack

| Stage | Model | Where |
| --- | --- | --- |
| Coding agent | Gemini Flash, free Claude models | Antigravity CLI or OpenCode |
| Script, storyboard, translation | Gemini Flash / Flash-Lite | Gemini API (free tier) |
| Narration | Gemini Flash TTS (130+ languages incl. Amharic) | Gemini API (free tier) |
| Keyframes | FLUX.2 klein or FLUX.1 schnell | Cloudflare Workers AI (daily free allowance, roughly 50–170 images) |
| Moving shots | Wan 2.2 TI2V-5B (HunyuanVideo 1.5 alternative) | Kaggle notebook, 2× T4, about 30 GPU hours a week; Colab as backup |
| Music | ACE-Step 1.5 | Kaggle or Colab |
| Assembly | FFmpeg (Remotion optional) | Local |
| Showcase | Static page or Gradio Space | Hugging Face |

Claude Code and Codex are paid and optional. The main constraint is GPU time
and queueing, not money: a 5-second 720p Wan clip takes several minutes, longer
on a T4. Drafting at 480p and batching is advised.

## Phases and checkpoints

1.  **Story and radio cut**: set up accounts; a smoke test that calls each
    provider once and logs latency; choose story and audience; record consent
    in ETHICS.md before generating any real person; write audience and intent
    in DESIGN.md; write the schema and draft 8–12 shots; generate TTS narration
    and assemble a radio cut (narration over placeholder music on black); test
    it with at least three audience members and record what changed.
2.  **Pictures and music**: character and style reference sheet first, then
    keyframes conditioned on it; Wan image-to-video on Kaggle as quota allows,
    cached by input hash; about three ACE-Step candidates, choose one and say
    why; log every call, experiment and failure.
3.  **Edit and release**: cut to music, duck score under narration, burn in
    subtitles, normalise loudness, add end card, export both ratios, all in
    code from the storyboard; second user test with at least three people;
    README, ARCHITECTURE, COSTS; report; public post with the platform AI label
    on; walkthrough video of at most five minutes showing the architecture, one
    hard decision, and one keyframe prompt or narration line changed in
    `storyboard.json` with only that shot regenerating (pausing during the job
    and showing logs is acceptable; Wan need not be rerun on camera).

Fallback allowed: if video generation fails, a slow pan-and-zoom over keyframes
in FFmpeg is acceptable.

## Consent, labelling, licences

*   Recorded, informed consent for any real person's face, likeness or voice,
    including the words put in their mouth.
*   Disclose AI content on the platform; keep the end card; leave watermarks
    and provenance metadata intact.
*   Note the licence of every model and output (Wan 2.2 Apache 2.0; ACE-Step 1.5
    outputs usable commercially).
*   Describe styles rather than naming living artists.
*   Keep private family details out of free endpoints that may train on inputs.

## Submissions

*   **Assignment 1 (codebase and report)**: public GitHub repo link plus a
    report (PDF, Word or link) covering what was made and for whom, what the
    audience said, the hardest problem and its solution, one suggested practice
    that helped and one that did not, ceiling work, and next steps. Followed by
    an AI interview about the pipeline, experiments, failures and audience.
*   **Assignment 2 (film, walkthrough, post; graded by hand)**: 9:16 MP4 link as
    the main submission; 16:9 MP4, walkthrough video and public post (or
    screenshot) as attachments. Links must open without login.

## Rubric

Assignment 1 (100 points):

| Criterion | Points |
| --- | --- |
| Software engineering and reproducibility | 20 |
| Documentation | 10 |
| Design thinking and audience (two user tests of 3+ people, storyboard visibly changed, a reason for every shot) | 10 |
| Experimentation and iteration (10+ logged experiments) | 10 |
| Troubleshooting and persistence | 10 |
| Measurement (latency, GPU minutes, list-price cost, frontier comparison if available) | 5 |
| Consent, labelling and licences | 5 |
| Report: reflection and audience learning | 10 |
| Report: suggested practices tested honestly | 10 |
| Report: curiosity beyond the floor | 10 |

Assignment 2 (100 points): film 50, walkthrough 30, public post 20.

**Gate**: if a real person appears or is voiced without a consent record in
ETHICS.md, the film scores zero.

## Optional ceiling work (examples)

Extra languages (Afaan Oromo, Tigrinya, Somali) with documented failures; a song
with timed lyric captions; an open-vs-frontier benchmark with a blind test of
5+ people; packaging the pipeline as a CLI or MCP server; a family web app; a
character LoRA; measuring audience response. Judged on insight, not volume.
