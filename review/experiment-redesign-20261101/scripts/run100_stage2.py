# -*- coding: utf-8 -*-
"""Stage 2 (2026-11-15): title-query retrievability probes + tiered gold run.

Probe : scoped kb_search_vector with a short title query (skill: rewrite short).
Gold  : BQ01-BQ10 tiered path — catalogue route (field->library),
        wide-net vector top-30 @0.35, Laya judge on top candidates,
        gold hit = gold arXiv doc among survivors or id inside evidence pack.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(r"D:\codes\ClaudeGPT\rag_project\rag-knowledge")
OUT = REPO / "review" / "_exp_rerun_20261114"
PDF_DIR = REPO / "benchmark-suite" / "data" / "papers"
STOP = {"a", "an", "the", "of", "for", "in", "on", "and", "with", "to", "via",
        "from", "by", "using", "based", "towards", "toward", "under", "over"}

sys.path.insert(0, str(REPO / "review" / "experiment-redesign-20261101" / "scripts"))
from run100_lib import LIBS  # noqa: E402

CALL = [sys.executable, "-X", "utf8", str(REPO / "scripts" / "mcp_call.py")]


def mcp(tool: str, args: dict, timeout: int = 120, retries: int = 3):
    import os
    import time

    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    last = {"_err": "no attempt"}
    for attempt in range(retries):
        try:
            r = subprocess.run(CALL + [tool, json.dumps(args, ensure_ascii=False)],
                               capture_output=True, timeout=timeout, env=env)
        except subprocess.TimeoutExpired:
            last = {"_err": "timeout"}
            time.sleep(2)
            continue
        out = r.stdout.decode("utf-8", errors="replace").strip()
        try:
            d = json.loads(out, strict=False)
        except Exception:
            names = re.findall(r'"(?:doc_name|doc_path)":\s*"([^"]+)"', out)
            if names:
                d = {"results": [{"doc_path": n} for n in names]}
            else:
                last = {"_err": out[:200] or r.stderr.decode("utf-8", "replace")[:200]}
                time.sleep(2)
                continue
        if isinstance(d, dict) and (d.get("results") or not d.get("_err")):
            return d
        last = d
        time.sleep(2)
    return last


def title_query(stem: str, n_words: int = 8) -> str:
    parts = stem.split("__")
    tail = parts[2] if len(parts) > 2 else stem
    words = [w for w in re.split(r"[-_]+", tail) if w and w.lower() not in STOP]
    return " ".join(words[:n_words])


def probe(p: Path, lib_id: str, arxiv: str, top_k: int = 8):
    q = title_query(p.stem)
    r = mcp("kb_search_vector", {"kb_id": lib_id, "query": q, "top_k": top_k})
    results = r.get("results") or []
    names = []
    for h in results:
        nm = (h.get("doc_name") or h.get("name")
              or (h.get("doc_path") or "").replace("/", "\\").split("\\")[-1])
        names.append(nm)
    if not names:
        names = r.get("_names") or []
    hit = any(arxiv.replace("-", "_") in n or arxiv in n for n in names)
    return hit, q, names[:top_k], r


def main() -> int:
    pmap = json.loads((OUT / "prefix_map.json").read_text(encoding="utf-8"))
    disk = json.loads((OUT / "disk_presence.json").read_text(encoding="utf-8"))

    # ---------- Probe: all 100 ----------
    rows = []
    for i, r in enumerate(disk, 1):
        p = PDF_DIR / r["pdf"]
        lib = pmap.get(r["domain"], "")
        lib_id = LIBS.get(lib, "")
        hit, q, names, raw = probe(p, lib_id, r["arxiv"])
        rows.append({"pdf": r["pdf"], "domain": r["domain"], "arxiv": r["arxiv"],
                     "lib": lib, "query": q, "probe_hit": hit,
                     "top_names": names})
        print(f"[{i:03d}] {'HIT ' if hit else 'MISS'} {r['domain']:22s} {r['arxiv']}",
              flush=True)
    (OUT / "probe2_title.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    miss = [r for r in rows if not r["probe_hit"]]
    print(f"\nPROBE2 SUMMARY hit={len(rows) - len(miss)}/100 miss={len(miss)}",
          flush=True)
    for r in miss:
        print("  MISS", r["domain"], r["arxiv"], "| q:", r["query"][:50], flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
