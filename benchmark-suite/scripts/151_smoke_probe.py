#!/usr/bin/env python
"""密索引 smoke 探针（只读）：核对 Corpus-Chunks800 的三条金标探针能否召回。

默认探针来自 106 的 smoke 段（写成硬编码就会像 106 那样「重建成功但退出码 1」；
这里把召回结果逐条打印，便于判断是**索引问题**还是**探针本身**的问题）。

用法:
    python scripts/151_smoke_probe.py
    python scripts/151_smoke_probe.py --query "..." --gold 2203.02155 --top-k 10
"""
from __future__ import annotations

import argparse
import json
import sys

from lib import DATA, McpClient

KB = "Corpus-Chunks800"
DEFAULT_PROBES = [
    ("training language models to follow instructions with human feedback",
     "2203.02155"),
    ("GAN-based downscaling of climate model output", "2409.13934"),
    ("influenza epitope prediction", "q-bio-0408016"),
]


def probe(mc: McpClient, query: str, gold: str, top_k: int) -> dict:
    r = mc.call("kb_search_vector",
                {"query": query, "kb_id": KB, "top_k": top_k}, timeout=300)
    res = r.get("results") or []
    paths = [str((x.get("metadata") or {}).get("doc_path")
                 or x.get("doc_path") or x.get("path") or "") for x in res]
    gold_key = gold.replace("-", "/")
    hit_rank = next((i + 1 for i, p in enumerate(paths)
                     if gold in p or gold_key in p), None)
    return {"query": query[:60], "gold": gold, "top_k": top_k,
            "returned": len(res), "hit_rank": hit_rank,
            "top_paths": [p.split("/")[-1][:70] for p in paths[:5]],
            "scores": [round(float(x.get("score") or 0), 4) for x in res[:5]]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--query")
    ap.add_argument("--gold")
    ap.add_argument("--top-k", type=int, default=5)
    args = ap.parse_args()

    probes = ([(args.query, args.gold)] if args.query and args.gold
              else DEFAULT_PROBES)
    mc = McpClient()
    try:
        stats = mc.call("kb_search_stats", {"kb_id": KB}, timeout=180)
        out = {"kb": KB, "stats": stats, "probes": []}
        for q, g in probes:
            out["probes"].append(probe(mc, q, g, args.top_k))
        probe_ok = all(p["hit_rank"] for p in out["probes"])
        out["verdict"] = ("密索引可用（三条金标探针全召回）" if probe_ok
                          else "有探针未召回 → 逐条看 top_paths 判断是索引还是探针问题")
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 0 if probe_ok else 1
    finally:
        mc.close()


if __name__ == "__main__":
    sys.exit(main())
