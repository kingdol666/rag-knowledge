# -*- coding: utf-8 -*-
"""终局 traces 合并：把串行跑各步产出的 s4_traces_<ts>.json 按 arm 合并为 s4_traces_final.json。

用法: python s6c_merge_traces.py <traces1.json> <traces2.json> [...]
规则：同臂取后传文件覆盖先传文件（调用方按时间升序传参）；显式传参，不做 glob 猜测。
"""
import json
import sys
from pathlib import Path

ART = Path(r"D:/codes/ClaudeGPT/rag_project/rag-knowledge/review/experiment-redesign-20261101/artifacts")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    merged = {}
    for p in sys.argv[1:]:
        data = json.loads(Path(p).read_text(encoding="utf-8"))
        for arm, rows in data.items():
            if rows:
                merged[arm] = rows
                print(f"  {arm:<12s} <- {Path(p).name} ({len(rows)} traces)")
    out = ART / "s4_traces_final.json"
    out.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"merged -> {out.name}")
    for arm, rows in merged.items():
        gold = sum(1 for x in rows if x.get("gold_hit"))
        print(f"  {arm}: n={len(rows)} gold={gold}")


if __name__ == "__main__":
    main()
