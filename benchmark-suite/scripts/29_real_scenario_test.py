#!/usr/bin/env python3
"""E19 真实场景测试 — 用户上传文档 × 论文复现检索算法矩阵 全链路.

场景: 两份从未进入任何测试语料的真实文档(英文架构指南 + 中文投稿规划)
按用户路径上传(kb_doc_create → 生产 KB), 再由各论文算法的 suite 复现索引;
问题由 omp Agent 从文档内容生成; 8 个检索算法在同一 omp Harness/模型下作答;
独立评审 Agent 依据逐字金标引文打分; 中间 Agent 对匿名答案排名。

产物:
  results/run-*/real_scenario.json   机器可读全量结果
  REALSCENARIO-QA-LOG.log            全部问题×算法的问答实录
  REALSCENARIO-BENCHMARK.md          汇总报告
用法:
  python scripts/29_real_scenario_test.py                # 全量 (6问 × 8法)
  python scripts/29_real_scenario_test.py --smoke        # 1问 × [qdcvr,dense_rag]
  python scripts/29_real_scenario_test.py --methods qdcvr,deepread --per-doc 2
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent          # benchmark-suite/scripts
SUITE = HERE.parent                             # benchmark-suite/
ALGO = SUITE / "algorithms"                     # benchmark-suite/algorithms/
REPO = SUITE.parent
sys.path.insert(0, str(ALGO))
sys.path.insert(0, str(HERE))

import user_scenario as us  # noqa: E402
from lib import McpClient, set_run  # noqa: E402
from methods import METHODS  # noqa: E402
from omp_client import OmpOneshot  # noqa: E402

DOCS = [REPO / "docs" / "ARCHITECTURE.md",
        REPO / "docs" / "paper" / "SUBMISSION-MASTER-PLAN.md"]
PROD_KB = "KB-UserDemo"
PREFIX = "UserDemo"
SCEN_METHODS = ["qdcvr", "dense_rag", "dense_rag_rerank", "raptor",
                "itrg_refresh", "itrg_refine", "search_o1", "deepread"]

_lock = threading.Lock()
_log_lines: list[str] = []


def log(line: str = "") -> None:
    with _lock:
        print(line, flush=True)
        _log_lines.append(line)


def retrieve(method: str, ctx, question: str) -> dict:
    import methods as m
    if method == "qdcvr":
        return m.qdcvr(ctx, question, allow_global_fallback=False)
    return METHODS[method]["fn"](ctx, question)


def run_question(q: dict, ctx_get, oneshot_factory) -> dict:
    rows = {}
    for method in SCEN_METHODS:
        t0 = time.perf_counter()
        ctx = ctx_get()
        ev = retrieve(method, ctx, q["question"])
        ans = us.answer_question(oneshot_factory, q["question"], ev)
        jd = us.judge_answer(oneshot_factory, q["question"], q["gold_quote"], ans)
        score = None
        if isinstance(jd.get("parsed"), dict):
            try:
                score = float(jd["parsed"].get("score"))
            except (TypeError, ValueError):
                score = None
        metrics = us.doc_hits(ev.get("doc_rank") or [], q["doc"])
        rows[method] = {
            "doc_rank": ev.get("doc_rank") or [],
            "metrics": metrics,
            "trace": ev.get("trace", {}),
            "latency": round(time.perf_counter() - t0, 2),
            "llm_calls": ev.get("llm_calls", 0),
            "evidence_chars": ans["evidence_chars"],
            "evidence_sources": ans["sources"],
            "answer": ans.get("parsed"),
            "answer_raw": ans.get("raw", "")[:1200],
            "judge": jd.get("parsed"),
            "judge_score": score}
        log(f"    [{q['qid']}] {method:<17} hit@1={metrics['hit@1']} "
            f"pos={metrics['rank_position']} judge={score} "
            f"lat={rows[method]['latency']}s")
    answers = {m: {"parsed": r["answer"], "raw": r["answer_raw"]}
               for m, r in rows.items()}
    ranking = us.middle_agent_rank(oneshot_factory, q["question"],
                                   q["gold_quote"], answers)
    judge_scores = {m: r["judge_score"] for m, r in rows.items()
                    if r["judge_score"] is not None}
    best_judge = max(judge_scores, key=judge_scores.get) if judge_scores else None
    best_rank = ranking[0]["method"] if ranking else None
    log(f"  [Q {q['qid']}] done — judge_best={best_judge} "
        f"({judge_scores.get(best_judge)}), middle_rank_best={best_rank}")
    return {"rows": rows, "ranking": ranking,
            "judge_best": {"method": best_judge,
                           "score": judge_scores.get(best_judge)},
            "rank_best": best_rank}


def write_log(meta: dict, results: dict, path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write(f"REAL SCENARIO QA LOG — {meta['ts']}\n")
        f.write(f"docs: {meta['docs']}\n")
        f.write(f"production KB: {meta['prod_kb']} (fingerprint {meta['fp']})\n")
        f.write(f"baseline KBs: {meta['baseline_kbs']}\n")
        f.write(f"harness: omp (provider=ustc model=deepseek-flash), "
                f"unified answer prompt, independent judge\n")
        f.write("=" * 80 + "\n\n")
        for q in meta["questions"]:
            r = results[q["qid"]]
            f.write("=" * 80 + "\n")
            f.write(f"[Q {q['qid']}] source_doc={q['doc']}\n")
            f.write(f"QUESTION : {q['question']}\n")
            f.write(f"EXPECTED : {q['expected']}\n")
            f.write(f"GOLD QUOTE: {q['gold_quote']}\n")
            f.write("-" * 80 + "\n")
            for m, row in r["rows"].items():
                f.write(f"--- method={m}\n")
                f.write(f"doc_rank: {row['doc_rank'][:6]}\n")
                f.write(f"retrieval: {row['metrics']} trace={_short(row['trace'])}\n")
                f.write(f"evidence: sources={row['evidence_sources']} "
                        f"chars={row['evidence_chars']} lat={row['latency']}s "
                        f"llm_calls={row['llm_calls']}\n")
                f.write(f"ANSWER: {json.dumps(row['answer'], ensure_ascii=False)}\n")
                f.write(f"JUDGE : {json.dumps(row['judge'], ensure_ascii=False)}\n\n")
            f.write(f"MIDDLE-AGENT RANKING: "
                    f"{json.dumps(r['ranking'], ensure_ascii=False)}\n")
            f.write(f"QUESTION WINNERS: judge_best={r['judge_best']} "
                    f"rank_best={r['rank_best']}\n\n")


def _short(trace: dict) -> str:
    out = {}
    for k, v in trace.items():
        if isinstance(v, list) and len(v) > 4:
            out[k] = v[:4] + ["..."]
        else:
            out[k] = v
    return json.dumps(out, ensure_ascii=False)[:400]


def write_report(meta: dict, results: dict, path: Path, json_path: Path,
                 log_path: Path) -> None:
    per_method: dict[str, dict] = {m: {"judge": [], "hit1": 0, "hit3": 0,
                                       "lat": [], "llm": 0}
                                   for m in SCEN_METHODS}
    for q in meta["questions"]:
        for m, row in results[q["qid"]]["rows"].items():
            agg = per_method[m]
            if row["judge_score"] is not None:
                agg["judge"].append(row["judge_score"])
            agg["hit1"] += row["metrics"]["hit@1"]
            agg["hit3"] += row["metrics"]["hit@3"]
            agg["lat"].append(row["latency"])
            agg["llm"] += row["llm_calls"]
    n_q = len(meta["questions"])

    lines = [
        "# 真实场景基准报告 — 用户上传文档 × 论文复现检索算法",
        "",
        f"- 运行: `{meta['ts']}` · 问题数: {n_q} "
        f"(每文档 {meta['per_doc']}, omp Agent 从文档内容生成)",
        f"- 文档: {', '.join(f'`{d}`' for d in meta['docs'])}",
        f"- 生产 KB: `{meta['prod_kb']}`(kb_doc_create 平台用户路径, "
        f"指纹 `{meta['fp']}`); 基线 KB: "
        f"{', '.join(f'`{k}`' for k in meta['baseline_kbs'])}",
        "- Harness: 全部算法同一 omp Agent 同一模型(ustc/deepseek-flash), "
        "同一开放 QA 作答 prompt; 独立评审 Agent 注入逐字金标引文; "
        "中间 Agent 对匿名答案排名。",
        "",
        "## 复现算法注册表",
        "",
        "| 算法 | 论文对应 |",
        "|---|---|"]
    for m in SCEN_METHODS:
        lines.append(f"| `{m}` | {METHODS[m]['paper']} |")
    lines += [
        "",
        "## 主表(文档级检索命中 + 评审得分)",
        "",
        "| 算法 | hit@1 | hit@3 | judge 均分 | 平均时延(s) | LLM 调用 |",
        "|---|---|---|---|---|---|"]
    for m in SCEN_METHODS:
        a = per_method[m]
        jm = sum(a["judge"]) / len(a["judge"]) if a["judge"] else float("nan")
        lat = sum(a["lat"]) / len(a["lat"]) if a["lat"] else float("nan")
        lines.append(f"| `{m}` | {a['hit1']}/{n_q} | {a['hit3']}/{n_q} | "
                     f"{jm:.2f} | {lat:.1f} | {a['llm']} |")
    lines += [
        "",
        "## 逐题胜出",
        "",
        "| qid | 文档 | judge 最佳 | 中间 Agent 排名第一 |",
        "|---|---|---|---|"]
    for q in meta["questions"]:
        r = results[q["qid"]]
        jb = r["judge_best"]
        lines.append(f"| {q['qid']} | {q['doc']} | {jb['method']} "
                     f"({jb['score']}) | {r['rank_best']} |")
    lines += [
        "",
        "## 问答实录",
        "",
        f"全部问题×算法的完整问答见 [`REALSCENARIO-QA-LOG.log`]({log_path.name});"
        f" 机器可读结果见 `{json_path.name}`。",
        "",
        "## 复现方式",
        "",
        "```bash",
        "cd benchmark-suite",
        "python scripts/29_real_scenario_test.py            # 全量",
        "python scripts/29_real_scenario_test.py --smoke    # 冒烟",
        "```",
        "",
        "前提: 后端 :8771 健康(embedding ready), `omp` 在 PATH,",
        "`.env` 含 `MCP_AUTH_TOKEN`(以及 `HF_HUB_OFFLINE=1` 离线嵌入)。",
        ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    global SCEN_METHODS
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--methods", default="")
    ap.add_argument("--per-doc", type=int, default=3)
    args = ap.parse_args()
    methods_want = (["qdcvr", "dense_rag"] if args.smoke
                    else ([m.strip() for m in args.methods.split(",")]
                          if args.methods else SCEN_METHODS))
    bad = [m for m in methods_want if m not in SCEN_METHODS]
    if bad:
        print(f"unknown methods: {bad}; valid: {SCEN_METHODS}")
        return 2
    SCEN_METHODS = [m for m in SCEN_METHODS if m in methods_want]

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    outdir = set_run(f"real-scenario-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
    docs = us.load_user_docs(DOCS)
    print(f"[docs] {[(d['cid'], len(d['text'])) for d in docs]}", flush=True)

    mc = McpClient()
    print("[stage] production KB (user upload path) ...", flush=True)
    prod = us.ensure_production_kb(mc, PROD_KB, docs)
    print(f"    -> {prod}", flush=True)
    print("[stage] baseline KBs (paper chunking schemes) ...", flush=True)
    baseline = us.build_baseline_kbs(mc, docs, PREFIX)
    for k, v in baseline.items():
        print(f"    -> {k}: {v['items']} items, probe={v['vector_probe_hits']}, "
              f"reused={v['reused']}, {v['build_seconds']}s", flush=True)
    print("[stage] raptor tree ...", flush=True)
    tree = us.build_user_raptor(mc, OmpOneshot(stage="raptor", timeout=300),
                                docs, PREFIX)
    print(f"    -> {tree}", flush=True)
    mc.close()

    print("[stage] question generation (omp) ...", flush=True)
    questions, qprov = us.generate_questions(
        OmpOneshot(stage="genq", timeout=300), docs,
        per_doc=1 if args.smoke else args.per_doc)
    for q in questions:
        print(f"    [{q['qid']}] ({q['doc']}) {q['question'][:70]}", flush=True)

    old_globals = us.activate_profile(PREFIX, PROD_KB)
    ctx_get = us.make_ctx_factory(McpClient, docs, PREFIX)

    def oneshot_factory(stage: str) -> OmpOneshot:
        return OmpOneshot(stage=stage, timeout=420)

    results: dict[str, dict] = {}
    workers = 1 if args.smoke else 3
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(run_question, q, ctx_get, oneshot_factory): q
                for q in questions}
        for fut, q in futs.items():
            results[q["qid"]] = fut.result()

    meta = {"ts": ts, "docs": [d["path"] for d in docs],
            "doc_chars": {d["cid"]: len(d["text"]) for d in docs},
            "fp": us.fingerprint(docs), "prod_kb": PROD_KB,
            "prod_index": prod, "baseline_kbs": list(baseline),
            "raptor": tree, "questions": questions,
            "question_provenance": qprov, "per_doc": len(questions) // len(docs),
            "methods": SCEN_METHODS, "smoke": args.smoke}

    json_path = outdir / "real_scenario.json"
    json_path.write_text(json.dumps({"meta": meta, "results": results},
                                    ensure_ascii=False, indent=1),
                         encoding="utf-8")
    log_path = SUITE / "REALSCENARIO-QA-LOG.log"
    write_log(meta, results, log_path)
    report_path = SUITE / "REALSCENARIO-BENCHMARK.md"
    write_report(meta, results, report_path, json_path, log_path)
    print(f"[done] json={json_path}\n       log={log_path}\n       "
          f"report={report_path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
