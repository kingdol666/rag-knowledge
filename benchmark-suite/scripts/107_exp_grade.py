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
TRACKS = ["a", "b", "c"]


def kw_hit(answer: str, kws: list[str]) -> list[str]:
    low = answer.lower()
    hits = []
    for k in kws:
        core = re.escape(k.lower())
        # 纯数字词允许序数后缀(95 ≡ 95th), 数量词义不变
        if k.isdigit():
            core += r"(?:st|nd|rd|th)?"
        pat = r"(?<![a-z0-9])" + core + r"(?![a-z0-9])"
        if re.search(pat, low):
            hits.append(k)
    return hits


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="", help="experiment_chat_* 目录名(默认最新)")
    ap.add_argument("--qfile", default="",
                    help="题集 JSON（默认 qa_questions_r2.json；BQ 题集传 "
                         "data/papers/qa_questions.json）")
    args = ap.parse_args()
    run_dir = (RESULTS / args.run) if args.run else \
        sorted(RESULTS.glob("experiment_chat_*"))[-1]
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
        kws = kw_hit(str(r.get("answer") or ""), q.get("gold_keywords", []))
        need = max(1, -(-len(q.get("gold_keywords", [])) * 3 // 5))
        kw_ok = len(kws) >= need
        rows.append({"qid": r.get("qid"), "track": r.get("track"),
                     "gold": gid, "gold_hit": gold_hit,
                     "kw": kws, "kw_ok": kw_ok,
                     "pass": bool(gold_hit and kw_ok),
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
            "pass": sum(r["pass"] for r in tr),
            "pass_rate": round(sum(r["pass"] for r in tr) / len(tr), 3),
            "avg_latency_s": round(sum(lat) / len(tr), 1),
            "avg_tools": round(sum(r["tools"] or 0 for r in tr) / len(tr), 1),
            "avg_cost_usd": round(sum(r["cost_usd"] or 0 for r in tr) /
                                  len(tr), 4),
            "tokens_out_total": sum(r["tokens_out"] or 0 for r in tr),
        }

    out = {"run_dir": run_dir.name, "grades": grades, "rows": rows}
    (RESULTS / "exp_r2_grade.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    lines = ["# 三模式检索实验报告 (Three-Track Experiment)", "",
             f"Run: `{run_dir.name}` · 题集: `{qname}` · "
             f"语料: 平台五门类库 = corpus_md 100 篇 = Corpus-Chunks800", "",
             "## 分轨结果", "",
             "| 轨 | 模式 | pass | gold 命中 | 关键词核验 | 平均时延 s | 平均工具数 | 平均成本 $ |",
             "|---|---|---|---|---|---:|---:|---:|"]
    tname = {"a": "A 平台 KB(QDCVR 工具面)", "b": "B 裸 Agent(文件工具)",
             "c": "C Dense-RAG(Chunks800)"}
    for t in TRACKS:
        g = grades.get(t)
        if not g:
            continue
        lines.append(f"| {t.upper()} | {tname[t]} | {g['pass']}/{g['n']} | "
                     f"{g['gold_hit']}/{g['n']} | {g['kw_ok']}/{g['n']} | "
                     f"{g['avg_latency_s']} | {g['avg_tools']} | "
                     f"{g['avg_cost_usd']} |")
    lines += ["", "## 逐题判分", "",
              "| QID | 轨 | gold | 关键词命中 | pass | 时延 s | 工具数 |", "|---|---|---|---|---|---:|---:|"]
    for r in rows:
        lines.append(f"| {r['qid']} | {str(r['track']).upper()} | "
                     f"{'✓' if r['gold_hit'] else '✗'} | "
                     f"{len(r['kw'])}/{len(gold.get(r['qid'], {}).get('gold_keywords', []))}"
                     f"{' (' + ','.join(r['kw']) + ')' if r['kw'] else ''} | "
                     f"{'✅' if r['pass'] else '❌'} | {r['latency_s']} | "
                     f"{r['tools']} |")
    lines += ["", "## 判分说明", "",
              "- pass = 金标论文可追溯(答案/工具轨迹含金标 id) 且 答案含 ≥60% 金标关键词(词边界匹配)。",
              "- C 轨金标证据依赖提示词要求的 chunk 文件名引用; 拒答(insufficient evidence)计为未通过。",
              "- 判分完全确定性(词边界正则), 不经 LLM; 逐题 trace 见 run 目录 track_*.json。",
              "", "逐字答案与监控表见 run 目录 `SUMMARY.md`。"]
    (RESULTS / "R2-EXP-3TRACK-REPORT.md").write_text(
        "\n".join(lines), encoding="utf-8")
    print(f"[grade] " + " | ".join(
        f"{t.upper()} {g['pass']}/{g['n']}" for t, g in grades.items()))
    print(f"[report] → {RESULTS / 'R2-EXP-3TRACK-REPORT.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
