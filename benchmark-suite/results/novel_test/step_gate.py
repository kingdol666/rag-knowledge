#!/usr/bin/env python3
"""Verify the part-13 miss + dump content-gate reads for scoring."""
from __future__ import annotations
import json, sys
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(SUITE / "scripts"))
from lib import McpClient  # noqa: E402

OUT = Path(__file__).resolve().parent
KB_ID = "b4c48237-6937-440a-9696-cc1e66bed5c1"
PART13 = "Novel-PridePrejudice/pride_and_prejudice (part 13 of 26).md"


def main():
    c = McpClient()
    try:
        # targeted searches for the pivotal beat (Ch 34 first proposal / Ch 35 letter)
        for q in ["In vain have I struggled It will not do My feelings will not be repressed",
                  "Elizabeth I have every reason in the world to think ill of you unjust and ungenerous",
                  "till this moment I never knew myself"]:
            r = c.call("kb_search_vector", {"query": q, "kb_id": KB_ID, "top_k": 5,
                                            "score_threshold": 0.35,
                                            "balance_kbs": False}, timeout=300)
            print(f"\n### targeted: {q[:60]!r}")
            for h in r.get("results", []):
                print(f"  {h.get('score'):.4f} {str(h.get('doc_path')).split('/')[-1]} "
                      f"c{h.get('chunk_index')} :: {str(h.get('content'))[:100]!r}")

        # read part 13 head directly (Ch XXXIII-XXXV)
        r = c.call("kb_doc_read", {"kb_id": KB_ID, "doc_path": PART13,
                                   "max_chars": 1200}, timeout=180)
        print("\n### part 13 head (direct read)")
        print("totalLines", r.get("totalLines"), "truncated", r.get("truncated"))
        print(str(r.get("content"))[:900])
    finally:
        c.close()


if __name__ == "__main__":
    main()
