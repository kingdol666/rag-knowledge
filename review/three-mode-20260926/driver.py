#!/usr/bin/env python3
"""Three-mode retrieval test driver (2026-09-26).

Mechanics only: every MCP call, catalog walk, segmentation and the real-Laya
judgment are scripted here; the 0-8 content rubric and the final answer stay
with the agent, per the skills' script/agent division of labor.

  mode A  QDCVR Phase 1: kb_search_vector -> hard threshold -> doc dedup
          -> kb_doc_read head (+ one 2/3 continuation probe when truncated)
  mode B  librarian L0-L5: kb_list -> agent shelf labels (arg) -> every doc
          description -> L3 trust -> budgeted reads (overlap full / untrusted
          head / stem completion) -> complete_recall.run_manifest (real Laya)
          -> doc-level retain_docs (shared policy)
Outputs land beside this script as JSON for the agent to judge and answer.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "benchmark-suite" / "scripts"))
sys.path.insert(0, str(REPO / ".claude" / "skills" / "knowledgebase-librarian" / "scripts"))

from lib import McpClient  # noqa: E402
import complete_recall as cr  # noqa: E402

OUT = Path(__file__).resolve().parent


def mode_a(query: str, out: str) -> None:
    t0 = time.time()
    mc = McpClient()
    trace: dict = {"mcp_calls": 0}
    try:
        raw = mc.call("kb_search_vector",
                      {"query": query, "kb_id": "", "top_k": 10,
                       "score_threshold": 0.35, "balance_kbs": True}, timeout=300)
        trace["mcp_calls"] += 1
        hits = raw.get("results") or []
        trace["raw_hits"] = len(hits)
        best: dict = {}
        for h in hits:
            s = h.get("score")
            if not isinstance(s, (int, float)) or isinstance(s, bool) or float(s) < 0.35:
                continue
            key = (str(h.get("kb_id")), str(h.get("doc_path")).replace("\\", "/"))
            if key not in best or float(s) > float(best[key]["score"]):
                best[key] = {**h, "kb_id": key[0], "doc_path": key[1], "score": float(s)}
        cands = sorted(best.values(), key=lambda r: -r["score"])[:5]
        trace["dedup_docs"] = len(cands)
        for c in cands:
            r = mc.call("kb_doc_read", {"kb_id": c["kb_id"], "doc_path": c["doc_path"],
                                        "max_chars": 3000}, timeout=180)
            trace["mcp_calls"] += 1
            c["read_head"] = str(r.get("content") or "")
            c["truncated"] = bool(r.get("truncated"))
            c["totalLines"] = r.get("totalLines")
            if c["truncated"] and c.get("totalLines"):
                off = max(1, int(int(c["totalLines"]) * 2 / 3))
                r2 = mc.call("kb_doc_read", {"kb_id": c["kb_id"], "doc_path": c["doc_path"],
                                             "offset": off, "limit": 100, "max_chars": 3000},
                             timeout=180)
                trace["mcp_calls"] += 1
                c["read_mid"] = str(r2.get("content") or "")
    finally:
        mc.close()
    trace["seconds"] = round(time.time() - t0, 1)
    (OUT / out).write_text(json.dumps({"query": query, "trace": trace, "candidates": cands},
                                      ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"mode": "A", "out": out, **trace}, ensure_ascii=False))


def mode_b(query: str, keep_shelves: list[str], budget: int, head_budget: int, out: str) -> None:
    t0 = time.time()
    mc = McpClient()
    trace: dict = {"mcp_calls": 0}
    try:
        kbs = (mc.call("kb_list", {"lightweight": True}, timeout=120).get("catalog") or [])
        trace["l0_kbs"] = len(kbs)
        shelves = [k for k in kbs if str(k.get("name") or "") in set(keep_shelves)]
        docs_all: list[dict] = []
        for k in shelves:
            kb_id = k.get("kb_id") or k.get("name")
            rows = (mc.call("kb_get_documents", {"lightweight": True, "kb_id": kb_id},
                            timeout=180).get("catalog") or [])
            trace["mcp_calls"] += 1
            for d in rows:
                docs_all.append({**d, "kb_id": kb_id, "kb_name": k.get("name")})
        trace["l1_kept_shelves"] = keep_shelves
        trace["l2_docs"] = len(docs_all)

        qterms = cr._terms(query)
        sibs: dict[str, list[str]] = {}
        for d in docs_all:
            sibs.setdefault(str(d.get("kb_id")), []).append(str(d.get("description") or ""))
        for d in docs_all:
            blob = f"{d.get('name', '')} {d.get('description', '')}"
            d["overlap"] = len(qterms & cr._terms(blob)) if qterms else 0
            trusted, reasons = cr._metadata_trust(str(d.get("description") or ""),
                                                  sibs[str(d.get("kb_id"))])
            d["description_trust"] = "trusted" if trusted else "untrusted"
            d["trust_reasons"] = reasons
        trace["l3_untrusted"] = sum(1 for d in docs_all if d["description_trust"] == "untrusted")

        picked_keys: set = set()
        manifest_docs: list[dict] = []

        def full_read(d: dict) -> None:
            key = (str(d.get("kb_id")), str(d.get("doc_path")))
            if key in picked_keys or len(manifest_docs) >= budget:
                return
            picked_keys.add(key)
            r = mc.call("kb_doc_read", {"kb_id": d["kb_id"], "doc_path": d["doc_path"],
                                        "max_chars": 20000}, timeout=180)
            trace["mcp_calls"] += 1
            manifest_docs.append({**d, "content": str(r.get("content") or ""),
                                  "truncated": bool(r.get("truncated")), "read_kind": "full"})

        def head_read(d: dict) -> None:
            key = (str(d.get("kb_id")), str(d.get("doc_path")))
            if key in picked_keys or len(manifest_docs) >= budget + head_budget:
                return
            picked_keys.add(key)
            r = mc.call("kb_doc_read", {"kb_id": d["kb_id"], "doc_path": d["doc_path"],
                                        "max_chars": 600}, timeout=120)
            trace["mcp_calls"] += 1
            manifest_docs.append({**d, "content": str(r.get("content") or ""),
                                  "truncated": bool(r.get("truncated")), "read_kind": "trust_head"})

        import re as _re

        def stem_of(p: str):
            m = _re.search(r"^(.*) \(part \d+ of \d+\)", str(p or "").replace("\\", "/"))
            return m.group(1) if m else None

        overlaps = sorted((d for d in docs_all if d["overlap"] > 0), key=lambda x: -x["overlap"])
        trace["l4_overlap_docs"] = len(overlaps)
        for d in overlaps:
            if len(manifest_docs) >= budget:
                break
            full_read(d)
        # stem completion: a picked part brings its siblings (bounded by budget)
        stems_picked = {stem_of(d["doc_path"]) for d in manifest_docs} - {None}
        for d in docs_all:
            if len(manifest_docs) >= budget:
                break
            if stem_of(d.get("doc_path")) in stems_picked:
                full_read(d)
        # L3: untrusted descriptions must be resolved by a content head read
        for d in docs_all:
            if d["description_trust"] == "untrusted":
                head_read(d)
        trace["l4_docs_read"] = sum(1 for d in manifest_docs if d["read_kind"] == "full")
        trace["l4_trust_heads"] = sum(1 for d in manifest_docs if d["read_kind"] == "trust_head")
        read_keys = picked_keys
        trace["unscanned"] = [
            {"kb_id": d["kb_id"], "doc_path": d["doc_path"],
             "reason": "budget" if d["overlap"] > 0 or d["description_trust"] == "trusted"
                       else "budget_after_trust_heads"}
            for d in docs_all
            if (str(d.get("kb_id")), str(d.get("doc_path"))) not in read_keys]
        trace["unscanned_count"] = len(trace["unscanned"])
    finally:
        mc.close()

    manifest = {"query": query, "engine": "laya", "threshold": 0.5,
                "max_segment_chars": 3000, "max_evidence_chars": 40_000,
                "documents": manifest_docs}
    run = cr.run_manifest(manifest)  # real Laya, fail-closed
    jev = run["jev"]
    # NEW contract (2026-09-26): the engine verdict is final. Every yes-scored
    # survivor is evidence — no retain_docs cut, no top-K floor, no rubric.
    result = {"query": query, "seconds": round(time.time() - t0, 1), "trace": trace,
              "judge": {"status": jev.get("status"), "engine": jev.get("engine"),
                        "backend": jev.get("backend"), "real_engine": jev.get("real_engine"),
                        "criterion": jev.get("criterion"), "threshold": jev.get("threshold"),
                        "candidates": jev.get("candidate_count"),
                        "scored": jev.get("scored_count"),
                        "survivors_kept": len(jev.get("survivors") or []),
                        "errors": (jev.get("errors") or [])[:5]},
              "docs_read": [{"kb_id": d["kb_id"], "doc_path": d["doc_path"],
                             "read_kind": d["read_kind"], "overlap": d["overlap"],
                             "trust": d["description_trust"]} for d in manifest_docs],
              "evidence_pack": run.get("evidence_pack", ""),
              "survivors": [{"doc_path": s.get("doc_path"), "part_index": s.get("part_index"),
                             "section_path": s.get("section_path"),
                             "start_line": s.get("start_line"), "end_line": s.get("end_line"),
                             "score": s.get("score"), "text": str(s.get("text") or "")}
                            for s in (jev.get("survivors") or [])]}
    dest = Path(out)
    dest = dest if dest.is_absolute() else OUT / dest.name  # --out lands beside this script
    dest.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"mode": "B", "out": dest.name, "seconds": result["seconds"],
                      "judge": result["judge"]}, ensure_ascii=False)[:600])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="mode", required=True)
    a = sub.add_parser("a")
    a.add_argument("--query", required=True)
    a.add_argument("--out", required=True)
    b = sub.add_parser("b")
    b.add_argument("--query", required=True)
    b.add_argument("--keep", required=True, help="comma-separated agent-labeled shelves (L1)")
    b.add_argument("--budget", type=int, default=35)
    b.add_argument("--head-budget", type=int, default=20)
    b.add_argument("--out", required=True)
    args = ap.parse_args()
    if args.mode == "a":
        mode_a(args.query, args.out)
    else:
        mode_b(args.query, [s.strip() for s in args.keep.split(",") if s.strip()],
               args.budget, args.head_budget, args.out)
