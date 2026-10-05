#!/usr/bin/env python3
"""List Novel-PridePrejudice docs + descriptions (read-only probe)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, "D:/codes/ClaudeGPT/rag_project/rag-knowledge/benchmark-suite/scripts")
from lib import McpClient

c = McpClient()
try:
    r = c.call("kb_list", {"lightweight": True}, timeout=120)
    kbs = r.get("kbs") or r.get("data") or r
    if isinstance(kbs, dict):
        kbs = kbs.get("kbs", [])
    print("=== KB LIST ===")
    for kb in kbs:
        print(json.dumps(kb, ensure_ascii=False))

    # find the target KB
    target = None
    for kb in kbs:
        name = str(kb.get("name") or kb.get("title") or "")
        if "PridePrejudice" in name or "Pride" in name:
            target = kb
    print("\n=== TARGET ===")
    print(json.dumps(target, ensure_ascii=False, indent=1))
finally:
    c.close()
