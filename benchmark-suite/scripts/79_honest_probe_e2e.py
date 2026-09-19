#!/usr/bin/env python3
"""WRITING-PLAN v2.0 步骤②/②′ 产证:
(a) honest-failure probe: 3 个语料外问题实跑 QDCVR 协议 Phase1(向量+门控读取)
    + Phase2(图书管理员=逐库摘要核查), 全程计时, 证据落盘供执行者判定;
(b) Track A e2e spot: 4 道库内题(BQ02/BQ04/BQ08/BQ10) 同一 scripted 段计时,
    回答段由执行者(agent)撰写并另录时间戳(补入 artifacts 的 judge 字段);
产出 results/probe_evidence_raw.json (证据) — 判定与回答由执行者工件追加。
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE / "scripts"))
from lib import McpClient  # noqa: E402

KBS = ["计算机与人工智能", "自然科学与地球科学", "生命科学与医学",
       "工程与能源", "经济与社会"]

OOC = [
    {"pid": "P1", "question": "How does the Herbert-Moulton collider benchmark quantify detector drift in particle physics experiments?",
     "why_ooc": "benchmark does not exist; corpus has no particle-physics detector paper"},
    {"pid": "P2", "question": "What did the paper 'Spectral Tuning for Low-Resource Odor Recognition' (NAACL 2023) report about training epochs?",
     "why_ooc": "fabricated citation; no such paper in the corpus"},
    {"pid": "P3", "question": "What is the recommended daily dosage of metformin for diabetic cats?",
     "why_ooc": "domain-mismatched veterinary question; clinical KB covers LLM clinical knowledge only"},
]

SPOT = ["BQ02", "BQ04", "BQ08", "BQ10"]


def search_all(mc, query: str, top_k: int = 10):
    t0 = time.perf_counter()
    results = []
    for kb in KBS:
        r = mc.call("kb_search_vector", {"query": query, "kb_id": kb,
                                        "top_k": top_k, "score_threshold": 0.35},
                    timeout=300)
        for it in (r.get("results") or []):
            it = dict(it)
            it["kb_selected"] = kb
            results.append(it)
    secs = round(time.perf_counter() - t0, 2)
    best: dict[str, dict] = {}
    for it in results:
        dp = str(it.get("doc_path", "")).replace("\\", "/")
        if dp and (dp not in best or it.get("score", 0) > best[dp]["score"]):
            best[dp] = it
    top = sorted(best.values(), key=lambda x: -x.get("score", 0))[:3]
    return top, secs


def read_head(mc, kb: str, dp: str, max_chars: int = 3000):
    t0 = time.perf_counter()
    r = mc.call("kb_doc_read", {"kb_id": kb, "doc_path": dp,
                                "max_chars": max_chars}, timeout=120)
    return (r or {}).get("content", ""), round(time.perf_counter() - t0, 2)


def librarian(mc):
    """Phase 2: 逐库清单+文档名核查(书架扫描), 供执行者判断是否存在相关文档."""
    t0 = time.perf_counter()
    shelf = []
    for kb in KBS:
        docs = mc.call("kb_get_documents", {"kb_id": kb}, timeout=180) or {}
        names = [d.get("name") or d.get("doc_path", "") for d in
                 (docs.get("documents") or [])]
        shelf.append({"kb": kb, "n_docs": len(names),
                      "names": [n[:90] for n in names[:60]]})
    return shelf, round(time.perf_counter() - t0, 2)


def probe(mc, rec: dict) -> dict:
    rec = dict(rec)
    rec["phase1_query"] = rec["question"]  # Phase 0: 疑问已具体化, 无需改写
    top, vec_s = search_all(mc, rec["phase1_query"])
    rec["timings"] = {"phase1_vector_search": vec_s}
    rec["hits"] = []
    read_s = 0.0
    for d in top:
        head, s = read_head(mc, d["doc_path"].split("/")[0], d["doc_path"])
        read_s += s
        rec["hits"].append({"doc_path": d["doc_path"],
                            "vector_score": d.get("score"),
                            "chunk_text": (d.get("content") or "")[:600],
                            "head_excerpt": head[:900]})
    rec["timings"]["phase1_doc_reads"] = round(read_s, 2)
    shelf, lib_s = librarian(mc)
    rec["phase2_librarian"] = {"seconds": lib_s, "shelf": shelf}
    print(f"[{rec.get('pid') or rec.get('qid')}] vec={vec_s}s reads={read_s}s "
          f"lib={lib_s}s top1={top[0]['doc_path'][:50] if top else 'NONE'} "
          f"vscore={top[0].get('score') if top else 0}", flush=True)
    return rec


def main() -> int:
    mc = McpClient()
    qs = {q["qid"]: q for q in json.loads(
        (SUITE / "data" / "papers" / "qa_questions.json")
        .read_text(encoding="utf-8"))["questions"]}
    out = {"ooc_probes": [probe(mc, r) for r in OOC],
           "track_a_e2e_spot": [probe(mc, {"qid": k, "question": qs[k]["question"],
                                           "field": qs[k]["field"],
                                           "paper": qs[k]["paper"]})
                                for k in SPOT]}
    mc.close()
    (SUITE / "results" / "probe_evidence_raw.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("[done] probe_evidence_raw.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
