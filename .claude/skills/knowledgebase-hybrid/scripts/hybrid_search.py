#!/usr/bin/env python3
"""Parallel hybrid retrieval for the knowledgebase-hybrid skill.

Two recall lanes run concurrently, each on its own MCP connection:

  vector lane   kb_search_vector -> hard threshold -> doc-level dedup (no reads)
  catalog lane  kb_list -> every kept shelf's document descriptions ->
                description-overlap ranking + budget top-up -> kb_doc_read
                -> structure-aware segments (complete_recall.segment_document)

The lanes merge on (kb_id, normalized doc_path). Documents seen by both lanes
are marked lane=both and are never read twice; vector-only documents get one
unified reread. Every merged document is segmented and sent to the selected
decision engine (default local Laya, explicit --engine jev for remote Jev).
Retention uses the absolute threshold plus a relative cut
(global_best - margin) because the local Laya score distribution on prose is
top-heavy (measured median ~0.88); the relative cut isolates evidence-bearing
documents. Missing scores fail closed per candidate.

The script never writes to the knowledge base and never fabricates coverage:
a failed lane is reported (status partial/error), never silently dropped.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
SKILLS_DIR = SKILL_DIR.parent
REPO = SKILL_DIR.parents[2]

LIBRARIAN_SCRIPTS = SKILLS_DIR / "knowledgebase-librarian" / "scripts"
if not LIBRARIAN_SCRIPTS.is_dir():
    raise ImportError(
        "knowledgebase-hybrid reuses the decision layer from the sibling skill; "
        f"expected scripts at {LIBRARIAN_SCRIPTS}")
if str(LIBRARIAN_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(LIBRARIAN_SCRIPTS))

import complete_recall as cr  # noqa: E402
import jev_filter as jf  # noqa: E402

DEFAULT_THRESHOLD = 0.5
DEFAULT_RELATIVE_MARGIN = 0.10
DEFAULT_VECTOR_TOP_K = 10
DEFAULT_VECTOR_THRESHOLD = 0.35
DEFAULT_DOC_BUDGET = 30
DEFAULT_MAX_STATE_CHARS = 6_000
DEFAULT_SEGMENT_CHARS = 2_400
DEFAULT_READ_MAX_CHARS = 20_000
DEFAULT_EVIDENCE_PACK_CHARS = 12_000
DEFAULT_DOC_HEAD_CHARS = 2_500
DEFAULT_MAX_KEPT = 30


def norm_path(path: Any) -> str:
    return str(path or "").replace("\\", "/")


def doc_key(kb_id: Any, path: Any) -> tuple[str, str]:
    return (str(kb_id or ""), norm_path(path))


def _default_mcp_factory() -> Callable[[], Any]:
    """Spawn a fresh stdio MCP client per connection (not shared across threads)."""
    lib_dir = REPO / "benchmark-suite" / "scripts"
    if not lib_dir.is_dir():
        raise RuntimeError(f"MCP client library not found at {lib_dir}")
    if str(lib_dir) not in sys.path:
        sys.path.insert(0, str(lib_dir))
    from lib import McpClient  # noqa: PLC0415
    return McpClient


# ───────────────────────────── pure helpers ─────────────────────────────

def select_shelves(kbs: Sequence[Mapping[str, Any]], exclude_prefixes: Sequence[str]) -> list[dict[str, Any]]:
    """Keep shelves that can hold documents, minus excluded name prefixes.

    A null doc_count is treated as unknown (kept) rather than empty: recall
    beats a cheaper scan, and kb_get_documents on an empty shelf is harmless.
    """
    prefixes = tuple(str(p) for p in exclude_prefixes or () if p)
    rows: list[dict[str, Any]] = []
    for raw in kbs or []:
        item = dict(raw)
        name = str(item.get("name") or "")
        count = item.get("doc_count")
        if prefixes and name.startswith(prefixes):
            continue
        if count is not None and int(count or 0) <= 0:
            continue
        rows.append(item)
    return rows


def entry_overlap(query_terms: set[str], entry: Mapping[str, Any]) -> int:
    blob = f"{entry.get('name', '')} {entry.get('description', '')}"
    return len(query_terms & cr._terms(blob)) if query_terms else 0


def _stem_of(doc_path: str) -> str | None:
    # real paths end with ".md" AFTER the part marker: "paper (part 1 of 3).md"
    m = re.search(r"^(.*) \(part \d+ of \d+\)", norm_path(str(doc_path or "")))
    return m.group(1) if m else None


def pick_catalog_docs(pool: list[tuple[int, dict[str, Any]]], budget: int,
                      *, kb_status: Mapping[str, int] | None = None,
                      stem_completion: bool = True, stem_max_parts: int = 6) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Budgeted selection: overlap hits first, then split-doc sibling completion,
    then a round-robin zero-overlap top-up (relevant/possible KBs first).

    v1 picked zero-overlap docs in catalog scan order, which silently biased the
    top-up toward whichever KB happened to be scanned first (measured 2026-09-25:
    T3's gold in the 4th KB was never read). Round-robin equalizes the KB bias;
    stem completion guarantees that a matched split document brings its sibling
    parts (the experiments/appendix parts a question actually targets).
    """
    ordered = sorted(pool, key=lambda x: -x[0])
    hits = [e for overlap, e in ordered if overlap > 0]
    zeros = [e for overlap, e in ordered if overlap <= 0]
    picked: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    def take(e: dict[str, Any]) -> bool:
        key = doc_key(e.get("kb_id"), e.get("doc_path"))
        if key in seen:
            return False
        seen.add(key)
        picked.append(e)
        return True

    for e in hits:
        if len(picked) >= budget:
            break
        take(e)
    completed = 0
    if stem_completion and len(picked) < budget:
        stems: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for _, e in ordered:
            stem = _stem_of(e.get("doc_path"))
            if stem:
                stems.setdefault((str(e.get("kb_id")), stem), []).append(e)
        for e in list(picked):
            stem = _stem_of(e.get("doc_path"))
            if not stem:
                continue
            for sib in stems.get((str(e.get("kb_id")), stem), [])[:max(0, stem_max_parts)]:
                if len(picked) >= budget:
                    break
                if take(sib):
                    completed += 1
            if len(picked) >= budget:
                break
    zeros_left: dict[str, list[dict[str, Any]]] = {}
    for e in zeros:
        zeros_left.setdefault(str(e.get("kb_id")), []).append(e)
    kb_ids = sorted(zeros_left, key=lambda k: ((kb_status or {}).get(k, 2), k))
    progressed = True
    while len(picked) < budget and progressed:
        progressed = False
        for k in kb_ids:
            if zeros_left.get(k):
                take(zeros_left[k].pop(0))
                progressed = True
                if len(picked) >= budget:
                    break
    trace = {"description_overlap_docs": len(hits),
             "stem_completion_docs": completed,
             "zero_overlap_docs_unread": sum(len(v) for v in zeros_left.values())}
    return picked, trace


