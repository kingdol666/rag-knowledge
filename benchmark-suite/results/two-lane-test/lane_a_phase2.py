#!/usr/bin/env python3
"""Lane A Phase-2 refined vector recall (triggered when the content gate <=5)."""
import json
import sys

sys.path.insert(0, "D:/codes/ClaudeGPT/rag_project/rag-knowledge/benchmark-suite/scripts")
from lib import McpClient  # noqa: E402

OUT = "D:/codes/ClaudeGPT/rag_project/rag-knowledge/benchmark-suite/results/two-lane-test"
KB = "b4c48237-6937-440a-9696-cc1e66bed5c1"

REFINED = {
    "Q2": "Mr. Darcy's marriage proposal to Elizabeth Bennet at Hunsford Parsonage 'In vain have I struggled' and the letter he gives her next morning about Wickham and Georgiana Darcy",
    "Q4": "Charlotte Lucas accepts Mr. Collins and Elizabeth's disbelief 'Engaged to Mr. Collins impossible', Charlotte says I am not romantic I ask only a comfortable home",
    "Q5": "Wickham's attempted elopement with Georgiana Darcy at Ramsgate and his elopement with Lydia Bennet",
}


def main():
    out = {}
    log = []
    c = McpClient()
    try:
        for qid, q in REFINED.items():
            v = c.call("kb_search_vector", {"query": q, "kb_id": "", "top_k": 10,
                                            "score_threshold": 0.35, "balance_kbs": True},
                       timeout=180)
            log.append({"tool": "kb_search_vector", "args": {"query": q}})
            res = v.get("results", []) or []
            # top novel parts
            novel = {}
            for r in res:
                if "PridePrejudice" in r["doc_path"]:
                    dp = r["doc_path"]
                    if dp not in novel or float(r["score"]) > float(novel[dp]["score"]):
                        novel[dp] = r
            ranked = sorted(novel.values(), key=lambda x: -float(x["score"]))
            gate = []
            for r in ranked[:2]:
                rd = c.call("kb_doc_read", {"kb_id": KB, "doc_path": r["doc_path"],
                                            "max_chars": 3000})
                log.append({"tool": "kb_doc_read", "args": {"doc_path": r["doc_path"]}})
                gate.append({"doc_path": r["doc_path"], "score": float(r["score"]),
                             "chunk": r.get("content", ""), "read": rd})
            out[qid] = {"vector_raw": res, "ranked_novel": ranked, "gate": gate}
        out["_log"] = log
        with open(f"{OUT}/lane_a_phase2.json", "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        for qid in REFINED:
            print(qid, "->",
                  [f"{float(r['score']):.4f} {r['doc_path'].split('/')[-1]}"
                   for r in out[qid]["ranked_novel"][:3]])
    finally:
        c.close()


if __name__ == "__main__":
    main()
