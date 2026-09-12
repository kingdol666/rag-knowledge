#!/usr/bin/env python3
"""等待阵发索引器静默: backend.log 中 'Indexed' 最近一条超过阈值秒数即 READY.

用法: python wait_ingest_quiet.py [quiet_s=180] [max_wait_s=2400]
退出码 0=READY, 1=超时仍嘈杂. 每分钟打印一次状态.
"""
from __future__ import annotations

import re
import sys
import time
from datetime import datetime
from pathlib import Path

LOG = Path(__file__).resolve().parents[3] / "backend" / "logs" / "backend.log"
TS_RE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")


def last_indexed_age_s() -> float:
    try:
        lines = LOG.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return 1e9
    for line in reversed(lines):
        if "Indexed" in line or "batch-index" in line.lower():
            m = TS_RE.match(line)
            if m:
                t = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
                return max(0.0, (datetime.now() - t).total_seconds())
    return 1e9


def main() -> int:
    quiet_s = float(sys.argv[1]) if len(sys.argv) > 1 else 180
    max_wait = float(sys.argv[2]) if len(sys.argv) > 2 else 2400
    t0 = time.time()
    while time.time() - t0 < max_wait:
        age = last_indexed_age_s()
        if age >= quiet_s:
            print(f"READY (quiet {age:.0f}s)", flush=True)
            return 0
        print(f"busy: last index {age:.0f}s ago, waiting...", flush=True)
        time.sleep(60)
    print("TIMEOUT still busy", flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())
