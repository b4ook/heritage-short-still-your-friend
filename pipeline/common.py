import hashlib
import json
import os
import re
import textwrap
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Homebrew's ffmpeg-full (with libass and freetype) is keg-only; prefer it when present
# so subtitles and drawtext work without relinking the system ffmpeg.
FFMPEG_FULL_BIN = Path("/opt/homebrew/opt/ffmpeg-full/bin")
if FFMPEG_FULL_BIN.is_dir() and str(FFMPEG_FULL_BIN) not in os.environ.get("PATH", "").split(os.pathsep):
    os.environ["PATH"] = f"{FFMPEG_FULL_BIN}{os.pathsep}{os.environ.get('PATH', '')}"
OUTPUTS = ROOT / "outputs"
RUNS = ROOT / "runs.jsonl"

BACKOFF_S = (2, 8, 30)
DAILY_LIMIT = re.compile(r"per[ _]?day|daily", re.IGNORECASE)
PARAM_TEXT_LIMIT = 200

# ponytail: usd stays None until a list price is sourced and dated in COSTS.md
PRICES = {
    "@cf/black-forest-labs/flux-2-klein-4b": {"unit": "image", "usd": None},
    "@cf/black-forest-labs/flux-1-schnell": {"unit": "image", "usd": None},
    "gemini-tts": {"unit": "audio_second", "usd": None},
    "kaggle-t4": {"unit": "t4_gpu_hour", "usd": None},
}


def load_env():
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")


def storyboard_path() -> Path:
    """STORYBOARD=storyboard_v2.json selects another version; the default is storyboard.json."""
    return ROOT / os.environ.get("STORYBOARD", "storyboard.json")


def load_storyboard(path=None) -> dict:
    return json.loads(Path(path or storyboard_path()).read_text(encoding="utf-8"))


def cache_key(job: dict) -> str:
    canonical = json.dumps(job, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def file_hash(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def output_path(stage: str, key: str, ext: str) -> Path:
    return OUTPUTS / stage / f"{key}.{ext}"


def write_atomic(path, data: bytes) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)
    return path


def wrap_subtitle(text: str) -> list[str]:
    return textwrap.wrap(text, width=40)


def cost_usd(model: str, units: float):
    price = PRICES.get(model, {}).get("usd")
    return None if price is None else round(price * units, 6)


def _truncate(params):
    if isinstance(params, dict):
        return {k: _truncate(v) for k, v in params.items()}
    if isinstance(params, list):
        return [_truncate(v) for v in params]
    if isinstance(params, str) and len(params) > PARAM_TEXT_LIMIT:
        return params[:PARAM_TEXT_LIMIT] + "…"
    return params


FIELDS = (
    "stage", "shot_id", "ratio", "provider", "model", "params", "seed", "cache_key",
    "status", "attempt", "latency_s", "gpu_s", "cost_usd_est", "output_path", "error",
)


def log_call(**fields):
    unknown = set(fields) - set(FIELDS)
    if unknown:
        raise ValueError(f"unknown log fields: {sorted(unknown)}")
    line = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "run_id": os.environ.get("RUN_ID") or "adhoc",
    }
    line.update({name: fields.get(name) for name in FIELDS})
    line["params"] = _truncate(line["params"])
    if line["output_path"] is not None:
        line["output_path"] = str(line["output_path"])
    with RUNS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")
    return line


def _status(exc):
    code = getattr(exc, "code", None)
    if isinstance(code, int):
        return code
    response = getattr(exc, "response", None)
    return getattr(response, "status_code", None)


def _body(exc) -> str:
    response = getattr(exc, "response", None)
    text = getattr(response, "text", None)
    return text if isinstance(text, str) else str(exc)


def _retry_after(exc):
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None) or {}
    value = headers.get("Retry-After") if hasattr(headers, "get") else None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_transient(exc) -> bool:
    import requests

    if isinstance(exc, (requests.Timeout, requests.ConnectionError, TimeoutError, ConnectionError)):
        return True
    # SDK transports (httpx, aiohttp) raise their own timeout classes; match by name rather than import them all.
    if any("Timeout" in cls.__name__ for cls in type(exc).__mro__):
        return True
    status = _status(exc)
    if status == 429:
        return not DAILY_LIMIT.search(_body(exc))
    return status is not None and 500 <= status < 600


def with_retry(fn, ctx: dict, sleep=time.sleep):
    attempts = len(BACKOFF_S) + 1
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as exc:
            if attempt == attempts or not _is_transient(exc):
                raise
            wait = _retry_after(exc) or BACKOFF_S[attempt - 1]
            log_call(**ctx, status="retry", attempt=attempt, error=f"{type(exc).__name__}: {exc}"[:500])
            sleep(wait)
