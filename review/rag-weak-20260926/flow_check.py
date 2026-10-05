#!/usr/bin/env python3
"""Flow-compliance checker: parse chat transcripts for the tool sequence each
mode actually used, and verify it matches the mode's skill contract."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

PATTERNS = {
    "kb_search_vector": r"kb_search_vector",
    "kb_doc_read": r"kb_doc_read",
    "kb_list": r'"name":\s*"kb_list"|kb_list\(',
    "kb_get_documents": r"kb_get_documents",
    "jev_filter_cli": r"jev_filter\.py",
    "vector_jev_cli": r"vector_jev_search\.py",
    "hybrid_cli": r"hybrid_search\.py",
    "bash_tool": r'"name":\s*"Bash"',
    "read_tool": r'"name":\s*"Read"',
    "mcp_prefix": r"mcp__kb-mcp__",
}


def scan(tag: str) -> dict:
    path = HERE / f"{tag}.transcript.txt"
    if not path.exists():
        return {"tag": tag, "exists": False}
    text = path.read_text(encoding="utf-8", errors="replace")
    out: dict = {"tag": tag, "exists": True, "chars": len(text)}
    for name, pat in PATTERNS.items():
        out[name] = len(re.findall(pat, text))
    # rubric leak check: did the agent run an old-style 0-8 rubric gate?
    out["rubric_mentions"] = len(re.findall(r"0-8|0–8", text))
    # real-engine evidence
    m = re.findall(r'"real_engine":\s*(true|false)', text)
    out["real_engine_flags"] = {"true": m.count("true"), "false": m.count("false")}
    return out


if __name__ == "__main__":
    for tag in (sys.argv[1:] or ["rw-A", "rw-B", "rw-C"]):
        print(json.dumps(scan(tag), ensure_ascii=False, indent=1))