def merge_lanes(vec_refs: Sequence[Mapping[str, Any]],
                cat_docs: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Merge on (kb_id, normalized doc_path); shared documents are never read twice."""
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for d in cat_docs or []:
        merged[doc_key(d.get("kb_id"), d.get("doc_path"))] = {**dict(d), "lane": "catalog"}
    for r in vec_refs or []:
        key = doc_key(r.get("kb_id"), r.get("doc_path"))
        if key in merged:
            merged[key]["lane"] = "both"
            merged[key]["vector_score"] = r.get("vector_score")
        else:
            ref = dict(r)
            ref.setdefault("name", Path(norm_path(ref.get("doc_path"))).name)
            merged[key] = {**ref, "lane": "vector", "content": "", "segments": []}
    rows = list(merged.values())
    trace = {"merged_docs": len(rows),
             "from_both": sum(1 for d in rows if d["lane"] == "both"),
             "from_vector_only": sum(1 for d in rows if d["lane"] == "vector"),
             "from_catalog_only": sum(1 for d in rows if d["lane"] == "catalog")}
    return rows, trace


def plan_rereads(merged: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Documents whose content no lane has fetched yet (vector-only proposals)."""
    return [d for d in merged if not str(d.get("content") or "").strip()]


# ────────────────────────────── MCP lanes ──────────────────────────────

def vector_lane(query: str, *, mcp_factory: Callable[[], Any], top_k: int,
                threshold: float, trace: dict[str, Any]) -> list[dict[str, Any]]:
    t0 = time.time()
    mc = mcp_factory()
    try:
        raw = mc.call("kb_search_vector",
                      {"query": query, "kb_id": "", "top_k": top_k,
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
            best[key] = {"kb_id": key[0], "doc_path": key[1], "doc_id": h.get("doc_id"),
                         "name": h.get("name") or Path(key[1]).name,
                         "vector_score": float(score), "chunk_index": h.get("chunk_index"),
                         "lane": "vector"}
    refs = sorted(best.values(), key=lambda r: -float(r["vector_score"]))
    trace.update({"vector_dedup_docs": len(refs), "seconds": round(time.time() - t0, 1)})
    return refs


def catalog_lane(query: str, *, mcp_factory: Callable[[], Any], doc_budget: int,
                 exclude_prefixes: Sequence[str], segment_chars: int,
                 read_max_chars: int, trace: dict[str, Any],
                 extra_terms: Sequence[str] = (), stem_completion: bool = True,
                 stem_max_parts: int = 6, peek_heads: bool = False,
                 peek_chars: int = 700, peek_limit: int = 300,
                 catalog_index: dict[tuple[str, str], list[dict[str, Any]]] | None = None) -> list[dict[str, Any]]:
    """L0 catalog -> L2 every document description -> budgeted picks -> reads.

    extra_terms are the agent's Phase-0 bilingual keywords merged into the
    description match (queries and descriptions often live in different
    languages). With peek_heads, zero-overlap docs that were not picked still
    get one cheap head read so the decision engine — not description
    vocabulary — decides their fate; the scan then has no blind spot by
    construction, only cheaper evidence.
    """
    t0 = time.time()
    query_blob = query + " " + " ".join(str(t) for t in extra_terms or ())
    match_terms = cr._terms(query_blob)
    mc = mcp_factory()
    pool: list[tuple[int, dict[str, Any]]] = []
    kb_rows: list[dict[str, Any]] = []
    try:
        kbs = (mc.call("kb_list", {"lightweight": True}, timeout=120).get("catalog") or [])
        shelves = select_shelves(kbs, exclude_prefixes)
        trace["shelves_scanned"] = len(shelves)
        trace["shelves_excluded"] = len(kbs) - len(shelves)
        kb_rows = cr.classify_kbs(query_blob, shelves)
        for kb in kb_rows:
            kb_id = kb.get("kb_id") or kb.get("name")
            entries = (mc.call("kb_get_documents", {"lightweight": True, "kb_id": kb_id},
                               timeout=180).get("catalog") or [])
            trace["descriptions_scanned"] = trace.get("descriptions_scanned", 0) + len(entries)
            for e in entries:
                pool.append((entry_overlap(match_terms, e), {**e, "kb_id": kb_id, "kb_name": kb.get("name")}))
                if catalog_index is not None:
                    stem = _stem_of(e.get("doc_path"))
                    if stem:
                        catalog_index.setdefault((str(kb_id), stem), []).append(
                            {**e, "kb_id": kb_id, "kb_name": kb.get("name")})
    finally:
        mc.close()
    status_order = {"relevant": 0, "possible": 1}
    kb_status = {str(k.get("kb_id") or k.get("name")): status_order.get(k.get("catalog_status"), 2)
                 for k in kb_rows}
    overlap_paths = {(str(e.get("kb_id")), norm_path(e.get("doc_path")))
                     for overlap, e in pool if overlap > 0}
    trace["description_overlap_paths"] = sorted(overlap_paths)
    picked, pick_trace = pick_catalog_docs(pool, doc_budget, kb_status=kb_status,
                                           stem_completion=stem_completion,
                                           stem_max_parts=stem_max_parts)
    trace.update(pick_trace)
    docs: list[dict[str, Any]] = []
    mc = mcp_factory()
    try:
        for e in picked:
            r = mc.call("kb_doc_read", {"kb_id": e["kb_id"], "doc_path": e["doc_path"],
                                        "max_chars": read_max_chars}, timeout=180)
            doc = {"kb_id": e["kb_id"], "kb_name": e.get("kb_name"),
                   "doc_id": e.get("doc_id") or e.get("file_id"), "doc_path": e["doc_path"],
                   "name": e.get("name"), "description": e.get("description"),
                   "lane": "catalog", "vector_score": None,
                   "content": str(r.get("content") or ""), "truncated": bool(r.get("truncated"))}
            doc["segments"] = cr.segment_document(doc, max_chars=segment_chars)
            docs.append(doc)
    finally:
        mc.close()
    trace.update({"docs_read": len(docs), "seconds": round(time.time() - t0, 1)})
    if peek_heads:
        t1 = time.time()
        picked_keys = {doc_key(e.get("kb_id"), e.get("doc_path")) for e in picked}
        zeros_all = [e for _, e in sorted(pool, key=lambda x: -x[0])
                     if doc_key(e.get("kb_id"), e.get("doc_path")) not in picked_keys]
        peeks = zeros_all[:max(0, peek_limit)]
        peek_docs: list[dict[str, Any]] = []
        peek_empty = 0
        mc = mcp_factory()
        try:
            for e in peeks:
                try:
                    r = mc.call("kb_doc_read", {"kb_id": e["kb_id"], "doc_path": e["doc_path"],
                                                "max_chars": peek_chars}, timeout=90)
                    content = str(r.get("content") or "")
                    if not content.strip():
                        peek_empty += 1
                        continue
                    doc = {"kb_id": e["kb_id"], "kb_name": e.get("kb_name"),
                           "doc_id": e.get("doc_id") or e.get("file_id"), "doc_path": e["doc_path"],
                           "name": e.get("name"), "description": e.get("description"),
                           "lane": "catalog", "vector_score": None, "head_peek": True,
                           "content": content, "truncated": bool(r.get("truncated"))}
                    doc["segments"] = cr.segment_document(doc, max_chars=segment_chars)
                    peek_docs.append(doc)
                except Exception as exc:  # noqa: BLE001 — one bad peek must not stop the scan
                    trace.setdefault("peek_errors", []).append(
                        {"doc_path": e.get("doc_path"), "error": f"{type(exc).__name__}:{str(exc)[:120]}"})
        finally:
            mc.close()
        trace.update({"peek_docs": len(peek_docs), "peek_empty": peek_empty,
                      "peek_seconds": round(time.time() - t1, 1)})
        docs.extend(peek_docs)
    return docs


def reread_missing(merged: list[dict[str, Any]], *, mcp_factory: Callable[[], Any],
                   read_max_chars: int, segment_chars: int, trace: dict[str, Any]) -> None:
    """One unified reread for documents no lane fetched (in place)."""
    targets = plan_rereads(merged)
    trace["docs_to_reread"] = len(targets)
    if not targets:
        trace["docs_reread"] = 0
        trace["reread_errors"] = []
        return
    errors: list[dict[str, Any]] = []
    mc = mcp_factory()
    try:
        for d in targets:
            try:
                r = mc.call("kb_doc_read", {"kb_id": d.get("kb_id"), "doc_path": d.get("doc_path"),
                                            "max_chars": read_max_chars}, timeout=180)
                d["content"] = str(r.get("content") or "")
                d["truncated"] = bool(r.get("truncated"))
                if d["content"].strip():
                    d["segments"] = cr.segment_document(d, max_chars=segment_chars)
                else:
                    d["segments"] = []
                    d["read_error"] = "empty_content"
            except Exception as exc:  # noqa: BLE001 — one bad read must not kill the rest
                d["segments"] = []
                d["read_error"] = f"{type(exc).__name__}:{str(exc)[:200]}"
                errors.append({"doc_path": d.get("doc_path"), "error": d["read_error"]})
    finally:
        mc.close()
    trace["docs_reread"] = sum(1 for d in targets if str(d.get("content") or "").strip())
    trace["reread_errors"] = errors


# ────────────────────────────── judgment ──────────────────────────────

def judge_docs(query: str, docs: Sequence[Mapping[str, Any]], *, engine: str,
               threshold: float, relative_margin: float,
               lane_agreement: bool = False, top_k_floor: int = 0,
               max_kept: int | None = DEFAULT_MAX_KEPT,
               agreed_paths: set | None = None,
               max_state_chars: int = DEFAULT_MAX_STATE_CHARS,
               env: Mapping[str, str] | None = None,
               score_fn: Callable[[str, str, str], tuple[float, dict[str, Any]]] | None = None) -> dict[str, Any]:
    """Segment-level decision-engine gate; per-doc best score; shared retention.

    Retention (complete_recall.retain_docs): relative cut against Laya's
    top-heavy distribution, plus a global top-K floor when real evidence
    exists — question-critical mid-score documents (experiments sections,
    appendices) survive the cut. lane_agreement additionally keeps both-lane
    documents at the absolute threshold. Kept indices are score-desc ordered.
    """
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
        return {"kept_doc_indices": [], "abs_kept": [], "relative_cut": None,
                "global_best": None, "doc_scores": [], "score_by_index": {},
                "status": "no_segments", "engine": engine, "backend": "none",
                "real_engine": False, "scored_segments": 0, "total_segments": 0, "errors": []}
    verdict = jf.filter_candidates(
        {"engine": engine, "query": query, "threshold": threshold,
         "candidates": [{"candidate_id": f"s{i:04d}", "text": t} for i, t in enumerate(flat)]},
        score_fn=score_fn, env=env)
    best: dict[int, dict[str, Any]] = {}
    for rec in verdict.get("scores") or []:
        cid = str(rec.get("candidate_id") or "")
        if not cid[1:].isdigit():
            continue
        di = owner[int(cid[1:])]
        score = rec.get("score")
        if score is None:
            continue
        if di not in best or float(score) > float(best[di]["score"]):
            best[di] = rec
    agreed_idx = set()
    for di, d in enumerate(docs):
        key = (str(d.get("kb_id")), norm_path(d.get("doc_path")))
        if key in (agreed_paths or ()):
            agreed_idx.add(di)
            try:
                d["description_agreed"] = True  # pack ordering reads this flag
            except TypeError:
                pass
    retention = cr.retain_docs(best, threshold=threshold, relative_margin=relative_margin,
                               top_k_floor=top_k_floor, max_kept=max_kept,
                               agreed_keys=agreed_idx)
    kept_set = set(retention["kept_keys"])
    if lane_agreement:
        kept_set |= {di for di, rec in best.items()
                     if rec.get("score") is not None and float(rec["score"]) >= threshold
                     and docs[di].get("lane") == "both"}
    kept = sorted(kept_set, key=lambda di: -float(best[di]["score"]))
    abs_kept = list(retention["abs_kept_keys"])
    doc_scores = [{"kb_id": docs[di].get("kb_id"), "doc_path": docs[di].get("doc_path"),
                   "lane": docs[di].get("lane"), "vector_score": docs[di].get("vector_score"),
                   "head_peek": docs[di].get("head_peek"),
                   "judge_score": best[di].get("score"), "kept": di in kept_set}
                  for di in sorted(best, key=lambda d: -float(best[d]["score"] or 0))]
    return {"kept_doc_indices": kept, "abs_kept": abs_kept,
            "relative_cut": retention["relative_cut"], "global_best": retention["global_best"],
            "floor_applied": retention["floor_applied"], "top_k_floor": top_k_floor,
            "kept_total": retention["kept_total"],
            "doc_scores": doc_scores,
            "score_by_index": {str(di): best[di].get("score") for di in best},
            "status": verdict.get("status"), "engine": verdict.get("engine"),
            "backend": verdict.get("backend"), "real_engine": verdict.get("real_engine"),
            "scored_segments": verdict.get("scored_count"), "total_segments": len(flat),
            "errors": verdict.get("errors") or []}


def _engine_score_fn(engine: str, env: Mapping[str, str] | None = None):
    if engine == "jev":
        return lambda q, t, c: jf.http_score(q, t, c, env=env)
    return lambda q, t, c: jf.laya_score(q, t, c, env=env)


def judge_with_expansion(query: str, docs: list[dict[str, Any]], catalog_index: Mapping[tuple[str, str], list[dict[str, Any]]],
                         *, engine: str, threshold: float, relative_margin: float,
                         lane_agreement: bool = False, top_k_floor: int = 0,
                         max_kept: int | None = DEFAULT_MAX_KEPT,
                         agreed_paths: set | None = None,
                         stem_expansion: bool = True, stem_max_parts: int = 6,
                         expansion_cap: int = 40, read_max_chars: int = DEFAULT_READ_MAX_CHARS,
                         segment_chars: int = DEFAULT_SEGMENT_CHARS,
                         max_state_chars: int = DEFAULT_MAX_STATE_CHARS,
                         env: Mapping[str, str] | None = None,
                         score_fn: Callable[[str, str, str], tuple[float, dict[str, Any]]] | None = None,
                         mcp_factory: Callable[[], Any] | None = None,
                         trace: dict[str, Any] | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Judge, then let kept split documents bring their sibling parts.

    Pass 1 judges every segment. For each KEPT `(part k of N)` document, the
    sibling parts listed in catalog_index are full-read and judged in pass 2 —
    a memoized score function makes the repeat pass free for already-scored
    segments. Rationale (measured T1 2026-09-25): the experiments/appendix
    parts that enumeration questions target sit outside the description-overlap
    picks and their peeked heads only show the abstract, so selection-time
    completion starves whenever hits fill the budget. Expansion around
    *confirmed* evidence is bounded (expansion_cap) and engine-driven.
    """
    trace = trace if trace is not None else {}
    trace.update({"expansion_docs": 0, "expansion_upgraded": 0,
                  "expansion_errors": [], "expansion_seconds": 0.0})
    memo: dict[str, tuple[float, dict[str, Any]]] = {}
    eff = score_fn or _engine_score_fn(engine, env)
    real_engine_path = score_fn is None  # injected fakes must keep offline labels

    def memo_fn(q: str, t: str, c: str) -> tuple[float, dict[str, Any]]:
        # Full-text hash: a 200-char-prefix key let distinct segments that share
        # a boilerplate header inherit each other's scores (phantom evidence).
        key = hashlib.sha256(str(t).encode("utf-8")).hexdigest()
        if key not in memo:
            memo[key] = eff(q, t, c)
        return memo[key]

    def _relabel(v: dict[str, Any]) -> dict[str, Any]:
        if not real_engine_path:
            return v
        # The memo wraps the REAL engine function; filter_candidates cannot know
        # that and would label it offline. Restore true provenance — but only
        # when every candidate actually scored (status "ok" ⇔ all_real in
        # filter_candidates): a failed or partial engine run stays fail-closed
        # (unavailable) instead of claiming a real verdict it never got.
        all_real = v.get("status") == "ok"
        v["backend"] = ("laya_sdk" if engine == "laya" else "http") if all_real else "unavailable"
        v["real_engine"] = all_real
        return v

    verdict = _relabel(judge_docs(query, docs, engine=engine, threshold=threshold,
                                  relative_margin=relative_margin, lane_agreement=lane_agreement,
                                  top_k_floor=top_k_floor, max_kept=max_kept, agreed_paths=agreed_paths,
                                  max_state_chars=max_state_chars, env=env, score_fn=memo_fn))
    if not (stem_expansion and catalog_index and verdict.get("kept_doc_indices") and mcp_factory):
        return docs, verdict
    t0 = time.time()
    # Only FULL reads count as already-read: a head-peek record is a cheap
    # 700-char look, not evidence — expansion upgrades it in place to a full
    # read instead of skipping it (measured T1 2026-09-25: peeked experiments
    # parts scored from their abstract and were never read in full).
    full_read = {(str(d.get("kb_id")), str(d.get("doc_path"))) for d in docs
                 if not d.get("head_peek")}
    peek_index = {(str(d.get("kb_id")), str(d.get("doc_path"))): i
                  for i, d in enumerate(docs) if d.get("head_peek")}
    stems_kept: dict[tuple[str, str], int] = {}
    for di in verdict["kept_doc_indices"]:
        d = docs[di]
        stem = _stem_of(d.get("doc_path"))
        if stem:
            key = (str(d.get("kb_id")), stem)
            stems_kept[key] = stems_kept.get(key, 0) + 1
    new_docs: list[dict[str, Any]] = []
    upgraded = 0
    errors: list[dict[str, Any]] = []
    mc = None
    try:
        for (kb_id, stem), _count in stems_kept.items():
            if len(new_docs) >= expansion_cap:
                break
            for e in catalog_index.get((kb_id, stem), []):
                if len(new_docs) >= expansion_cap:
                    break
                key = (str(e.get("kb_id")), str(e.get("doc_path")))
                if key in full_read:
                    continue
                full_read.add(key)
                try:
                    if mc is None:
                        mc = mcp_factory()
                    r = mc.call("kb_doc_read", {"kb_id": e["kb_id"], "doc_path": e["doc_path"],
                                                "max_chars": read_max_chars}, timeout=180)
                    content = str(r.get("content") or "")
                    if not content.strip():
                        continue
                    doc = {**e, "lane": "catalog", "vector_score": None, "via": "stem_expansion",
                           "content": content, "truncated": bool(r.get("truncated"))}
                    doc["segments"] = cr.segment_document(doc, max_chars=segment_chars)
                    if doc["segments"]:
                        if key in peek_index:
                            docs[peek_index[key]] = doc  # upgrade the peek copy in place
                            upgraded += 1
                        else:
                            new_docs.append(doc)
                except Exception as exc:  # noqa: BLE001 — one bad read must not stop expansion
                    errors.append({"doc_path": e.get("doc_path"),
                                   "error": f"{type(exc).__name__}:{str(exc)[:120]}"})
    finally:
        if mc is not None:
            mc.close()
    trace.update({"expansion_docs": len(new_docs), "expansion_upgraded": upgraded,
                  "expansion_errors": errors,
                  "expansion_seconds": round(time.time() - t0, 1)})
    if new_docs:
        docs = list(docs) + new_docs
        verdict = _relabel(judge_docs(query, docs, engine=engine, threshold=threshold,
                                      relative_margin=relative_margin, lane_agreement=lane_agreement,
                                      top_k_floor=top_k_floor, max_kept=max_kept, agreed_paths=agreed_paths,
                                      max_state_chars=max_state_chars, env=env, score_fn=memo_fn))
    return docs, verdict


def build_result_list(docs: Sequence[Mapping[str, Any]], verdict: Mapping[str, Any]) -> list[dict[str, Any]]:
    scores = verdict.get("score_by_index") or {}
    rows: list[dict[str, Any]] = []
    for di in verdict.get("kept_doc_indices") or []:
        d = docs[di]
        rows.append({"kb_id": d.get("kb_id"), "kb_name": d.get("kb_name"),
                     "doc_id": d.get("doc_id"), "doc_path": d.get("doc_path"),
                     "name": d.get("name"), "description": d.get("description"),
                     "lane": d.get("lane"), "vector_score": d.get("vector_score"),
                     "judge_score": scores.get(str(di)), "truncated": d.get("truncated"),
                     "read_error": d.get("read_error")})
    return rows


def build_evidence_pack(docs: Sequence[Mapping[str, Any]], verdict: Mapping[str, Any], *,
                        head_chars: int = DEFAULT_DOC_HEAD_CHARS,
                        max_chars: int = DEFAULT_EVIDENCE_PACK_CHARS) -> str:
    """Pack kept docs' heads, AGREEMENT DOCS FIRST.

    Ordering rule: dual-signal documents (lane=both, description-agreed, or
    stem-expanded confirmations) precede score-ordered ones. Measured E2E
    2026-09-25: a saturated judge band (96 heads >= 0.9) pushed the gold doc
    to the tail of the score order and the 12K pack cap truncated its content
    out of the answer context entirely, even though it was kept.
    """
    def _rank(di: int) -> tuple:
        d = docs[di]
        dual = 1 if (d.get("lane") == "both" or d.get("description_agreed")
                     or d.get("via") == "stem_expansion") else 0
        score = float((verdict.get("score_by_index") or {}).get(str(di)) or 0)
        return (0 if dual else 1, -score)

    order = sorted(verdict.get("kept_doc_indices") or [], key=_rank)
    parts = []
    for di in order:
        d = docs[di]
        parts.append(f"[{d.get('doc_path')} · lane={d.get('lane')}]\n"
                     f"{str(d.get('content') or '')[:head_chars]}")
    return "\n\n".join(parts)[:max_chars]


# ─────────────────────────── orchestrator ───────────────────────────

def run_hybrid(query: str, *, engine: str = "laya", threshold: float = DEFAULT_THRESHOLD,
               relative_margin: float = DEFAULT_RELATIVE_MARGIN,
               lane_agreement: bool = False, top_k_floor: int = 0,
               max_kept: int | None = DEFAULT_MAX_KEPT,
               vector_top_k: int = DEFAULT_VECTOR_TOP_K,
               vector_threshold: float = DEFAULT_VECTOR_THRESHOLD,
               doc_budget: int = DEFAULT_DOC_BUDGET,
               exclude_prefixes: Sequence[str] = (),
               extra_terms: Sequence[str] = (),
               stem_completion: bool = True, stem_max_parts: int = 6,
               stem_expansion: bool = True,
               peek_heads: bool = False, peek_chars: int = 700, peek_limit: int = 300,
               max_state_chars: int = DEFAULT_MAX_STATE_CHARS,
               segment_chars: int = DEFAULT_SEGMENT_CHARS,
               read_max_chars: int = DEFAULT_READ_MAX_CHARS,
               env: Mapping[str, str] | None = None,
               score_fn: Callable[[str, str, str], tuple[float, dict[str, Any]]] | None = None,
               mcp_factory: Callable[[], Any] | None = None) -> dict[str, Any]:
    t0 = time.time()
    if mcp_factory is None:
        mcp_factory = _default_mcp_factory()
    vec_trace: dict[str, Any] = {}
    cat_trace: dict[str, Any] = {}
    vec_state: dict[str, Any] = {"refs": [], "error": None}
    cat_state: dict[str, Any] = {"docs": [], "error": None}
    catalog_index: dict[tuple[str, str], list[dict[str, Any]]] = {}

    def vec_worker() -> None:
        try:
            vec_state["refs"] = vector_lane(query, mcp_factory=mcp_factory, top_k=vector_top_k,
                                            threshold=vector_threshold, trace=vec_trace)
        except Exception as exc:  # noqa: BLE001 — lane failure is reported, never hidden
            vec_state["error"] = f"{type(exc).__name__}:{str(exc)[:200]}"

    def cat_worker() -> None:
        try:
            cat_state["docs"] = catalog_lane(query, mcp_factory=mcp_factory, doc_budget=doc_budget,
                                             exclude_prefixes=exclude_prefixes,
                                             segment_chars=segment_chars,
                                             read_max_chars=read_max_chars, trace=cat_trace,
                                             extra_terms=extra_terms,
                                             stem_completion=stem_completion,
                                             stem_max_parts=stem_max_parts,
                                             peek_heads=peek_heads, peek_chars=peek_chars,
                                             peek_limit=peek_limit,
                                             catalog_index=catalog_index)
        except Exception as exc:  # noqa: BLE001
            cat_state["error"] = f"{type(exc).__name__}:{str(exc)[:200]}"

    threads = [threading.Thread(target=vec_worker), threading.Thread(target=cat_worker)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    merged, merge_trace = merge_lanes(vec_state["refs"], cat_state["docs"])
    reread_trace: dict[str, Any] = {}
    reread_missing(merged, mcp_factory=mcp_factory, read_max_chars=read_max_chars,
                   segment_chars=segment_chars, trace=reread_trace)
    judgeable = [d for d in merged if d.get("segments")]
    unscanned = [{"kb_id": d.get("kb_id"), "doc_path": d.get("doc_path"), "lane": d.get("lane"),
                  "reason": d.get("read_error") or "content_missing"}
                 for d in merged if not d.get("segments")]
    expansion_trace: dict[str, Any] = {}
    agreed_paths = {(str(k), norm_path(p))
                    for k, p in (cat_trace.get("description_overlap_paths") or [])}
    judgeable, verdict = judge_with_expansion(
        query, judgeable, catalog_index, engine=engine, threshold=threshold,
        relative_margin=relative_margin, lane_agreement=lane_agreement,
        top_k_floor=top_k_floor, max_kept=max_kept, agreed_paths=agreed_paths,
        stem_expansion=stem_expansion, stem_max_parts=stem_max_parts,
        read_max_chars=read_max_chars, segment_chars=segment_chars,
        max_state_chars=max_state_chars, env=env, score_fn=score_fn,
        mcp_factory=mcp_factory, trace=expansion_trace)
    result_list = build_result_list(judgeable, verdict)
    lane_status = ("error" if vec_state["error"] and cat_state["error"]
                   else "partial" if vec_state["error"] or cat_state["error"] else "ok")
    return {"status": lane_status, "query": query, "engine": engine,
            "backend": verdict.get("backend"), "real_engine": verdict.get("real_engine"),
            "parameters": {"threshold": threshold, "relative_margin": relative_margin,
                           "lane_agreement": lane_agreement, "top_k_floor": top_k_floor,
                           "max_kept": max_kept,
                           "extra_terms": list(extra_terms),
                           "stem_completion": stem_completion, "stem_max_parts": stem_max_parts,
                           "stem_expansion": stem_expansion,
                           "peek_heads": peek_heads, "peek_chars": peek_chars, "peek_limit": peek_limit,
                           "vector_top_k": vector_top_k, "vector_threshold": vector_threshold,
                           "doc_budget": doc_budget, "exclude_prefixes": list(exclude_prefixes),
                           "max_state_chars": max_state_chars, "segment_chars": segment_chars,
                           "read_max_chars": read_max_chars},
            "lanes": {"vector": {**vec_trace, "error": vec_state["error"]},
                      "catalog": {**cat_trace, "error": cat_state["error"]}},
            "merge": merge_trace, "reread": reread_trace, "judge": verdict,
            "expansion": expansion_trace,
            "result_list": result_list,
            "kept_doc_paths": [r["doc_path"] for r in result_list],
            "evidence_pack": build_evidence_pack(judgeable, verdict),
            "unscanned": unscanned,
            "seconds": round(time.time() - t0, 1)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Parallel hybrid retrieval: vector lane ∥ catalog lane -> merge/dedup "
                    "-> unified reread -> Laya/Jev judge -> deduplicated result_list")
    parser.add_argument("--query", help="question text (or use --input)")
    parser.add_argument("--input", help="JSON payload file with query + optional parameter overrides")
    parser.add_argument("--output", help="JSON output path; default stdout")
    parser.add_argument("--engine", choices=["laya", "jev"], default="laya")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--relative-margin", type=float, default=DEFAULT_RELATIVE_MARGIN)
    parser.add_argument("--lane-agreement", action="store_true",
                        help="keep lane=both documents at the absolute threshold without "
                             "the relative cut (two agreeing independent signals)")
    parser.add_argument("--top-k-floor", type=int, default=0,
                        help="when real evidence exists, always keep the global top-K docs "
                             "(protects mid-score experiments/appendix parts from the cut)")
    parser.add_argument("--max-kept", type=int, default=DEFAULT_MAX_KEPT,
                        help="cap the kept set to the global top-N (kept_total reports the "
                             "uncapped count; keeps the answer context lean when the "
                             "head-peek scan widens the cut band)")
    parser.add_argument("--extra-terms", default="",
                        help="agent-supplied bilingual Phase-0 keywords merged into the "
                             "description match (space separated)")
    parser.add_argument("--no-stem-completion", action="store_true",
                        help="do not auto-include sibling parts of picked split docs")
    parser.add_argument("--no-stem-expansion", action="store_true",
                        help="do not full-read and judge sibling parts of KEPT split docs "
                             "(post-judge expansion around confirmed evidence)")
    parser.add_argument("--stem-max-parts", type=int, default=6)
    parser.add_argument("--peek-heads", action="store_true",
                        help="head-read every unpicked zero-overlap doc so the engine, "
                             "not description vocabulary, decides its fate")
    parser.add_argument("--peek-chars", type=int, default=700)
    parser.add_argument("--peek-limit", type=int, default=300)
    parser.add_argument("--vector-top-k", type=int, default=DEFAULT_VECTOR_TOP_K)
    parser.add_argument("--vector-threshold", type=float, default=DEFAULT_VECTOR_THRESHOLD)
    parser.add_argument("--doc-budget", type=int, default=DEFAULT_DOC_BUDGET)
    parser.add_argument("--exclude-prefix", action="append", default=[],
                        help="skip shelves whose name starts with this prefix (repeatable)")
    parser.add_argument("--max-state-chars", type=int, default=DEFAULT_MAX_STATE_CHARS)
    parser.add_argument("--segment-chars", type=int, default=DEFAULT_SEGMENT_CHARS)
    parser.add_argument("--read-max-chars", type=int, default=DEFAULT_READ_MAX_CHARS)
    parser.add_argument("--require-real", action="store_true",
                        help="exit 2 unless the selected engine produced real scores")
    args = parser.parse_args(argv)
    payload: dict[str, Any] = {}
    if args.input:
        payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    query = str(args.query or payload.get("query") or "").strip()
    if not query:
        print(json.dumps({"status": "error", "errors": [{"error": "query_missing"}]}))
        return 1
    try:
        result = run_hybrid(
            query, engine=args.engine, threshold=args.threshold,
            relative_margin=args.relative_margin, lane_agreement=args.lane_agreement,
            top_k_floor=args.top_k_floor, max_kept=args.max_kept,
            vector_top_k=args.vector_top_k,
            vector_threshold=args.vector_threshold, doc_budget=args.doc_budget,
            exclude_prefixes=tuple(args.exclude_prefix) or tuple(payload.get("exclude_prefixes") or ()),
            extra_terms=tuple(str(args.extra_terms or payload.get("extra_terms") or "").split()),
            stem_completion=not args.no_stem_completion, stem_max_parts=args.stem_max_parts,
            stem_expansion=not args.no_stem_expansion,
            peek_heads=args.peek_heads, peek_chars=args.peek_chars, peek_limit=args.peek_limit,
            max_state_chars=args.max_state_chars, segment_chars=args.segment_chars,
            read_max_chars=args.read_max_chars)
    except Exception as exc:  # noqa: BLE001 — emit a machine-readable failure
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
