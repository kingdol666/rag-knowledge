#!/usr/bin/env python3
"""修复 EN 库 50 篇缺失文档: 从 checkpoint 移除使其重走入库(409 幂等)."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bench_http import get_json  # noqa: E402
import os

WEB = os.environ.get("RAG_BENCH_WEB_URL", "http://localhost:6790").rstrip("/")
TOKEN = os.environ.get("RAG_BENCH_TOKEN", "")
KB = "KB-CrossLang-EN"
CKPT = Path(__file__).resolve().parent.parent / "results" / "benchmark" / f"ingest-checkpoint-{KB}.json"
SPLIT = Path(__file__).resolve().parent.parent / "data" / "benchmarks" / "kb_split" / f"pages_{KB}.jsonl"


def main() -> int:
    catalog = get_json(WEB, "/api/kb/catalog", token=TOKEN, timeout=120)
    kb_id = next(k["kbId"] for k in catalog["knowledgeBases"] if k["name"] == KB)
    docs = get_json(WEB, f"/api/kb/documents?kb_id={kb_id}", token=TOKEN, timeout=180)
    listed = set()
    for d in docs.get("documents") or []:
        n = str(d.get("name"))
        b = n[:-3] if n.endswith(".md") else n
        listed.add(re.sub(r" \(\d+\)$", "", re.sub(r" \(part \d+ of \d+\)$", "", b)))
    pages = [json.loads(l) for l in SPLIT.open(encoding="utf-8")]

    def san(t: str) -> str:
        s = re.sub(r'[\\/:*?"<>|]', "_", t).strip().rstrip(".")
        return s or "untitled"

    missing = [p["title"] for p in pages if san(p["title"]) not in listed]
    ck = json.loads(CKPT.read_text(encoding="utf-8"))
    for t in missing:
        ck.pop(t, None)
    CKPT.write_text(json.dumps(ck, ensure_ascii=False), encoding="utf-8")
    print(f"removed {len(missing)} stale checkpoint entries -> will re-ingest")
    return 0


if __name__ == "__main__":
    sys.exit(main())
