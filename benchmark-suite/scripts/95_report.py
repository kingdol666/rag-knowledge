#!/usr/bin/env python3
"""Step 5 — 汇总报告: 三个阶段 JSON → results/BENCHMARK.md(英文, 简明)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
RESULTS = SUITE / "results"
PAPERS = SUITE / "data" / "papers"


def load(name: str) -> dict:
    try:
        return json.loads((RESULTS / name).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def main() -> int:
    up, rq, ex = (load("upload_parse.json"), load("retrieval_qa.json"),
                  load("experience_smoke.json"))
    man = load(str(PAPERS / "manifest.json").replace(str(SUITE) + "/", "")) \
        if not (PAPERS / "manifest.json").exists() else \
        json.loads((PAPERS / "manifest.json").read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    L: list[str] = []
    w = L.append
    w("# Platform Smoke Benchmark — rag-knowledge")
    w("")
    w(f"Generated {now} · pipeline: `benchmark-suite/TEST-PLAN.md` · corpus: "
      f"{len(man.get('papers', []))} real multi-field papers in `data/papers/`")
    w("")
    w("Simple functional tests only: document parse/upload, content retrieval QA,")
    w("experience summarisation. No IR metrics, no LLM judge, no baseline")
    w("comparison — deterministic checks against the live platform.")
    w("")
    w("## 1. Document parse & upload (official MinerU chain)")
    w("")
    w(f"- Papers parsed & stored: **{up.get('papers_parsed')}/{up.get('papers_total')}**"
      f" · catalog documents: {up.get('docs_in_catalog')}"
      f" · batch-indexed: {up.get('batch_indexed')}")
    w(f"- Per-paper vector probes: {'**all ok**' if up.get('all_probes_ok') else '**FAILED**'}"
      f" · graph build: **{up.get('graph_build_ok')}** · tags: {up.get('tags_count')}"
      f" · wall time: {up.get('seconds')} s")
    w("")
    w("## 2. Content retrieval QA (1 question per paper, deterministic)")
    w("")
    w(f"- Pass rate: **{rq.get('passed')}/{rq.get('total')}"
      f" ({rq.get('pass_rate', 0):.0%})** — gold document in top-3 AND keyword"
      " verified in retrieved content")
    w("")
    w("| QID | Field | Doc hit | Keywords hit | Verdict |")
    w("|---|---|:---:|---|:---:|")
    for r in rq.get("rows", []):
        w(f"| {r['qid']} | {r['field']} | {r['doc_hit']} | "
          f"{', '.join(r['keywords_hit']) or '—'} | {'PASS' if r['pass'] else 'FAIL'} |")
    w("")
    w("## 3. Experience summarisation (deterministic smoke)")
    w("")
    w(f"- Extractor candidates: {ex.get('extract_candidates')} · drafts created: "
      f"{ex.get('drafts_created')} · library size: {ex.get('list_count')}")
    w(f"- Create + search round-trip: **{'PASS' if ex.get('pass') else 'FAIL'}**"
      f" (created experience found by search: {ex.get('search_hit')})")
    w("")
    w("## Verdict")
    w("")
    checks = [up.get("papers_parsed") == up.get("papers_total"),
              up.get("all_probes_ok"), rq.get("pass_rate", 0) >= 0.9,
              ex.get("pass")]
    labels = ["parse/upload", "index probes", "retrieval QA >= 90%",
              "experience round-trip"]
    for label, okc in zip(labels, checks):
        w(f"- {'✅' if okc else '❌'} {label}")
    all_ok = all(checks)
    w("")
    w(f"**Overall: {'PASS' if all_ok else 'FAIL'}**")
    w("")
    out = RESULTS / "BENCHMARK.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"[done] {out}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
