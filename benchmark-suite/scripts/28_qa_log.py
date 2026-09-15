#!/usr/bin/env python3
"""全量问答日志 — 把 E16 矩阵中所有问题 × 所有 RAG 算法的回答完整汇整.

输入: results/run-*/deepread_matrix.json (最新一次)
输出: results/RETRIEVAL-QA-LOG.log   (纯文本完整日志, 一行不落)
      results/RETRIEVAL-QA-LOG.md    (结构化 Markdown 汇总)
每个条目: 问题(含金标) → 该方法的检索排名 → 引用来源 → 完整回答 → 判分与理由。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent / "results"


def latest(pattern: str) -> Path | None:
    hits = sorted(RESULTS.glob(f"run-*/{pattern}"))
    return hits[-1] if hits else None


def main() -> int:
    src = latest("deepread_matrix.json")
    if not src:
        print("deepread_matrix.json 不存在 — 先跑 retrieval_track 的 E16 阶段")
        return 1
    d = json.loads(src.read_text(encoding="utf-8"))
    meta = d.get("meta") or {}
    methods = list((d.get("summary") or {}).get("retrieval") or {})
    qa = d.get("qa") or []

    by_q: dict[str, dict] = {}
    for item in qa:
        by_q.setdefault(item["qid"], {})[item["method"]] = item

    order = []
    for item in qa:
        if item["qid"] not in order:
            order.append(item["qid"])

    hdr = [
        "=" * 78,
        "RETRIEVAL QA LOG — 全部问题 × 全部 RAG 算法 回答完整记录",
        "=" * 78,
        f"来源     : {src}",
        f"语料     : {meta.get('corpus', '')}",
        f"问题数   : {len(order)}  方法数: {len(methods)}  问答对: {len(qa)}",
        f"回答通道 : {meta.get('agent_channel', '')}",
        f"判分     : {meta.get('judge', '')}",
        f"证据预算 : {meta.get('evidence_budget_chars')} 字符/方法 (统一)",
        "=" * 78,
        "",
    ]

    md = [
        "# RETRIEVAL QA LOG — 全部问题 × 全部 RAG 算法 回答记录",
        "",
        f"- 语料: {meta.get('corpus', '')}",
        f"- 回答通道: {meta.get('agent_channel', '')}",
        f"- 判分: {meta.get('judge', '')}",
        f"- 证据预算: {meta.get('evidence_budget_chars')} 字符/方法（统一）",
        f"- 问答对: {len(qa)}（{len(order)} 问 × {len(methods)} 法）",
        "",
    ]

    for n, qid in enumerate(order, 1):
        items = by_q.get(qid) or {}
        first = next(iter(items.values()), {})
        claim = first.get("claim", "")
        gold = ", ".join(first.get("golden_ids") or [])
        hdr += [f"Q{n:03d} [{qid}] gold: {gold}", f"  问题/主张: {claim}", "-" * 78]
        md += [f"## Q{n:03d} [{qid}]", "", f"**问题/主张**: {claim}", "",
               f"**金标文档**: {gold}", ""]
        for m in methods:
            it = items.get(m)
            if not it:
                hdr += [f"  [{m}] (无记录)", ""]
                continue
            a = it.get("answer") or {}
            j = it.get("judge") or {}
            ans_text = str(a.get("answer") or a.get("raw") or "")\
                .replace("\n", " ")
            hdr += [
                f"  --- 方法: {m} ---",
                f"  检索排名: {it.get('evidence_sources') or it.get('trace', '')}",
                f"  回答: {ans_text}",
                f"  判分: {j.get('score', '-')} | {j.get('issues', '')}",
                "",
            ]
            md += [f"### {m}", "",
                   f"**回答**: {ans_text}", "",
                   f"**判分**: {j.get('score', '-')} — {j.get('issues', '')}",
                   ""]
        hdr.append("")

    out_log = RESULTS / "RETRIEVAL-QA-LOG.log"
    out_md = RESULTS / "RETRIEVAL-QA-LOG.md"
    out_log.write_text("\n".join(hdr), encoding="utf-8")
    out_md.write_text("\n".join(md), encoding="utf-8")
    print(f"-> {out_log}  ({out_log.stat().st_size} B, {len(order)} 问 × "
          f"{len(methods)} 法)")
    print(f"-> {out_md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
