#!/usr/bin/env python3
"""用户自带文件 × 论文复现算法矩阵 — 检索 top-k + 依据检索内容作答.

这是 E19(user_scenario.py / scripts/29_real_scenario_test.py)所依赖的**同一批
原语**的命令行入口, 补上"用户自由传入文件 + 自由提问"这一环(29 号脚本把文档
与问题都写死在源码里, 且只跑离线批量矩阵).

流程(全部走平台真实用户路径):
  1. 读取用户文件(任意 .md/.txt, UTF-8)
  2. 生产 KB: kb_doc_create 逐篇上传(tree-fs + 后台向量/图索引) → qdcvr 在此库检索
  3. 基线 KB: 按各论文自己的分块方案建 suite 侧索引
     Chunks800(单遍/ITRG) · Struct(Search-o1/DeepRead) · Paras(DeepRead Retrieve)
     · Raptor(Collapsed Tree, 可选, 需 LLM 建树)
  4. 选算法检索 → doc_rank(top-k) + 证据 chunks
  5. 同一 omp Agent 依据检索证据作答(可挑选任一算法)

用法:
  python ask_user_docs.py --docs f1.md f2.md --question "..." \
      --methods qdcvr,dense_rag --prefix VerifyDemo
  python ask_user_docs.py --docs f.md --question "..." --with-raptor --judge
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "scripts"))

import user_scenario as us  # noqa: E402
from lib import McpClient  # noqa: E402
from methods import METHODS, pack  # noqa: E402
from omp_client import OmpOneshot  # noqa: E402

ALL_METHODS = ["qdcvr", "dense_rag", "dense_rag_rerank", "raptor",
               "itrg_refresh", "itrg_refine", "search_o1", "deepread"]


def oneshot_factory(stage: str) -> OmpOneshot:
    return OmpOneshot(stage=stage, timeout=420)


def retrieve(method: str, ctx, question: str) -> dict:
    import methods as m
    if method == "qdcvr":
        # 用户场景禁用全局兜底: 会混入本库之外的其他 KB 文档
        return m.qdcvr(ctx, question, allow_global_fallback=False)
    return METHODS[method]["fn"](ctx, question)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", nargs="+", required=True,
                    help="用户文件路径(可多个)")
    ap.add_argument("--question", required=True, help="用户问题")
    ap.add_argument("--methods", default="qdcvr,dense_rag",
                    help=f"逗号分隔, 可选: {','.join(ALL_METHODS)}")
    ap.add_argument("--prefix", default="VerifyDemo",
                    help="基线 KB 名前缀(默认 VerifyDemo, 不污染 E19 的 UserDemo)")
    ap.add_argument("--prod-kb", default="",
                    help="生产 KB 名(默认 KB-<prefix>)")
    ap.add_argument("--with-raptor", action="store_true",
                    help="建 RAPTOR 树(需要 LLM, 小语料约 1-2 分钟)")
    ap.add_argument("--judge", action="store_true",
                    help="额外让独立 Agent 依据 golden 引文打分(需 --gold)")
    ap.add_argument("--gold", default="", help="金标引文(用于 --judge)")
    ap.add_argument("--reuse-kb", action="store_true",
                    help="复用已有索引(默认按内容指纹自动判定)")
    args = ap.parse_args()

    paths = [Path(p) for p in args.docs]
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        print(f"[error] 文件不存在: {missing}")
        return 2
    want = [m.strip() for m in args.methods.split(",") if m.strip()]
    bad = [m for m in want if m not in ALL_METHODS]
    if bad:
        print(f"[error] 未知算法 {bad}; 可选: {ALL_METHODS}")
        return 2
    if "raptor" in want and not args.with_raptor:
        args.with_raptor = True
        print("[note] 选中 raptor → 自动建树 (--with-raptor)")

    prefix = args.prefix
    prod_kb = args.prod_kb or f"KB-{prefix}"

    docs = us.load_user_docs(paths)
    print(f"[1/5] 读取用户文件: {[(d['cid'], len(d['text'])) for d in docs]}",
          flush=True)
    print(f"      指纹 {us.fingerprint(docs)}", flush=True)

    mc = McpClient()
    try:
        print(f"[2/5] 上传到生产 KB `{prod_kb}` (kb_doc_create 真实用户路径) ...",
              flush=True)
        prod = us.ensure_production_kb(mc, prod_kb, docs)
        print(f"      -> {json.dumps(prod, ensure_ascii=False)}", flush=True)

        print(f"[3/5] 建论文基线索引 (前缀 {prefix}) ...", flush=True)
        baseline = us.build_baseline_kbs(mc, docs, prefix)
        for k, v in baseline.items():
            print(f"      -> {k}: {v['items']} items, probe="
                  f"{v['vector_probe_hits']}, reused={v['reused']}, "
                  f"{v['build_seconds']}s", flush=True)

        if args.with_raptor:
            print("      -> RAPTOR 建树 (omp 摘要) ...", flush=True)
            tree = us.build_user_raptor(mc, oneshot_factory("raptor"), docs,
                                        prefix)
            print(f"      -> {json.dumps(tree, ensure_ascii=False)}", flush=True)
    finally:
        mc.close()

    us.activate_profile(prefix, prod_kb)
    ctx_get = us.make_ctx_factory(McpClient, docs, prefix)

    print(f"[4/5] 检索 + 作答 (问题: {args.question!r}) ...", flush=True)
    out = {"question": args.question, "docs": [str(p) for p in paths],
           "prod_kb": prod_kb, "prefix": prefix, "results": {}}
    for method in want:
        t0 = time.perf_counter()
        ctx = ctx_get()
        ev = retrieve(method, ctx, args.question)
        evidence, used = pack(ev.get("chunks") or [])
        ans = us.answer_question(oneshot_factory, args.question, ev)
        row = {"doc_rank_topk": (ev.get("doc_rank") or [])[:10],
               "n_chunks": len(ev.get("chunks") or []),
               "evidence_sources": ans["sources"],
               "evidence_chars": ans["evidence_chars"],
               "answer": ans.get("parsed"),
               "trace": ev.get("trace", {}),
               "latency_s": round(time.perf_counter() - t0, 1),
               "llm_calls": ev.get("llm_calls", 0)}
        if args.judge and args.gold:
            jd = us.judge_answer(oneshot_factory, args.question, args.gold, ans)
            row["judge"] = jd.get("parsed")
        out["results"][method] = row
        print(f"      [{method:<17}] topk={row['doc_rank_topk'][:5]} "
              f"chunks={row['n_chunks']} lat={row['latency_s']}s", flush=True)
        print(f"        answer: "
              f"{json.dumps(row['answer'], ensure_ascii=False)[:600]}",
              flush=True)

    print("[5/5] 结果 JSON:", flush=True)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
