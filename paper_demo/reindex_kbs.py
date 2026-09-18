#!/usr/bin/env python3
"""Reindex the renamed bases so the vector metadata carries the new paths.

kb_update moves the directory, the tree index and the YAML catalogue, but the
stored doc_path prefix inside ChromaDB and the BM25 index keeps the old base
name. two_stage stage-2 matches candidates by exact doc_path, so leaving it
stale is the failure mode the project documents as a silent zero-result bug.

kb_reindex is non-blocking: it returns a task_id and the work is polled with
kb_task_status.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO = Path(r"D:\codes\ClaudeGPT\rag_project\rag-knowledge")
sys.path.insert(0, str(REPO / "benchmark-suite" / "scripts"))
from lib import McpClient  # noqa: E402

NAMES = ["Computer Science and AI", "Natural and Earth Sciences",
         "Life Sciences and Medicine", "Engineering and Energy",
         "Economics and Society"]


def main() -> int:
    mc = McpClient()
    tasks: dict[str, str] = {}
    try:
        for n in NAMES:
            try:
                r = mc.call("kb_reindex", {"kb_id": n, "force": True},
                            timeout=300)
                tid = r.get("task_id") or r.get("taskId") or ""
                tasks[n] = tid
                print(f"  [reindex] {n:<28} task={tid or r}")
            except Exception as e:  # noqa: BLE001
                print(f"  [reindex] {n:<28} ERROR {str(e)[:100]}")

        # poll
        deadline = time.time() + 2400
        pending = dict(tasks)
        while pending and time.time() < deadline:
            time.sleep(12)
            for n, tid in list(pending.items()):
                if not tid:
                    pending.pop(n, None)
                    continue
                try:
                    st = mc.call("kb_task_status", {"task_id": tid},
                                 timeout=120)
                except Exception:  # noqa: BLE001
                    continue
                state = str(st.get("status") or st.get("state") or "?")
                if state.lower() in ("completed", "success", "done", "failed",
                                     "error"):
                    print(f"  [done] {n:<28} {state}  "
                          f"{json.dumps(st, ensure_ascii=False)[:180]}")
                    pending.pop(n, None)

        print("\n=== verify the prefix now stored in the vector layer ===")
        for n in NAMES:
            r = mc.call("kb_search_vector",
                        {"query": "Transformer attention", "kb_id": n,
                         "top_k": 1}, timeout=300)
            hits = r.get("results") or []
            dp = str(hits[0].get("doc_path")) if hits else "(no hits)"
            print(f"  {n:<28} {dp[:66]}")
    finally:
        mc.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
