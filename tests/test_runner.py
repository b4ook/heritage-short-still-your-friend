import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from pipeline import common, kaggle_runner


@pytest.fixture(autouse=True)
def runs_file(tmp_path, monkeypatch):
    monkeypatch.setattr(common, "RUNS", tmp_path / "runs.jsonl")


@pytest.fixture
def kernel_dir(tmp_path):
    d = tmp_path / "kernel"
    d.mkdir()
    (d / "k.py").write_text("print('x')\n# __JOBS__\nprint(JOBS)\n")
    (d / "kernel-metadata.template.json").write_text(json.dumps({"id": "<user>/heritage-test", "code_file": "k.py"}))
    return d


def test_full_cache_never_imports_kaggle(tmp_path, kernel_dir, monkeypatch):
    out = tmp_path / "out"
    out.mkdir()
    (out / "abc.wav").write_bytes(b"x")
    monkeypatch.delitem(sys.modules, "kaggle", raising=False)
    monkeypatch.setattr(kaggle_runner, "_api", lambda: pytest.fail("contacted Kaggle with a full cache"))
    statuses = kaggle_runner.run_stage(kernel_dir, [{"key": "abc"}], out, "wav", "test", 1, 1)
    assert statuses == {"abc": "cached"}
    assert "kaggle" not in sys.modules


def test_build_templates_jobs_once(tmp_path, kernel_dir):
    build = kaggle_runner.build(kernel_dir, "me", [{"key": "k1"}], 25)
    source = (build / "k.py").read_text()
    assert 'JOBS = [{"key": "k1"}]' in source and "TIME_BUDGET_MIN = 25" in source and "# __JOBS__" not in source
    assert json.loads((build / "kernel-metadata.json").read_text())["id"] == "me/heritage-test"
    (kernel_dir / "k.py").write_text("no marker\n")
    with pytest.raises(ValueError):
        kaggle_runner.build(kernel_dir, "me", [], 1)


def test_never_pushed_errors():
    assert kaggle_runner._never_pushed(ValueError("Permission 'kernels.get' was denied"))
    assert not kaggle_runner._never_pushed(ValueError("server exploded"))


class FakeApi:
    def __init__(self, files: dict[str, bytes], manifest: list[dict]):
        self.files, self.manifest = files, manifest

    def kernels_output(self, slug, path):
        for name, data in self.files.items():
            (Path(path) / name).write_bytes(data)
        (Path(path) / "manifest.jsonl").write_text("".join(json.dumps(m) + "\n" for m in self.manifest))


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
def test_collect_keeps_only_valid_ok_outputs(tmp_path):
    wav = tmp_path / "good.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=d=1", str(wav)], check=True)
    api = FakeApi({"good.wav": wav.read_bytes(), "empty.wav": b"", "bad.wav": b"junk"},
                  [{"key": "good", "status": "ok"}, {"key": "empty", "status": "ok"},
                   {"key": "bad", "status": "error", "error": "boom"}, {"key": "kernel", "status": "ok", "seconds": 9}])
    out = tmp_path / "out"
    statuses = kaggle_runner.collect(api, "me/x", out, "wav", "test")
    assert statuses == {"good": "ok", "empty": "failed", "bad": "failed"}
    assert sorted(p.name for p in out.iterdir()) == ["good.wav"]
