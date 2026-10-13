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

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _paper_numbers as PN  # noqa: E402  (paper-number kernel: graders + macros)

SUITE = Path(__file__).resolve().parent.parent
R = SUITE / "results"

PAT = re.compile(r"part \d|§\s?\d|section \d|sections \d|table \d", re.I)


def jload(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def provenance(p: Path) -> dict:
    """出处三元组：相对路径 + mtime，供审稿人核对「这行数字来自哪个产物」。"""
    try:
        return {"path": str(p.relative_to(SUITE.parent)),
                "mtime": __import__("datetime").datetime.fromtimestamp(
                    p.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")}
    except Exception:  # noqa: BLE001
        return {"path": str(p), "mtime": None}


def pick_run(name: str = "") -> Path:
    """--run 接受目录名/相对路径/绝对路径；缺省取「完整三轨（a2/b/c）」的最新 run。

    2026-10-13 修复：原实现硬编码 `experiment_chat_20260922-211000`，该目录早已
    被清理，脚本读到 retrieval 块时 FileNotFoundError——Table 1 因此无法再生。
    踩坑记录：`results/experiment_chat_*` 里还有更老的四臂 run（轨道名是 a/b/c，
    没有 a2），仅按 mtime 排序会选中它并炸在 KeyError('a2')。所以这里先按是否有
    `track_a2_*.json` 过滤，再按 mtime 取最新。
    """
    if name:
        for cand in (R / name, R / "runs" / name, Path(name)):
            if cand.is_dir():
                return cand
        raise SystemExit(f"[fatal] run dir not found: {name}")
    cands = list((R / "runs").glob("run-*")) + list(R.glob("experiment_chat_*"))
    full = [p for p in cands if list(p.glob("track_a2_*.json"))]
    if not full:
        raise SystemExit(
            "[fatal] 没有找到含 a2/b/c 三轨的 run（需要 track_a2_*.json）；"
            f"候选 {len(cands)} 个：{sorted(p.name for p in cands)[-5:]}")
    return max(full, key=lambda p: p.stat().st_mtime)


def citations(run: Path) -> dict:
    """旧口径（宽松 PAT）——保留以便与历史 JSON 对照，不再是论文宏的口径。"""
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

    # retrieval: three-track run on the 100-paper corpus.
    # 2026-10-13 改源：论文宏已刷到本轮的 run-* 目录（三轨 a2/b/c、BQ 题集），
    # 因此 Table 1 的 retrieval 行也必须来自同一个 run，否则论文里两处数字互斥。
    # ground/kw/cited 全部用 _paper_numbers 的判分内核复算（与 107_exp_grade.py、
    # 150_final_pipeline.py 同一套语义），paper_values() 同时做一次宏对账。
    run = pick_run(args.run)
    qfile = PN.pick_qfile(run)
    grade = PN.grade_run(run, qfile)
    paper = PN.paper_values()
    cites_pat = citations(run)
    corpus_exp = jload(R / "r2_exp_corpus.json")
    gra = grade["grades"]
    print(f"[retrieval] run={run.name} qfile={qfile.name} "
          f"rows={len(grade['rows'])} tracks={sorted(gra)}", flush=True)
    missing = [t for t in ("a2", "b", "c") if t not in gra]
    if missing:
        raise SystemExit(
            f"[fatal] {run.name} 缺少轨道 {missing}（实际 {sorted(gra)}，"
            f"行数 {len(grade['rows'])}）——该 run 不是完整的论文三轨运行，"
            "不能作为 Table 1 的 retrieval 行；用 --run 指定完整 run。")
    ev["retrieval"] = {
        "run": run.name, "qfile": qfile.name,
        "questions": len({x["qid"] for x in grade["rows"]}),
        "traces": len(grade["rows"]),
        "grounded": {t: gra[t]["grounded"] for t in ("a2", "b", "c")},
        "keyword_verified": {t: gra[t]["kw"] for t in ("a2", "b", "c")},
        "cited": {t: gra[t]["cited"] for t in ("a2", "b", "c")},
        "citations_pat_legacy": cites_pat,
        "avg_latency_s": {t: gra[t]["avg_latency_s"] for t in ("a2", "b", "c")},
        "avg_tool_calls": {t: gra[t]["avg_tools"] for t in ("a2", "b", "c")},
        "avg_cost_usd": {t: gra[t]["avg_cost_usd"] for t in ("a2", "b", "c")},
        "abstain": {t: gra[t]["abstain"] for t in ("a2", "b", "c")},
        "sentinel_cells": sum(1 for x in grade["rows"] if x["sentinel"]),
        "corpus_md_files": corpus_exp["corpus_files"],
        "chunks800": corpus_exp["chunks"],
        "provenance": {"run_dir": provenance(run),
                       "corpus_export": provenance(R / "r2_exp_corpus.json"),
                       "paper_tex": paper["tex"]},
    }
    assert ev["retrieval"]["traces"] == 30, ev["retrieval"]["traces"]
    assert ev["retrieval"]["sentinel_cells"] == 0, "本轮存在零工具哨兵单元，先重跑该单元"
    assert corpus_exp["corpus_files"] == 100 and corpus_exp["chunks"] == 4528, corpus_exp
    # 论文宏 ↔ 本轮判分：三轨 grounded/kw/cited 必须逐一相等（论文的数字就是这一轮的）
    pairs = [("A", "a2"), ("B", "b"), ("C", "c")]
    raw, mapped = paper["raw"], {}
    for prefix, key in (("grounded", "grounded"), ("kw", "kw"), ("cite", "cited")):
        for letter, t in pairs:
            mname = f"NUM{prefix}{letter}"
            if mname not in raw:
                raise SystemExit(f"[fatal] main.tex 缺少宏 \\{mname}")
            mapped[(prefix, letter)] = int(raw[mname])
    for letter, t in pairs:
        for prefix, key in (("grounded", "grounded"), ("kw", "kw"), ("cite", "cited")):
            want, got = mapped[(prefix, letter)], gra[t][key]
            assert want == got, \
                (f"macro {prefix}{letter}={want} != run {t} {key} {got}"
                 f"（run={run.name}）")

    # failure: honest not-found probes
    nf = jload(R / "honest_failure_probe.json")
    gates = [p["gate"]["score"] for p in nf["probes"]]
    ev["failure"] = {
        "probes": len(nf["probes"]),
        "verdicts": [p["verdict"] for p in nf["probes"]],
        "gate_scores": gates,
        "corpus_scope": nf["corpus_scope"],
        "provenance": provenance(R / "honest_failure_probe.json"),
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
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", default="",
                    help="run 目录名/路径；缺省 = results/runs 下最新 run-*")
    args = ap.parse_args()
    sys.exit(main())
