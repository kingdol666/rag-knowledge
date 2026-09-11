#!/usr/bin/env python3
"""入库完成守护器 — 轮询 checkpoint 直到 13 库入库齐, 自动跑正式内容级基准套件.

条件: 每 KB checkpoint 行数 >= shard 行数(People 允许 +0, 全部 13 库).
完成后: 依次执行 run_content_all.sh 的内容(构建/双轮/比对/报告), 写日志到
results/content-suite.log, 终态写 results/content-suite.status (DONE/FAILED).

用法: python run_when_ingested.py   (长时间运行, 可 Ctrl-C)
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
SPLIT_DIR = SCRIPTS_DIR.parent / "data" / "benchmarks" / "kb_split"
RESULTS_DIR = SCRIPTS_DIR.parent / "results"
STATUS = RESULTS_DIR / "content-suite.status"
LOG = RESULTS_DIR / "content-suite.log"
POLL_S = 300


def progress() -> tuple[int, int, list[str]]:
    total_shard = total_done = 0
    incomplete = []
    for shard in sorted(SPLIT_DIR.glob("pages_KB-*.jsonl")):
        kb = shard.stem.replace("pages_", "")
        n_shard = sum(1 for _ in shard.open(encoding="utf-8"))
        ckpt = RESULTS_DIR / f"checkpoint-{kb}.jsonl"
        n_done = sum(1 for _ in ckpt.open(encoding="utf-8")) if ckpt.exists() else 0
        total_shard += n_shard
        total_done += min(n_shard, n_done)
        if n_done < n_shard:
            incomplete.append(f"{kb}:{n_done}/{n_shard}")
    return total_done, total_shard, incomplete


def main() -> int:
    STATUS.write_text("WAITING", encoding="utf-8")
    while True:
        done, total, incomplete = progress()
        msg = (f"{time.strftime('%H:%M:%S')} ingest {done}/{total} pages, "
               f"incomplete={incomplete}")
        print(msg, flush=True)
        with LOG.open("a", encoding="utf-8") as fh:
            fh.write(msg + "\n")
        if not incomplete:
            break
        time.sleep(POLL_S)

    STATUS.write_text("RUNNING", encoding="utf-8")
    print("ingest complete — starting content benchmark suite", flush=True)
    r = subprocess.run(["bash", str(SCRIPTS_DIR / "run_content_all.sh")],
                       capture_output=True, text=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(r.stdout[-8000:])
        fh.write(r.stderr[-4000:])
    ok = r.returncode == 0
    STATUS.write_text("DONE" if ok else "FAILED", encoding="utf-8")
    print("suite finished:", r.returncode, flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
