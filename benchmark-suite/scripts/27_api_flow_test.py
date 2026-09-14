#!/usr/bin/env python3
"""E16b · API 全流程测试 — 通过 algorithms/api_server.py 的 HTTP 接口,
对同一语料同一问题选择 8 种检索算法问答: 检索指标(RAG 常用评价体系) +
统一作答对比 + 中间 Agent 匿名排名打分, 全部落盘并与 E16 缓存核对一致性.

流程:
  1. GET /health                — 服务存活/方法注册表(启动验证)
  2. GET /methods /questions
  3. 每条冻结查询 POST /compare {"qid", "rank": true}
       → 8 方法各自 检索指标 + 回答 + 第三方 judge(0-10)
       → 中间 Agent 对匿名答案(A-H)排名打分
  4. 与 run_matrix 缓存(E16)核对作答/判分一致性(同 prompt 同缓存 ⇒ 逐字一致)
  5. 落盘 results/run-*/api_matrix.json + api_side_by_side.md

用法:
  python scripts/27_api_flow_test.py            # 全量 30 查询
  BENCH_LIMIT=2 python scripts/27_api_flow_test.py   # 冒烟
前置: python algorithms/api_server.py 已启动(127.0.0.1:8790)。
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from lib import env_fingerprint, http_get, http_post, now_iso  # noqa: E402

API = "http://127.0.0.1:8790"
RESULTS = HERE.parent / "results"
LIMIT = int(__import__("os").environ.get("BENCH_LIMIT", "0"))


def mean(xs):
    xs = [x for x in xs if isinstance(x, (int, float))]
    return round(sum(xs) / len(xs), 4) if xs else None


def main() -> int:
    # 1) 启动验证
    health = http_get(API + "/health", timeout=30)
    assert health.get("status") == "ok", health
    methods = health["methods"]
    print(f"[api] alive: {len(methods)} methods, {health['queries']} queries",
          flush=True)
    reg = http_get(API + "/methods", timeout=30)
    questions = http_get(API + "/questions", timeout=30)["queries"]
    if LIMIT:
        questions = questions[:LIMIT]

    # 2) 逐查询并答 + 中间 Agent 排名
    rows = []
    t0 = time.time()
    for i, q in enumerate(questions):
        resp = http_post(API + "/compare",
                         {"qid": q["qid"], "rank": True}, timeout=1800)
        if resp.get("error"):
            raise RuntimeError(f"{q['qid']}: {resp['error']}")
        rows.append(resp)
        best = (resp.get("middle_agent_ranking") or [{}])[0]
        print(f"  [{i+1}/{len(questions)}] {q['qid']} "
              f"中间Agent首选={best.get('method')}({best.get('score')})",
              flush=True)

    # 3) 与 E16 缓存一致性核对(同 prompt 同缓存 ⇒ 应逐字一致)
    algo_cache = HERE.parent / "algorithms" / "cache"
    mism = 0
    checked = 0
    for row in rows:
        for m, r in row["results"].items():
            cf = algo_cache / f"ans_{m}_{row['qid']}.json"
            if cf.exists():
                cached = json.loads(cf.read_text(encoding="utf-8"))
                if cached.get("parsed") != r.get("answer"):
                    mism += 1
                checked += 1
            jf = algo_cache / f"judge_{m}_{row['qid']}.json"
            if jf.exists() and r.get("judge") is not None:
                cj = json.loads(jf.read_text(encoding="utf-8")).get("parsed")
                if (cj or {}).get("score") != (r["judge"] or {}).get("score"):
                    mism += 1
                    checked += 1
                checked += 1

    # 4) 聚合
    summary = {}
    for m in methods:
        met = {"hit@1": [], "hit@5": [], "recall@5": [], "ndcg@10": [],
               "mrr": []}
        judges, ranks = [], []
        for row in rows:
            r = row["results"][m]
            mm = r.get("metrics") or {}
            for k in met:
                if isinstance(mm.get(k), (int, float)):
                    met[k].append(mm[k])
            j = (r.get("judge") or {}).get("score")
            if isinstance(j, (int, float)):
                judges.append(j)
            for pos, item in enumerate(row.get("middle_agent_ranking") or []):
                if item.get("method") == m:
                    ranks.append({"pos": pos + 1, "score": item.get("score"),
                                  "n": len(row.get("middle_agent_ranking") or [])})
        wins = sum(1 for x in ranks if x["pos"] == 1)
        summary[m] = {
            "hit@1": mean(met["hit@1"]), "hit@5": mean(met["hit@5"]),
            "recall@5": mean(met["recall@5"]), "ndcg@10": mean(met["ndcg@10"]),
            "mrr": mean(met["mrr"]),
            "mean_judge": mean(judges), "n_judged": len(judges),
            "mean_middle_rank_pos": mean([x["pos"] for x in ranks]),
            "middle_agent_wins": wins, "n_ranked": len(ranks),
        }

    result = {
        "meta": {"generated": now_iso(), "env": env_fingerprint(),
                 "api": API, "queries": len(questions),
                 "methods": methods,
                 "consistency_vs_e16_cache": {
                     "checked": checked, "mismatches": mism,
                     "ok": mism == 0}},
        "summary": summary,
        "rows": rows,
    }
    run_stamp = time.strftime("run-%Y%m%dT%H%M%SZ", time.gmtime())
    out_dir = RESULTS / run_stamp
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "api_matrix.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1),
                   encoding="utf-8")

    # 5) 并排问答记录
    lines = ["# API 并排问答 — 同一问题 × 8 检索算法", ""]
    for row in rows:
        lines += [f"## {row['qid']} — {row['question']}", "",
                  f"金标: {', '.join(row['golden_ids'])}", ""]
        ranking = row.get("middle_agent_ranking") or []
        if ranking:
            lines += ["中间 Agent 排名: " + " > ".join(
                f"{x['method']}({x['score']})" for x in ranking), ""]
        for m in methods:
            r = row["results"][m]
            a = r.get("answer") or {}
            j = (r.get("judge") or {}).get("score")
            lines += [f"### {m}", "",
                      f"- 指标: hit@1={fmt0((r.get('metrics') or {}).get('hit@1'))} "
                      f"R@5={fmt0((r.get('metrics') or {}).get('recall@5'))} "
                      f"nDCG@10={fmt0((r.get('metrics') or {}).get('ndcg@10'))} "
                      f"judge={j}",
                      f"- 回答({a.get('verdict')}): {a.get('answer','')}", ""]
    (out_dir / "api_side_by_side.md").write_text("\n".join(lines),
                                                 encoding="utf-8")

    print(json.dumps({"summary": summary,
                      "consistency": result["meta"]["consistency_vs_e16_cache"],
                      "out": str(out)}, ensure_ascii=False, indent=1))
    return 0


def fmt0(x):
    return f"{x:.3f}" if isinstance(x, (int, float)) else "-"


if __name__ == "__main__":
    sys.exit(main())
