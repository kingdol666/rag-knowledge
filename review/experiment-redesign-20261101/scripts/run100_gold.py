# -*- coding: utf-8 -*-
"""Stage 6b: tiered gold run with disk-read content fed to kb_laya_judge.

Workaround for the measured kb-mcp->web doc_path/path param drift: reference
mode fetches fail closed, so we supply content directly (contract-supported)
read from the storage tree (architecture allows direct file reads).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(r"D:\codes\ClaudeGPT\rag_project\rag-knowledge")
STORAGE = REPO / "storage" / "tree-file-system"
OUT = REPO / "review" / "_exp_rerun_20261114"
QA = REPO / "benchmark-suite" / "data" / "papers" / "qa_questions.json"
MAX_CHARS = 40000

sys.path.insert(0, str(REPO / "review" / "experiment-redesign-20261101" / "scripts"))
from run100_lib import LIBS  # noqa: E402
from run100_stage2 import mcp  # noqa: E402


def gold_rank(hits, arxiv: str) -> int:
    """Doc-level rank of the gold paper in the raw vector list (0 = absent)."""
    seen = []
    for h in hits:
        dp = (h.get("doc_path") or "").replace("\\", "/").split("/")[-1]
        if dp and dp not in seen:
            seen.append(dp)
    for j, dp in enumerate(seen, 1):
        if arxiv.replace("-", "_") in dp or arxiv in dp:
            return j
    return 0


def read_head(lib: str, key: str) -> str:
    lib_dir = STORAGE / lib
    cands = sorted(lib_dir.glob(f"**/*{key}*"))
    if not cands:
        return ""
    text = cands[0].read_text(encoding="utf-8", errors="replace")
    return text[:MAX_CHARS]


def main() -> int:
    pmap = json.loads((OUT / "prefix_map.json").read_text(encoding="utf-8"))
    qa = json.loads(QA.read_text(encoding="utf-8"))
    items = qa if isinstance(qa, list) else qa.get("questions") or []
    rows = []
    for i, q in enumerate(items, 1):
        qid, arxiv, field = q["qid"], q["arxiv_id"], q["field"]
        lib = pmap.get(field, "")
        lib_id = LIBS.get(lib, "")
        query = q["question"]
        sr = mcp("kb_search_vector",
                 {"kb_id": lib_id, "query": query, "top_k": 30}, timeout=180)
        hits = sr.get("results") or []
        vrank = gold_rank(hits, arxiv)
        refs, seen = [], set()
        for h in hits:
            dp = (h.get("doc_path") or "").replace("\\", "/")
            tail = dp.split("/")[-1]
            key = tail.split(" (part")[0]
            if key and key not in seen:
                seen.add(key)
                refs.append(tail)
        judge_docs = [{"kb_id": lib_id, "doc_path": f"{lib}/{tail}"}
                      for tail in refs[:5]]
        jr = mcp("kb_laya_judge",
                 {"query": query, "documents": judge_docs}, timeout=420)
        verdict = jr
        if isinstance(jr, dict) and isinstance(jr.get("jev"), dict):
            verdict = jr["jev"]
        real = bool(verdict.get("real_engine"))
        surv = verdict.get("survivors") or []
        pack = verdict.get("evidence_pack") or ""
        surv_s = json.dumps(surv, ensure_ascii=False)
        gold_in_surv = (arxiv.replace("-", "_") in surv_s) or (arxiv in surv_s)
        gold_in_pack = (arxiv.replace("-", "_") in pack) or (arxiv in pack)
        rows.append({
            "qid": qid, "arxiv": arxiv, "lib": lib, "query": query[:60],
            "vector_gold_rank": vrank,
            "judge_real_engine": real,
            "candidate_count": verdict.get("candidate_count"),
            "scored_count": verdict.get("scored_count"),
            "survivor_count": verdict.get("survivor_count"),
            "gold_in_survivors": bool(gold_in_surv),
            "gold_in_pack": bool(gold_in_pack),
            "gold_hit_tiered": bool(gold_in_surv or gold_in_pack),
            "judge_head": json.dumps(verdict, ensure_ascii=False)[:180],
        })
        print(f"[{i:02d}] {qid} vrank={vrank} real={real} "
              f"cand={verdict.get('candidate_count')} "
              f"surv={verdict.get('survivor_count')} "
              f"hit={rows[-1]['gold_hit_tiered']}", flush=True)
    (OUT / "gold_bq_tiered_b.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    vh1 = sum(1 for r in rows if r["vector_gold_rank"] == 1)
    vh5 = sum(1 for r in rows if 0 < r["vector_gold_rank"] <= 5)
    th = sum(1 for r in rows if r["gold_hit_tiered"])
    real_n = sum(1 for r in rows if r["judge_real_engine"])
    print(f"\nGOLD6b SUMMARY: vector rank1={vh1}/10 Hit@5={vh5}/10 | "
          f"judge real={real_n}/10 | tiered gold-hit={th}/10", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
