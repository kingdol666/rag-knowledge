#!/usr/bin/env python3
"""158_a_retrieval_regression — A 任务（检索回归探针）的可复现工件。

论文 Table 1 有一行「Retrieval regression probes 15/15」，出处是
`results/r2_organize_report.json` 的 `o5c_probes` —— 那是 2026-09 整理阶段留下的
历史产物，**无法重跑**（原始整理脚本已不在管线里）。这构成审稿风险：一行被引用的
数字没有可执行的再生路径。本脚本补上这条路径。

做法：对五个门类库各取 3 篇 manifest 里的真实论文（共 15 篇），用论文标题里的
判别性短语做查询，在**该门类库自己的 collection** 上跑 `kb_search_vector`
（kb_id = 门类库 UUID，top_k = 10），断言金标论文出现在召回集里，并记录名次/分数。

判据是「召回可达性」，不是「答案质量」：分母固定 15，失败即 exit 1，便于 CI。
用法：python scripts/158_a_retrieval_regression.py [--top-k 10]
输出：results/a_retrieval_regression.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402

SUITE = Path(__file__).resolve().parent.parent
R = SUITE / "results"

# (门类库名, 判别性查询, 金标 arxiv id, 金标文件前缀)
#
# ⚠️ 金标库归属以 `results/_corpus_routing.json`（100 篇 → 实况分类，2026-10-13 实测）
# 为准，**不是 manifest 的 field**：平台按内容路由，robotics/social-networks 这类
# field 的论文会落到「计算机与人工智能」库，seismology 的 1308.1846 落在「自然科学
# 与地球科学」。按 manifest field 猜库会得到假 MISS——这里 15 条探针全部核对过实测归属。
PROBES = [
    ("计算机与人工智能", "scaled dot-product attention multi-head parallel computation",
     "1706.03762", "artificial-intelligence__1706.03762"),
    ("计算机与人工智能", "masked language model bidirectional pre-training fine-tuning",
     "1810.04805", "nlp__1810.04805"),
    ("计算机与人工智能", "few-shot learners in-context learning scaling language models",
     "2005.14165", "large-language-models__2005.14165"),
    ("自然科学与地球科学", "daily precipitation extremes under climate change",
     "1503.07557", "climate-science__1503.07557"),
    ("自然科学与地球科学", "supershear rupture indicator in near-fault particle motion",
     "2606.10843", "seismology__2606.10843"),
    ("自然科学与地球科学", "quantum error mitigation benchmarking noisy intermediate-scale devices",
     "2303.00445", "quantum-physics__2303.00445"),
    ("生命科学与医学", "tumor elimination immune evasion control strategies",
     "2604.01385", "immunology__2604.01385"),
    ("生命科学与医学", "influenza vaccine design epitope analysis",
     "0408016", "immunology__q-bio-0408016"),
    ("生命科学与医学", "large language models encode clinical knowledge",
     "2212.13138", "clinical-medicine__2212.13138"),
    ("工程与能源", "disruption sources in the power grid resilience",
     "2207.08146", "power-systems__2207.08146"),
    ("工程与能源", "oxygen redox in battery cathodes anionic redox",
     "2408.09942", "materials__2408.09942"),
    ("计算机与人工智能", "multilayer perceptron simultaneous localization and mapping MLP SLAM",
     "2410.10669", "robotics__2410.10669"),
    ("经济与社会", "unified growth theory economic growth in Europe",
     "1512.08067", "economics__1512.08067"),
    ("经济与社会", "backtest of trading systems on candle charts",
     "1412.5558", "finance__1412.5558"),
    ("计算机与人工智能", "information consumption boundary spanning decentralized social media",
     "2203.15752", "social-networks__2203.15752"),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument("--out", default=str(R / "a_retrieval_regression.json"))
    args = ap.parse_args()

    mc = lib.McpClient()
    try:
        cat = mc.call("kb_list", {"lightweight": True})
        name2id = {i.get("name"): i.get("kb_id") for i in (cat.get("catalog") or [])}
    finally:
        pass

    probes, failures = [], []
    try:
        for lib_name, query, gold, slug in PROBES:
            kb_id = name2id.get(lib_name)
            if not kb_id:
                probes.append({"library": lib_name, "query": query, "gold": gold,
                               "hit": False, "error": "library not found"})
                failures.append(f"{gold}: library {lib_name} missing")
                continue
            r = mc.call("kb_search_vector", {"query": query, "kb_id": kb_id,
                                             "top_k": args.top_k})
            res = r.get("results") or []
            paths = [str(x.get("doc_path") or "") for x in res]
            rank = next((i + 1 for i, p in enumerate(paths) if slug in p), None)
            hit = rank is not None
            probes.append({
                "library": lib_name, "query": query, "gold": gold, "slug": slug,
                "hit": hit, "rank": rank, "returned": len(res),
                "top_score": round(float(res[0].get("score") or 0), 4) if res else None,
                "gold_score": (round(float(res[rank - 1].get("score") or 0), 4)
                               if hit else None),
                "top_paths": paths[:3],
            })
            if not hit:
                failures.append(f"{gold}: not in top-{args.top_k} of {lib_name}")
            print(f"{'HIT ' if hit else 'MISS'} rank={rank} {gold:12s} {lib_name} "
                  f"· {query[:52]}", flush=True)
    finally:
        mc.close()

    out = {
        "task": "A — retrieval regression (dense recall reachability)",
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "top_k": args.top_k,
        "probes_pass": len(PROBES) - len(failures),
        "probes_total": len(PROBES),
        "failures": failures,
        "libraries": sorted({p[0] for p in PROBES}),
        "probes": probes,
        "verdict": "pass" if not failures else "fail",
    }
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1),
                              encoding="utf-8")
    print(f"\n[verdict] {out['verdict']} — probes "
          f"{out['probes_pass']}/{out['probes_total']}")
    print(f"[done] → {args.out}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
