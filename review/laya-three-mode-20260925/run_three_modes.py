#!/usr/bin/env python3
"""Three-mode retrieval comparison on the live knowledge base.

Modes:
  A  vector+content gate   — kb_search_vector -> doc-level dedup -> kb_doc_read
  B  complete-recall       — kb_list -> all doc descriptions -> read+segment -> Laya judge
  C  parallel hybrid       — A's vector branch ∥ B's catalog branch (threads,
                             separate MCP connections) -> merge/dedup -> reread -> Laya

Every mode runs the real local Laya model as the segment judge. Transcripts
are written as JSON per (mode, question). Read-only: no KB mutations.
"""
from __future__ import annotations

import json
import re
import sys
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "benchmark-suite" / "scripts"))
sys.path.insert(0, str(REPO / ".claude" / "skills" / "knowledgebase-librarian" / "scripts"))
sys.path.insert(0, str(REPO / ".claude" / "skills" / "knowledgebase-hybrid" / "scripts"))

from lib import McpClient  # noqa: E402
import complete_recall as cr  # noqa: E402
import jev_filter as jf  # noqa: E402
import hybrid_search as hs  # noqa: E402

OUT_DIR = REPO / "review" / "laya-three-mode-20260925"
VECTOR_THRESHOLD = 0.35
VECTOR_TOP_K = 10
DOC_BUDGET = 30          # per-shelf read budget for lanes B/C (test budget)
MAX_STATE_CHARS = 6000   # shorter segments for CPU test throughput

QUESTIONS = [
    {"id": "q1", "query": "How does InstructDS generate high-quality query-based dialogue summaries?"},
    {"id": "q2", "query": "What datasets does MultiMedQA evaluate and how does Flan-PaLM perform on MedQA?"},
    {"id": "q3", "query": "How should farmers allocate trap cropping investments to maximize yield?"},
]


def norm(path: str) -> str:
    return str(path or "").replace("\\", "/")


def doc_key(kb_id: str, path: str) -> tuple[str, str]:
    return (str(kb_id or ""), norm(path))


# ─────────────────────────── shared helpers ───────────────────────────

def segment(text: str, limit: int = 2400):
    """Simple structure-aware segmentation for judge throughput."""
    blocks = [b for b in re.split(r"\n\s*\n", text) if b.strip()]
    segments, current, size = [], [], 0
    for block in blocks:
        if size + len(block) > limit and current:
            segments.append("\n\n".join(current))
            current, size = [], 0
        current.append(block)
        size += len(block)
    if current:
        segments.append("\n\n".join(current))
    return segments or ([text] if text.strip() else [])


def judge(query: str, docs: list[dict], threshold: float = 0.5,
          relative_margin: float = 0.10, top_k_floor: int = 0) -> dict:
    """Run real Laya over doc segments; keep per-doc best score.

    Retention now delegates to complete_recall.retain_docs (shared with the
    hybrid skill): relative cut against Laya's top-heavy distribution plus a
    global top-K floor that protects question-critical mid-score documents.
    Segments may be plain strings (mode A) or segment records with a "text"
    field (catalog_lane's structure-aware segments).
    """
    flat, owner = [], []
    for di, doc in enumerate(docs):
        for seg in doc["segments"]:
            text = seg.get("text") if isinstance(seg, dict) else seg
            flat.append(str(text)[:MAX_STATE_CHARS])
            owner.append(di)
    if not flat:
        return {"kept_docs": [], "abs_kept": [], "doc_scores": [], "status": "no_segments",
                "engine": "laya"}
    verdict = jf.filter_candidates({"engine": "laya", "query": query, "threshold": threshold,
                                    "candidates": [{"candidate_id": f"s{i:04d}", "text": t}
                                                   for i, t in enumerate(flat)]})
    best: dict[int, dict] = {}
    for rec in verdict["scores"]:
        di = owner[int(rec["candidate_id"][1:])]
        score = rec.get("score")
        if score is not None and (di not in best or score > best[di]["score"]):
            best[di] = rec
    retention = cr.retain_docs(best, threshold=threshold, relative_margin=relative_margin,
                               top_k_floor=top_k_floor)
    kept_docs = list(retention["kept_keys"])
    return {"kept_docs": kept_docs, "abs_kept": list(retention["abs_kept_keys"]),
            "relative_cut": retention["relative_cut"], "global_best": retention["global_best"],
            "floor_applied": retention["floor_applied"],
            "doc_scores": [{"doc": docs[di]["doc_path"], "kb_id": docs[di]["kb_id"],
                            "score": best[di]["score"], "kept": di in set(kept_docs)}
                           for di in sorted(best)],
            "status": verdict["status"], "engine": verdict["engine"],
            "backend": verdict["backend"], "real_engine": verdict["real_engine"],
            "scored_segments": verdict["scored_count"], "total_segments": len(flat)}


