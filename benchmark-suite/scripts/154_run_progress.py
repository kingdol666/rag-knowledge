#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""运行进度速览（只读）：把某个 run 目录的 track_*.json 汇总成一张小表。

为什么需要：跑一轮 30 单元要 1-2 小时，用 PowerShell 现场解析 JSON 既啰嗦又容易
被回答里的 emoji/弯引号打断（ConvertFrom-Json 报 Invalid object passed in）。
这里用 Python json 解析，输出固定宽度的小表，稳定可读。

用法:
    python scripts/154_run_progress.py                 # 最新 run
    python scripts/154_run_progress.py --run <name|path>
    python scripts/154_run_progress.py --tail 400      # 表尾附最近一格的回答摘要
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
RUNS = SUITE / "results" / "runs"

SENTINELS = ("KB_TOOLS_NOT_READY", "KB_NO_RETRIEVAL")


def latest_run() -> Path | None:
    cands = [d for d in RUNS.glob("run-*") if d.is_dir()]
    return max(cands, key=lambda d: (d.stat().st_mtime, d.name)) if cands else None


def load(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="")
    ap.add_argument("--tail", type=int, default=0, help="打印最后一格的回答前 N 字")
    a = ap.parse_args()

    run = Path(a.run) if a.run and Path(a.run).is_dir() else (
        (RUNS / a.run) if a.run else latest_run())
    if run is None or not run.is_dir():
        print("no run dir")
        return 1

    cells = sorted(run.glob("track_*.json"))
    print(f"[run] {run.name} · {len(cells)} cells")
    print(f"{'cell':<18}{'lat_s':>8}{'tools':>7}{'turns':>7}{'cost$':>10}  flag")
    tot = {"lat": 0.0, "cost": 0.0}
    for f in cells:
        d = load(f)
        ans = str(d.get("answer") or "")
        flag = ""
        if any(s in ans for s in SENTINELS):
            flag = "SENTINEL"
        elif d.get("is_error"):
            flag = "ERROR"
        elif not ans.strip():
            flag = "EMPTY"
        elif (d.get("tool_call_count") or 0) == 0:
            flag = "ZERO_TOOLS"
        lat = float(d.get("latency_s") or 0.0)
        cost = float(d.get("total_cost_usd") or 0.0)
        tot["lat"] += lat
        tot["cost"] += cost
        print(f"{f.stem.replace('track_', ''):<18}{lat:>8.1f}"
              f"{d.get('tool_call_count', 0):>7}{d.get('num_turns', 0):>7}"
              f"{cost:>10.3f}  {flag}")
    if cells:
        print(f"{'TOTAL/AVG':<18}{tot['lat'] / len(cells):>8.1f}"
              f"{'':>14}{tot['cost']:>10.3f}  ({len(cells)} cells, "
              f"${tot['cost']:.2f})")

    if a.tail and cells:
        last = load(cells[-1])
        ans = str(last.get("answer") or "")
        print(f"\n[tail] {cells[-1].name} ({len(ans)} chars)\n{ans[:a.tail]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
