#!/usr/bin/env python3
"""Exp 三轨实验确定性判分 + 报告生成.

判分(不用 LLM):
  gold_evidence = 金标论文 id(slug 连字符形或斜杠形)出现在
                  answer + texts_full + tool_calls 序列化文本任一处
                  (A 轨: kb_doc_read 的 doc_path / 检索 query;
                   B 轨: Read/Grep 的 file_path 与 pattern;
                   C 轨: 按提示词要求在答案中引用的 chunk 文件名)
  kw_hit        = gold_keywords 全部按词边界正则在 answer 命中(大小写不敏感)
  pass          = gold_evidence and kw_hit
输出 results/exp_r2_grade.json + results/R2-EXP-3TRACK-REPORT.md。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
RESULTS = SUITE / "results"
QFILE = SUITE / "data" / "papers" / "qa_questions_r2.json"
TRACKS = ["a", "a2", "b", "c"]  # a2 = leakage-free platform arm (2026-09-30 rerun)

# Citation-marker presence is a lexical proxy, not citation correctness.
# Accept numeric and Roman-numeral section locators, including subsections
# (e.g. §III-C); reject ordinary prose such as "sections for Europe".
CITE_PART = r"\bparts?\s+\d+\s+of\s+\d+"
_CITE_NUMBER = r"(?:\d+(?:\.\d+)*(?:-[A-Z0-9]+)?|[IVXLCDM]+(?:-[A-Z0-9]+)?)"
CITE_STRUCT = (r"\b(?:section|sections|table|tables|appendix|appendices)\s+"
               + _CITE_NUMBER + r"\b")
CITE_SECT = r"§\s*" + _CITE_NUMBER + r"\b"
CITE_CHUNK = r"\bchunk[_ ]?(?:index|id)?\s*\d+"
CITE_DEF = ("part/section/table markers present: " + CITE_PART + " | " +
            CITE_STRUCT + " | " + CITE_SECT)
CITE_DEF_DENSE = ("dense chunk references (reported separately, NOT counted in "
                  "the paper's cited numbers): " + CITE_CHUNK)
RX_CITE = re.compile(f"(?:{CITE_PART}|{CITE_STRUCT}|{CITE_SECT})", re.I)
RX_CITE_DENSE = re.compile(CITE_CHUNK, re.I)

# Explicit lexical aliases for known acronym/concept variants. The original
# strict keyword result is retained alongside this revised coverage check.
KW_ALIASES = {
    "BQ09": {"multilayer perceptron": (r"\bmlp(?:-slam)?\b",)},
    "BQ10": {"immune evasion": (
        r"\bimmune[- ]resistant\b",
        r"\bimmune checkpoint (?:evasion|resistance|regulation)\b",
        r"\breduced antigen presentation\b",
    )},
}

def merge_declared_aliases(question: dict) -> dict[str, tuple[str, ...]]:
    """Merge per-question aliases with the stable script defaults."""
    aliases = dict(KW_ALIASES.get(question.get("qid", ""), {}))
    declared = question.get("gold_keyword_aliases") or {}
    if isinstance(declared, dict):
        items = declared.items()
    else:
        items = zip(question.get("gold_keywords", []), declared)
    for keyword, forms in items:
        aliases[keyword.lower()] = tuple(
            re.escape(str(form).lower()) for form in forms)
    return aliases


def cite_markers(answer: str) -> tuple[bool, bool, list[str]]:
    """返回 (论文口径 cited, 稠密 chunk 引用, 命中的标记样例)。"""
    ans = str(answer or "")
    hits = sorted({m.group(0).strip() for m in RX_CITE.finditer(ans)})
    return bool(hits), bool(RX_CITE_DENSE.search(ans)), hits


def kw_hit(answer: str, kws: list[str], qid: str = "", aliases: bool = False,
           alias_map: dict[str, tuple[str, ...]] | None = None) -> list[str]:
    low = answer.lower()
    hits = []
    alias_map = alias_map or (KW_ALIASES.get(qid, {}) if aliases else {})
    for k in kws:
        core = re.escape(k.lower())
        # Pure numeric terms allow ordinal suffixes (95 == 95th).
        if k.isdigit():
            core += r"(?:st|nd|rd|th)?"
        pat = r"(?<![a-z0-9])" + core + r"(?![a-z0-9])"
        if re.search(pat, low) or any(re.search(alias, low)
                                      for alias in alias_map.get(k.lower(), ())):
            hits.append(k)
    return hits


def resolve_run(arg: str) -> Path:
    """--run 接受：目录名 / 相对路径 / 绝对路径；默认取最新 run。

    历史遗留：老式实验目录在 results/experiment_chat_*，当前运行器写在
    results/runs/run-*。两者都要找得到（2026-10-13：旧版只 glob
    results/experiment_chat_*，对当前的 runs/run-* 失效 → 判分报 no track）。
    """
    if arg:
        p = Path(arg)
        for cand in (p, RESULTS / arg, RESULTS / "runs" / arg):
            if cand.is_dir():
                return cand
        return p  # 交给下游报错
    old = sorted(RESULTS.glob("experiment_chat_*"))
    new = [d for d in (RESULTS / "runs").glob("run-*") if d.is_dir()]
    cands = old + new
    if not cands:
        return RESULTS / "experiment_chat_missing"
    return max(cands, key=lambda d: (d.stat().st_mtime, d.name))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="", help="run 目录（名/相对/绝对路径，默认最新）")
    ap.add_argument("--qfile", default="",
                    help="question set JSON (default qa_questions_r2.json)")
    ap.add_argument("--grade-out", default="",
                    help="grade JSON output path (default results/exp_r2_grade.json)")
    ap.add_argument("--report-out", default="",
                    help="report Markdown output path (default results/R2-EXP-3TRACK-REPORT.md)")
    args = ap.parse_args()
    run_dir = resolve_run(args.run)
    qfile = SUITE / args.qfile if args.qfile else QFILE
    gold = {q["qid"]: q for q in
            json.loads(qfile.read_text(encoding="utf-8"))["questions"]}
    qname = qfile.name
    files = sorted(run_dir.glob("track_*.json"))
    if not files:
        print(f"no track_*.json under {run_dir}")
        return 1

    rows = []
    for f in files:
        r = json.loads(f.read_text(encoding="utf-8"))
        q = gold.get(r.get("qid"), {})
        gid = q.get("arxiv_id", "")
        gid_alt = gid.replace("-", "/")
        trace = json.dumps(r.get("tool_calls") or [], ensure_ascii=False) + \
            "\n" + "\n".join(r.get("texts_full") or [])
        blob = str(r.get("answer") or "") + "\n" + trace
        gold_hit = bool(gid and (gid in blob or gid_alt in blob))
        kws_strict = kw_hit(str(r.get("answer") or ""), q.get("gold_keywords", []),
                            qid=r.get("qid", ""), aliases=False)
        alias_map = merge_declared_aliases(q)
        kws_alias = kw_hit(str(r.get("answer") or ""), q.get("gold_keywords", []),
                           qid=r.get("qid", ""), aliases=True,
                           alias_map=alias_map)
        need = max(1, -(-len(q.get("gold_keywords", [])) * 3 // 5))
        kw_ok = len(kws_strict) >= need
        kw_alias_ok = len(kws_alias) >= need
        cited, cited_chunk, cmarkers = cite_markers(r.get("answer"))
        rows.append({"qid": r.get("qid"), "track": r.get("track"),
                     "gold": gid, "gold_hit": gold_hit,
                     "kw": kws_strict, "kw_alias": kws_alias,
                     "kw_ok": kw_ok, "kw_alias_ok": kw_alias_ok,
                     "pass": bool(gold_hit and kw_ok),
                     "pass_alias": bool(gold_hit and kw_alias_ok),
                     "cited": cited, "cited_chunk": cited_chunk,
                     "cite_markers": cmarkers,
                     "is_error": r.get("is_error"),
                     "latency_s": r.get("latency_s"),
                     "tools": r.get("tool_call_count"),
                     "cost_usd": r.get("total_cost_usd"),
                     "tokens_out": (r.get("tokens") or {}).get("output"),
                     "insufficient_evidence": "insufficient" in
                     str(r.get("answer") or "").lower()})

    grades = {}
    for t in TRACKS:
        tr = [r for r in rows if r["track"] == t]
        if not tr:
            continue
        lat = [r["latency_s"] or 0 for r in tr]
        grades[t] = {
            "n": len(tr),
            "gold_hit": sum(r["gold_hit"] for r in tr),
            "kw_ok": sum(r["kw_ok"] for r in tr),
            "kw_alias_ok": sum(r["kw_alias_ok"] for r in tr),
            "pass": sum(r["pass"] for r in tr),
            "pass_alias": sum(r["pass_alias"] for r in tr),
            "pass_rate": round(sum(r["pass"] for r in tr) / len(tr), 3),
            "pass_alias_rate": round(sum(r["pass_alias"] for r in tr) / len(tr), 3),
            "cited": sum(r["cited"] for r in tr),
            "cited_chunk": sum(r["cited_chunk"] for r in tr),
            "avg_latency_s": round(sum(lat) / len(lat), 1),
            "avg_tools": round(sum(r["tools"] or 0 for r in tr) / len(tr), 1),
            "avg_cost_usd": round(sum(r["cost_usd"] or 0 for r in tr) /
                                  len(tr), 4),
            "tokens_out_total": sum(r["tokens_out"] or 0 for r in tr),
        }

    grade_out = Path(args.grade_out) if args.grade_out else RESULTS / "exp_r2_grade.json"
    report_out = Path(args.report_out) if args.report_out else RESULTS / "R2-EXP-3TRACK-REPORT.md"
    grade_out.parent.mkdir(parents=True, exist_ok=True)
    report_out.parent.mkdir(parents=True, exist_ok=True)
    out = {"run_dir": run_dir.name, "question_file": qname,
           "grades": grades, "rows": rows,
           "citation_definition": CITE_DEF,
           "citation_definition_dense": CITE_DEF_DENSE,
           "keyword_alias_policy": KW_ALIASES}
    grade_out.write_text(json.dumps(out, ensure_ascii=False, indent=1),
                         encoding="utf-8")

    lines = ["# Three-Track Experiment (deterministic regrade)", "",
             f"Run: `{run_dir.name}` · question set: `{qname}` · 100-paper corpus", "",
             "## Arm-level results", "",
             "| Arm | Gold-ID coverage | Strict keyword | Alias-aware keyword | Strict pass | Alias-aware pass | Citation markers | Chunk markers | Mean wall s | Mean cost USD |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for t in TRACKS:
        g = grades.get(t)
        if not g:
            continue
        lines.append(f"| {t.upper()} | {g['gold_hit']}/{g['n']} | "
                     f"{g['kw_ok']}/{g['n']} | {g['kw_alias_ok']}/{g['n']} | "
                     f"{g['pass']}/{g['n']} | {g['pass_alias']}/{g['n']} | "
                     f"{g['cited']}/{g['n']} | {g['cited_chunk']}/{g['n']} | "
                     f"{g['avg_latency_s']} | {g['avg_cost_usd']:.4f} |")
    lines += ["", "## Per-question grades", "",
              "| QID | Arm | Gold-ID | Strict keywords | Alias-aware keywords | Citation marker | Strict pass | Alias-aware pass | Wall s | Tools |",
              "|---|---|---|---:|---:|---|---|---|---:|---:|"]
    for r in rows:
        kws = gold.get(r["qid"], {}).get("gold_keywords", [])
        lines.append(f"| {r['qid']} | {str(r['track']).upper()} | "
                     f"{'yes' if r['gold_hit'] else 'no'} | "
                     f"{len(r['kw'])}/{len(kws)} | {len(r['kw_alias'])}/{len(kws)} | "
                     f"{'yes' if r['cited'] else 'no'}"
                     f"{' (' + ', '.join(r['cite_markers'][:3]) + ')' if r['cite_markers'] else ''} | "
                     f"{'yes' if r['pass'] else 'no'} | "
                     f"{'yes' if r['pass_alias'] else 'no'} | "
                     f"{r['latency_s']} | {r['tools']} |")
    lines += ["", "## Scoring definitions", "",
              "- Gold-ID coverage means the gold identifier occurs in the answer or recorded retrieval trace; it is provenance/document contact, not semantic grounding.",
              "- Strict keyword coverage uses the original exact lexical keywords and the 60% threshold.",
              "- Alias-aware keyword coverage additionally accepts the explicit aliases defined for BQ09 and BQ10; it remains lexical coverage, not a factuality score.",
              "- Citation-marker hits are syntactic locator-pattern matches. They do not test whether a locator resolves or supports an answer claim.",
              "- Chunk identifiers are counted separately and are not document citation markers.",
              f"  Citation regex: `{CITE_DEF}`",
              f"  Chunk regex: `{CITE_DEF_DENSE}`",
              "- This report regrades immutable saved answers and traces; raw run records are unchanged.",
              "", "Verbatim answers and run monitoring are in `SUMMARY.md`."]

    report_out.write_text("\n".join(lines), encoding="utf-8")
    print(f"[grade] " + " | ".join(
        f"{t.upper()} strict {g['pass']}/{g['n']} alias {g['pass_alias']}/{g['n']}"
        for t, g in grades.items()))
    print(f"[grade json] → {grade_out}")
    print(f"[report] → {report_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
