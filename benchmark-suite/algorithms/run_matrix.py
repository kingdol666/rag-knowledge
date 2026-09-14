#!/usr/bin/env python3
"""DeepRead 基线矩阵 — 同一语料(KB-SciFact 148 篇)同一查询(BEIR SciFact 30 条)
下, QDCVR 真 skill 链路 vs DeepRead 论文 Table 1 全部对比算法.

阶段(可单跑, 全部幂等/断点续跑; LLM 调用以 prompt 哈希落盘缓存):
  ingest   建 chunk 级基线索引 KB(入库即度量) + 确保 KB-SciFact 可检索
  raptor   RAPTOR 建树(omp 摘要, 树落盘缓存)
  retrieve 每查询 × 8 方法产出证据(检索层指标 vs qrels)
  answer   每证据经 omp Agent 统一作答(同一 4000 字符预算) — 记录完整问答
  judge    第三方 omp Agent(fresh 进程, 注入金标文档)0-10 打分 — 记录理由
  report   汇总 → results/run-*/deepread_matrix.json + deepread_qa_transcripts.*

用法:
  BENCH_LIMIT=2 python run_matrix.py --stage ingest --stage retrieve ...   # 冒烟
  python run_matrix.py --all          # 全量 30 查询 × 8 方法
  DR_WORKERS=3 python run_matrix.py --stage answer --stage judge
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ALGO = Path(__file__).resolve().parent
SUITE = ALGO.parent
sys.path.insert(0, str(ALGO))
sys.path.insert(0, str(SUITE / "scripts"))

from corpus import load_queries  # noqa: E402
from omp_client import OmpOneshot, OmpRpc, extract_json  # noqa: E402
from lib import McpClient, env_fingerprint, mean, now_iso  # noqa: E402

CACHE = ALGO / "cache"
CACHE.mkdir(exist_ok=True)
WORKERS = int(os.environ.get("DR_WORKERS", "3"))
LIMIT = int(os.environ.get("BENCH_LIMIT", "0"))

METHOD_ORDER = ["qdcvr", "dense_rag", "dense_rag_rerank", "raptor",
                "itrg_refresh", "itrg_refine", "search_o1", "deepread"]

ANSWER_PROMPT = """You are a research assistant verifying a scientific claim against a corpus.
Claim: {claim}

Evidence excerpts retrieved from the corpus (source id in brackets):
{evidence}

Using ONLY the evidence above, respond with ONLY a JSON object:
{{"verdict": "supported"|"refuted"|"insufficient",
  "answer": "<2-3 sentence factual assessment of the claim>",
  "evidence_used": ["<source id>", ...]}}"""

JUDGE_PROMPT = """You are an independent, strict grader. You did not retrieve anything
yourself and you have no stake in any retrieval method. Grade the ANSWER below against
the GOLD EVIDENCE taken from the ground-truth document of this claim.

Claim: {claim}

GOLD EVIDENCE (ground-truth document):
{gold}

ANSWER UNDER EVALUATION:
{answer}

