"""Smoke test: one call per provider, logged to runs.jsonl with stage "smoke".

Each check returns (verdict, note). verdict is "pass", "fallback" or "fail".
"""
import os
import subprocess
import sys
import time

from pipeline import cloudflare
from pipeline.common import OUTPUTS, load_env, log_call, with_retry, write_atomic

SMOKE_DIR = OUTPUTS / "smoke"
TEXT_MODEL = os.environ.get("GEMINI_TEXT_MODEL", "gemini-3.8-flash")
TTS_MODEL = os.environ.get("GEMINI_TTS_MODEL", "gemini-3.8-flash-tts")
TTS_VOICE = os.environ.get("GEMINI_TTS_VOICE", "Kore")
TTS_TEXT = os.environ.get("SMOKE_TTS_TEXT", "This is a smoke test for the heritage film.")
TTS_STYLE = os.environ.get("SMOKE_TTS_STYLE", "calm and warm")
REQUIRED_FILTERS = ("subtitles", "drawtext", "zoompan", "sidechaincompress")


def timed(stage_ctx: dict, fn):
    start = time.monotonic()
    try:
        value = with_retry(fn, stage_ctx)
    except Exception as exc:
        log_call(**stage_ctx, status="failed", attempt=1, latency_s=round(time.monotonic() - start, 2),
                 error=f"{type(exc).__name__}: {exc}"[:500])
        raise
    latency = round(time.monotonic() - start, 2)
    return value, latency


def check_gemini():
    from pipeline import tts

    client = tts.client()
    try:
        ctx = {"stage": "smoke", "provider": "gemini", "model": TEXT_MODEL, "params": {"prompt": "ping"}}
        text, latency = timed(ctx, lambda: client.models.generate_content(
            model=TEXT_MODEL, contents="Reply with the single word: ok").text)
        log_call(**ctx, status="ok", attempt=1, latency_s=latency)

        ctx = {"stage": "smoke", "provider": "gemini", "model": TTS_MODEL,
               "params": {"text": TTS_TEXT, "voice": TTS_VOICE, "style": TTS_STYLE}}
        wav, tts_latency = timed(ctx, lambda: tts.synthesize(client, TTS_MODEL, TTS_TEXT, TTS_VOICE, TTS_STYLE))
        path = write_atomic(SMOKE_DIR / "tts.wav", wav)
        seconds = tts.wav_seconds(path)
        log_call(**ctx, status="ok", attempt=1, latency_s=tts_latency, output_path=path)
        return "pass", f"text {latency}s; TTS {tts_latency}s for {seconds:.1f}s of audio -> {path}"
    except Exception as exc:
        try:
            names = sorted(m.name for m in client.models.list() if "flash" in m.name or "tts" in m.name)
        except Exception as list_exc:
            names = f"(model list failed: {list_exc})"
        return "fail", f"{type(exc).__name__}: {exc}. Models with flash/tts in the name: {names}"


def _image(model, prompt, width, height, inputs=()):
    ctx = {"stage": "smoke", "provider": "cloudflare", "model": model, "seed": 7,
           "params": {"prompt": prompt, "width": width, "height": height, "inputs": len(inputs)}}
    png, latency = timed(ctx, lambda: cloudflare.generate_image(model, prompt, 7, width, height, list(inputs)))
    path = write_atomic(SMOKE_DIR / f"{model.split('/')[-1]}_{width}x{height}_{len(inputs)}ref.png", png)
    log_call(**ctx, status="ok", attempt=1, latency_s=latency, output_path=path)
    return path, latency


def check_cloudflare():
    os.environ["CLOUDFLARE_ACCOUNT_ID"], os.environ["CLOUDFLARE_API_TOKEN"]
    prompt = "An elderly woman in a white cotton shawl at a market stall, warm morning light, painterly"
    try:
        wide, t1 = _image(cloudflare.KLEIN, prompt, 1344, 768)
        tall_plain, _ = _image(cloudflare.KLEIN, prompt + ", close portrait", 768, 1344)
        tall_ref, t2 = _image(cloudflare.KLEIN, prompt + ", close portrait", 768, 1344, [wide])
        return "pass", (f"klein 1344x768 {t1}s, 768x1344 with reference {t2}s. Reference pass rule: compare "
                        f"{tall_plain.name} (no reference) with {tall_ref.name} (reference {wide.name}) "
                        f"in {SMOKE_DIR} and record the result in EXPERIMENTS.md")
    except Exception as klein_exc:
        try:
            path, latency = _image(cloudflare.SCHNELL, prompt, 768, 1344)
            return "fallback", f"klein failed ({type(klein_exc).__name__}: {klein_exc}); schnell {latency}s -> {path}"
        except Exception as exc:
            return "fail", f"klein: {klein_exc}; schnell: {exc}"


def check_kaggle():
    from pathlib import Path

    kaggle_dir = Path.home() / ".kaggle"
    has_credentials = (
        os.environ.get("KAGGLE_API_TOKEN") or os.environ.get("KAGGLE_KEY")
        or any((kaggle_dir / name).exists() for name in ("access_token", "access_token.txt", "kaggle.json"))
    )
    if not has_credentials:
        return "fail", "no Kaggle credentials: save the API token to ~/.kaggle/access_token"
    from pipeline import smoke_kaggle

    ctx = {"stage": "smoke", "provider": "kaggle", "model": "kaggle-t4", "params": {"kernel": "heritage-smoke"}}
    try:
        result = smoke_kaggle.run()
    except Exception as exc:
        log_call(**ctx, status="failed", attempt=1, error=f"{type(exc).__name__}: {exc}"[:500])
        return "fail", f"{type(exc).__name__}: {exc}"
    log_call(**ctx, status="ok" if result.get("is_t4") else "failed", attempt=1,
             latency_s=result["seconds"], gpu_s=result["seconds"], error=result.get("error"))
    if result.get("is_t4"):
        return "pass", f"T4 confirmed in {result['seconds']}s ({result['kernel']})"
    gpu = (result.get("gpu") or "").strip().splitlines()[:12]
    return "fail", (f"status {result['status']}, not a T4. Select the T4 accelerator on the kernel page "
                    f"once and re-run. nvidia-smi: {gpu or result.get('error')}")


def check_ffmpeg():
    out = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True).stdout
    names = {line.split()[1] for line in out.splitlines() if len(line.split()) > 2 and line.startswith(" ")}
    missing = [f for f in REQUIRED_FILTERS if f not in names]
    if missing:
        return "fail", f"missing filters {missing}; install ffmpeg-full (brew install ffmpeg-full) or a static build"
    return "pass", "all required filters present"


CHECKS = {"gemini": check_gemini, "cloudflare": check_cloudflare, "kaggle": check_kaggle, "ffmpeg": check_ffmpeg}


def main(names):
    load_env()
    verdicts = {}
    for name in names or CHECKS:
        try:
            verdict, note = CHECKS[name]()
        except KeyError as exc:
            verdict, note = "fail", f"missing environment variable {exc}"
        verdicts[name] = verdict
        print(f"[{verdict.upper():8}] {name}: {note}")
    return 0 if all(v != "fail" for v in verdicts.values()) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
