"""Audit all 30 traces of experiment_chat_20260920-145455 for paper numbers.

Recomputes, from the per-run JSON traces only:
  - outcome classification (answered-with-evidence vs honest not-found)
  - permission_denied count and whether the run's tools were allowlist-denied
  - designated-paper citation (gold arxiv id or paper slug in the answer text)
  - gold-keyword presence in the answer text
  - latency / tool calls / tokens / cost per track

Writes audit_paper_numbers.json next to the traces. Paper text must quote
these numbers, not hand-typed ones.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

RESULTS = Path(__file__).resolve().parents[1] / "results"
RUN = Path(sys.argv[1]) if len(sys.argv) > 1 else RESULTS / "experiment_chat_20260920-145455"
QUESTIONS = (Path(sys.argv[2]) if len(sys.argv) > 2 else
             Path(__file__).resolve().parents[1] / "data" / "papers" / "qa_questions.json")

ABSTAIN_MARKERS = (
    "unable to answer this question",
    "retrieved evidence is insufficient",
    "could not answer this question",
    "i am not giving one",
    "not-found report",
)


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def main() -> int:
    qs = {q["qid"]: q for q in json.loads(QUESTIONS.read_text(encoding="utf-8"))["questions"]}
    rows = []
    for qid in sorted(qs):
        q = qs[qid]
        gold_ids = {norm(q["arxiv_id"]), norm(q["arxiv_id"].replace(".", ""))}
        # slug fragments of the gold paper title, distinctive enough to cite
        slug = norm(q["paper"])[:24]
        for track in ("a", "b", "c"):
            d = json.loads((RUN / f"track_{track}_{qid}.json").read_text(encoding="utf-8"))
            ans = d.get("answer") or ""
            low = ans.lower()
            nlow = norm(ans)
            abstain = any(m in low for m in ABSTAIN_MARKERS)
            cites = any(g in nlow for g in gold_ids) or (slug in nlow and not abstain)
            kw_hit = [k for k in q["gold_keywords"] if norm(k) in nlow]
            toks = d.get("tokens") or {}
            rows.append({
                "qid": qid,
                "track": track,
                "latency_s": d.get("latency_s"),
                "tool_calls": d.get("tool_call_count"),
                "permission_denied": d.get("permission_denied", 0),
                "tokens_in": toks.get("input"),
                "tokens_out": toks.get("output"),
                "cost_usd": d.get("total_cost_usd"),
                "abstained": abstain,
                "cites_gold_paper": bool(cites),
                "gold_keywords_in_answer": kw_hit,
            })

    agg = {}
    for track in ("a", "b", "c"):
        rs = [r for r in rows if r["track"] == track]
        n = len(rs)
        agg[track] = {
            "runs": n,
            "answered_with_gold_citation": sum(r["cites_gold_paper"] for r in rs),
            "honest_not_found": sum(r["abstained"] for r in rs),
            "runs_with_denied_tools": sum(1 for r in rs if r["permission_denied"] > 0),
            "avg_latency_s": round(sum(r["latency_s"] for r in rs) / n, 1),
            "avg_tool_calls": round(sum(r["tool_calls"] for r in rs) / n, 1),
            "tokens_in_total": sum(r["tokens_in"] for r in rs),
            "tokens_out_total": sum(r["tokens_out"] for r in rs),
            "cost_usd_total": round(sum(r["cost_usd"] for r in rs), 2),
        }

    out = {"run": RUN.name, "rows": rows, "per_track": agg}
    (RUN / "audit_paper_numbers.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"{'QID':5} {'trk':3} {'lat_s':>6} {'tols':>4} {'deny':>4} "
          f"{'abstain':>7} {'goldcite':>8}  gold-kw")
    for r in rows:
        print(f"{r['qid']:5} {r['track']:3} {r['latency_s']:6.1f} {r['tool_calls']:4d} "
              f"{r['permission_denied']:4d} {str(r['abstained']):>7} "
              f"{str(r['cites_gold_paper']):>8}  {','.join(r['gold_keywords_in_answer']) or '-'}")
    print("\nPer-track:")
    for t, a in agg.items():
        print(f"  {t}: {json.dumps(a)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