Score 0-10. Rubric: final verdict correctness vs the gold evidence (0-4); factual
grounding in the gold evidence with no fabrication (0-4); clarity and completeness (0-2).
Reply ONLY a JSON object:
{{"score": <0-10>, "verdict_ok": true|false, "issues": "<one short sentence>"}}"""

STOP = set("""the a an of in on for to and or is are was were be been being with as
by at from that this these those it its we our their they he she his her you your
i not no do does did can could may might will would should shall than then so such
which who whom whose what when where why how also into over under between during
""".split())


def content_words(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z]{2,}", text.lower()) if t not in STOP]


def eval_vs_qrels(ranked_cids: list[str], relevant: set[str],
                  k_list=(1, 3, 5, 10)) -> dict:
    """与 scripts/22_std2_retrieval.py 同式(BEIR qrels)。"""
    out = {}
    for k in k_list:
        matched = len({c for c in ranked_cids[:k] if c in relevant})
        out[f"recall@{k}"] = matched / len(relevant) if relevant else 0.0
        out[f"hit@{k}"] = 1 if matched else 0
    dcg = sum((1 / math.log2(i + 2)) for i, c in enumerate(ranked_cids[:10])
              if c in relevant)
    n_rel = min(len(relevant), 10)
    idcg = sum(1 / math.log2(i + 2) for i in range(n_rel)) or 1.0
    out["ndcg@10"] = dcg / idcg
    rel5 = sum(1 for c in ranked_cids[:5] if c in relevant)
    out["precision@5"] = rel5 / 5.0
    out["mrr"] = next((1.0 / (i + 1) for i, c in enumerate(ranked_cids)
                       if c in relevant), 0.0)
    return out


def results_dir() -> Path:
    """本子项目独立 run 目录(与套件 run-* 同级)。"""
    from lib import RESULTS, run_id
    out = RESULTS / run_id()
    out.mkdir(parents=True, exist_ok=True)
    return out


# ── 缓存原语 ─────────────────────────────────────────────────────────────────

def _load(kind: str, key: str):
    p = CACHE / f"{kind}_{key}.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return None
    return None


def _save(kind: str, key: str, obj: dict) -> None:
    p = CACHE / f"{kind}_{key}.json"
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    tmp.replace(p)


# ── 阶段: ingest ─────────────────────────────────────────────────────────────

def _ensure_scifact_indexed(mc) -> dict:
    """KB-SciFact 当前 UUID 的向量集合缺失时(代际漂移, 套件陷阱④)按标准配方
    force 重建; 已可查则跳过。返回探针证据。"""
    from lib import BACKEND, http_post
    probe = mc.call("kb_search_vector",
                    {"query": "endoplasmic reticulum stress",
                     "kb_id": "KB-SciFact", "top_k": 3}, timeout=300)
    if probe.get("results"):
        return {"scifact_reindexed": False, "probe_hits": len(probe["results"])}
    docs = mc.call("kb_get_documents", {"kb_id": "KB-SciFact"}, timeout=600)
    names = [str(d.get("name")) for d in docs.get("documents") or []]
    if not names:
        raise RuntimeError("KB-SciFact 无文档 — 先跑 scripts/21_std2_ingest.py")
    url = BACKEND + "/api/v1/search/batch-index"
    r = http_post(url, {"kb_id": "KB-SciFact", "doc_paths": names,
                        "force": True}, timeout=1200)
    time.sleep(3)
    probe = mc.call("kb_search_vector",
                    {"query": "endoplasmic reticulum stress",
                     "kb_id": "KB-SciFact", "top_k": 3}, timeout=300)
    hits = len(probe.get("results") or [])
    if hits == 0:
        raise RuntimeError("KB-SciFact force 重索引后向量探针仍为 0 — 需人工排查")
    return {"scifact_reindexed": True, "docs": len(names),
            "indexed": len(r.get("indexed") or []), "probe_hits": hits}


def stage_ingest() -> dict:
    from index_kb import build_all
    mc = McpClient()
    try:
        scifact = _ensure_scifact_indexed(mc)
        idx = build_all(mc, force=bool(os.environ.get("DR_REBUILD_KB")))
        # KB-SciFact 作用域检索可用性(陷阱④: 长存活后端的 BM25 内存索引)
        probe = mc.call("kb_search_two_stage",
                        {"query": "endoplasmic reticulum stress",
                         "kb_id": "KB-SciFact", "stage1_top_k": 5,
                         "stage2_top_k": 3, "balance_kbs": False}, timeout=420)
        scoped_hits = len(((probe.get("stage1") or {}).get("candidates")) or [])
        return {"scifact": scifact,
                "baseline_indexes": idx,
                "kb_scifact_scoped_probe_hits": scoped_hits,
                "scifact_scoped_ok": scoped_hits > 0}
    finally:
        mc.close()


# ── 阶段: raptor ─────────────────────────────────────────────────────────────

def stage_raptor() -> dict:
    import raptor as raptor_mod
    mc = McpClient()
    oneshot = OmpOneshot(stage="raptor", timeout=300)
    try:
        tree = raptor_mod.build_tree(mc, oneshot,
                                     force=bool(os.environ.get("DR_REBUILD_KB")))
        return {"levels": tree.get("levels"), "nodes": len(tree.get("nodes", {})),
                "summarize_calls": tree.get("summarize_calls"),
                "build_seconds": tree.get("build_seconds"), "reused": tree.get("reused"),
                "omp_calls": oneshot.calls}
    finally:
        mc.close()


# ── 阶段: retrieve ───────────────────────────────────────────────────────────

def _make_ctx_factory(tree):
    """每 worker 线程一个独立 Ctx(独立 MCP 进程, 避免stdio 竞争)。"""
    import threading
    local = threading.local()

    def factory():
        ctx = getattr(local, "ctx", None)
        if ctx is None:
            import methods
            mc = McpClient()
            ctx = methods.Ctx(mc, lambda stage: OmpRpc(stage=stage, timeout=420),
                              OmpOneshot(stage="aux", timeout=300))
            ctx.tree = tree
            local.ctx = ctx
        return ctx
    return factory


def _run_one_query(method: str, q: dict, ctx_factory) -> str:
    key = f"{method}_{q['qid']}"
    if _load("ev", key):
        return f"{key}: cached"
    import methods
    ctx = ctx_factory()
    if method == "qdcvr":
        ev = methods.qdcvr(ctx, q["question"])
    else:
        fn = methods.METHODS[method]["fn"]
        ev = fn(ctx, q["question"])
    ev["qid"] = q["qid"]
    ev["method"] = method
    _save("ev", key, ev)
    hit1 = "1" if ev["doc_rank"][:1] and ev["doc_rank"][0].lower() in \
        {g.lower() for g in q["golden_ids"]} else "0"
    return f"{key}: hit@1={hit1} chunks={len(ev.get('chunks') or [])}"


def stage_retrieve() -> dict:
    import methods
    tree = _load("tree", "raptor") or {}
    if not tree:
        tp = CACHE / "raptor_tree.json"
        tree = json.loads(tp.read_text(encoding="utf-8")) if tp.exists() else {}
    queries = load_queries(LIMIT)
    ctx_factory = _make_ctx_factory(tree)
    t0 = time.time()
    total = len(queries) * len(METHOD_ORDER)
    done = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = [pool.submit(_run_one_query, m, q, ctx_factory)
                for q in queries for m in METHOD_ORDER]
        for f in futs:
            f.result()
            done += 1
            if done % 8 == 0 or done == total:
                print(f"  [retrieve] {done}/{total}", flush=True)
    return {"queries": len(queries), "methods": len(METHOD_ORDER),
            "seconds": round(time.time() - t0, 1)}


# ── 阶段: answer ─────────────────────────────────────────────────────────────

def _answer_one(method: str, q: dict, ev: dict) -> str:
    key = f"{method}_{q['qid']}"
    if _load("ans", key):
        return f"{key}: cached"
    from methods import pack
    evidence, used = pack(ev.get("chunks") or [])
    oneshot = OmpOneshot(stage="answer", timeout=420)
    raw = oneshot(ANSWER_PROMPT.format(claim=q["question"], evidence=evidence
                                       or "(no evidence retrieved)"))
    parsed = extract_json(raw)
    ans = {"raw": raw[:2000], "parsed": parsed if isinstance(parsed, dict) else {},
           "evidence_chars": len(evidence), "evidence_chunks": len(used),
           "sources": sorted({c.get("src", "") for c in used})}
    _save("ans", key, ans)
    return key


def stage_answer() -> dict:
    queries = load_queries(LIMIT)
    jobs = []
    for q in queries:
        for m in METHOD_ORDER:
            ev = _load("ev", f"{m}_{q['qid']}")
            if ev:
                jobs.append((m, q, ev))
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = [pool.submit(_answer_one, m, q, ev) for m, q, ev in jobs]
        for i, f in enumerate(futs):
            f.result()
            if (i + 1) % 8 == 0:
                print(f"  [answer] {i+1}/{len(jobs)}", flush=True)
    return {"answered": len(jobs), "seconds": round(time.time() - t0, 1)}


# ── 阶段: judge(第三方 omp Agent) ────────────────────────────────────────────

def _gold_map(mc) -> dict:
    """cid → (doc_path, content) 惰性缓存。"""
    docs = mc.call("kb_get_documents", {"kb_id": "KB-SciFact"}, timeout=300)
    paths = {}
    for d in docs.get("documents") or []:
        name = str(d.get("name") or d.get("path") or "")
        m = re.search(r"\[([^\[\]]+)\]\s*\.md$", name)
        if m:
            paths[m.group(1)] = f"KB-SciFact/{name}"
    return paths


def _judge_one(method: str, q: dict, ans: dict, gold_text: str) -> str:
    key = f"{method}_{q['qid']}"
    if _load("judge", key):
        return f"{key}: cached"
    answer_text = json.dumps(ans.get("parsed") or {"raw": ans.get("raw", "")},
                             ensure_ascii=False)
    oneshot = OmpOneshot(stage="judge", timeout=420)
    prompt = JUDGE_PROMPT.format(claim=q["question"],
                                 gold=gold_text[:3500],
                                 answer=answer_text[:2200])
    raw = oneshot(prompt)
    parsed = extract_json(raw)
    if not isinstance(parsed, dict) or "score" not in parsed:
        # 一次重判(附格式强化后缀); 两次都失败才落盘空判
        raw = oneshot(prompt + "\n\nIMPORTANT: reply with ONLY the JSON object "
                      '{"score": <0-10>, "verdict_ok": true|false, '
                      '"issues": "..."} — no other text.', )
        parsed = extract_json(raw)
        if not isinstance(parsed, dict):
            parsed = {}
    _save("judge", key, {"raw": raw[:1200], "parsed": parsed})
    return key


def stage_judge() -> dict:
    queries = load_queries(LIMIT)
    gold_paths = {}
    mc = McpClient()
    try:
        gold_paths = _gold_map(mc)
    finally:
        mc.close()
    gold_cache: dict[str, str] = {}

    def gold_text(cid: str) -> str:
        if cid not in gold_cache:
            mc = McpClient()
            try:
                dp = gold_paths.get(cid)
                if not dp:
                    return ""
                d = mc.call("kb_doc_read", {"doc_path": dp, "max_chars": 4000},
                            timeout=120)
                gold_cache[cid] = str(d.get("content") or d.get("raw") or "")
            finally:
                mc.close()
        return gold_cache[cid]

    jobs = []
    for q in queries:
        for m in METHOD_ORDER:
            ans = _load("ans", f"{m}_{q['qid']}")
            if ans:
                jobs.append((m, q, ans, q["golden_ids"][0] if q["golden_ids"] else ""))
    t0 = time.time()

    def work(job):
        m, q, ans, cid = job
        return _judge_one(m, q, ans, gold_text(cid) if cid else "")

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = [pool.submit(work, j) for j in jobs]
        for i, f in enumerate(futs):
            f.result()
            if (i + 1) % 8 == 0:
                print(f"  [judge] {i+1}/{len(jobs)}", flush=True)
    return {"judged": len(jobs), "seconds": round(time.time() - t0, 1)}


# ── 阶段: report ─────────────────────────────────────────────────────────────

def stage_report() -> dict:
    queries = load_queries(LIMIT)
    out = results_dir()
    retrieval, answers, judges, qa = {}, {}, {}, []
    for q in queries:
        relevant = {g.lower() for g in q["golden_ids"]}
        qw = set(content_words(q["question"]))
        row_q = {"qid": q["qid"], "claim": q["question"]}
        for m in METHOD_ORDER:
            ev = _load("ev", f"{m}_{q['qid']}")
            ans = _load("ans", f"{m}_{q['qid']}")
            jd = _load("judge", f"{m}_{q['qid']}")
            row = {}
            if ev:
                row["retrieval"] = eval_vs_qrels([c.lower() for c in
                                                  ev.get("doc_rank") or []],
                                                 relevant)
                ev_text = " ".join(c.get("text", "") for c in ev.get("chunks") or [])
                cov = (len(qw & set(content_words(ev_text))) / len(qw)) if qw else 0
                row["retrieval"]["evidence_coverage"] = round(cov, 4)
                row["cost"] = {"latency_s": round(ev.get("latency", 0), 2),
                               "llm_calls": ev.get("llm_calls", 0),
                               "chunks": len(ev.get("chunks") or []),
                               "turns": (ev.get("trace") or {}).get("turns")}
                retrieval.setdefault(m, []).append(
                    {"qid": q["qid"], **row["retrieval"], **row["cost"]})
            if ans:
                p = ans.get("parsed") or {}
                answers.setdefault(m, []).append(
                    {"qid": q["qid"], "verdict": p.get("verdict", ""),
                     "answer": p.get("answer", ""),
                     "evidence_chars": ans.get("evidence_chars")})
                row["answer"] = p
            if jd:
                jp = jd.get("parsed") or {}
                try:
                    score = float(jp.get("score"))
                except (TypeError, ValueError):
                    score = None
                judges.setdefault(m, []).append(
                    {"qid": q["qid"], "score": score,
                     "verdict_ok": jp.get("verdict_ok"),
                     "issues": jp.get("issues", "")})
                row["judge"] = jp
                row["judge_score"] = score
            if ev or ans or jd:
                qa.append({"qid": q["qid"], "method": m,
                           "claim": q["question"],
                           "golden_ids": q["golden_ids"],
                           "evidence_sources": ans.get("sources") if ans else None,
                           "answer": (ans or {}).get("parsed"),
                           "judge": (jd or {}).get("parsed"),
                           "trace": (ev or {}).get("trace")})
                row_q[m] = row

    def agg_rows(rows):
        if not rows:
            return {}
        keys = ["hit@1", "hit@3", "hit@5", "hit@10", "recall@5", "ndcg@10",
                "precision@5", "mrr", "evidence_coverage"]
        out = {k: round(mean([r[k] for r in rows if isinstance(r.get(k), (int, float))]), 4)
               for k in keys}
        out["n"] = len(rows)
        out["mean_latency_s"] = round(mean([r.get("latency_s") for r in rows]), 2)
        out["sum_llm_calls"] = sum(r.get("llm_calls", 0) for r in rows)
        return {k: v for k, v in out.items() if v is not None}

    judge_summary = {}
    for m, rows in judges.items():
        scores = [r["score"] for r in rows if isinstance(r.get("score"), (int, float))]
        judge_summary[m] = {
            "mean_score": round(mean(scores), 3) if scores else None,
            "verdict_ok_rate": round(mean([1 if r.get("verdict_ok") else 0
                                           for r in rows]), 4) if rows else None,
            "n_scored": len(scores), "n": len(rows)}

    verdict_summary = {}
    for m, rows in answers.items():
        vs: dict[str, int] = {}
        for r in rows:
            vs[r.get("verdict") or "?"] = vs.get(r.get("verdict") or "?", 0) + 1
        verdict_summary[m] = vs

    report = {
        "meta": {"generated": now_iso(), "env": env_fingerprint(),
                 "paper": "DeepRead: Document Structure-Aware Reasoning to "
                          "Enhance Agentic Search (arXiv:2602.05014)",
                 "corpus": "BEIR SciFact subset, 148 docs (KB-SciFact, frozen)",
                 "queries": len(queries),
                 "evidence_budget_chars": 4000,
                 "agentic_turn_cap": 8,
                 "agent_channel": "omp RPC (deepseek-flash via omp --mode=rpc / -p --mode=json)",
                 "judge": "independent omp agent, fresh process, gold evidence injected",
                 "methods": {m: METHODS_PAPER[m] for m in METHOD_ORDER}},
        "summary": {
            "retrieval": {m: agg_rows(retrieval.get(m) or []) for m in METHOD_ORDER},
            "judge": judge_summary,
            "verdicts": verdict_summary},
        "retrieval_rows": retrieval,
        "judge_rows": judges,
        "answer_rows": answers,
        "qa": qa,
    }
    jp = out / "deepread_matrix.json"
    jp.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    _write_transcripts(out, report)
    print(f"-> {jp}")
    for m in METHOD_ORDER:
        s = report["summary"]["retrieval"].get(m) or {}
        j = judge_summary.get(m) or {}
        print(f"  {m:17s} hit@1={s.get('hit@1')} nDCG@10={s.get('ndcg@10')} "
              f"R@5={s.get('recall@5')} judge={j.get('mean_score')}")
    return {"written": str(jp)}


def _write_transcripts(out: Path, report: dict) -> None:
    lines = ["# DeepRead 基线矩阵 — 提问与回答全记录",
             "",
             f"- paper: {report['meta']['paper']}",
             f"- corpus/queries: {report['meta']['corpus']} / {report['meta']['queries']} 条",
             f"- agent: {report['meta']['agent_channel']}",
             f"- judge: {report['meta']['judge']}",
             ""]
    by_q: dict[str, list] = {}
    for item in report["qa"]:
        by_q.setdefault(item["qid"], []).append(item)
    for q in load_queries(LIMIT):
        lines += [f"## {q['qid']} — {q['question']}", "",
                  f"- 金标文档: {', '.join(q['golden_ids'])}", ""]
        for item in by_q.get(q["qid"], []):
            a = item.get("answer") or {}
            j = item.get("judge") or {}
            lines += [f"### {item['method']}", "",
                      f"- 判分: **{j.get('score', '-')}**/10 "
                      f"(verdict_ok={j.get('verdict_ok')}) {j.get('issues', '')}",
                      f"- 证据来源: {', '.join(item.get('evidence_sources') or []) or '-'}",
                      f"- 回答: **{a.get('verdict', '-')}** — {a.get('answer', '')}",
                      ""]
    (out / "deepread_qa_transcripts.md").write_text(
        "\n".join(lines), encoding="utf-8")


METHODS_PAPER = {
    "qdcvr": "this system: knowledgebase-search skill (two-stage + 0.35 threshold "
             "+ kb_doc_read content verification rerank)",
    "dense_rag": "DeepRead Table 1 'Dense RAG' (chunk 800/400, dense top-10)",
    "dense_rag_rerank": "DeepRead Table 1 'Dense RAG w/ Reranker' "
                        "(30 cands → rerank → 10; LLM listwise surrogate)",
    "raptor": "DeepRead Table 1 'RAPTOR' (Collapsed Tree, ≤800 tok/node, "
              "5 layers, cluster top-5, top-10)",
    "itrg_refresh": "DeepRead Table 1 'ITRG (refresh)' (4 rounds × top-6)",
    "itrg_refine": "DeepRead Table 1 'ITRG (refine)' (4 rounds × top-6)",
    "search_o1": "DeepRead Table 1 'Search-o1' (flat struct chunks o0, "
                 "2 chunks/call, cap 8 turns)",
    "deepread": "DeepRead Table 1 'DeepRead' (TOC + Retrieve ω=(1,1) + "
                "ReadSection, cap 8 turns)",
}

STAGES = {"ingest": stage_ingest, "raptor": stage_raptor,
          "retrieve": stage_retrieve, "answer": stage_answer,
          "judge": stage_judge, "report": stage_report}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", action="append", choices=[*STAGES, "all"])
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    order = ["ingest", "raptor", "retrieve", "answer", "judge", "report"]
    todo = order if (args.all or not args.stage) else args.stage
    for s in todo:
        print(f"=== stage {s} ===", flush=True)
        res = STAGES[s]()
        print(json.dumps(res, ensure_ascii=False)[:400], flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
