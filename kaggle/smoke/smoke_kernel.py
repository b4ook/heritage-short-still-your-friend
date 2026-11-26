import subprocess
from pathlib import Path

out = Path("/kaggle/working/gpu.txt")
try:
    result = subprocess.run(["nvidia-smi"], capture_output=True, text=True, timeout=60)
    out.write_text(result.stdout + result.stderr)
except Exception as exc:
    out.write_text(f"nvidia-smi unavailable: {type(exc).__name__}: {exc}\n")
