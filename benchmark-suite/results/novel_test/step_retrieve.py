#!/usr/bin/env python3
"""QDCVR v2 retrieval protocol for the long-arc question (real MCP calls).

Phase 0 rewrite -> Phase 1 vector (whole-library + novel KB) -> per-beat sub-queries
-> content gate reads. Saves the full trace to retrieval_trace.json.
"""
from __future__ import annotations
import json, sys
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(SUITE / "scripts"))
from lib import McpClient  # noqa: E402

OUT = Path(__file__).resolve().parent
KB_ID = "b4c48237-6937-440a-9696-cc1e66bed5c1"

QUESTION = (
    "Trace how Elizabeth Bennet's opinion of Mr. Darcy changes across the whole "
    "novel, and identify the specific scenes that cause each change -- from the "
    "Meryton assembly, through Wickham's account and the Hunsford proposal and "
    "Darcy's letter, to the Pemberley visit and the Lydia elopement crisis. In "
    "what ways does Darcy himself change, and how does each acknowledge their "
    "earlier error by the end?"
)
REWRITE = (
    "Elizabeth Bennet's changing judgment of Mr Darcy across Pride and Prejudice: "
    "his insult at the Meryton assembly; Wickham's false account of the living; "
    "the first proposal at Hunsford and Darcy's letter revealing Wickham's true "
    "character; the Pemberley visit and the housekeeper's praise; Darcy secretly "
    "resolving Lydia's elopement; the second proposal and mutual acknowledgement "
    "of past error."
)
SUBQUERIES = {
    "S1_meryton_insult": "Mr Darcy refuses to dance with Elizabeth at the Meryton assembly and says she is tolerable but not handsome enough to tempt him",
    "S2_wickham_account": "Wickham tells Elizabeth that Darcy deprived him of the living promised by Darcy's father",
    "S3_first_proposal": "Darcy's first proposal to Elizabeth at Hunsford and her refusal accusing him over Jane and Wickham",
    "S4_letter": "Darcy's letter to Elizabeth revealing Wickham's dissipation and his attempt to elope with Georgiana for her fortune",
    "S5_pemberley": "Elizabeth visits Pemberley and the housekeeper Mrs Reynolds praises Darcy as the best master and landlord",
    "S6_lydia_elopement": "Darcy secretly finds Wickham and Lydia and pays his debts and buys his commission, revealed in Mrs Gardiner's letter",
    "S7_second_proposal": "Darcy's second proposal to Elizabeth and both acknowledging their past errors and improvement",
}


def search(c, query, kb_id="", top_k=10, thr=0.35, balance=True):
    r = c.call("kb_search_vector", {"query": query, "kb_id": kb_id,
                                    "top_k": top_k, "score_threshold": thr,
                                    "balance_kbs": balance}, timeout=300)
    return r.get("results", []) if r.get("success") else []


def main():
    c = McpClient()
    trace = {"question": QUESTION, "rewrite": REWRITE, "phases": {}}
    try:
        # ---- Phase 1a: main rewrite, whole library ----
        whole = search(c, REWRITE, kb_id="", top_k=10, balance=True)
        novel = search(c, REWRITE, kb_id=KB_ID, top_k=10, balance=False)
        trace["phases"]["phase1a_whole_library"] = [
            {k: h.get(k) for k in ("score", "doc_path", "chunk_index", "kb_id")}
            | {"content": str(h.get("content"))[:400]} for h in whole]
        trace["phases"]["phase1a_novel_kb"] = [
            {k: h.get(k) for k in ("score", "doc_path", "chunk_index")}
            | {"content": str(h.get("content"))[:400]} for h in novel]
        print(f"Phase1a whole-library: {len(whole)} hits; novel-KB: {len(novel)} hits")

        # ---- Phase 1a-bis: per-beat sub-queries (multi-concept split) ----
        beats = {}
        for name, q in SUBQUERIES.items():
            hits = search(c, q, kb_id=KB_ID, top_k=5, balance=False)
            beats[name] = [{"score": h.get("score"), "doc_path": h.get("doc_path"),
                            "chunk_index": h.get("chunk_index"),
                            "content": str(h.get("content"))[:500]} for h in hits]
            top = hits[0] if hits else {}
            print(f"  {name}: {len(hits)} hits, top={top.get('score')} "
                  f"{str(top.get('doc_path')).split('/')[-1]}")
        trace["phases"]["phase1b_subqueries"] = beats

        # unique candidate docs across everything
        cand = {}
        for h in whole + novel:
            cand.setdefault(h["doc_path"], h["score"])
        for hits in beats.values():
            for h in hits:
                cand.setdefault(h["doc_path"], h["score"])
        trace["candidates"] = sorted(
            [{"doc_path": k, "score": v} for k, v in cand.items()],
            key=lambda x: -x["score"])

        # ---- Phase 1c content gate: read candidate heads ----
        reads = {}
        for dp in cand:
            r = c.call("kb_doc_read", {"kb_id": KB_ID, "doc_path": dp,
                                       "max_chars": 3000}, timeout=180)
            reads[dp] = {"totalLines": r.get("totalLines"),
                         "truncated": r.get("truncated"),
                         "content": str(r.get("content", ""))[:3000]}
        trace["phases"]["phase1c_reads"] = reads
        print(f"\ncontent-gate reads: {len(reads)} docs")

        # ---- Phase 2: librarian fallback ----
        cat = c.call("kb_list", {"lightweight": True}, timeout=120)
        docs_lw = c.call("kb_get_documents", {"kb_id": KB_ID, "lightweight": True},
                         timeout=180)
        two = c.call("kb_search_two_stage", {
            "query": REWRITE, "kb_id": KB_ID, "stage1_top_k": 20,
            "stage2_top_k": 5, "enable_graph_expansion": True,
            "score_threshold": 0.30, "balance_kbs": False}, timeout=600)
        tags = c.call("kb_tags_list", {}, timeout=120)
        tag_hits = {}
        for t in ("Pride and Prejudice", "Jane Austen"):
            tag_hits[t] = c.call("kb_doc_get_by_tag", {"tag": t, "kb_id": KB_ID},
                                 timeout=180)
        trace["phases"]["phase2_librarian"] = {
            "kb_list_lightweight": cat,
            "novel_docs_lightweight": docs_lw,
            "two_stage": two,
            "tags": tags,
            "tag_hits": tag_hits,
        }
        print("Phase2 librarian: catalog + docs + two_stage + tags captured")

        (OUT / "retrieval_trace.json").write_text(
            json.dumps(trace, ensure_ascii=False, indent=1), encoding="utf-8")
        print("\nsaved retrieval_trace.json")
    finally:
        c.close()


if __name__ == "__main__":
    main()
