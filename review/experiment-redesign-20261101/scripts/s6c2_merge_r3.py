# -*- coding: utf-8 -*-
"""S6c2 — R3 checkpoint 合并器：replication_bench_20261112/s4_checkpoint.jsonl → s4_traces_r3.json。

行级对账：每臂 n 应=76（72 gold + 4 OOD probe），qid 唯一；异常行原样保留并计入 warnings。
"""
import json
import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent
OUT = BASE.parent / "artifacts" / "replication_bench_20261112"


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ck = OUT / "s4_checkpoint.jsonl"
    rows = [json.loads(l) for l in ck.read_text(encoding="utf-8").splitlines() if l.strip()]
    traces, warn = {}, []
    for r in rows:
        arm, qid = r.get("arm"), r.get("qid")
        if not arm or not qid:
            warn.append(f"bad row: {str(r)[:80]}")
            continue
        traces.setdefault(arm, {})
        if qid in traces[arm]:
            # 同 (qid,arm) 重复 = 断点续跑重写行，保留最新
            warn.append(f"duplicate (qid,arm)={qid},{arm} — keeping latest")
        traces[arm][qid] = r
    merged = {arm: list(rows_.values()) for arm, rows_ in traces.items()}
    (OUT / "s4_traces_r3.json").write_text(json.dumps(merged, ensure_ascii=False, indent=1), encoding="utf-8")
    # stats-ready 版本：只含 gold 行数 = 72 的完整臂（部分臂会破坏 qid 配对检验）
    stats_ready = {arm: rlist for arm, rlist in merged.items()
                   if sum(1 for r in rlist if not r.get("is_refusal")) == 72}
    (OUT / "s4_traces_r3_statsready.json").write_text(
        json.dumps(stats_ready, ensure_ascii=False, indent=1), encoding="utf-8")
    summary = {arm: {"n": len(rows_), "qids_unique": len({r['qid'] for r in rows_.values()})} for arm, rows_ in traces.items()}
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    if warn:
        print("WARNINGS:")
        for w in warn[:10]:
            print(" -", w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
