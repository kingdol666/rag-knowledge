#!/usr/bin/env python3
"""入库完成判定: 13 库 checkpoint 页数 >= shard 页数则输出 YES, 否则 NO."""
from __future__ import annotations

from pathlib import Path

SPLIT = Path(__file__).resolve().parent.parent / "data" / "benchmarks" / "kb_split"
RESULTS = Path(__file__).resolve().parent.parent / "results"


def main() -> None:
    for shard in sorted(SPLIT.glob("pages_KB-*.jsonl")):
        kb = shard.stem.replace("pages_", "")
        with shard.open(encoding="utf-8") as fh:
            n_shard = sum(1 for _ in fh)
        ckpt = RESULTS / f"checkpoint-{kb}.jsonl"
        if ckpt.exists():
            with ckpt.open(encoding="utf-8") as fh:
                n_done = sum(1 for _ in fh)
        else:
            n_done = 0
        if n_done < n_shard:
            print("NO")
            return
    print("YES")


if __name__ == "__main__":
    main()
