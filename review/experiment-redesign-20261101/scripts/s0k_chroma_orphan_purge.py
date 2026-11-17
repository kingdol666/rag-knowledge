# -*- coding: utf-8 -*-
"""S0k — chroma 孤儿集合终极清剿（backend 停机态执行）。

删除：① 内容含路由目录卡的集合 ② 不属于任何现存合法 KB 的孤儿集合（含历次
被删库的残留）。保留：34 生产库 + 10 MD语料 + 10 A3（如存在）。
"""
import json
import re
import sys
import time
from pathlib import Path

ROOT = r"D:/codes/ClaudeGPT/rag_project/rag-knowledge"
TREE = Path(ROOT) / "storage" / "tree-file-system"


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    import chromadb
    client = chromadb.PersistentClient(path=ROOT + "/chroma_db")

    # 合法 kb_id 全集 = 树目录所有 .knowledge-base.yml 的 id（唯一事实源）
    valid = {}
    for d in TREE.iterdir():
        if d.is_dir():
            y = d / ".knowledge-base.yml"
            if y.exists():
                m = re.search(r"id:\s*([0-9a-f-]{36})", y.read_text(encoding="utf-8"))
                if m:
                    valid[m.group(1)] = d.name
    print(f"valid KBs: {len(valid)}", flush=True)

    cols = client.list_collections()
    print(f"chroma collections: {len(cols)}", flush=True)
    killed, kept, cards = 0, 0, []
    for c in cols:
        name = c.name
        if not name.startswith("kb_"):
            kept += 1
            continue
        kid = name[3:]
        if kid in valid:
            kept += 1
            continue
        # 孤儿集合：查内容是否目录卡（记录证据）
        try:
            got = c.get(limit=2, include=["documents"])
            docs = " ".join(str(x)[:100] for x in (got.get("documents") or []) if x)
            if "路由目录卡" in docs or "description" in docs and "各知识库描述卡" in docs:
                cards.append(name)
        except Exception:
            pass
        client.delete_collection(name)
        killed += 1
        print(f"[killed] {name} (orphan, not in valid set)", flush=True)
        time.sleep(0.5)
    print(f"killed={killed} kept={kept} card-bearing={len(cards)}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
