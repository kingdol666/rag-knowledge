#!/usr/bin/env python3
# DEPRECATED 2026-09-20 — superseded by the experiments/ platform
# (python -m experiments.runner, chat API + harness=claude). Kept only to
# reproduce historical reports. Do not use for new retrieval testing.
"""三轨对照 QA 报告 — 分轨汇整(每轨独立小节: 汇总表 + 逐题回答全文)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
RESULTS = SUITE / "results"

TRACKS = [
    ("track_a_kb_system", "Track A — Platform KB retrieval",
     "MCP two_stage over the 5 category KBs → doc-level dedup → top-3 chunk "
     "excerpts (4000-char budget) → unified answer prompt"),
    ("track_b_bare_agent", "Track B — Bare agent direct search",
     "Same omp engine WITH file tools, cwd=data/corpus_md/ (50 markdown "
     "papers, no index); it locates and reads passages itself"),
    ("track_c_dense_rag", "Track C — RAG reproduction (dense baseline)",
     "methods.dense over Corpus-Chunks800 (fixed 800-char chunks, top-10) → "
     "same 4000-char budget → same unified answer prompt"),
]


def main() -> int:
    rows = json.loads((RESULTS / "threeway_qa.json").read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    L = []
    w = L.append
    w("# Three-Way Retrieval QA — 10 Content-Grounded Questions")
    w("")
    w(f"Generated {now} · corpus: 50 real multi-field papers · "
      f"answering harness: **same omp engine for all tracks** (A/C share the "
      f"identical unified answer prompt with a 4000-char evidence budget; B "
      f"answers from the same engine with file tools and no budget)")
    w("")
    w("| Track | Method | Avg latency | Gold-keyword answers |")
    w("|---|---|:---:|:---:|")
    for key, title, _ in TRACKS:
        lats = [r[key]["latency"] for r in rows]
        hits = sum(1 for r in rows if r[key]["gold_kw_hit"])
        w(f"| {title} | {key} | {sum(lats)/len(lats):.0f} s | {hits}/10 |")
    w("")

    for key, title, desc in TRACKS:
        w(f"## {title}")
        w("")
        w(f"_{desc}_")
        w("")
        w("| QID | Field | Latency | Gold keywords in answer |")
        w("|---|---|:---:|---|")
        for r in rows:
            t = r[key]
            kw = ", ".join(t["gold_kw_hit"]) or "—"
            w(f"| {r['qid']} | {r['field']} | {t['latency']} s | {kw} |")
        w("")
        for r in rows:
            t = r[key]
            w(f"### {r['qid']} — {r['paper']}")
            w("")
            w(f"**Q:** {r['question']}")
            w("")
            ev = t.get("evidence_docs") or t.get("parsed", {}).get("files_used") \
                or []
            if ev:
                w(f"**Sources:** {', '.join(ev[:3])}")
                w("")
            w(f"**Answer:** {t['parsed'].get('answer', '').strip()}")
            w("")
        w("---")
        w("")

    w("## Notes")
    w("")
    w("- Gold-keyword check is a coarse indicator: an answer can be correct")
    w("  without echoing the exact keyword string (e.g. paraphrase).")
    w("- Track A and C answered from their own retrieved evidence under the")
    w("  identical prompt and budget; Track B chose which files to read itself,")
    w("  which explains its higher per-question latency.")
    w("- Raw records (full evidence lists, raw model output): "
      "`results/threeway_qa.json`")
    w("")
    out = RESULTS / "threeway_qa.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"[done] {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
