#!/usr/bin/env python3
"""Novel long-text test — ingest driver (real kb-mcp stdio calls)."""
from __future__ import annotations
import json, sys, time
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent.parent  # benchmark-suite
sys.path.insert(0, str(SUITE / "scripts"))
from lib import McpClient  # noqa: E402

OUT = Path(__file__).resolve().parent
PARTS_DIR = SUITE / "data" / "novels" / "parts"


def jprint(label, obj, limit=1500):
    s = json.dumps(obj, ensure_ascii=False)
    print(f"\n### {label}\n{s[:limit]}" + ("…" if len(s) > limit else ""))


def main():
    c = McpClient()
    try:
        st = c.call("kb_project_status", {"scope": "runtime"}, timeout=120)
        jprint("kb_project_status", st)

        lst = c.call("kb_list", {}, timeout=120)
        jprint("kb_list (before)", lst)

        # create the KB
        desc = ("Novel-PridePrejudice 知识库：《Pride and Prejudice》(Jane Austen, "
                "Project Gutenberg #1342) 英文小说全文，用于长文本检索测试。"
                "领域：文学/古典小说；语言 en。全书按 30000 字符窗口拆为 26 个 part。")
        created = c.call("kb_create", {
            "name": "Novel-PridePrejudice",
            "description": desc,
            "parent_id": "",
        }, timeout=180)
        jprint("kb_create", created)

        lst2 = c.call("kb_list", {}, timeout=120)
        jprint("kb_list (after)", lst2, limit=3000)
    finally:
        c.close()


if __name__ == "__main__":
    main()
