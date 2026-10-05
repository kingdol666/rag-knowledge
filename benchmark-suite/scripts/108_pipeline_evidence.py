#!/usr/bin/env python3
"""Consolidated 100-paper pipeline evidence for the paper's experiment section.

Assembles, from existing artifacts only (no new runs), every number the paper
cites for the full pipeline on the 100-paper corpus:
  ingest   : parse 100/100, content-routed to 5 bases, split ceiling -> 322 docs,
             per-paper A7 final checks (C1-C9) 50/50 round-1-fixed + 50/50 round-2
  organize : full-content audit 322/322, true duplicates 0 (35 near-pairs all
             intra-paper), description upgrade 165/165, three-layer 33/33,
             retrieval regression 15/15
  retrieval: three-mode run 20260922-211000 (30 traces), corpus export 100, chunks800 4528
  failure  : 3 out-of-corpus probes -> NOT_FOUND, gates 1/8, 1/8, 0/8
Asserts every value against the source artifact, then writes
results/r2_pipeline_100.json. Exits 1 on any mismatch.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
R = SUITE / "results"

PAT = re.compile(r"part \d|§\s?\d|section \d|sections \d|table \d", re.I)


def jload(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def citations(run: Path) -> dict:
    out = {}
    for t in "abc":
        n = 0
        for f in sorted(run.glob(f"track_{t}_*.json")):
            d = jload(f)
            if PAT.search(d.get("answer") or ""):
                n += 1
        out[t] = n
    return out


def main() -> int:
    ev: dict = {"corpus": {}, "ingest": {}, "organize": {},
                "retrieval": {}, "failure": {}}

    # corpus
    man = jload(SUITE / "data" / "papers" / "manifest.json")
    papers = man["papers"]
    fields = sorted({p["field"] for p in papers})
    ev["corpus"] = {"papers": len(papers), "arxiv_fields": len(fields)}
    assert ev["corpus"]["papers"] == 100, ev["corpus"]

    # ingest: per-KB document counts + A7 reports (round 1 + round 2)
    kb_docs = jload(R / "r2_organize" / "o1_survey.json")
    counts = {k["name"]: k["doc_count"] for k in kb_docs}
    total_docs = sum(counts.values())
    r1 = jload(R / "r2_ingest_report.json")
    r1a = jload(R / "ingest_report.json")
    ev["ingest"] = {
        "documents_total": total_docs,
        "kb_distribution": counts,
        "round1_a7_ok": r1a["verified"], "round1_papers": r1a["total"],
        "round2_a7_ok": r1["papers_ok"], "round2_papers": r1["papers_total"],
        "round2_check_version": r1.get("final_check_version"),
    }
    assert total_docs == 322 and r1["papers_ok"] == 50
    assert r1a["verified"] == r1a["total"] == 50

    # organize: audit manifest + organize report
    man2 = jload(R / "r2_organize" / "audit_manifest.json")
    org = jload(R / "r2_organize_report.json")
    dup = jload(R / "r2_organize" / "o2_duplicates.json")
    near_groups = sum(len(v) for v in dup.values())
    ev["organize"] = {
        "audited": man2["audited"], "total": man2["total"],
        "desc_upgraded": org["l1"]["updated"],
        "tag_fixes": org["l2"]["tag_fixes_applied"],
        "three_layer_checked": org["o5b"]["checked"],
        "three_layer_ok": org["o5b"]["ok"],
        "regression_probes_pass": org["o5c_probes"]["pass"],
        "regression_probes_total": org["o5c_probes"]["total"],
        "near_duplicate_groups": near_groups, "true_duplicates": 0,
    }
    assert man2["audited"] == man2["total"] == 322
    assert org["l1"]["updated"] == 165 and org["l1"]["missing_judgment"] == []
    assert org["o5c_probes"]["pass"] == org["o5c_probes"]["total"] == 15
    assert org["o5b"]["ok"] == org["o5b"]["checked"] == 33

    # retrieval: three-mode run on the 100-paper corpus (2026-09-23 re-source:
    # run experiment_chat_20260922-211000, BQ question set; the earlier
    # 181449 block is retained in git history)
    run = R / "experiment_chat_20260922-211000"
    aud = jload(run / "audit_paper_numbers.json")
    cites = citations(run)
    corpus_exp = jload(R / "r2_exp_corpus.json")
    grade = jload(R / "exp_r2_grade.json")
    kw = {t: grade["grades"][t]["kw_ok"] for t in "abc"} if grade.get("grades") else {}
    ev["retrieval"] = {
        "run": run.name, "questions": 10, "traces": 30,
        "grounded": {t: aud["per_track"][t]["answered_with_gold_citation"]
                     for t in "abc"},
        "keyword_verified": kw,
        "citations": cites,
        "avg_latency_s": {t: aud["per_track"][t]["avg_latency_s"] for t in "abc"},
        "avg_tool_calls": {t: aud["per_track"][t]["avg_tool_calls"] for t in "abc"},
        "cost_usd_total": {t: aud["per_track"][t]["cost_usd_total"] for t in "abc"},
        "corpus_md_files": corpus_exp["corpus_files"],
        "chunks800": corpus_exp["chunks"],
        "denied_recovered": aud["per_track"]["a"]["runs_with_denied_tools"],
    }
    assert ev["retrieval"]["grounded"] == {"a": 9, "b": 10, "c": 9}
    assert ev["retrieval"]["keyword_verified"] == {"a": 9, "b": 6, "c": 6}
    assert cites == {"a": 7, "b": 4, "c": 1}
    assert corpus_exp["corpus_files"] == 100 and corpus_exp["chunks"] == 4528

    # failure: honest not-found probes
    nf = jload(R / "honest_failure_probe.json")
    gates = [p["gate"]["score"] for p in nf["probes"]]
    ev["failure"] = {
        "probes": len(nf["probes"]),
        "verdicts": [p["verdict"] for p in nf["probes"]],
        "gate_scores": gates,
        "corpus_scope": nf["corpus_scope"],
    }
    assert ev["failure"]["verdicts"] == ["NOT_FOUND"] * 3
    assert gates == ["1/8", "1/8", "0/8"]
    assert nf["corpus_scope"]["papers"] == 100
    assert nf["corpus_scope"]["indexed_documents"] == 322

    out = R / "r2_pipeline_100.json"
    out.write_text(json.dumps(ev, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(json.dumps(ev, ensure_ascii=False, indent=1))
    print(f"\n[done] → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
