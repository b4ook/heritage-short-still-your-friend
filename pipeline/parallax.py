"""Depth parallax: a 2.5D camera move over one keyframe.

A small depth model (Depth Anything V2) estimates how near each pixel is. Each output
frame maps back into the keyframe with float coordinates (no integer stepping), so near
things grow and slide a little more than far things as the camera eases through its move.
"""
import subprocess
import time
from pathlib import Path

from pipeline.common import ROOT, cache_key, file_hash, log_call, output_path

STAGE = "depth"
DEPTH_MODEL = "depth-anything/Depth-Anything-V2-Small-hf"
DOLLY = 0.07       # near layers scale this much more than far ones over a push-in
LATERAL = 0.022    # near layers slide this fraction of the frame width more than far ones on a pan
PAN_USE = 0.7      # share of the zoom margin a pan travels, leaving room for the parallax
_estimator = None


def depth_file(still: Path) -> Path:
    """16-bit depth map for a keyframe (brighter is nearer), cached by the keyframe's hash."""
    job = {"stage": STAGE, "model": DEPTH_MODEL, "payload": {}, "inputs": {"keyframe": file_hash(still)}, "code": None}
    key = cache_key(job)
    path = output_path(STAGE, key, "png")
    if path.exists():
        return path
    global _estimator
    import cv2
    import numpy as np
    from PIL import Image

    start = time.monotonic()
    if _estimator is None:
        import torch
        from transformers import pipeline

        device = "mps" if torch.backends.mps.is_available() else "cpu"
        _estimator = pipeline("depth-estimation", model=DEPTH_MODEL, device=device)
    result = _estimator(Image.open(still).convert("RGB"))
    depth = np.asarray(result["predicted_depth"].squeeze().float().cpu().numpy(), dtype=np.float32)
    lo, hi = np.percentile(depth, [1, 99])
    depth = np.clip((depth - lo) / max(hi - lo, 1e-6), 0, 1)
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), (depth * 65535).astype(np.uint16))
    log_call(stage=STAGE, provider="local", model=DEPTH_MODEL, cache_key=key, status="ok", attempt=1,
             latency_s=round(time.monotonic() - start, 2), output_path=path)
    return path


def ease(p: float) -> float:
    """Mostly smoothstep, with a little linear so the camera never fully stops at a cut."""
    smooth = p * p * (3 - 2 * p)
    return 0.75 * smooth + 0.25 * p


def render(still: Path, kb: dict, length: float, w: int, h: int, fps: int, out: Path) -> None:
    import cv2
    import numpy as np

    img = cv2.imread(str(still), cv2.IMREAD_COLOR)
    sh, sw = img.shape[:2]
    depth = cv2.imread(str(depth_file(still)), cv2.IMREAD_UNCHANGED).astype(np.float32) / 65535
    depth = cv2.resize(depth, (sw, sh), interpolation=cv2.INTER_LINEAR)
    depth = cv2.GaussianBlur(depth, (0, 0), sigmaX=sw * 0.012)  # soft edges: no tearing at outlines

    c = max(w / sw, h / sh)                   # cover scale, source -> output pixels
    u, v = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    X, Y = (u - w / 2) / c, (v - h / 2) / c   # output grid in centred source pixels
    zf, zt, pan = kb["zoom_from"], kb["zoom_to"], kb["pan"]
    D = cv2.remap(depth, sw / 2 + X / zf, sh / 2 + Y / zf, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    D -= float(np.median(D))
    push = 1.0 if zt >= zf else -1.0
    dx, dy = {"none": (0, 0), "right": (1, 0), "left": (-1, 0), "down": (0, 1), "up": (0, -1)}[pan]

    frames = max(round(fps * length), 2)
    out.parent.mkdir(parents=True, exist_ok=True)
    enc = subprocess.Popen(
        ["ffmpeg", "-hide_banner", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}",
         "-r", str(fps), "-i", "-", "-vf", "noise=alls=4:allf=t", "-c:v", "libx264", "-crf", "17",
         "-preset", "medium", "-pix_fmt", "yuv420p", str(Path(out).resolve().relative_to(ROOT))],
        cwd=ROOT, stdin=subprocess.PIPE)
    try:
        for f in range(frames):
            s = ease(f / (frames - 1))
            m = s - 0.5
            z = zf + (zt - zf) * s
            zpx = z * (1 + DOLLY * push * m * D)
            margin_x = max(sw / 2 - (w / c) / (2 * z), 0) * PAN_USE
            margin_y = max(sh / 2 - (h / c) / (2 * z), 0) * PAN_USE
            ox = dx * margin_x * 2 * m + dx * LATERAL * sw * m * D
            oy = dy * margin_y * 2 * m + dy * LATERAL * sh * m * D
            mx = sw / 2 + X / zpx + ox
            my = sh / 2 + Y / zpx + oy
            frame = cv2.remap(img, mx, my, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
            enc.stdin.write(frame.tobytes())
    finally:
        enc.stdin.close()
        if enc.wait() != 0:
            raise RuntimeError(f"ffmpeg failed encoding {out}")