def read_doc(mc: McpClient, kb_id: str, doc: dict, max_chars: int = 20000) -> dict:
    r = mc.call("kb_doc_read", {"kb_id": kb_id, "doc_path": doc["doc_path"], "max_chars": max_chars},
                timeout=180)
    return {"kb_id": kb_id, "doc_id": doc.get("doc_id"), "doc_path": doc["doc_path"],
            "name": doc.get("name"), "description": doc.get("description"),
            "content": str(r.get("content") or ""), "truncated": bool(r.get("truncated")),
            "totalLines": r.get("totalLines")}


# ─────────────────────────── Mode A: vector gate ───────────────────────────

def mode_a(query: str, trace: dict, *, top_k_floor: int = 0) -> dict:
    t0 = time.time()
    mc = McpClient()
    try:
        raw = mc.call("kb_search_vector", {"query": query, "kb_id": "", "top_k": VECTOR_TOP_K,
                                            "score_threshold": VECTOR_THRESHOLD, "balance_kbs": True},
                      timeout=300)
    finally:
        mc.close()
    hits = raw.get("results") or []
    trace["vector_raw_hits"] = [{"doc_path": h.get("doc_path"), "kb_id": h.get("kb_id"),
                                 "score": h.get("score"), "chunk_index": h.get("chunk_index")}
                                for h in hits]
    # hard threshold + doc-level dedup keeping best chunk
    best: dict[tuple, dict] = {}
    for h in hits:
        if float(h.get("score") or 0) < VECTOR_THRESHOLD:
            continue
        key = doc_key(h.get("kb_id"), h.get("doc_path"))
        if key not in best or float(h["score"]) > float(best[key]["score"]):
            best[key] = h
    trace["vector_dedup_docs"] = len(best)
    # read top docs
    docs = []
    mc = McpClient()
    try:
        for key, h in sorted(best.items(), key=lambda kv: -float(kv[1]["score"]))[:5]:
            kb_id, path = key
            docs.append(read_doc(mc, kb_id, {"doc_path": path, "doc_id": None,
                                              "name": Path(path).name, "description": None}))
    finally:
        mc.close()
    for d in docs:
        d["segments"] = segment(d["content"])
    trace["docs_read"] = [{"doc_path": d["doc_path"], "chars": len(d["content"]),
                           "truncated": d["truncated"]} for d in docs]
    verdict = judge(query, docs, top_k_floor=top_k_floor)
    trace["judge"] = {k: v for k, v in verdict.items() if k != "kept_docs"}
    trace["kept_doc_paths"] = [docs[i]["doc_path"] for i in verdict["kept_docs"]]
    trace["seconds"] = round(time.time() - t0, 1)
    # evidence pack from kept docs
    pack = "\n\n".join(f"[{docs[i]['doc_path']}]\n{docs[i]['content'][:2500]}"
                       for i in verdict["kept_docs"])[:12000]
    return {"evidence_pack": pack, "kept": trace["kept_doc_paths"], "verdict": verdict}


# ────────────────────── Mode B: complete-recall lane ──────────────────────

B_EXCLUDES = ("Corpus", "soul-", "e2e-", "Novel-")


