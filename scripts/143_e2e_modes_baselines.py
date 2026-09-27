#!/usr/bin/env python3
"""143 — 端到端检索×问答全矩阵: 三模式(A/B/C) + baselines, 10 题(PIPELINE 规范).

同题同答链: 每方法检索(各按其机制) → 统一 4000 字符证据包 → answer_closed_book
(平台对外 chat API, 无工具, 与 baseline 逐字节同通道) → 差异只来自检索本身.
产出(单 run 目录):
  track_<method>_<qid>.json   每格一行(runner 行协议, 兼容 compare_report)
  judgments.json              LLM 逐格评分(0-5, 对照 gold_points/keywords)
  COMPARE.md / COMPARE.html   exp 原生对照报告
  RESULTS-E2E.md / .html      完整报告: 全部原始回答 + 评价 + 指标
可断点续跑: 已存在的格文件/评分自动跳过.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SUITE = REPO / "benchmark-suite"          # 143 位于仓库 scripts/ 下
sys.path.insert(0, str(SUITE))
sys.path.insert(0, str(SUITE / "experiments"))
sys.path.insert(0, str(SUITE / "scripts"))

ANSWER_EVIDENCE_BUDGET = 4000  # 与 baseline _pack 同预算, 全方法统一
MODES = ("A", "B", "C")
RET_BASELINES = ("bm25", "vector", "rrf", "rerank")


def load_questions(path: Path, limit: int) -> list[dict]:
    d = json.loads(path.read_text(encoding="utf-8"))
    qs = d["questions"][:limit]
    for q in qs:
        q.setdefault("question", q.get("question_zh", ""))
    return qs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", default="data/papers/qa_quick10.json")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--out", default="")
    ap.add_argument("--skip-judge", action="store_true")
    args = ap.parse_args()

    from experiments.retrieval_modes import RUNNERS, ensure_laya_interpreter
    ensure_laya_interpreter()

    qfile = Path(args.questions)
    if not qfile.is_absolute():
        qfile = SUITE / qfile
    questions = load_questions(qfile, args.limit)
    from lib import new_run_dir
    run_dir = Path(args.out) if args.out else new_run_dir("e2e")
    run_dir.mkdir(parents=True, exist_ok=True)
    print(f"[143] run={run_dir.name} · {len(questions)} 题 × "
          f"{len(MODES)} 模式 + {len(RET_BASELINES)} baseline", flush=True)

    from chat_tracks import answer_closed_book
    from lib import McpClient

    def field_shelf_map() -> dict:
        """field(arXiv 前缀)→KB 名, 从目录文档名结构推导(语料元数据, 非金标)."""
        mapping: dict = {}
        mc = McpClient()
        try:
            for k in (mc.call("kb_list", {"lightweight": True}, timeout=120).get("catalog") or []):
                kb_id = k.get("kb_id") or k.get("name")
                for d in (mc.call("kb_get_documents", {"kb_id": kb_id, "lightweight": True},
                                  timeout=120).get("catalog") or []):
                    name = str(d.get("name") or "")
                    if "__" in name:
                        f = name.split("__", 1)[0]
                        mapping.setdefault(f, {})
                        mapping[f][kb_id] = mapping[f].get(kb_id, 0) + 1
        finally:
            mc.close()
        return {f: max(kbs, key=kbs.get) for f, kbs in mapping.items()}

    fmap = field_shelf_map()
    mc0 = McpClient()
    kb_names = [str(k.get("name") or "") for k in
                (mc0.call("kb_list", {"lightweight": True}, timeout=120).get("catalog") or [])]
    mc0.close()
    print(f"[143] field→KB: {fmap} · KBs={len(kb_names)}", flush=True)

    def spread_pack(docs: list, per_doc: int, budget: int) -> str:
        """按文档顺序逐篇头部摘录直到预算(对齐 baseline 的相关摘录打包策略)."""
        parts, total = [], 0
        for d in docs:
            if total >= budget:
                break
            piece = str(d.get("content") or "")[:per_doc]
            parts.append(piece)
            total += len(piece)
        return "\n\n".join(parts)[:budget]

    def mode_pack(out_path: Path, mode: str) -> tuple:
        """统一分散打包: C= 全文按篇(共识优先); A/B= 判决序文档 → 逐篇头部读取."""
        d = json.loads(out_path.read_text(encoding="utf-8"))
        if mode == "C":
            docs = d.get("docs") or []
            return spread_pack(docs, 700, ANSWER_EVIDENCE_BUDGET), \
                [r.get("doc_path", "") for r in docs]
        if mode == "A":
            ordered = [r.get("doc_path", "") for r in (d.get("result_list") or [])]
        else:  # B: survivors 判决序
            ordered = [s.get("doc_path", "") for s in (d.get("survivors") or [])]
        mc = McpClient()
        seen, docs = set(), []
        try:
            cat = mc.call("kb_list", {"lightweight": True}, timeout=120).get("catalog") or []
            kb_of = {}
            for k in cat:
                kb_id = k.get("kb_id") or k.get("name")
                kb_of[str(k.get("name") or "").lower()] = kb_id
                kb_of[str(k.get("kb_id") or "").lower()] = kb_id
            for path in ordered:
                path = str(path).replace("\\", "/")
                key = path.lower()
                if not path or key in seen:
                    continue
                seen.add(key)
                kb_name = path.split("/")[0]
                kb_id = kb_of.get(kb_name.lower()) or kb_name
                r = mc.call("kb_doc_read", {"kb_id": kb_id,
                                            "doc_path": path.split("/", 1)[-1],
                                            "max_chars": 700}, timeout=120)
                docs.append({"doc_path": path, "content": str(r.get("content") or "")})
        finally:
            mc.close()
        return spread_pack(docs, 700, ANSWER_EVIDENCE_BUDGET), [x["doc_path"] for x in docs]

    # ── 三模式: 检索(子进程/脚本内) + 闭卷回答 ──
    for m in MODES:
        for q in questions:
            cell = run_dir / f"track_mode_{m}_{q['qid']}.json"
            if cell.exists():
                continue
            t0 = time.time()
            field = str(q.get("field") or "")
            shelf = [fmap[field]] if field in fmap else list(kb_names)
            qd = {"text": q["question"], "shelf_b": shelf, "gold_substr": "", "gold_name": ""}
            out_path = run_dir / f"arm_{m}-{q['qid']}.json"
            print(f"[143] mode {m} × {q['qid']} retrieving …", flush=True)
            try:
                RUNNERS[m](qd, out_path)
                d = json.loads(out_path.read_text(encoding="utf-8"))
                kept = sorted({str(r.get("doc_path", "")).replace("\\", "/")
                               for r in (d.get("docs") or [])
                               }) if m == "C" else sorted(set(
                                   str(x).replace("\\", "/") for x in (d.get("kept_doc_paths") or [])))
                if m == "C":
                    kept = sorted({r.get("doc_path", "") for r in (d.get("docs") or [])})
                pack, _ = mode_pack(out_path, m)
                native = {"A": 24000, "B": 40000, "C": 60000}  # 各模式设计预算
                pack = pack[:native.get(m, ANSWER_EVIDENCE_BUDGET)]
                ans = answer_closed_book(q["question"], pack)
                lat = round(time.time() - t0, 1)
                row = {"qid": q["qid"], "question": q["question"],
                       "track": f"mode_{m}", "method": f"mode_{m}",
                       "via": "retrieval-mode+closed-book",
                       "answer": ans.get("answer"),
                       "is_error": ans.get("is_error"),
                       "latency_s": lat, "retrieval_s": d.get("total_s") or d.get("seconds"),
                       "tool_call_count": 0,
                       "tokens": ans.get("tokens") or {},
                       "total_cost_usd": ans.get("total_cost_usd"),
                       "ranked": kept,
                       "evidence_sources": kept[:5],
                       "evidence_chars": len(pack),
                       "real_engine": d.get("real_engine") if m != "C" else None,
                       "merge": d.get("merge") if m == "C" else None}
            except Exception as e:  # noqa: BLE001
                row = {"qid": q["qid"], "question": q["question"],
                       "track": f"mode_{m}", "method": f"mode_{m}", "via": "retrieval-mode",
                       "answer": f"(failed: {type(e).__name__}: {str(e)[:200]})",
                       "latency_s": round(time.time() - t0, 1), "error": True,
                       "ranked": [], "tool_call_count": 0}
            cell.write_text(json.dumps(row, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"[143]   → {row.get('latency_s')}s ans={len(str(row.get('answer') or ''))}ch",
                  flush=True)

    # ── baselines: 检索 + 闭卷回答(run_method 全流程) ──
    import baselines as bl
    bm25 = bl.BM25(bl.load_docs())
    for b in RET_BASELINES:
        for q in questions:
            cell = run_dir / f"track_{b}_{q['qid']}.json"
            if cell.exists():
                continue
            print(f"[143] baseline {b} × {q['qid']} …", flush=True)
            try:
                r = bl.run_method(b, q["question"], q["qid"], bm25=bm25)
            except Exception as e:  # noqa: BLE001
                r = {"qid": q["qid"], "method": b, "answer": f"(failed: {e})",
                     "latency_s": 0, "error": True, "ranked": [], "tokens": {}}
            r.update({"track": b, "via": "baseline+closed-book"})
            cell.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"[143]   → {r.get('latency_s')}s ranked={len(r.get('ranked') or [])}",
                  flush=True)

    # ── 评价: LLM 逐格评分(对照 gold_points/keywords) ──
    jpath = run_dir / "judgments.json"
    judgments = json.loads(jpath.read_text(encoding="utf-8")) if jpath.exists() else {}
    if not args.skip_judge:
        for q in questions:
            for m in [f"mode_{x}" for x in MODES] + list(RET_BASELINES):
                key = f"{m}|{q['qid']}"
                if key in judgments:
                    continue
                cell = run_dir / f"track_{m}_{q['qid']}.json"
                if not cell.exists():
                    continue
                ans = str(json.loads(cell.read_text(encoding="utf-8")).get("answer") or "")
                gp = q.get("gold_points") or []
                gk = q.get("gold_keywords") or []
                prompt = (
                    "You are a strict QA grader. Grade the ANSWER against GOLD POINTS.\n"
                    "score: 0=wrong or refusal on answerable, 3=partial, 5=complete&correct.\n"
                    "Reply with ONLY a JSON object: "
                    '{"score": <0-5>, "verdict": "correct|partial|wrong|refusal", '
                    '"rationale": "<one sentence>"}\n\n'
                    f"QUESTION: {q['question']}\n"
                    f"GOLD_POINTS: {json.dumps(gp, ensure_ascii=False)}\n"
                    f"GOLD_KEYWORDS: {json.dumps(gk, ensure_ascii=False)}\n"
                    f"STRATUM: {q.get('stratum', 'single')}\n"
                    f"ANSWER: {ans[:4000]}")
                try:
                    r = answer_closed_book(prompt, "", timeout_s=180)
                    txt = str(r.get("answer") or "")
                    mt = re.search(r"\{.*\}", txt, re.S)
                    j = json.loads(mt.group(0)) if mt else {"score": None, "verdict": "unparsed",
                                                            "rationale": txt[:120]}
                except Exception as e:  # noqa: BLE001
                    j = {"score": None, "verdict": "error", "rationale": str(e)[:120]}
                judgments[key] = j
                jpath.write_text(json.dumps(judgments, ensure_ascii=False, indent=1),
                                 encoding="utf-8")
        print(f"[143] judgments: {len(judgments)} cells", flush=True)

    # ── exp 原生对照报告 ──
    import compare_html
    import compare_report
    md, payload = compare_report.build(run_dir, {"questions": questions})
    (run_dir / "COMPARE.md").write_text(md, encoding="utf-8")
    (run_dir / "COMPARE.html").write_text(compare_html.render(payload), encoding="utf-8")

    # ── RESULTS-E2E.md: 全部原始回答 + 评价 ──
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    methods = [f"mode_{x}" for x in MODES] + list(RET_BASELINES)
    L = ["# 端到端检索×问答 全矩阵报告（三模式 + baselines × 10 题）", "",
         f"- Run: `{run_dir.name}` · 生成: {stamp}",
         "- 通道: 每方法各自检索 → 统一 4000 字符证据包 → 平台闭卷 chat API 回答"
         "（与 baseline 逐字节同通道, 差异只来自检索）",
         f"- 评价: LLM 逐格评分（对照 gold_points/gold_keywords, 0-5 分）", ""]
    # 聚合表
    L += ["## 1 · 方法聚合", "",
          "| 方法 | 平均延迟s | 检索命中率 | 引用命中率 | 平均评分 | 弃答 | 错误 |", "|---|---:|---:|---:|---:|---:|---:|"]
    agg = payload.get("per_method", {})
    for m in methods:
        a = agg.get(m)
        if not a:
            continue
        scores = [judgments[k]["score"] for k in judgments
                  if k.startswith(m + "|") and isinstance(judgments[k].get("score"), (int, float))]
        avg = round(sum(scores) / len(scores), 2) if scores else None
        L.append(f"| {m} | {a['latency_avg_s']} | {a['retrieval_gold_rate']} "
                 f"| {a['citation_gold_rate']} | {avg} | {a['abstentions']} | {a['errors']} |")
    L.append("")
    # 逐题原始回答 + 评价
    qmeta = {q["qid"]: q for q in questions}
    for q in questions:
        L += [f"## Q {q['qid']} · [{q.get('stratum')}] {q['question']}", ""]
        L += [f"- gold_docs: {q.get('gold_docs')} · stratum: {q.get('stratum')}", ""]
        for m in methods:
            cell = run_dir / f"track_{m}_{q['qid']}.json"
            if not cell.exists():
                continue
            row = json.loads(cell.read_text(encoding="utf-8"))
            j = judgments.get(f"{m}|{q['qid']}", {})
            L += [f"### {m}", "",
                  f"- 延迟 {row.get('latency_s')}s · 检索文档 {len(row.get('ranked') or [])} 篇"
                  f" · tokens out {(row.get('tokens') or {}).get('output')}",
                  f"- 评分: **{j.get('score')}** ({j.get('verdict')}) — {j.get('rationale','')}", "",
                  "```", str(row.get("answer") or "")[:2500], "```", ""]
    (run_dir / "RESULTS-E2E.md").write_text("\n".join(L), encoding="utf-8")

    # RESULTS-E2E.html(轻量 md→html)
    def md2html(t: str) -> str:
        out, in_code = [], False
        for ln in t.splitlines():
            if ln.startswith("```"):
                in_code = not in_code
                out.append("<pre>" if in_code else "</pre>")
                continue
            if in_code:
                out.append(html.escape(ln))
                continue
            if ln.startswith("## "):
                out.append(f"<h2>{html.escape(ln[3:])}</h2>")
            elif ln.startswith("# "):
                out.append(f"<h1>{html.escape(ln[2:])}</h1>")
            elif ln.startswith("- "):
                out.append(f"<li>{html.escape(ln[2:])}</li>")
            elif ln.startswith("|"):
                cells = [f"<td>{html.escape(c.strip())}</td>" for c in ln.strip("|").split("|")]
                out.append("<tr>" + "".join(cells) + "</tr>")
            elif ln.strip():
                out.append(f"<p>{html.escape(ln)}</p>")
        return ("<html><head><meta charset='utf-8'><title>E2E Results</title>"
                "<style>body{font-family:Georgia,serif;max-width:1100px;margin:2em auto;"
                "line-height:1.5}pre{background:#f4f4f4;padding:8px;white-space:pre-wrap}"
                "table{border-collapse:collapse}td{border:1px solid #ccc;padding:2px 8px}"
                "</style></head><body>" + "\n".join(out) + "</body></html>")
    (run_dir / "RESULTS-E2E.html").write_text(md2html("\n".join(L)), encoding="utf-8")
    print(f"[143] done → {run_dir / 'RESULTS-E2E.md'} + .html + COMPARE.md/.html", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
