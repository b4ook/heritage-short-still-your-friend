"""Dialogue stage: one TTS call per spoken line, in the speaker's voice."""
import sys
import time

from pipeline import tts
from pipeline.common import cache_key, cost_usd, load_env, load_storyboard, log_call, output_path, with_retry, write_atomic

STAGE = "narration"


def line_job(sb: dict, line: dict) -> dict:
    speaker = next(c for c in sb["characters"] if c["id"] == line["speaker"])
    style = ", ".join(s for s in (speaker["voice_style"], line["style"]) if s)
    return {
        "stage": STAGE,
        "model": line["tts_model"] or sb["tts_model"],
        "payload": {"text": line["text"], "voice": speaker["voice"], "style": style, "language": sb["language"]},
        "inputs": {},
        "code": None,
    }


def line_file(sb: dict, line: dict):
    return output_path(STAGE, cache_key(line_job(sb, line)), "wav")


def durations(sb: dict, missing_s: float | None = None) -> dict[str, list[float]]:
    """Seconds per spoken line, per shot id. A missing line is an error unless missing_s is given (drafts)."""
    result = {}
    for shot in sb["shots"]:
        seconds = []
        for line in shot["lines"]:
            path = line_file(sb, line)
            if path.exists():
                seconds.append(tts.wav_seconds(path))
            elif missing_s is not None:
                seconds.append(missing_s)
            else:
                raise FileNotFoundError(f"{shot['id']} line {line['text'][:30]!r} missing at {path}; run narration")
        result[shot["id"]] = seconds
    return result


def run(sb: dict) -> None:
    client = None
    for shot in sb["shots"]:
        for i, line in enumerate(shot["lines"]):
            job = line_job(sb, line)
            key = cache_key(job)
            path = output_path(STAGE, key, "wav")
            base = {"stage": STAGE, "shot_id": f"{shot['id']}.{i}", "provider": "gemini", "model": job["model"],
                    "params": job["payload"], "cache_key": key}
            if path.exists():
                log_call(**base, status="cache_hit", output_path=path)
                continue
            if client is None:
                client = tts.client()
            p = job["payload"]
            start = time.monotonic()
            try:
                wav = with_retry(lambda: tts.synthesize(client, job["model"], p["text"], p["voice"], p["style"]), base)
            except Exception as exc:
                log_call(**base, status="failed", attempt=1, error=f"{type(exc).__name__}: {exc}"[:500])
                raise
            write_atomic(path, wav)
            seconds = tts.wav_seconds(path)
            log_call(**base, status="ok", attempt=1, latency_s=round(time.monotonic() - start, 2),
                     cost_usd_est=cost_usd("gemini-tts", seconds), output_path=path)
            print(f"{shot['id']}.{i} {line['speaker']}: {seconds:.1f}s")


def main():
    load_env()
    run(load_storyboard())
    return 0


if __name__ == "__main__":
    sys.exit(main())
