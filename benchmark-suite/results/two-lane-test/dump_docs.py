#!/usr/bin/env python3
"""Dump the full Novel-PridePrejudice document catalog to JSON (read-only)."""
import json
import sys

sys.path.insert(0, "D:/codes/ClaudeGPT/rag_project/rag-knowledge/benchmark-suite/scripts")
from lib import McpClient  # noqa: E402

OUT = "D:/codes/ClaudeGPT/rag_project/rag-knowledge/benchmark-suite/results/two-lane-test"
KB = "b4c48237-6937-440a-9696-cc1e66bed5c1"


def main():
    c = McpClient()
    try:
        d = c.call("kb_get_documents", {"kb_id": KB, "lightweight": True}, timeout=120)
        with open(f"{OUT}/kb_documents.json", "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        cat = d.get("catalog", [])
        print(f"count={len(cat)}")
        for doc in cat:
            print(f"- {doc.get('name')}")
            print(f"    DESC: {str(doc.get('description'))[:200]}")
    finally:
        c.close()


if __name__ == "__main__":
    main()
