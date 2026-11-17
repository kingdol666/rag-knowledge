# -*- coding: utf-8 -*-
"""Stage 6c: retry the four judge-unparsed questions with raw-text metrics."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

REPO = Path(r"D:\codes\ClaudeGPT\rag_project\rag-knowledge")
STORAGE = REPO / "storage" / "tree-file-system"
OUT = REPO / "review" / "_exp_rerun_20261114"
QA = REPO / "benchmark-suite" / "data" / "papers" / "qa_questions.json"
CALL = [sys.executable, "-X", "utf8", str(REPO / "scripts" / "mcp_call.py")]
MAX_CHARS = 40000

sys.path.insert(0, str(REPO / "review" / "experiment-redesign-20261101" / "scripts"))
from run100_lib import LIBS  # noqa: E402


def raw_call(tool: str, args: dict, timeout: int = 420) -> str:
    """Call via scripts/mcp_call.py (now SSE-accumulation-fixed) for raw text."""
    import subprocess

    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run(CALL + [tool, json.dumps(args, ensure_ascii=False),
                               "--max-chars", "200000"],
                       capture_output=True, timeout=timeout, env=env)
    return r.stdout.decode("utf-8", errors="replace")


def read_head(lib: str, key: str) -> str:
    cands = sorted((STORAGE / lib).glob(f"**/*{key}*"))
    if not cands:
        return ""
    return cands[0].read_text(encoding="utf-8", errors="replace")[:MAX_CHARS]


def judge_raw(query: str, docs: list, tries: int = 3) -> str:
    last = ""
    for t in range(tries):
        raw = raw_call("kb_laya_judge",
                       {"query": query, "documents": docs}, timeout=420)
        if '"real_engine"' in raw and '"candidate_count"' in raw:
            return raw
        last = raw
        time.sleep(3)
    return last


def main() -> int:
    pmap = json.loads((OUT / "prefix_map.json").read_text(encoding="utf-8"))
    qa = json.loads(QA.read_text(encoding="utf-8"))
    items = qa if isinstance(qa, list) else qa.get("questions") or []
    targets = {q["qid"] for q in items}
    results = []
    for q in items:
        if q["qid"] not in targets:
            continue
        arxiv, lib = q["arxiv_id"], pmap.get(q["field"], "")
        if not lib:
            results.append({"qid": q["qid"], "error": f"no library for {q['field']}"})
            print(f"{q['qid']}: NO LIBRARY for field {q['field']}", flush=True)
            continue
        lib_id = LIBS.get(lib, "")
        query = q["question"]
        sr_raw = raw_call("kb_search_vector",
                          {"kb_id": lib_id, "query": query, "top_k": 30},
                          timeout=180)
        sr = json.loads(sr_raw, strict=False)
        hits = sr.get("results") or []
        refs, seen = [], set()
        for h in hits:
            tail = (h.get("doc_path") or "").replace("\\", "/").split("/")[-1]
            key = tail.split(" (part")[0]
            if key and key not in seen:
                seen.add(key)
                refs.append(tail)
        vrank = 0
        seen2 = []
        for h in hits:
            tail = (h.get("doc_path") or "").replace("\\", "/").split("/")[-1]
            key = tail.split(" (part")[0]
            if key and key not in seen2:
                seen2.append(key)
        for j, key in enumerate(seen2, 1):
            if arxiv.replace("-", "_") in key or arxiv in key:
                vrank = j
                break
        docs = []
        for tail in refs[:3]:
            base = tail.split(" (part")[0].removesuffix(".md")
            content = read_head(lib, base.split("__", 2)[-1][:40]) or \
                read_head(lib, arxiv.replace("-", "_"))
            docs.append({"kb_id": lib_id, "doc_path": f"{lib}/{tail}",
                         "content": content[:8000]})
        raw = judge_raw(query, docs)
        m = re.search(r'"real_engine":\s*(true|false)', raw)
        real = bool(m and m.group(1) == "true")
        cand = re.search(r'"candidate_count":\s*(\d+)', raw)
        surv = re.search(r'"survivor_count":\s*(\d+)', raw)
        hit = (arxiv.replace("-", "_") in raw) or (arxiv in raw)
        results.append({"qid": q["qid"], "arxiv": arxiv, "lib": lib,
                        "query": query[:50],
                        "raw_len": len(raw), "real_engine": real,
                        "vector_gold_rank": vrank,
                        "candidate_count": int(cand.group(1)) if cand else None,
                        "survivor_count": int(surv.group(1)) if surv else None,
                        "gold_in_judge_output": bool(hit),
                        "raw_head": raw[:200]})
        print(f"{q['qid']}: vrank={vrank} real={real} cand={cand.group(1) if cand else '?'} "
              f"surv={surv.group(1) if surv else '?'} hit={hit}", flush=True)
    (OUT / "gold_bq_retry.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    ok = sum(1 for r in results if r.get("gold_in_judge_output"))
    vh1 = sum(1 for r in results if r.get("vector_gold_rank") == 1)
    vh5 = sum(1 for r in results if 0 < r.get("vector_gold_rank", 0) <= 5)
    real_n = sum(1 for r in results if r.get("real_engine"))
    print(f"FINAL SUMMARY: vector rank1={vh1}/10 Hit@5={vh5}/10 | "
          f"judge real={real_n}/10 | tiered gold-hit={ok}/10", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
