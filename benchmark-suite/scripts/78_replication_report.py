#!/usr/bin/env python3
# DEPRECATED 2026-09-20 — superseded by the experiments/ platform
# (python -m experiments.runner, chat API + harness=claude). Kept only to
# reproduce historical reports. Do not use for new retrieval testing.
"""复刻实验汇整报告 — QDCVR v2 skill 流程 vs 裸 Agent vs dense 复刻.
每题分别记录: 分步执行时间 + 原始最终回答(全文, 不删节)。"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
RESULTS = SUITE / "results"


def _load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _pipeline_section(w) -> None:
    """管线执行统计 + RAG 向量库全覆盖 + 检索回归 (全部取自落盘工件, 缺失写 unmeasured)."""
    survey = _load(RESULTS / "ingest_survey.json")
    ingest = _load(RESULTS / "ingest_report.json")
    tags = _load(RESULTS / "tags_report.json")
    repro = _load(RESULTS / "repro_ingest.json")
    cov = _load(RESULTS / "repro_coverage.json")
    bench = _load(RESULTS / "bench10_qa.json")

    w("## Pipeline execution & corpus coverage")
    w("")
    w("| Stage | Result |")
    w("|---|---|")
    if survey:
        w(f"| Papers parsed into staging (MinerU → Papers-Inbox) | {survey.get('n', 'unmeasured')}/{len(survey.get('papers', [])) or 'unmeasured'} |")
    else:
        w("| Papers parsed into staging | unmeasured |")
    if ingest:
        w(f"| Routed into 5 category KBs (probe-verified) | {ingest.get('verified', 'unmeasured')}/{ingest.get('total', 'unmeasured')} |")
        graph = ingest.get("graph") or {}
        w(f"| Category knowledge graphs built | {sum(1 for v in graph.values() if v)}/{len(graph)} |")
    if tags:
        w(f"| Content tags applied to document parts | ok={tags.get('ok', 'unmeasured')} fail={tags.get('fail', 'unmeasured')} |")
    if repro:
        baselines = repro.get("baselines") or {}
        for name in ("Corpus-Chunks800", "Corpus-Struct", "Corpus-Paras"):
            if name in baselines:
                w(f"| RAG index `{name}` chunks indexed | {baselines[name]} |")
    if cov:
        for kb, st in (cov.get("kbs") or {}).items():
            w(f"| Coverage `{kb}` | chunks expected {st.get('expected_chunks')} = "
              f"indexed_ok {st.get('build_indexed_ok')} (errors {st.get('build_errors')}) · "
              f"per-doc retrieval probes {st.get('probe_hit')}/{st.get('probe_total')} · "
              f"{'PASS' if st.get('pass') else 'FAIL'} |")
    else:
        w("| Vector-store coverage check | unmeasured |")
    if bench:
        w(f"| 10-question retrieval regression (`kb_search_vector`) | {bench.get('passed')}/{bench.get('total')} = {bench.get('pass_rate')} |")
    else:
        w("| 10-question retrieval regression | unmeasured |")
    w("")
    w("All questions are asked in **English**; every answer below is produced in "
      "**English** (answer prompts enforce it; the Track A five-section answers "
      "are written in English by the executing agent).")
    w("")


def main() -> int:
    ev = json.loads((RESULTS / "skill_track_evidence.json").read_text("utf-8"))
    ans = json.loads((RESULTS / "skill_track_answers.json").read_text("utf-8"))
    bc = json.loads((RESULTS / "track_bc.json").read_text("utf-8"))
    answers = {a["qid"]: a for a in ans["answers"]}
    bcmap = {r["qid"]: r for r in bc}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    L = []
    w = L.append
    w("# Three-Track Replication — QDCVR v2 Skill Flow vs Bare Agent vs Dense Baseline")
    w("")
    w(f"Generated {now} · corpus: 50 real multi-field papers · 10 content-grounded questions")
    w("")
    w("| Track | Retrieval | Answering |")
    w("|---|---|---|")
    w("| A · Platform KB retrieval | **QDCVR v2 skill flow, executed step by step**: Phase 0 query rewrite → Phase 1 `kb_search_vector` per category KB (balance) → doc dedup → `kb_doc_read` content gate (0-8 rubric, ≥6 fast exit) → Phase 2 librarian targeted recall when gate fails → five-section answer | composed by the executing agent per the skill's Phase 3 format |")
    w("| B · Bare agent | no index — same omp engine with file tools over `data/corpus_md/` (50 md files) | the agent's own final JSON answer, recorded verbatim |")
    w("| C · Dense baseline (reproduction) | `methods.dense` over Corpus-Chunks800 → 4000-char evidence pack | unified SCEN_ANSWER_PROMPT on the same omp engine |")
    w("")
    _pipeline_section(w)

    # ── Track A ──
    w("## Track A — QDCVR v2 skill flow (platform KB retrieval)")
    w("")
    w("| QID | Phase1 vector | Doc reads | Gate (0-8) | Decision | Phase 2 |")
    w("|---|:---:|:---:|:---:|---|:---:|")
    for e in ev:
        a = answers[e["qid"]]
        p2 = "yes (librarian fallback)" if "phase2" in e else "—"
        w(f"| {e['qid']} | {e['timings']['phase1_vector_search']} s | "
          f"{e['timings']['phase1_doc_reads']} s | {a['gate']['score']} | "
          f"{a['gate']['decision']} | {p2} |")
    w("")
    for e in ev:
        a = answers[e["qid"]]
        w(f"### {e['qid']} — {e['paper']}")
        w("")
        w(f"- **Phase 0 rewrite:** `{e['rewritten_query']}`")
        w(f"- **Gate:** best {a['gate']['score']}/8 — {a['gate']['decision']}")
        if "phase2" in e:
            w(f"- **Phase 2:** targeted search {e['phase2']['timings']['targeted_search']} s, "
              f"continuation reads {e['phase2']['timings']['continuation_reads']} s "
              f"in {e['phase2']['kb']}")
        w("")
        w("**Final answer (verbatim, five-section format):**")
        w("")
        w(a["final_answer"])
        w("")
    w("---")
    w("")

    # ── Track B ──
    w("## Track B — Bare agent direct search (same omp engine, file tools)")
    w("")
    lats = [bcmap[r["qid"]]["track_b_bare_agent"]["latency"] for r in bc]
    w(f"Average latency: **{sum(lats)/len(lats):.0f} s** per question "
      f"(independent omp session per question; it lists/greps/reads files itself).")
    w("")
    for r in bc:
        b = r["track_b_bare_agent"]
        w(f"### {r['qid']} — {r['paper']}")
        w("")
        w(f"**Q:** {r['question']}")
        w("")
        w(f"**Execution:** {b['latency']} s · {b['omp_calls']} omp turn · "
          f"files used: {', '.join(b['files_used']) or '—'}")
        w("")
        w("**Final answer (verbatim):**")
        w("")
        w(b["raw_answer"])
        w("")
    w("---")
    w("")

    # ── Track C ──
    w("## Track C — Dense baseline (RAG reproduction, Corpus-Chunks800)")
    w("")
    rets = [bcmap[r["qid"]]["track_c_dense_rag"]["latency_retrieval"] for r in bc]
    anss = [bcmap[r["qid"]]["track_c_dense_rag"]["latency_answer"] for r in bc]
    w(f"Average retrieval **{sum(rets)/len(rets):.2f} s** + answering "
      f"**{sum(anss)/len(anss):.0f} s** (unified SCEN_ANSWER_PROMPT, 4000-char "
      f"evidence pack).")
    w("")
    for r in bc:
        c = r["track_c_dense_rag"]
        w(f"### {r['qid']} — {r['paper']}")
        w("")
        w(f"**Q:** {r['question']}")
        w("")
        w(f"**Execution:** retrieval {c['latency_retrieval']} s · answering "
          f"{c['latency_answer']} s · {c['evidence_chunks']} chunks / "
          f"{c['evidence_chars']} chars evidence")
        if c.get("evidence_docs"):
            w("")
            w(f"**Sources:** {', '.join(c['evidence_docs'][:3])}")
        w("")
        w("**Final answer (verbatim):**")
        w("")
        w(c["raw_answer"])
        w("")
    w("---")
    w("")
    w("Raw records: `skill_track_evidence.json` · `skill_track_answers.json` · "
      "`track_bc.json`")
    w("")
    out = RESULTS / "skill_threeway_replication.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"[done] {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
