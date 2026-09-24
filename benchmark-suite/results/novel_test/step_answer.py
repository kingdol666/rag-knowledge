#!/usr/bin/env python3
"""Assemble evidence from the KB (targeted retrieval) and answer via the real chat API."""
from __future__ import annotations
import json, sys
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(SUITE / "scripts"))
sys.path.insert(0, str(SUITE / "experiments"))
from lib import McpClient  # noqa: E402
from chat_tracks import answer_closed_book  # noqa: E402

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

# beat -> (label, near-verbatim probe phrase used to RETRIEVE the passage from the KB)
BEATS = [
    ("B1 Meryton assembly insult (Ch 3)",
     "She is tolerable but not handsome enough to tempt me and I am in no humour at present to give consequence to young ladies"),
    ("B2 Wickham's account of the living (Ch 15-16)",
     "Mr Wickham told Elizabeth that the living had been designed for him and that Darcy had refused to give it to him"),
    ("B3 Darcy's first proposal at Hunsford (Ch 34)",
     "In vain have I struggled It will not do My feelings will not be repressed You must allow me to tell you how ardently I admire and love you"),
    ("B4 Elizabeth's refusal (Ch 34)",
     "I have every reason in the world to think ill of you you are the man who has been the means of ruining the happiness of a most beloved sister"),
    ("B5 Darcy's letter: Wickham's real character (Ch 35)",
     "she was persuaded to believe herself in love and to consent to an elopement my sister Georgiana Wickham chief object was my sister fortune"),
    ("B6 Elizabeth's self-reproach (Ch 36)",
     "Till this moment I never knew myself"),
    ("B7 Pemberley: the housekeeper's praise (Ch 43)",
     "He is the best landlord and the best master that ever lived I have never had a cross word from him in my life"),
    ("B8 Lydia's elopement news (Ch 46)",
     "into the power of Mr Wickham they are gone off together from Brighton"),
    ("B9 Darcy secretly resolves the crisis (Ch 52)",
     "Darcy did everything made up the match gave the money paid the fellows debts and got him his commission"),
    ("B10 The second proposal (Ch 58)",
     "My affections and wishes are unchanged Had you behaved in a more gentlemanlike manner your reproof so well applied I shall never forget"),
]


def main():
    c = McpClient()
    try:
        pack = []
        for label, phrase in BEATS:
            r = c.call("kb_search_vector", {"query": phrase, "kb_id": KB_ID,
                                            "top_k": 3, "score_threshold": 0.35,
                                            "balance_kbs": False}, timeout=300)
            hits = r.get("results", [])
            if not hits:
                pack.append((label, None, None))
                print(f"{label}: NO HIT")
                continue
            top = hits[0]
            pack.append((label, top, [{"score": h.get("score"),
                                       "doc_path": h.get("doc_path")} for h in hits]))
            print(f"{label}: {top.get('score'):.4f} "
                  f"{str(top.get('doc_path')).split('/')[-1]}")

        ev_lines = []
        for label, top, _ in pack:
            if not top:
                continue
            part = str(top["doc_path"]).replace("\\", "/").split("/")[-1]
            ev_lines.append(f"[{label}] (source: {part}, chunk {top.get('chunk_index')})\n"
                            f"{str(top.get('content')).strip()}\n")
        evidence = "\n".join(ev_lines)
        (OUT / "evidence_pack.txt").write_text(evidence, encoding="utf-8")
        print(f"\nevidence pack: {len(evidence)} chars")

        ans = answer_closed_book(QUESTION, evidence, timeout_s=300)
        (OUT / "answer_a.json").write_text(
            json.dumps(ans, ensure_ascii=False, indent=1), encoding="utf-8")
        print("\n=== ANSWER (a) ===")
        print(ans.get("answer"))
        print("\ntools", ans.get("tool_call_count"), "latency", ans.get("latency_s"))
    finally:
        c.close()


if __name__ == "__main__":
    main()
