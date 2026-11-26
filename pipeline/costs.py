"""Summarise runs.jsonl per stage and model into the table between the markers in COSTS.md."""
import json
import re
import statistics
import sys
from collections import defaultdict

from pipeline.common import ROOT, RUNS

COSTS = ROOT / "COSTS.md"
START, END = "<!-- costs:start -->", "<!-- costs:end -->"
CALLS = {"ok", "retry", "failed"}


def summarise(lines: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for line in lines:
        if line.get("stage") in (None, "test"):
            continue
        groups[(line["stage"], line.get("model") or line.get("provider") or "?")].append(line)
    rows = []
    for (stage, model), items in sorted(groups.items()):
        kernel = [i for i in items if (i.get("params") or {}).get("kernel_total")]
        per_job = [i for i in items if i not in kernel]
        latencies = [i["latency_s"] for i in per_job if i.get("status") == "ok" and i.get("latency_s")]
        costs = [i["cost_usd_est"] for i in per_job if i.get("cost_usd_est") is not None]
        rows.append({
            "stage": stage, "model": model,
            "calls": sum(i.get("status") in CALLS for i in per_job),
            "ok": sum(i.get("status") == "ok" for i in per_job),
            "failed": sum(i.get("status") == "failed" for i in per_job),
            "cache_hits": sum(i.get("status") == "cache_hit" for i in per_job),
            "fallbacks": sum(i.get("status") == "fallback" for i in per_job),
            "mean_latency_s": round(statistics.mean(latencies), 1) if latencies else None,
            "gpu_min": round(sum(i.get("gpu_s") or 0 for i in kernel) / 60, 1) if kernel else None,
            "cost_usd": round(sum(costs), 4) if costs else None,
        })
    return rows


def table(rows: list[dict]) -> str:
    head = ("| Stage | Model | Calls | OK | Failed | Cache hits | Fallbacks | Mean latency (s) | GPU min | "
            "List-price USD |\n| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n")
    fmt = lambda v: "n/a" if v is None else str(v)  # noqa: E731
    return head + "".join(
        f"| {r['stage']} | `{r['model']}` | {r['calls']} | {r['ok']} | {r['failed']} | {r['cache_hits']} | "
        f"{r['fallbacks']} | {fmt(r['mean_latency_s'])} | {fmt(r['gpu_min'])} | {fmt(r['cost_usd'])} |\n"
        for r in rows)


def main():
    lines = [json.loads(l) for l in RUNS.read_text(encoding="utf-8").splitlines() if l.strip()]
    block = f"{START}\n{table(summarise(lines))}{END}"
    text = COSTS.read_text(encoding="utf-8")
    COSTS.write_text(re.sub(re.escape(START) + ".*?" + re.escape(END), lambda _: block, text, flags=re.S),
                     encoding="utf-8")
    print(f"COSTS.md updated from {len(lines)} log lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
