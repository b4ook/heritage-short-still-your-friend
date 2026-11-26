import base64
import os
import subprocess
from pathlib import Path

import requests

KLEIN = "@cf/black-forest-labs/flux-2-klein-4b"
SCHNELL = "@cf/black-forest-labs/flux-1-schnell"
MAX_INPUT_IMAGES = 4
INPUT_SIZE = 512
TIMEOUT_S = 120


def _url(model: str) -> str:
    return f"https://api.cloudflare.com/client/v4/accounts/{os.environ['CLOUDFLARE_ACCOUNT_ID']}/ai/run/{model}"


def _headers() -> dict:
    return {"Authorization": f"Bearer {os.environ['CLOUDFLARE_API_TOKEN']}"}


def ffmpeg_image(data: bytes, vf: str) -> bytes:
    """Re-encode image bytes as PNG through an FFmpeg filter chain."""
    result = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", "pipe:0", "-vf", vf, "-frames:v", "1",
         "-f", "image2pipe", "-c:v", "png", "pipe:1"],
        input=data, capture_output=True, check=True,
    )
    return result.stdout


def _decode(response: requests.Response) -> bytes:
    response.raise_for_status()
    if response.headers.get("content-type", "").startswith("image/"):
        return response.content
    body = response.json()
    image = (body.get("result") or {}).get("image") or body.get("image")
    if not image:
        raise ValueError(f"no image in Cloudflare response: {str(body)[:300]}")
    return base64.b64decode(image)


def cover_crop(width: int, height: int) -> str:
    return f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}"


def generate_image(model, prompt, seed, width, height, input_images: list[Path] = ()) -> bytes:
    """Return PNG bytes of size width×height."""
    if model == KLEIN:
        if len(input_images) > MAX_INPUT_IMAGES:
            raise ValueError(f"at most {MAX_INPUT_IMAGES} input images, got {len(input_images)}")
        files = {
            f"input_image_{i}": (f"ref{i}.png", ffmpeg_image(
                Path(p).read_bytes(),
                f"scale={INPUT_SIZE}:{INPUT_SIZE}:force_original_aspect_ratio=decrease"), "image/png")
            for i, p in enumerate(input_images)
        }
        fields = {"prompt": prompt, "width": str(width), "height": str(height), "seed": str(seed)}
        multipart = {k: (None, v) for k, v in fields.items()} | files
        raw = _decode(requests.post(_url(model), headers=_headers(), files=multipart, timeout=TIMEOUT_S))
    elif model == SCHNELL:
        payload = {"prompt": prompt, "steps": 8, "seed": seed}
        raw = _decode(requests.post(_url(model), headers=_headers(), json=payload, timeout=TIMEOUT_S))
    else:
        raise ValueError(f"unknown image model: {model}")
    return ffmpeg_image(raw, cover_crop(width, height))
