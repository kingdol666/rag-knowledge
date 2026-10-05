#!/usr/bin/env python3
"""Inspect raw kb_doc_read response for part 2 and part 3."""
import json
import sys

sys.path.insert(0, "D:/codes/ClaudeGPT/rag_project/rag-knowledge/benchmark-suite/scripts")
from lib import McpClient

KB = "b4c48237-6937-440a-9696-cc1e66bed5c1"
c = McpClient()
try:
    for name in ["pride_and_prejudice (part 2 of 26).md",
                 "pride_and_prejudice (part 3 of 26).md"]:
        r = c.call("kb_doc_read", {"kb_id": KB, "doc_path": "Novel-PridePrejudice\\" + name,
                                   "max_chars": 40000}, timeout=180)
        print("=" * 30, name)
        print("KEYS:", list(r.keys()))
        for k, v in r.items():
            if isinstance(v, str):
                print(f"  {k}: len={len(v)} :: {v[:200]!r}")
            else:
                print(f"  {k}: {v!r}")
        # full text
        txt = r.get("content") or r.get("text") or r.get("markdown") or ""
        print("--- TEXT len", len(txt))
        print(txt[:1200])
        print("...TAIL...")
        print(txt[-800:])
finally:
    c.close()