def mode_b(query: str, trace: dict, *, extra_terms: tuple = (), top_k_floor: int = 0,
           peek_heads: bool = False, peek_chars: int = 700, peek_limit: int = 300,
           doc_budget: int = DOC_BUDGET, stem_expansion: bool = True,
           stem_max_parts: int = 6) -> dict:
    """Librarian catalog lane via the shared hybrid_search.catalog_lane + the
    post-judge stem expansion (kept split docs bring their sibling parts)."""
    t0 = time.time()
    catalog_index: dict = {}
    docs = hs.catalog_lane(query, mcp_factory=McpClient, doc_budget=doc_budget,
                           exclude_prefixes=B_EXCLUDES, segment_chars=2400,
                           read_max_chars=20000, trace=trace, extra_terms=extra_terms,
                           peek_heads=peek_heads, peek_chars=peek_chars, peek_limit=peek_limit,
                           catalog_index=catalog_index)
    docs, verdict = hs.judge_with_expansion(
        query, docs, catalog_index, engine="laya", threshold=0.5, relative_margin=0.10,
        top_k_floor=top_k_floor, stem_expansion=stem_expansion, stem_max_parts=stem_max_parts,
        read_max_chars=20000, segment_chars=2400, mcp_factory=McpClient, trace=trace,
        agreed_paths={(str(k), hs.norm_path(p)) for k, p in
                      (trace.get("description_overlap_paths") or [])})
    trace["judge"] = {k: v for k, v in verdict.items() if k != "kept_doc_indices"}
    trace["kept_doc_paths"] = [docs[i]["doc_path"] for i in verdict["kept_doc_indices"]]
    trace["seconds"] = round(time.time() - t0, 1)
    pack = hs.build_evidence_pack(docs, verdict, head_chars=2500, max_chars=12000)
    return {"evidence_pack": pack, "kept": trace["kept_doc_paths"], "verdict": verdict}


# ────────────────────── Mode C: parallel hybrid ──────────────────────

def mode_c(query: str, trace: dict) -> dict:
    t0 = time.time()
    vec_trace: dict = {}
    cat_trace: dict = {}
    vec_result: dict = {}

    def vector_branch():
        try:
            vec_result.update(mode_a_light(query, vec_trace))
        except Exception as exc:  # noqa: BLE001
            vec_trace["error"] = str(exc)[:200]

    def catalog_branch_thread():
        try:
            docs = hs.catalog_lane(query, mcp_factory=McpClient, doc_budget=DOC_BUDGET,
                                   exclude_prefixes=B_EXCLUDES, segment_chars=2400,
                                   read_max_chars=20000, trace=cat_trace)
            cat_trace["docs"] = docs
        except Exception as exc:  # noqa: BLE001
            cat_trace["error"] = f"{type(exc).__name__}: {str(exc)[:200]}"

    th1 = threading.Thread(target=vector_branch)
    th2 = threading.Thread(target=catalog_branch_thread)
    th1.start(); th2.start(); th1.join(); th2.join()
    trace["parallel"] = {"vector": {k: v for k, v in vec_trace.items() if k != "vector_raw_hits"},
                          "catalog": {k: v for k, v in cat_trace.items() if k != "docs"},
                          "vector_branch_error": vec_trace.get("error"),
                          "catalog_branch_error": cat_trace.get("error")}

    # merge by (kb_id, normalized doc_path)
    merged: dict[tuple, dict] = {}
    for d in cat_trace.get("docs", []):
        merged[doc_key(d["kb_id"], d["doc_path"])] = {**d, "lane": "catalog"}
    for ref in vec_result.get("docs", []):
        key = doc_key(ref["kb_id"], ref["doc_path"])
        if key in merged:
            merged[key]["lane"] = "both"
            merged[key]["vector_score"] = ref.get("vector_score")
        else:
            merged[key] = {**ref, "lane": "vector"}
    trace["merge"] = {"merged_docs": len(merged),
                      "from_both": sum(1 for d in merged.values() if d.get("lane") == "both"),
                      "from_vector_only": sum(1 for d in merged.values() if d.get("lane") == "vector"),
                      "from_catalog_only": sum(1 for d in merged.values() if d.get("lane") == "catalog")}
    # unified reread of merged result-list docs that lack body content
    docs = list(merged.values())
    mc = McpClient()
    try:
        for d in docs:
            if not str(d.get("content") or "").strip():
                body = read_doc(mc, d["kb_id"], d)
                d["content"] = body["content"]
    finally:
        mc.close()
    for d in docs:
        if "segments" not in d:
            d["segments"] = segment(d["content"])
    verdict = judge(query, docs)
    trace["judge"] = {k: v for k, v in verdict.items() if k != "kept_docs"}
    trace["kept_doc_paths"] = [docs[i]["doc_path"] for i in verdict["kept_docs"]]
    trace["seconds"] = round(time.time() - t0, 1)
    pack = "\n\n".join(f"[{docs[i]['doc_path']} · lane={docs[i]['lane']}]\n{docs[i]['content'][:2500]}"
                       for i in verdict["kept_docs"])[:12000]
    return {"evidence_pack": pack, "kept": trace["kept_doc_paths"], "verdict": verdict,
            "lane_map": {docs[i]["doc_path"]: docs[i].get("lane") for i in verdict["kept_docs"]}}


