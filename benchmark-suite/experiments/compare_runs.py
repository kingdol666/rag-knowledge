"""Compare two experiment runs side by side.

Usage:
  python experiments/compare_runs.py <runDirOld> <runDirNew>

Outputs per-question outcomes (grounded / not-found / denial count), per-track
aggregates, and drills into any run whose tools were denied (cause analysis).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

RESULTS = Path(__file__).resolve().parents[1] / "results"
QUESTIONS = RESULTS.parent / "data" / "papers" / "qa_questions.json"

ABSTAIN_MARKERS = (
    "unable to answer this question",
    "retrieved evidence is insufficient",
    "could not answer this question",
    "i am not giving one",
    "not-found report",
)


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def load(run: Path):
    qs = json.loads(QUESTIONS.read_text(encoding="utf-8"))["questions"]
    out = {}
    for q in qs:
        for trk in "abc":
            f = run / f"track_{trk}_{q['qid']}.json"
            if not f.exists():
                out[(trk, q["qid"])] = None
                continue
            d = json.loads(f.read_text(encoding="utf-8"))
            ans = d.get("answer") or ""
            abstain = any(m in ans.lower() for m in ABSTAIN_MARKERS)
            gold_ids = {norm(q["arxiv_id"]), norm(q["arxiv_id"].replace(".", ""))}
            cites = any(g in norm(ans) for g in gold_ids)
            toks = d.get("tokens") or {}
            out[(trk, q["qid"])] = {
                "lat": d["latency_s"], "tools": d["tool_call_count"],
                "denied": d.get("permission_denied", 0),
                "abstain": abstain, "cites": cites,
                "tok_in": toks.get("input", 0), "cost": d["total_cost_usd"],
            }
    return out


def agg(rows):
    rs = [r for r in rows if r]
    n = len(rs)
    return {
        "n": n,
        "cites": sum(r["cites"] for r in rs),
        "abstain": sum(r["abstain"] for r in rs),
        "denied_runs": sum(1 for r in rs if r["denied"] > 0),
        "lat_avg": round(sum(r["lat"] for r in rs) / n, 1),
        "tools_avg": round(sum(r["tools"] for r in rs) / n, 1),
        "cost": round(sum(r["cost"] for r in rs), 2),
    }


def main() -> int:
    old, new = RESULTS / sys.argv[1], RESULTS / sys.argv[2]
    do, dn = load(old), load(new)
    qids = sorted({k[1] for k in do})
    print(f"OLD = {old.name}   NEW = {new.name}\n")
    print(f"{'QID':5} {'trk':3} | {'old':>28} | {'new':>28}")
    print(f"{'':5} {'':3} | {'lat  tol deny abst cite':>28} | {'lat  tol deny abst cite':>28}")
    for qid in qids:
        for trk in "abc":
            o, n = do[(trk, qid)], dn[(trk, qid)]
            def fmt(r):
                if not r:
                    return f"{'MISSING':>28}"
                return (f"{r['lat']:6.1f} {r['tools']:4d} {r['denied']:4d} "
                        f"{'ABST' if r['abstain'] else '    '} "
                        f"{'gold' if r['cites'] else '----'}")
            flag = "  <-- changed" if (o and n and (o["abstain"], o["cites"]) != (n["abstain"], n["cites"])) else ""
            print(f"{qid:5} {trk:3} | {fmt(o)} | {fmt(n)}{flag}")
    print("\nPer-track:")
    for trk in "abc":
        ao, an = agg([do[(trk, q)] for q in qids]), agg([dn[(trk, q)] for q in qids])
        print(f"  {trk}: old cites {ao['cites']}/{ao['n']} abst {ao['abstain']} "
              f"lat {ao['lat_avg']}s tools {ao['tools_avg']} ${ao['cost']}"
              f"   ||   new cites {an['cites']}/{an['n']} abst {an['abstain']} "
              f"lat {an['lat_avg']}s tools {an['tools_avg']} ${an['cost']}")
    # cause drill-down for denied runs in the new experiment
    print("\nDenied-call runs in NEW (cause check):")
    for (trk, qid), r in sorted(dn.items()):
        if r and r["denied"] > 0:
            d = json.loads((new / f"track_{trk}_{qid}.json").read_text(encoding="utf-8"))
            names = [e["detail"] for e in d["timeline"] if e["event"] == "permission_denied"]
            direct = sum(1 for e in d["timeline"]
                         if e["event"] == "tool_use" and e["detail"].startswith("mcp__kb-mcp__"))
            print(f"  {trk}/{qid}: denied={r['denied']} abstained={r['abstain']} "
                  f"deniedTools={sorted(set(names))[:2]} directKbCalls={direct}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
