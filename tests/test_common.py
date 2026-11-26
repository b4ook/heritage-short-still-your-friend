import json

import pytest
import requests

from pipeline import common


@pytest.fixture(autouse=True)
def runs_file(tmp_path, monkeypatch):
    path = tmp_path / "runs.jsonl"
    monkeypatch.setattr(common, "RUNS", path)
    return path


def http_error(status, body="", headers=None):
    response = requests.Response()
    response.status_code = status
    response._content = body.encode()
    response.headers.update(headers or {})
    return requests.HTTPError(f"{status}", response=response)


class Flaky:
    def __init__(self, *errors, result="done"):
        self.errors = list(errors)
        self.result = result
        self.calls = 0

    def __call__(self):
        self.calls += 1
        if self.errors:
            raise self.errors.pop(0)
        return self.result


CTX = {"stage": "test", "shot_id": "s01", "ratio": "9x16"}


def test_cache_key_ignores_dict_order():
    assert common.cache_key({"a": 1, "b": {"x": 2, "y": 3}}) == common.cache_key({"b": {"y": 3, "x": 2}, "a": 1})
    assert common.cache_key({"a": 1}) != common.cache_key({"a": 2})


def test_write_atomic_leaves_no_tmp(tmp_path):
    path = common.write_atomic(tmp_path / "out" / "x.bin", b"data")
    assert path.read_bytes() == b"data"
    assert [p.name for p in path.parent.iterdir()] == ["x.bin"]


def test_wrap_subtitle_width():
    lines = common.wrap_subtitle("My grandmother walked to the market in Dessie every Saturday morning")
    assert all(len(line) <= 40 for line in lines)
    assert len(lines) == 2


def test_retry_503_then_success(runs_file):
    sleeps = []
    fn = Flaky(http_error(503))
    assert common.with_retry(fn, CTX, sleep=sleeps.append) == "done"
    assert fn.calls == 2 and sleeps == [2]
    line = json.loads(runs_file.read_text())
    assert (line["status"], line["shot_id"], line["attempt"]) == ("retry", "s01", 1)


def test_retry_honours_retry_after():
    sleeps = []
    common.with_retry(Flaky(http_error(429, "slow down", {"Retry-After": "5"})), CTX, sleep=sleeps.append)
    assert sleeps == [5.0]


def test_retry_timeout():
    sleeps = []
    assert common.with_retry(Flaky(requests.Timeout()), CTX, sleep=sleeps.append) == "done"
    assert sleeps == [2]


@pytest.mark.parametrize("error", [
    http_error(400, "bad request"),
    http_error(429, '{"quota_metric": "generate_requests_per_day"}'),
    http_error(429, "you have used your daily free allocation of neurons"),
])
def test_no_retry(error):
    fn = Flaky(error)
    with pytest.raises(requests.HTTPError):
        common.with_retry(fn, CTX, sleep=lambda s: None)
    assert fn.calls == 1


def test_gives_up_after_four_attempts():
    sleeps = []
    fn = Flaky(*[http_error(500)] * 5)
    with pytest.raises(requests.HTTPError):
        common.with_retry(fn, CTX, sleep=sleeps.append)
    assert fn.calls == 4 and sleeps == [2, 8, 30]


def test_genai_style_code_attribute():
    class APIError(Exception):
        code = 503

    assert common.with_retry(Flaky(APIError()), CTX, sleep=lambda s: None) == "done"


def test_log_call_rejects_unknown_fields():
    with pytest.raises(ValueError):
        common.log_call(stage="x", bogus=1)


def test_log_call_truncates_long_prompt(runs_file, monkeypatch):
    monkeypatch.delenv("RUN_ID", raising=False)
    line = common.log_call(stage="x", params={"prompt": "a" * 500})
    assert line["run_id"] == "adhoc"
    assert len(line["params"]["prompt"]) == common.PARAM_TEXT_LIMIT + 1


def test_retry_sdk_timeout_by_class_name():
    class ReadTimeout(Exception):
        pass

    assert common.with_retry(Flaky(ReadTimeout()), CTX, sleep=lambda s: None) == "done"


def test_no_retry_on_gemini_tts_daily_limit_message():
    body = "Rate limit exceeded for model gemini-3.8-flash-tts (limit: 10 requests per day on Free Tier)."
    fn = Flaky(http_error(429, body))
    with pytest.raises(requests.HTTPError):
        common.with_retry(fn, CTX, sleep=lambda s: None)
    assert fn.calls == 1
