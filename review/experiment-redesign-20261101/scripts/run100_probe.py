# -*- coding: utf-8 -*-
"""2026-11-14 rerun: inventory + per-paper retrievability probes (100 papers).

Stage A: inventory five domain libraries -> prefix->library map.
Stage B: per-paper vector probe (arXiv id query, scoped to owning library).
Writes JSON artifacts into review/_exp_rerun_20261114/.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(r"D:\codes\ClaudeGPT\rag_project\rag-knowledge")
OUT = REPO / "review" / "_exp_rerun_20261114"
OUT.mkdir(parents=True, exist_ok=True)
PDF_DIR = REPO / "benchmark-suite" / "data" / "papers"
sys.path.insert(0, str(REPO / "review" / "experiment-redesign-20261101" / "scripts"))
from run100_lib import LIBS  # noqa: E402

CALL = [sys.executable, "-X", "utf8", str(REPO / "scripts" / "mcp_call.py")]


def mcp(tool: str, args: dict, timeout: int = 90):
    import os

    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run(CALL + [tool, json.dumps(args, ensure_ascii=False)],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout, env=env,
                       shell=False)
    out = (r.stdout or "").strip()
    if not out:
        return {"_err": (r.stderr or "empty output")[:300]}
    try:
        return json.loads(out, strict=False)
    except Exception as e:
        return {"_err": f"parse: {e}", "_raw": out[:300]}


def main() -> int:
    # ---- Stage A: inventory ----
    inv = {}
    for name, kb in LIBS.items():
        r = mcp("kb_get_documents", {"kb_id": kb, "lightweight": True,
                                     "page_size": 400}, timeout=120)
        docs = r.get("catalog") or r.get("documents") or []
        inv[name] = {"kb_id": kb, "n": r.get("count", len(docs)),
                     "docs": [{"name": d.get("name") or "",
                               "path": d.get("doc_path") or d.get("path") or "",
                               "description": (d.get("description") or "")}
                              for d in docs]}
        print(f"[inv] {name}: {inv[name]['n']}", flush=True)
    (OUT / "doc_inventory.json").write_text(
        json.dumps(inv, ensure_ascii=False, indent=1), encoding="utf-8")

    from collections import Counter, defaultdict
    pref = defaultdict(Counter)
    name2lib = {}
    for lib, info in inv.items():
        for d in info["docs"]:
            name2lib[d["name"]] = lib
            m = re.match(r"^([a-z-]+)__", d["name"])
            if m:
                pref[m.group(1)][lib] += 1
    pmap = {k: v.most_common(1)[0][0] for k, v in pref.items()}
    (OUT / "prefix_map.json").write_text(
        json.dumps(pmap, ensure_ascii=False, indent=1), encoding="utf-8")

    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    print(f"[inv] pdfs={len(pdfs)} libs_docs={sum(i['n'] for i in inv.values())}",
          flush=True)

    # ---- Stage B: per-paper probe ----
    rows = []
    for i, p in enumerate(pdfs, 1):
        stem = p.stem
        m = re.match(r"^([a-z-]+)__([^_]+)__", stem)
        domain, arxiv = (m.group(1), m.group(2)) if m else ("", stem[:20])
        lib = pmap.get(domain) or name2lib.get(stem + ".md")
        probe_lib = LIBS.get(lib or "", "")
        q = arxiv.replace("-", " ")
        sr = mcp("kb_search_vector",
                 {"kb_id": probe_lib, "query": q, "top_k": 5}, timeout=120)
        hits = sr.get("results") or sr.get("data", {}).get("results") or []
        hit_name = ""
        for h in hits:
            nm = (h.get("doc_name") or h.get("name") or
                  (h.get("doc_path") or "").split("\\")[-1].split("/")[-1])
            if arxiv.replace("-", "_") in nm or arxiv in nm:
                hit_name = nm
                break
        rows.append({"pdf": p.name, "domain": domain, "arxiv": arxiv,
                     "lib": lib, "probe_lib_id": probe_lib,
                     "probe_hit": bool(hit_name), "hit_doc": hit_name,
                     "n_results": len(hits)})
        print(f"[{i:03d}/100] {'HIT ' if hit_name else 'MISS'} {domain:22s} {arxiv}",
              flush=True)
    (OUT / "probe_100.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    misses = [r for r in rows if not r["probe_hit"]]
    print(f"\nPROBE SUMMARY: hit={100 - len(misses)}/100 miss={len(misses)}",
          flush=True)
    for r in misses:
        print("  MISS", r["domain"], r["arxiv"], r["pdf"], flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
