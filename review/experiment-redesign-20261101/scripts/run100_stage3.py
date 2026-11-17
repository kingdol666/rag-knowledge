# -*- coding: utf-8 -*-
"""Stage 3: re-probe the post-reindex misses (title query, top_k 8 then 15)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(r"D:\codes\ClaudeGPT\rag_project\rag-knowledge")
OUT = REPO / "review" / "_exp_rerun_20261114"
PDF_DIR = REPO / "benchmark-suite" / "data" / "papers"

sys.path.insert(0, str(REPO / "review" / "experiment-redesign-20261101" / "scripts"))
from run100_lib import LIBS  # noqa: E402
from run100_stage2 import mcp, title_query  # noqa: E402


def probe_once(arxiv: str, lib_id: str, q: str, top_k: int):
    r = mcp("kb_search_vector", {"kb_id": lib_id, "query": q, "top_k": top_k})
    names = []
    for h in r.get("results") or []:
        nm = (h.get("doc_name") or h.get("name")
              or (h.get("doc_path") or "").replace("/", "\\").split("\\")[-1])
        names.append(nm)
    if not names:
        names = r.get("_names") or []
    hit = any(arxiv.replace("-", "_") in n or arxiv in n for n in names)
    return hit, names


def main() -> int:
    rows = json.loads((OUT / "probe2_title.json").read_text(encoding="utf-8"))
    miss = [r for r in rows if not r["probe_hit"]]
    print(f"re-probing {len(miss)} misses after force reindex", flush=True)
    fixed, still = [], []
    for i, r in enumerate(miss, 1):
        p = PDF_DIR / r["pdf"]
        lib_id = LIBS.get(r["lib"], "")
        q = r["query"]
        hit, names = probe_once(r["arxiv"], lib_id, q, 8)
        used_k = 8
        if not hit:
            hit, names = probe_once(r["arxiv"], lib_id, q, 15)
            used_k = 15
        entry = dict(r)
        entry.update({"reprobe_hit": hit, "used_top_k": used_k,
                      "reprobe_names": names[:6]})
        (fixed if hit else still).append(entry)
        print(f"[{i:02d}] {'FIXED' if hit else 'STILL'} {r['domain']:22s} {r['arxiv']}",
              flush=True)
    (OUT / "probe3_reindexed.json").write_text(
        json.dumps({"fixed": fixed, "still": still}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    print(f"\nSTAGE3 SUMMARY: fixed={len(fixed)} still={len(still)}", flush=True)
    for s in still:
        print("  STILL MISS:", s["domain"], s["arxiv"], s["pdf"][:60], flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
