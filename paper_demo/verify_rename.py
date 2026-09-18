#!/usr/bin/env python3
"""Post-rename consistency check across the five layers."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(r"D:\codes\ClaudeGPT\rag_project\rag-knowledge")
sys.path.insert(0, str(REPO / "benchmark-suite" / "scripts"))
from lib import McpClient  # noqa: E402

STORAGE = REPO / "storage" / "tree-file-system"
NAMES = ["Computer Science and AI", "Natural and Earth Sciences",
         "Life Sciences and Medicine", "Engineering and Energy",
         "Economics and Society"]
PROBE = "How does the Transformer compute attention?"


def main() -> int:
    print("=== L1 disk + L2 tree-fs ===")
    tf = json.loads((STORAGE / ".tree-fs.json").read_text(encoding="utf-8"))
    folders = tf.get("folders") or {}
    seq = folders.values() if isinstance(folders, dict) else folders
    names = set()
    for v in seq:
        if isinstance(v, dict):
            names.add(v.get("name"))
        elif isinstance(v, str):
            names.add(v)
    for n in NAMES:
        on_disk = (STORAGE / n).is_dir()
        in_tree = n in names
        yml = (STORAGE / n / ".knowledge-base.yml").exists()
        print(f"  {n:<28} disk={on_disk!s:<5} tree-fs={in_tree!s:<5} "
              f"kb-yml={yml!s:<5}")

    print("\n=== L4 vector + L5 graph: retrieval probe per KB ===")
    mc = McpClient()
    try:
        for n in NAMES:
            try:
                r = mc.call("kb_search_vector",
                            {"query": PROBE, "kb_id": n, "top_k": 3},
                            timeout=300)
                res = r.get("results") or []
                paths = [str(h.get("doc_path", ""))[:44] for h in res[:2]]
                print(f"  {n:<28} hits={len(res):<3} {paths}")
            except Exception as e:  # noqa: BLE001
                print(f"  {n:<28} ERROR {str(e)[:90]}")
        print("\n=== global two-stage over the renamed bases ===")
        try:
            r = mc.call("kb_search_two_stage",
                        {"query": PROBE, "kb_id": "", "stage1_top_k": 20,
                         "stage2_top_k": 5, "balance_kbs": True}, timeout=420)
            c = (r.get("stage1") or {}).get("candidates") or []
            s2 = (r.get("stage2") or {}).get("results") or []
            print(f"  stage1 candidates={len(c)}  stage2 results={len(s2)}")
            for h in s2[:3]:
                print(f"    {str(h.get('doc_path'))[:60]}  score={h.get('score')}")
        except Exception as e:  # noqa: BLE001
            print(f"  ERROR {str(e)[:120]}")
    finally:
        mc.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
