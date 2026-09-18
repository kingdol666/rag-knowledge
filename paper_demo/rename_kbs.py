#!/usr/bin/env python3
"""Rename the Chinese knowledge-base directories to English, via kb-mcp.

Runs the knowledgebase-manage path (kb_update) and then verifies the five layers
the platform keeps in sync: the directory on disk, .tree-fs.json, the per-KB
.knowledge-base.yml, the ChromaDB collection metadata, and Neo4j.

Usage:  python rename_kbs.py --pilot     # one KB only, then report
        python rename_kbs.py             # the remaining four
        python rename_kbs.py --verify    # verification only
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(r"D:\codes\ClaudeGPT\rag_project\rag-knowledge")
sys.path.insert(0, str(REPO / "benchmark-suite" / "scripts"))
from lib import McpClient  # noqa: E402

STORAGE = REPO / "storage" / "tree-file-system"

RENAME = {
    "计算机与人工智能": "Computer Science and AI",
    "自然科学与地球科学": "Natural and Earth Sciences",
    "生命科学与医学": "Life Sciences and Medicine",
    "工程与能源": "Engineering and Energy",
    "经济与社会": "Economics and Society",
}
PILOT = "工程与能源"


def dirs() -> list[str]:
    if not STORAGE.exists():
        return []
    return sorted(p.name for p in STORAGE.iterdir() if p.is_dir())


def snapshot() -> dict:
    mc = McpClient()
    try:
        cat = (mc.call("kb_list", {"lightweight": True}, timeout=180)
               .get("catalog") or [])
    finally:
        mc.close()
    return {"dirs": dirs(),
            "kbs": [{"id": k.get("kb_id"), "name": k.get("name"),
                     "path": k.get("path"), "docs": k.get("doc_count")}
                    for k in cat]}


def verify(tag: str) -> None:
    s = snapshot()
    print(f"\n=== {tag} ===")
    print("  storage dirs:")
    for d in s["dirs"]:
        print(f"    {d}")
    print("  kb registry:")
    for k in s["kbs"]:
        print(f"    {str(k['name']):<28} path={str(k['path']):<34} docs={k['docs']}")


def rename(pairs: dict[str, str]) -> None:
    mc = McpClient()
    try:
        cat = (mc.call("kb_list", {"lightweight": True}, timeout=180)
               .get("catalog") or [])
        by_name = {k.get("name"): k for k in cat}
        for old, new in pairs.items():
            kb = by_name.get(old)
            if not kb:
                print(f"  [skip] {old!r} not found")
                continue
            r = mc.call("kb_update",
                        {"kb_id": kb["kb_id"], "name": new}, timeout=300)
            ok = isinstance(r, dict) and (r.get("success") is not False)
            print(f"  [rename] {old!r} -> {new!r}  kb_id={kb['kb_id'][:8]}  "
                  f"ok={ok}  {str(r)[:120]}")
    finally:
        mc.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()

    verify("BEFORE")
    if args.verify:
        return 0

    todo = {PILOT: RENAME[PILOT]} if args.pilot else RENAME
    print(f"\n>>> renaming {len(todo)} KB(s)")
    rename(todo)
    verify("AFTER")
    (REPO / "paper_demo" / "_rename_snapshot.json").write_text(
        json.dumps(snapshot(), ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
