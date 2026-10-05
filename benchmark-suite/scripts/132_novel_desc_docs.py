#!/usr/bin/env python3
"""List tools + get documents of Novel-PridePrejudice."""
import json
import sys

sys.path.insert(0, "D:/codes/ClaudeGPT/rag_project/rag-knowledge/benchmark-suite/scripts")
from lib import McpClient

KB = "b4c48237-6937-440a-9696-cc1e66bed5c1"

c = McpClient()
try:
    r = c.call("kb_get_documents", {"kb_id": KB, "lightweight": True}, timeout=120)
    print("=== kb_get_documents RAW (truncated) ===")
    print(json.dumps(r, ensure_ascii=False)[:2000])
    # save full
    with open("D:/codes/ClaudeGPT/rag_project/rag-knowledge/benchmark-suite/results/_novel_docs_raw.json", "w", encoding="utf-8") as f:
        json.dump(r, f, ensure_ascii=False, indent=1)
    print("\nsaved to results/_novel_docs_raw.json")
finally:
    c.close()
