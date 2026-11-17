# -*- coding: utf-8 -*-
"""Stage 5: definitive full-100 title-query probe (settled index, fixed fields)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(r"D:\codes\ClaudeGPT\rag_project\rag-knowledge")
OUT = REPO / "review" / "_exp_rerun_20261114"
PDF_DIR = REPO / "benchmark-suite" / "data" / "papers"

sys.path.insert(0, str(REPO / "review" / "experiment-redesign-20261101" / "scripts"))
from run100_stage2 import mcp, title_query  # noqa: E402


def gold_names(hits) -> list[str]:
    names = []
    for h in hits:
        dp = h.get("doc_path") or ""
        nm = h.get("doc_name") or h.get("name") or dp.replace("\\", "/").split("/")[-1]
        if nm:
            names.append(nm)
    return names


def probe(arxiv: str, lib_id: str, q: str, top_k: int):
    r = mcp("kb_search_vector", {"kb_id": lib_id, "query": q, "top_k": top_k})
    hits = r.get("results") or []
    names = gold_names(hits)
    hit = any(arxiv.replace("-", "_") in n or arxiv in n for n in names)
    return hit, names, hits


def main() -> int:
    disk = json.loads((OUT / "disk_presence.json").read_text(encoding="utf-8"))
    pmap = json.loads((OUT / "prefix_map.json").read_text(encoding="utf-8"))
    rows = []
    for i, r in enumerate(disk, 1):
        p = PDF_DIR / r["pdf"]
        lib = pmap.get(r["domain"], "")
        from run100_lib import LIBS
        lib_id = LIBS.get(lib, "")
        q = title_query(p.stem)
        hit, names, hits = probe(r["arxiv"], lib_id, q, 8)
        rank = 0
        for j, h in enumerate(hits, 1):
            nm = (h.get("doc_path") or "").replace("\\", "/").split("/")[-1]
            if r["arxiv"].replace("-", "_") in nm or r["arxiv"] in nm:
                rank = j
                break
        rows.append({"pdf": r["pdf"], "domain": r["domain"], "arxiv": r["arxiv"],
                     "lib": lib, "query": q, "probe_hit": hit, "best_rank": rank,
                     "top_score": hits[0].get("score") if hits else None,
                     "names": names[:5]})
        print(f"[{i:03d}] {'HIT ' if hit else 'MISS'} rank={rank} "
              f"{r['domain']:22s} {r['arxiv']}", flush=True)
    (OUT / "probe5_final.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    miss = [r for r in rows if not r["probe_hit"]]
    print(f"\nSTAGE5 SUMMARY: hit={len(rows)-len(miss)}/100 miss={len(miss)}",
          flush=True)
    for mrow in miss:
        print("  MISS", mrow["domain"], mrow["arxiv"], flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
