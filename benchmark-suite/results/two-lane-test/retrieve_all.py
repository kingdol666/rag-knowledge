#!/usr/bin/env python3
"""Two-lane retrieval harness (read-only).

Lane A (knowledgebase-search): kb_search_vector -> threshold/dedup -> content gate reads.
Lane B (knowledgebase-librarian, VECTOR-FREE): L0 catalog -> L1 shelf -> L2 every doc
description -> L3 trust check (heads of every part) -> L4 shortlist (done in a later step)
-> L5 targeted reads.

Everything is dumped to JSON/text so the agent can apply the 0-8 rubric by hand and
assemble the two evidence packs. NO kb_search_vector / kb_search_two_stage is called
anywhere inside the Lane B code path; the call log records every tool call.
"""
import json
import sys

sys.path.insert(0, "D:/codes/ClaudeGPT/rag_project/rag-knowledge/benchmark-suite/scripts")
from lib import McpClient  # noqa: E402

OUT = "D:/codes/ClaudeGPT/rag_project/rag-knowledge/benchmark-suite/results/two-lane-test"
KB = "b4c48237-6937-440a-9696-cc1e66bed5c1"  # Novel-PridePrejudice

QUESTIONS = {
    "Q1": "At the Mertyon assembly where the Netherfield party first appears, what does Mr. Darcy say about Elizabeth when Bingley suggests he dance with her, and how does Elizabeth respond to it?",
    "Q2": "What happens at Hunsford when Mr. Darcy proposes to Elizabeth, why does she refuse him, and what does his letter the next morning reveal about Wickham?",
    "Q3": "How does Elizabeth learn the truth about Mr. Darcy's role in Lydia's marriage, and what exactly did Darcy do and pay?",
    "Q4": "How did Charlotte Lucas come to marry Mr. Collins, and how did Elizabeth react to the engagement?",
    "Q5": "In the novel, Mr. Wickham is linked to two young women in connection with an elopement. Who are the two young women, roughly how old was each, and how did each affair end?",
}

# Phase-0 rewrites (Lane A only)
REWRITE = {
    "Q1": "Mr. Darcy at the Meryton assembly refuses to dance with Elizabeth Bennet, saying she is tolerable but not handsome enough to tempt him, and Elizabeth overhears and laughs it off",
    "Q2": "Mr. Darcy's first marriage proposal to Elizabeth Bennet at Hunsford Parsonage, her refusal, and the letter he gives her next morning revealing Wickham's attempted elopement with Georgiana Darcy",
    "Q3": "Mrs. Gardiner's letter revealing that Mr. Darcy secretly found Lydia and Wickham in London, paid Wickham's debts, settled money on Lydia, and bought his commission",
    "Q4": "Charlotte Lucas's marriage to Mr. Collins and Elizabeth Bennet's reaction to the engagement",
    "Q5": "Wickham's attempted elopement with Georgiana Darcy at Ramsgate and his actual elopement with Lydia Bennet",
}


def main():
    log = []
    out = {"questions": QUESTIONS, "rewrite": REWRITE, "lane_a": {}, "lane_b": {}}
    c = McpClient()
    _lane = {"v": "?"}

    def call(name, args, timeout=180):
        import time as _t
        _t0 = _t.perf_counter()
        r = c.call(name, args, timeout=timeout)
        log.append({"lane": _lane["v"], "tool": name, "args": args,
                    "ms": round((_t.perf_counter() - _t0) * 1000)})
        return r

    try:
        # ---------------- LANE B: L0 catalog ----------------
        _lane["v"] = "B"
        cat = call("kb_list", {"lightweight": True})
        out["lane_b"]["L0_catalog"] = cat

        # ---------------- LANE B: L2 every document description ----------------
        docs = call("kb_get_documents", {"kb_id": KB, "lightweight": True})
        out["lane_b"]["L2_documents"] = docs
        doc_cat = docs.get("catalog", [])

        # ---------------- LANE B: L3 trust check — read head of every part ----------------
        heads = {}
        for d in doc_cat:
            dp = d.get("doc_path")
            r = call("kb_doc_read", {"kb_id": KB, "doc_path": dp, "max_chars": 600})
            heads[dp] = r
        out["lane_b"]["L3_heads"] = heads

        # ---------------- LANE A: per-question vector + content gate ----------------
        _lane["v"] = "A"
        for qid, rq in REWRITE.items():
            vres = call("kb_search_vector", {
                "query": rq, "kb_id": "", "top_k": 10,
                "score_threshold": 0.35, "balance_kbs": True}, timeout=180)
            results = vres.get("results", []) or []
            # step2.5: hard threshold + doc-level dedup (keep best per doc_path)
            best = {}
            for r in results:
                sc = float(r.get("score", 0))
                if sc < 0.35:
                    continue
                dp = str(r.get("doc_path", ""))
                if dp not in best or sc > float(best[dp]["score"]):
                    best[dp] = r
            ranked = sorted(best.values(), key=lambda x: -float(x["score"]))
            # content gate: read top 5 docs
            gate = []
            for r in ranked[:5]:
                dp = r["doc_path"]
                rd = call("kb_doc_read", {"kb_id": KB, "doc_path": dp, "max_chars": 3000})
                gate.append({"doc_path": dp, "score": float(r["score"]),
                             "chunk": r.get("content", ""), "read": rd})
            out["lane_a"][qid] = {"vector_raw": results, "ranked": ranked, "gate": gate}

        out["call_log"] = log
        with open(f"{OUT}/retrieval_dump.json", "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        print("dumped. lane_a questions:", list(out["lane_a"].keys()))
        print("lane_b docs:", len(doc_cat), "heads:", len(heads))
        print("total tool calls:", len(log))
        # audit: lane B must NEVER call vector tools
        lb_vec = [e for e in log if e["lane"] == "B" and e["tool"] in
                  ("kb_search_vector", "kb_search_two_stage")]
        la_vec = [e for e in log if e["lane"] == "A" and e["tool"] == "kb_search_vector"]
        print("LANE B vector calls (must be 0):", len(lb_vec))
        print("LANE A vector calls:", len(la_vec))
    finally:
        c.close()


if __name__ == "__main__":
    main()
