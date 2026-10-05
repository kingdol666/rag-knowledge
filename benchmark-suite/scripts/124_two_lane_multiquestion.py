#!/usr/bin/env python3
"""多问题 · 双车道对照测试（先修描述 → 再逐级穷尽召回 + Jev 门）。

  车道 A · 向量 + 内容       chat API + 平台完整 kb 工具（含 kb_search_vector）
  车道 B · 逐级 + Jev 门     122_jev_exhaustive_pipeline.py --mode union
                             （L2.5 描述驱动候选 ∪ 向量 → L4 读全部候选 → L5.5 Jev 门 → L5 深读 → L7）

用法（benchmark-suite/）：
    python scripts/124_two_lane_multiquestion.py
    python scripts/124_two_lane_multiquestion.py --limit 3 --mode desc
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
REPO = SUITE.parent
sys.path.insert(0, str(SUITE / "experiments"))
sys.path.insert(0, str(SUITE / "scripts"))

from chat_tracks import A2_TOOLS, chat_stream  # noqa: E402

VECTOR_MARKERS = ("kb_search_vector", "kb_search_two_stage", "kb_search_stats")

QUESTIONS = [
    {"qid": "Q1", "type": "early scene",
     "q": "At the Meryton assembly, what does Mr. Darcy say about Elizabeth when Bingley "
          "suggests he dance with her, and how does Elizabeth react to it?"},
    {"qid": "Q2", "type": "mid turning point",
     "q": "Why does Elizabeth refuse Mr. Darcy's proposal at Hunsford, and what does his "
          "letter the next morning reveal about Mr. Wickham's past?"},
    {"qid": "Q3", "type": "late reveal",
     "q": "How does Elizabeth learn the truth about Mr. Darcy's role in Lydia's marriage, "
          "and what exactly did he do and pay?"},
    {"qid": "Q4", "type": "confusable detail",
     "q": "Mr. Wickham was involved in two elopements. For each, state who the girl was, how "
          "old she was, where it happened, and whether it was carried out."},
    {"qid": "Q5", "type": "character arc",
     "q": "Trace how Elizabeth's opinion of Mr. Darcy changes from the beginning of the novel "
          "to the end, and name the scenes that turn it."},
    {"qid": "Q6", "type": "enumeration / completeness",
     "q": "List every scene in the novel where Darcy and Elizabeth meet in person, in order, "
          "and say what changes in their relationship at each."},
]

PROMPT_A = (
    "Answer the QUESTION using the knowledge base (KB: Novel-PridePrejudice, the novel Pride and "
    "Prejudice). Execute the retrieval yourself in THIS session with the kb_* tools. Name the "
    "specific part file(s) you used. You MUST finish with a final answer in this session. "
    "ENGLISH, at most 8 sentences.\n\nQUESTION: {q}")


def lane_a(q: str) -> dict:
    t0 = time.perf_counter()
    r = chat_stream(PROMPT_A.format(q=q), cwd=str(REPO), allowed_tools=A2_TOOLS,
                    max_turns=14, timeout_s=900)
    return {"answer": r.get("answer"), "tools": [t["tool"] for t in (r.get("tool_calls") or [])],
            "tool_count": r.get("tool_call_count"), "denied": r.get("permission_denied"),
            "latency_s": round(time.perf_counter() - t0, 1),
            "tokens": r.get("tokens"), "cost": r.get("total_cost_usd")}


def lane_b(q: str, qid: str, mode: str, threshold: float) -> dict:
    out = SUITE / f"results/_laneB_{qid}.md"
    t0 = time.perf_counter()
    p = subprocess.run([sys.executable, "scripts/122_jev_exhaustive_pipeline.py",
                        "--question", q, "--mode", mode, "--threshold", str(threshold),
                        "--out", f"results/_laneB_{qid}.md"],
                       capture_output=True, text=True, cwd=str(SUITE), timeout=1800)
    d = {}
    jf = out.with_suffix(".json")
    if jf.exists():
        d = json.loads(jf.read_text(encoding="utf-8"))
    return {"answer": d.get("answer"), "latency_s": round(time.perf_counter() - t0, 1),
            "rc": p.returncode, "candidates": d.get("L4_candidates"),
            "windows": d.get("L4_windows"),
            "selected": d.get("L2_5_selected"), "after_union": d.get("L2_5_after_union"),
            "kept_parts": d.get("L5_5_kept_parts"), "kept_docs": d.get("L5_5_kept_docs"),
            "backend": (d.get("L5_5_jev") or {}).get("backend"),
            "criterion": (d.get("L5_5_jev") or {}).get("criterion"),
            "threshold": (d.get("L5_5_jev") or {}).get("threshold"),
            "cost": d.get("answer_cost"), "evidence_chars": d.get("evidence_chars")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=len(QUESTIONS))
    ap.add_argument("--mode", default="union", choices=["desc", "all", "union"])
    ap.add_argument("--threshold", type=float, default=0.4)
    ap.add_argument("--out", default="results/TWO-LANE-MULTI-TEST.md")
    args = ap.parse_args()

    rows = []
    for item in QUESTIONS[: args.limit]:
        print(f"[{item['qid']}] lane A ...", flush=True)
        a = lane_a(item["q"])
        print(f"[{item['qid']}] A {a['latency_s']}s tools={a['tool_count']}", flush=True)
        print(f"[{item['qid']}] lane B ...", flush=True)
        b = lane_b(item["q"], item["qid"], args.mode, args.threshold)
        print(f"[{item['qid']}] B {b['latency_s']}s kept={b.get('kept_parts')} "
              f"backend={b.get('backend')}", flush=True)
        rows.append({"qid": item["qid"], "type": item["type"], "q": item["q"], "A": a, "B": b})

    L = ["# 多问题 · 双车道对照测试（描述修复后）", "",
         "车道 A = 向量+内容（chat API + 完整 kb 工具）· "
         f"车道 B = 逐级穷尽召回 + Jev 门（122 管线，mode `{args.mode}`，阈值 {args.threshold}）", "",
         "## 监控总表", "",
         "| QID | 类型 | A 时延 | A 工具 | A 成本 | B 时延 | B 候选 | B 窗口 | B 保留 part | B 判据 | B 后端 |",
         "|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|"]
    for r in rows:
        a, b = r["A"], r["B"]
        L.append(f"| {r['qid']} | {r['type']} | {a['latency_s']}s | {a['tool_count']} | "
                 f"{a.get('cost')} | {b['latency_s']}s | {b.get('candidates')} | "
                 f"{b.get('windows')} | {b.get('kept_parts')} | {b.get('criterion')} | "
                 f"{b.get('backend')} |")
    L += ["", "## 车道 A 向量工具使用情况（确认 A 是向量车道）", ""]
    for r in rows:
        used = [t for t in r["A"]["tools"] if any(v in t for v in VECTOR_MARKERS)]
        L.append(f"- {r['qid']}: {'、'.join(used) if used else '（未用向量工具）'}")
    L += [""]
    for r in rows:
        L += [f"## {r['qid']} — {r['type']}", "", f"**Q**：{r['q']}", "",
              "### 车道 A（向量 + 内容）", "", r["A"]["answer"] or "(空)", "",
              "### 车道 B（逐级穷尽 + Jev 门）", "", r["B"]["answer"] or "(空)", ""]

    out = SUITE / args.out
    out.write_text("\n".join(L), encoding="utf-8")
    out.with_suffix(".json").write_text(json.dumps(rows, ensure_ascii=False, indent=1),
                                        encoding="utf-8")
    print(f"\n[test] → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
