#!/usr/bin/env python3
"""两种检索方式的 chat-API 对照测试（小说情节题）。

两条车道都通过**同一个对外 chat API**（POST /api/claude/chat）执行，唯一差别是
**允许的工具集**与**流程指令**：

  车道 A · 向量 + 内容   工具集 = 平台完整 kb 工具（含 kb_search_vector / kb_search_two_stage）
                         → 系统自带的 QDCVR 流程（向量优先 → 0-8 内容门控）
  车道 B · 纯内容（无向量）工具集 = 上述**去掉** kb_search_vector / kb_search_two_stage
                         → 强制走逐级检索（kb_list 库描述 → kb_get_documents 文档描述
                           → kb_doc_read 读正文），不允许相似度排序

用法（benchmark-suite/）：
    python scripts/121_chat_two_lane_test.py
    python scripts/121_chat_two_lane_test.py --limit 2
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
REPO = SUITE.parent
sys.path.insert(0, str(SUITE / "experiments"))
sys.path.insert(0, str(SUITE / "scripts"))

from chat_tracks import A2_TOOLS, chat_stream  # noqa: E402

VECTOR_MARKERS = ("kb_search_vector", "kb_search_two_stage", "kb_search_stats")
LANE_B_TOOLS = [t for t in A2_TOOLS if not any(v in t for v in VECTOR_MARKERS)]

KB = "Novel-PridePrejudice"

QUESTIONS = [
    {"qid": "NQ1", "q": "At the Meryton assembly, what does Mr. Darcy say about Elizabeth when "
                        "Bingley suggests he dance with her, and how does Elizabeth react to it?"},
    {"qid": "NQ2", "q": "Why does Elizabeth refuse Mr. Darcy's proposal at Hunsford, and what "
                        "does his letter the next morning reveal about Mr. Wickham's past?"},
    {"qid": "NQ3", "q": "How does Elizabeth learn the truth about Mr. Darcy's role in Lydia's "
                        "marriage, and what exactly did he do and pay?"},
    {"qid": "NQ4", "q": "Mr. Wickham was involved in two elopements. For each, state who the girl "
                        "was, how old she was, where it happened, and whether it was carried out."},
]

PROMPT_A = (
    f"Answer the QUESTION using the knowledge base (KB: {KB}) — the novel Pride and Prejudice. "
    "Execute the retrieval yourself in THIS session with the kb_* tools; do not delegate. "
    "Name the specific part file(s) you used. Answer in ENGLISH, at most 8 sentences.\n\n"
    "QUESTION: {q}")

PROMPT_B = (
    f"Answer the QUESTION about the novel Pride and Prejudice held in KB: {KB}. "
    "You have NO similarity-search tools — you must find the answer by NAVIGATING and READING:\n"
    "1) kb_list(lightweight=true) to read every knowledge base's description and pick the right shelf;\n"
    "2) kb_get_documents(lightweight=true, kb_id) to read every document description in that shelf;\n"
    "3) distrust descriptions that look like boilerplate — verify by reading the document head "
    "(kb_doc_read, max_chars=600) and judge from CONTENT;\n"
    "4) read the parts that actually hold the answer (kb_doc_read) and answer only from what you read.\n"
    "Do not call kb_search_vector or kb_search_two_stage. "
    "Name the specific part file(s) you used. Answer in ENGLISH, at most 8 sentences.\n\n"
    "QUESTION: {q}")


def run_lane(track: str, prompt: str, tools: list) -> dict:
    t0 = time.perf_counter()
    r = chat_stream(prompt, cwd=str(REPO), allowed_tools=tools, max_turns=12,
                    timeout_s=600)
    return {"track": track, "answer": r.get("answer"),
            "tools": [t["tool"] for t in (r.get("tool_calls") or [])],
            "tool_count": r.get("tool_call_count"),
            "denied": r.get("permission_denied"),
            "latency_s": round(time.perf_counter() - t0, 1),
            "tokens": r.get("tokens"), "cost": r.get("total_cost_usd"),
            "is_error": r.get("is_error")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=len(QUESTIONS))
    ap.add_argument("--out", default="results/CHAT-TWO-LANE-TEST.md")
    args = ap.parse_args()

    rows = []
    for item in QUESTIONS[: args.limit]:
        print(f"[{item['qid']}] lane A ...", flush=True)
        a = run_lane("A", PROMPT_A.format(q=item["q"]), A2_TOOLS)
        print(f"[{item['qid']}] lane A done {a['latency_s']}s tools={a['tool_count']} "
              f"denied={a['denied']}", flush=True)
        print(f"[{item['qid']}] lane B ...", flush=True)
        b = run_lane("B", PROMPT_B.format(q=item["q"]), LANE_B_TOOLS)
        print(f"[{item['qid']}] lane B done {b['latency_s']}s tools={b['tool_count']} "
              f"denied={b['denied']}", flush=True)
        rows.append({"qid": item["qid"], "question": item["q"], "A": a, "B": b})

    L = ["# 两种检索方式的 chat-API 对照测试（小说情节题）", "",
         f"KB：`{KB}` · 两条车道均经 `POST /api/claude/chat` 执行 · "
         f"车道 B 的工具集已剔除 {VECTOR_MARKERS}", "",
         "## 监控总表", "",
         "| QID | 车道 | 时延 s | 工具数 | tokens in/out | 成本 $ | 被拒工具 |",
         "|---|---|---:|---:|---|---:|---:|"]
    for r in rows:
        for k in ("A", "B"):
            d = r[k]
            tok = d.get("tokens") or {}
            L.append(f"| {r['qid']} | {k} | {d['latency_s']} | {d['tool_count']} | "
                     f"{tok.get('input')}/{tok.get('output')} | {d.get('cost')} | "
                     f"{d['denied']} |")
    L += ["", "## 调用轨迹（验证车道 B 是否真的没用向量工具）", ""]
    for r in rows:
        L.append(f"### {r['qid']}")
        for k in ("A", "B"):
            tools = r[k]["tools"]
            used_vec = [t for t in tools if any(v in t for v in VECTOR_MARKERS)]
            flag = "⚠️ 用了向量工具" if (k == "B" and used_vec) else "✓"
            L.append(f"- **{k}** {flag}：`{'`, `'.join(tools) or '(无)'}`")
        L.append("")
    for r in rows:
        L += [f"## {r['qid']}", "", f"**Q**：{r['question']}", "",
              "### 车道 A（向量 + 内容）", "", r["A"]["answer"] or "(空)", "",
              "### 车道 B（纯内容 · 无向量）", "", r["B"]["answer"] or "(空)", ""]
    out = SUITE / args.out
    out.write_text("\n".join(L), encoding="utf-8")
    (out.with_suffix(".json")).write_text(json.dumps(rows, ensure_ascii=False, indent=1),
                                          encoding="utf-8")
    print(f"\n[test] → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
