#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Exp 5b — capture the full Q2 hybrid run for the anatomy-of-a-query figure.

One real kb_hybrid_search(enable_judge=true) call; the complete response
(fusion order, per-candidate judge scores, reads) is dumped verbatim so the
case-study figure is drawn from actual system output, not a sketch.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kbcommon import QUESTIONS, RESULTS, McpClient


def main() -> int:
    q = next(q for q in QUESTIONS if q["qid"] == "Q2")
    mc = McpClient()
    r = mc.call("kb_hybrid_search",
                {"query": q["text"], "candidate_cap": 12,
                 "enable_judge": True}, timeout=300)
    out = RESULTS / "exp5_q2_anatomy.json"
    out.write_text(json.dumps({"question": q, "response": r},
                              ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print("wrote", out)
    merge = (r.get("merge") or {}).get("judged_candidates") or []
    kept = (r.get("cut", {}) or {}).get("kept", []) or []
    print("fusion order:")
    for i, p in enumerate(merge, 1):
        print(f"  {i:2d}. {p}")
    print("judge kept:")
    for k in kept:
        print(f"  {float(k.get('score') or 0):.3f}  {k.get('doc_path')}")
    top = r.get("topk") or r.get("final_topk") or []
    print("other keys:", [k for k in r if k not in ("merge", "cut")])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
