#!/usr/bin/env python3
"""Vector-first retrieval with a Laya/Jev verify gate (knowledgebase-search Phase 1).

2026-09-26 contract — replaces the former read-content + LLM 0-8 rubric gate:

  kb_search_vector (WIDE net, default top_k=30) -> hard threshold
    -> doc-level dedup, keep ALL deduped docs (no top 3-5 cut)
    -> batch kb_doc_read by doc_id/doc_path (the verify input)
    -> structure-aware segmentation (complete_recall.segment_document)
    -> real Laya (default) / Jev decision gate, fail-closed, EVERY segment scored
    -> every doc with >=1 yes-scored segment enters result_list (no rubric,
       no retention cut — the engine verdict is final)
    -> evidence_pack renders survivor content for knowledge-enhanced answering

Zero survivors is a first-class outcome: the caller must escalate to the
librarian fallback (Phase 2), never fabricate. The script never writes to the
knowledge base; a failed recall/judge is reported, never hidden.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
SKILLS_DIR = SKILL_DIR.parent

LIBRARIAN_SCRIPTS = SKILLS_DIR / "knowledgebase-librarian" / "scripts"
if not LIBRARIAN_SCRIPTS.is_dir():
    raise ImportError(
        "knowledgebase-search reuses the decision layer from the librarian skill; "
        f"expected scripts at {LIBRARIAN_SCRIPTS}")
if str(LIBRARIAN_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(LIBRARIAN_SCRIPTS))

import complete_recall as cr  # noqa: E402
import jev_filter as jf  # noqa: E402

DEFAULT_TOP_K = 30
DEFAULT_VECTOR_THRESHOLD = 0.35
DEFAULT_THRESHOLD = 0.5
DEFAULT_DOC_READ_CHARS = 20_000
DEFAULT_SEGMENT_CHARS = 3_000
DEFAULT_MAX_STATE_CHARS = 6_000
DEFAULT_EVIDENCE_CHARS = 24_000
DEFAULT_DOC_HEAD_CHARS = 2_500


def norm_path(path: Any) -> str:
    return str(path or "").replace("\\", "/")


def doc_key(kb_id: Any, path: Any) -> tuple[str, str]:
    return (str(kb_id or ""), norm_path(path))


def _default_mcp_factory() -> Callable[[], Any]:
    """Spawn a fresh stdio MCP client per connection (same launcher as hybrid)."""
    lib_dir = SKILLS_DIR.parents[1] / "benchmark-suite" / "scripts"
    if not lib_dir.is_dir():
        raise RuntimeError(f"MCP client library not found at {lib_dir}")
    if str(lib_dir) not in sys.path:
        sys.path.insert(0, str(lib_dir))
    from lib import McpClient  # noqa: PLC0415
    return McpClient


# ───────────────────────────── recall lane ─────────────────────────────

def vector_recall(query: str, *, mcp_factory: Callable[[], Any], kb_id: str,
                  top_k: int, threshold: float, trace: dict[str, Any]) -> list[dict[str, Any]]:
    """Wide-net recall: hard threshold + doc-level dedup, keep EVERY deduped doc."""
    t0 = time.time()
    mc = mcp_factory()
    try:
        raw = mc.call("kb_search_vector",
                      {"query": query, "kb_id": kb_id, "top_k": top_k,
                       "score_threshold": threshold, "balance_kbs": True},
                      timeout=300)
    finally:
        mc.close()
    hits = raw.get("results") or []
    trace["vector_raw_hits"] = len(hits)
    best: dict[tuple[str, str], dict[str, Any]] = {}
    for h in hits:
        score = h.get("score")
        if not isinstance(score, (int, float)) or isinstance(score, bool) or float(score) < threshold:
            continue
        key = doc_key(h.get("kb_id"), h.get("doc_path"))
        if key not in best or float(score) > float(best[key]["vector_score"] or 0):
            best[key] = {"kb_id": key[0], "doc_path": key[1],
                         "doc_id": h.get("doc_id"),
                         "name": h.get("name") or Path(key[1]).name,
                         "vector_score": float(score), "chunk_index": h.get("chunk_index")}
    refs = sorted(best.values(), key=lambda r: -float(r["vector_score"]))
    trace.update({"vector_dedup_docs": len(refs), "recall_seconds": round(time.time() - t0, 1)})
    return refs


def reread_and_segment(refs: list[dict[str, Any]], *, mcp_factory: Callable[[], Any],
                       read_chars: int, segment_chars: int,
                       trace: dict[str, Any]) -> list[dict[str, Any]]:
    """Verify input: batch kb_doc_read by doc_id/path; segment the real body."""
    t0 = time.time()
    docs: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    mc = mcp_factory()
    try:
        for r in refs:
            try:
                resp = mc.call("kb_doc_read", {"kb_id": r["kb_id"], "doc_path": r["doc_path"],
                                               "max_chars": read_chars}, timeout=180)
                content = str(resp.get("content") or "")
                doc = {**r, "content": content, "truncated": bool(resp.get("truncated"))}
                if content.strip():
                    doc["segments"] = cr.segment_document(doc, max_chars=segment_chars)
                else:
                    doc["segments"] = []
                    doc["read_error"] = "empty_content"
            except Exception as exc:  # noqa: BLE001 — one bad read must not kill the batch
                doc = {**r, "content": "", "segments": [],
                       "read_error": f"{type(exc).__name__}:{str(exc)[:160]}"}
            if doc.get("read_error"):
                errors.append({"doc_path": doc.get("doc_path"), "error": doc["read_error"]})
            docs.append(doc)
    finally:
        mc.close()
    trace.update({"docs_read": sum(1 for d in docs if str(d.get("content") or "").strip()),
                  "read_errors": errors, "reread_seconds": round(time.time() - t0, 1)})
    return docs


# ────────────────────────────── judgment ──────────────────────────────

def judge_docs(query: str, docs: Sequence[Mapping[str, Any]], *, engine: str,
               threshold: float, max_state_chars: int = DEFAULT_MAX_STATE_CHARS,
               env: Mapping[str, str] | None = None,
               score_fn: Callable[[str, str, str], tuple[float, dict[str, Any]]] | None = None) -> dict[str, Any]:
    """Segment-level decision-engine gate; a doc survives on ANY yes segment."""
    flat: list[str] = []
    owner: list[int] = []
    for di, doc in enumerate(docs):
        for seg in doc.get("segments") or []:
            text = seg.get("text") if isinstance(seg, Mapping) else str(seg)
            if not str(text or "").strip():
                continue
            flat.append(str(text)[:max_state_chars])
            owner.append(di)
    if not flat:
        return {"kept_doc_indices": [], "global_best": None, "doc_scores": [],
                "score_by_index": {}, "status": "no_segments", "engine": engine,
                "backend": "none", "real_engine": False, "scored_segments": 0,
                "total_segments": 0, "errors": []}
    verdict = jf.filter_candidates(
        {"engine": engine, "query": query, "threshold": threshold,
         "candidates": [{"candidate_id": f"s{i:04d}", "text": t} for i, t in enumerate(flat)]},
        score_fn=score_fn, env=env)
    doc_best: dict[int, dict[str, Any]] = {}
    for rec in verdict.get("scores") or []:
        cid = str(rec.get("candidate_id") or "")
        if not cid[1:].isdigit():
            continue
        di = owner[int(cid[1:])]
        score = rec.get("score")
        if score is None:
            continue
        if di not in doc_best or float(score) > float(doc_best[di]["score"]):
            doc_best[di] = rec
    # yes = segment kept by the engine (score >= threshold). A doc survives on
    # ANY yes segment; kept set is NOT cut further (engine verdict is final).
    kept = sorted((di for di, rec in doc_best.items()
                   if rec.get("kept") is True and rec.get("score") is not None),
                  key=lambda di: -float(doc_best[di]["score"]))
    doc_scores = [{"kb_id": docs[di].get("kb_id"), "doc_path": docs[di].get("doc_path"),
                   "vector_score": docs[di].get("vector_score"),
                   "judge_score": doc_best[di].get("score"), "kept": di in set(kept)}
                  for di in sorted(doc_best, key=lambda d: -float(doc_best[d]["score"] or 0))]
    return {"kept_doc_indices": kept,
            "global_best": max((float(doc_best[di]["score"]) for di in doc_best), default=None),
            "doc_scores": doc_scores,
            "score_by_index": {str(di): doc_best[di].get("score") for di in doc_best},
            "status": verdict.get("status"), "engine": verdict.get("engine"),
            "backend": verdict.get("backend"), "real_engine": verdict.get("real_engine"),
            "criterion": verdict.get("criterion"), "threshold": verdict.get("threshold"),
            "scored_segments": verdict.get("scored_count"), "total_segments": len(flat),
            "errors": verdict.get("errors") or []}


def build_result_list(docs: Sequence[Mapping[str, Any]], verdict: Mapping[str, Any]) -> list[dict[str, Any]]:
    scores = verdict.get("score_by_index") or {}
    rows: list[dict[str, Any]] = []
    for di in verdict.get("kept_doc_indices") or []:
        d = docs[di]
        rows.append({"kb_id": d.get("kb_id"), "doc_id": d.get("doc_id"),
                     "doc_path": d.get("doc_path"), "name": d.get("name"),
                     "vector_score": d.get("vector_score"),
                     "judge_score": scores.get(str(di)), "truncated": d.get("truncated"),
                     "read_error": d.get("read_error")})
    return rows


def build_evidence_pack(docs: Sequence[Mapping[str, Any]], verdict: Mapping[str, Any], *,
                        head_chars: int = DEFAULT_DOC_HEAD_CHARS,
                        max_chars: int = DEFAULT_EVIDENCE_CHARS) -> str:
    parts = []
    for di in verdict.get("kept_doc_indices") or []:
        d = docs[di]
        parts.append(f"[{d.get('doc_path')} · vec={d.get('vector_score')}]\n"
                     f"{str(d.get('content') or '')[:head_chars]}")
    return "\n\n".join(parts)[:max_chars]


# ──────────────────────────── orchestrator ────────────────────────────

def run_search(query: str, *, kb_id: str = "", engine: str = "laya",
               threshold: float = DEFAULT_THRESHOLD,
               vector_top_k: int = DEFAULT_TOP_K,
               vector_threshold: float = DEFAULT_VECTOR_THRESHOLD,
               doc_read_chars: int = DEFAULT_DOC_READ_CHARS,
               segment_chars: int = DEFAULT_SEGMENT_CHARS,
               max_state_chars: int = DEFAULT_MAX_STATE_CHARS,
               max_evidence_chars: int = DEFAULT_EVIDENCE_CHARS,
               env: Mapping[str, str] | None = None,
               score_fn: Callable[[str, str, str], tuple[float, dict[str, Any]]] | None = None,
               mcp_factory: Callable[[], Any] | None = None) -> dict[str, Any]:
    t0 = time.time()
    if mcp_factory is None:
        mcp_factory = _default_mcp_factory()
    recall_trace: dict[str, Any] = {}
    refs = vector_recall(query, mcp_factory=mcp_factory, kb_id=kb_id,
                         top_k=vector_top_k, threshold=vector_threshold, trace=recall_trace)
    docs = reread_and_segment(refs, mcp_factory=mcp_factory, read_chars=doc_read_chars,
                              segment_chars=segment_chars, trace=recall_trace)
    unscanned = [{"kb_id": d.get("kb_id"), "doc_path": d.get("doc_path"),
                  "reason": d.get("read_error") or "content_missing"}
                 for d in docs if not d.get("segments")]
    judgeable = [d for d in docs if d.get("segments")]
    verdict = judge_docs(query, judgeable, engine=engine, threshold=threshold,
                         max_state_chars=max_state_chars, env=env, score_fn=score_fn)
    result_list = build_result_list(judgeable, verdict)
    return {"status": "ok", "query": query, "engine": engine,
            "backend": verdict.get("backend"), "real_engine": verdict.get("real_engine"),
            "parameters": {"kb_id": kb_id, "threshold": threshold,
                           "vector_top_k": vector_top_k, "vector_threshold": vector_threshold,
                           "doc_read_chars": doc_read_chars, "segment_chars": segment_chars,
                           "max_state_chars": max_state_chars,
                           "max_evidence_chars": max_evidence_chars},
            "recall": recall_trace,
            "judge": {k: verdict.get(k) for k in
                      ("status", "engine", "backend", "real_engine", "criterion", "threshold",
                       "global_best", "scored_segments", "total_segments", "errors")},
            "judge_doc_scores": verdict.get("doc_scores"),
            "result_list": result_list,
            "kept_doc_paths": [r["doc_path"] for r in result_list],
            "evidence_pack": build_evidence_pack(judgeable, verdict, max_chars=max_evidence_chars),
            "unscanned": unscanned,
            "seconds": round(time.time() - t0, 1)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Vector-first retrieval with a fail-closed Laya/Jev verify gate: "
                    "wide top_k recall -> doc dedup (keep all) -> batch kb_doc_read by "
                    "doc_id/path -> segment -> engine judges EVERY segment -> all yes docs "
                    "into result_list")
    parser.add_argument("--query", help="question text (Phase 0 rewritten recommended)")
    parser.add_argument("--kb-id", default="", help="scope to one KB; default whole library")
    parser.add_argument("--engine", choices=["laya", "jev"], default="laya")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--vector-threshold", type=float, default=DEFAULT_VECTOR_THRESHOLD)
    parser.add_argument("--doc-read-chars", type=int, default=DEFAULT_DOC_READ_CHARS)
    parser.add_argument("--segment-chars", type=int, default=DEFAULT_SEGMENT_CHARS)
    parser.add_argument("--max-state-chars", type=int, default=DEFAULT_MAX_STATE_CHARS)
    parser.add_argument("--max-evidence-chars", type=int, default=DEFAULT_EVIDENCE_CHARS)
    parser.add_argument("--output", help="JSON output path; default stdout")
    parser.add_argument("--require-real", action="store_true",
                        help="exit 2 unless the selected engine produced real scores")
    args = parser.parse_args(argv)
    query = str(args.query or "").strip()
    if not query:
        print(json.dumps({"status": "error", "errors": [{"error": "query_missing"}]}))
        return 1
    try:
        result = run_search(query, kb_id=args.kb_id, engine=args.engine,
                            threshold=args.threshold, vector_top_k=args.top_k,
                            vector_threshold=args.vector_threshold,
                            doc_read_chars=args.doc_read_chars,
                            segment_chars=args.segment_chars,
                            max_state_chars=args.max_state_chars,
                            max_evidence_chars=args.max_evidence_chars)
    except Exception as exc:  # noqa: BLE001 — machine-readable failure
        result = {"status": "error", "errors": [{"error": f"{type(exc).__name__}:{str(exc)[:240]}"}],
                  "result_list": [], "evidence_pack": "", "unscanned": [], "real_engine": False}
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    if result.get("status") == "error" and not result.get("judge"):
        return 1
    if args.require_real and not result.get("real_engine"):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
