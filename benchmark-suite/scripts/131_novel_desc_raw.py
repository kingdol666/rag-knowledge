#!/usr/bin/env python3
"""Raw probe of kb_list + fs_get_tree (read-only)."""
import json
import sys

sys.path.insert(0, "D:/codes/ClaudeGPT/rag_project/rag-knowledge/benchmark-suite/scripts")
from lib import McpClient

c = McpClient()
try:
    r = c.call("kb_list", {"lightweight": True}, timeout=120)
    print("=== kb_list RAW ===")
    print(json.dumps(r, ensure_ascii=False)[:3000])
    print()
    t = c.call("fs_get_tree", {"max_depth": 3}, timeout=120)
    print("=== fs_get_tree RAW ===")
    print(json.dumps(t, ensure_ascii=False)[:5000])
finally:
    c.close()
