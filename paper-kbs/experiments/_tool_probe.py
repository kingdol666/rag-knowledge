#!/usr/bin/env python3
"""One-off probe: list the live kb-mcp tool surface (SSE, 127.0.0.1:8000).

Answers two questions for the manuscript:
  (a) how many tools the deployed server registers (the paper claims 95),
  (b) whether kb_hybrid_search is one of them (it is absent from the
      checkout's kb-mcp/server.py source).
Read-only: tools/list only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kbcommon import McpClient


def main() -> int:
    mc = McpClient()
    r = mc._rpc("tools/list", {}, timeout=60) or {}
    tools = r.get("tools") or []
    names = sorted(t["name"] for t in tools)
    print("tool_count", len(names))
    for pat in ("hybrid", "laya", "search", "judge", "graph"):
        hits = [n for n in names if pat in n]
        print(f"[{pat}] {len(hits)}: {', '.join(hits)}")
    print("has_kb_hybrid_search", "kb_hybrid_search" in names)
    print("all_names_json", json.dumps(names))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
