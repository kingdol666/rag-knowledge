#!/usr/bin/env python3
"""Assemble evidence packs (<=20000 chars) for both lanes from real kb_doc_read calls.

Same evidence CAP for both lanes. Lane A spends it on the one part the vector lane
landed on (retrieved chunk + head + continuation windows). Lane B spreads it across its
head-based shortlist (per-part budget = CAP // n_parts, uniform sampling).
"""
import json
import sys

sys.path.insert(0, "D:/codes/ClaudeGPT/rag_project/rag-knowledge/benchmark-suite/scripts")
from lib import McpClient  # noqa: E402

OUT = "D:/codes/ClaudeGPT/rag_project/rag-knowledge/benchmark-suite/results/two-lane-test"
KB = "b4c48237-6937-440a-9696-cc1e66bed5c1"
BUDGET = 20000

LANE_A_PART = {"Q1": 2, "Q2": 6, "Q3": 21, "Q4": 9, "Q5": 19}
LANE_B_PARTS = {"Q1": [2, 3], "Q2": [13, 14], "Q3": [21, 20], "Q4": [9, 10],
                "Q5": [14, 19, 20]}


def dp(k):
    return f"Novel-PridePrejudice/pride_and_prejudice (part {k} of 26).md"


def read(c, doc_path, max_chars, offset=None, limit=100):
    a = {"kb_id": KB, "doc_path": doc_path, "max_chars": max_chars}
    if offset is not None:
        a["offset"] = offset
        a["limit"] = limit
    return c.call("kb_doc_read", a)


def main():
    c = McpClient()
    log = []
    packs = {"lane_a": {}, "lane_b": {}, "trace": {}, "_log": log, "budget": BUDGET}
    # Lane A retrieved chunks (admissible evidence per the skill)
    dump = json.load(open(f"{OUT}/retrieval_dump.json", encoding="utf-8"))
    p2 = json.load(open(f"{OUT}/lane_a_phase2.json", encoding="utf-8"))
    chunk_a = {}
    for qid in LANE_A_PART:
        src = dump["lane_a"][qid] if qid not in ("Q2", "Q4", "Q5") else None
        # use the chunk from whichever phase produced the lane's chosen part
        chosen = None
        for cand in (dump["lane_a"][qid]["ranked"], p2.get(qid, {}).get("ranked_novel", [])):
            for r in cand:
                if "PridePrejudice" in r["doc_path"] and f"(part {LANE_A_PART[qid]} of 26)" in r["doc_path"]:
                    chosen = r
                    break
            if chosen:
                break
        chunk_a[qid] = (chosen or {}).get("content", "")
    try:
        # ---------- LANE A: one located part, read thoroughly ----------
        for qid, k in LANE_A_PART.items():
            path = dp(k)
            head = read(c, path, 3000)
            log.append({"lane": "A", "tool": "kb_doc_read", "path": path, "win": "head"})
            tl = int(head.get("totalLines") or 0)
            parts = [("head", head.get("content", ""))]
            if chunk_a.get(qid):
                parts.insert(0, ("retrieved chunk", chunk_a[qid]))
            for i in range(1, 6):
                off = (tl * i) // 6
                r = read(c, path, 3000, offset=off)
                log.append({"lane": "A", "tool": "kb_doc_read", "path": path,
                            "win": f"{i}/6@{off}"})
                parts.append((f"window {i}/6 @line{off}", r.get("content", "")))
            packs["trace"][f"A_{qid}"] = {"part": k, "totalLines": tl}
            packs["lane_a"][qid] = {"part": k, "windows": parts}

        # ---------- LANE B: head-based shortlist, uniform sampling ----------
        for qid, ks in LANE_B_PARTS.items():
            n = len(ks)
            per_part = BUDGET // n
            per_win = per_part // 6
            parts = []
            for k in ks:
                path = dp(k)
                head = read(c, path, per_win)
                log.append({"lane": "B", "tool": "kb_doc_read", "path": path, "win": "head"})
                tl = int(head.get("totalLines") or 0)
                parts.append((f"p{k}:head", head.get("content", "")))
                for i in range(1, 6):
                    off = (tl * i) // 6
                    r = read(c, path, per_win, offset=off)
                    log.append({"lane": "B", "tool": "kb_doc_read", "path": path,
                                "win": f"p{k}:{i}/6@{off}"})
                    parts.append((f"p{k}:{i}/6@line{off}", r.get("content", "")))
            packs["trace"][f"B_{qid}"] = {"parts": ks, "per_part": per_part,
                                          "per_win": per_win}
            packs["lane_b"][qid] = {"parts": ks, "windows": parts}

        def assemble(windows):
            out, used = [], 0
            for tag, txt in windows:
                if used >= BUDGET:
                    break
                piece = f"[{tag}]\n{txt}"
                take = piece[: BUDGET - used]
                out.append(take)
                used += len(take)
            return "\n\n".join(out)

        packs["evidence_a"] = {q: assemble(v["windows"]) for q, v in packs["lane_a"].items()}
        packs["evidence_b"] = {q: assemble(v["windows"]) for q, v in packs["lane_b"].items()}
        with open(f"{OUT}/evidence_packs.json", "w", encoding="utf-8") as f:
            json.dump(packs, f, ensure_ascii=False, indent=1)
        for q in LANE_A_PART:
            print(q, "A part", LANE_A_PART[q], "evid", len(packs["evidence_a"][q]),
                  "| B parts", LANE_B_PARTS[q], "evid", len(packs["evidence_b"][q]))
        print("total reads:", len(log))
    finally:
        c.close()


if __name__ == "__main__":
    main()
