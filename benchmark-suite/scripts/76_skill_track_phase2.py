#!/usr/bin/env python3
"""Track A — Phase 2 图书管理员兜底(BQ06/BQ10): 在所属门类库内用调整后的
查询定向检索定位证据 part, 再 kb_doc_read 续读. 全程计时, 追加到 evidence.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE / "scripts"))

from lib import McpClient  # noqa: E402

PHASE2 = {
    "BQ06": {"kb": "自然科学与地球科学",
             "refined": "precipitation efficiency moisture thermodynamic "
                        "contributions intensity extremes section",
             "read_query": "precipitation efficiency"},
    "BQ10": {"kb": "生命科学与医学",
             "refined": "optimal strategies tumor elimination control timing "
                        "dosage immune evasion resistance discussion",
             "read_query": "strategies tumor control"},
}


def read_head(mc, kb: str, doc_path: str, max_chars: int = 3000) -> str:
    r = mc.call("kb_doc_read", {"kb_id": kb, "doc_path": doc_path,
                                "max_chars": max_chars}, timeout=120)
    return (r or {}).get("content", "")


def main() -> int:
    ev_path = SUITE / "results" / "skill_track_evidence.json"
    ev = json.loads(ev_path.read_text(encoding="utf-8"))
    mc = McpClient()
    for rec in ev:
        p2 = PHASE2.get(rec["qid"])
        if not p2:
            continue
        rec["phase2"] = {"kb": p2["kb"], "timings": {}, "hits": []}
        t0 = time.perf_counter()
        r = mc.call("kb_search_vector",
                    {"query": p2["refined"], "kb_id": p2["kb"], "top_k": 5,
                     "score_threshold": 0.30}, timeout=300)
        rec["phase2"]["timings"]["targeted_search"] = round(
            time.perf_counter() - t0, 2)
        hits = r.get("results") or []
        best: dict[str, dict] = {}
        for it in hits:
            dp = str(it.get("doc_path", "")).replace("\\", "/")
            if dp and (dp not in best or it.get("score", 0) > best[dp]["score"]):
                best[dp] = it
        top = sorted(best.values(), key=lambda x: -x.get("score", 0))[:2]
        t0 = time.perf_counter()
        for d in top:
            dp = d["doc_path"]
            head = read_head(mc, p2["kb"], dp, max_chars=6000)
            rec["phase2"]["hits"].append(
                {"doc_path": dp, "vector_score": d.get("score"),
                 "head_excerpt": head[:1500], "head_chars": len(head)})
        rec["phase2"]["timings"]["continuation_reads"] = round(
            time.perf_counter() - t0, 2)
        print(f"[{rec['qid']}] phase2 search="
              f"{rec['phase2']['timings']['targeted_search']}s reads="
              f"{rec['phase2']['timings']['continuation_reads']}s "
              f"top1={top[0]['doc_path'][-46:] if top else 'NONE'}", flush=True)
    mc.close()
    ev_path.write_text(json.dumps(ev, ensure_ascii=False, indent=1),
                       encoding="utf-8")
    print("[done] phase2 appended")
    return 0


if __name__ == "__main__":
    sys.exit(main())
