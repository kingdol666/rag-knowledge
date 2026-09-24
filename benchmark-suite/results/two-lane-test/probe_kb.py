#!/usr/bin/env python3
"""Probe: list KBs, find Novel-PridePrejudice, list its documents (read-only)."""
import json
import sys

sys.path.insert(0, "D:/codes/ClaudeGPT/rag_project/rag-knowledge/benchmark-suite/scripts")
from lib import McpClient  # noqa: E402

OUT = "D:/codes/ClaudeGPT/rag_project/rag-knowledge/benchmark-suite/results/two-lane-test"


def main():
    c = McpClient()
    try:
        r = c.call("kb_list", {"lightweight": True}, timeout=120)
        print("=== kb_list ===")
        print(json.dumps(r, ensure_ascii=False, indent=1)[:4000])
        kbs = r.get("kbs") or r.get("data") or r.get("knowledge_bases") or []
        if isinstance(r, dict) and not kbs:
            # maybe nested
            for k, v in r.items():
                if isinstance(v, list):
                    kbs = v
                    break
        target = None
        for kb in kbs:
            if not isinstance(kb, dict):
                continue
            name = str(kb.get("name", ""))
            if "pride" in name.lower() or "novel" in name.lower():
                target = kb
                print("FOUND target:", json.dumps(kb, ensure_ascii=False))
        if target:
            kb_id = target.get("kb_id") or target.get("id")
            d = c.call("kb_get_documents", {"kb_id": kb_id, "lightweight": True},
                       timeout=120)
            print("=== kb_get_documents ===")
            print(json.dumps(d, ensure_ascii=False, indent=1)[:8000])
    finally:
        c.close()


if __name__ == "__main__":
    main()