def mode_a_light(query: str, trace: dict) -> dict:
    """Vector branch only (no reads) — returns candidate docs with scores."""
    t0 = time.time()
    mc = McpClient()
    try:
        raw = mc.call("kb_search_vector", {"query": query, "kb_id": "", "top_k": VECTOR_TOP_K,
                                            "score_threshold": VECTOR_THRESHOLD, "balance_kbs": True},
                      timeout=300)
    finally:
        mc.close()
    best: dict[tuple, dict] = {}
    for h in (raw.get("results") or []):
        if float(h.get("score") or 0) < VECTOR_THRESHOLD:
            continue
        key = doc_key(h.get("kb_id"), h.get("doc_path"))
        if key not in best or float(h["score"]) > float(best[key]["score"]):
            best[key] = h
    trace["vector_hits"] = len(raw.get("results") or [])
    trace["vector_dedup_docs"] = len(best)
    trace["seconds"] = round(time.time() - t0, 1)
    docs = []
    mc = McpClient()
    try:
        for (kb_id, path), h in sorted(best.items(), key=lambda kv: -float(kv[1]["score"]))[:5]:
            docs.append({"kb_id": kb_id, "doc_id": None, "doc_path": path,
                         "name": Path(path).name, "description": None,
                         "content": "", "vector_score": h["score"]})
    finally:
        mc.close()
    # vector branch contributes its chunk text as content so segments exist
    for d in docs:
        d["content"] = d.get("content") or ""
    return {"docs": docs}


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # warm the model once (outside timings)
    jf.filter_candidates({"engine": "laya", "query": "warmup",
                          "candidates": [{"candidate_id": "w", "text": "warmup"}]})
    summary = []
    for q in QUESTIONS:
        for mode, fn in (("A_vector", mode_a), ("B_complete", mode_b), ("C_parallel", mode_c)):
            trace = {"question": q["query"], "mode": mode, "started": time.strftime("%H:%M:%S")}
            try:
                result = fn(q["query"], trace)
                trace["evidence_chars"] = len(result["evidence_pack"])
                trace["lanes"] = result.get("lane_map")
            except Exception as exc:  # noqa: BLE001
                trace["fatal"] = f"{type(exc).__name__}: {str(exc)[:300]}"
            (OUT_DIR / f"{mode}_{q['id']}.json").write_text(
                json.dumps(trace, ensure_ascii=False, indent=1), encoding="utf-8")
            kept = trace.get("kept_doc_paths") or []
            print(f"[{mode} {q['id']}] {trace.get('seconds','?')}s · kept={len(kept)} · "
                  f"{[Path(p).name[:50] for p in kept][:3]}", flush=True)
            summary.append({"mode": mode, "qid": q["id"], "seconds": trace.get("seconds"),
                            "kept": kept, "fatal": trace.get("fatal")})
    (OUT_DIR / "SUMMARY.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1),
                                          encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
