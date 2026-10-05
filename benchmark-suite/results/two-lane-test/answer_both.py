#!/usr/bin/env python3
"""Answer both lanes with the SAME evidence budget via answer_closed_book."""
import json
import sys
import time

sys.path.insert(0, "D:/codes/ClaudeGPT/rag_project/rag-knowledge/benchmark-suite/experiments")
sys.path.insert(0, "D:/codes/ClaudeGPT/rag_project/rag-knowledge/benchmark-suite/scripts")
from chat_tracks import answer_closed_book  # noqa: E402

OUT = "D:/codes/ClaudeGPT/rag_project/rag-knowledge/benchmark-suite/results/two-lane-test"

QUESTIONS = {
    "Q1": "At the Mertyon assembly where the Netherfield party first appears, what does Mr. Darcy say about Elizabeth when Bingley suggests he dance with her, and how does Elizabeth respond to it?",
    "Q2": "What happens at Hunsford when Mr. Darcy proposes to Elizabeth, why does she refuse him, and what does his letter the next morning reveal about Wickham?",
    "Q3": "How does Elizabeth learn the truth about Mr. Darcy's role in Lydia's marriage, and what exactly did Darcy do and pay?",
    "Q4": "How did Charlotte Lucas come to marry Mr. Collins, and how did Elizabeth react to the engagement?",
    "Q5": "In the novel, Mr. Wickham is linked to two young women in connection with an elopement. Who are the two young women, roughly how old was each, and how did each affair end?",
}


def main():
    p = json.load(open(f"{OUT}/evidence_packs.json", encoding="utf-8"))
    res = {}
    for lane, key in (("A", "evidence_a"), ("B", "evidence_b")):
        for qid in QUESTIONS:
            ev = p[key][qid]
            t0 = time.perf_counter()
            r = answer_closed_book(QUESTIONS[qid], ev)
            res[f"{lane}_{qid}"] = {
                "lane": lane, "qid": qid, "evidence_chars": len(ev),
                "answer": r.get("answer"), "is_error": r.get("is_error"),
                "latency_s": r.get("latency_s"), "num_turns": r.get("num_turns"),
                "tokens": r.get("tokens"), "total_cost_usd": r.get("total_cost_usd"),
                "wall_s": round(time.perf_counter() - t0, 1),
            }
            print(f"{lane} {qid}: {r.get('latency_s')}s err={r.get('is_error')} "
                  f"ans={len(r.get('answer') or '')}ch", flush=True)
            json.dump(res, open(f"{OUT}/answers.json", "w", encoding="utf-8"),
                      ensure_ascii=False, indent=1)
    print("DONE")


if __name__ == "__main__":
    main()
