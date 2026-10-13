#!/usr/bin/env python3
r"""163_paper_macro_table.py —— 把 results/paper_report.json 摊成一张「论文宏 vs 本轮实测」对照表。

用途：投稿前决定要不要改 main.tex 的 15 个 \NUM* 宏，以及哪些论文论断（成本排序、
延迟排序、缺 2 次=工具不可用）在新一轮里还站得住。

用法
    python scripts/163_paper_macro_table.py                    # 用 results/paper_report.json
    python scripts/163_paper_macro_table.py --report <path>
    python scripts/163_paper_macro_table.py --tex                # 只打可直接粘进 main.tex 的宏块
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
RESULTS = SUITE / "results"
TRACKS = ("a2", "b", "c")
LABEL = {"a2": "A", "b": "B", "c": "C"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", default=str(RESULTS / "paper_report.json"))
    ap.add_argument("--tex", action="store_true", help="只输出 LaTeX 宏块")
    args = ap.parse_args()

    p = Path(args.report)
    if not p.exists():
        print(f"[fail] 找不到 {p}；先跑 python scripts/161_final_evidence.py")
        return 2
    d = json.loads(p.read_text(encoding="utf-8"))
    m, g = d["meta"], d["grades"]
    # per_question 结构：{qid: {qid, question, gold, cells:[{track, grounded, kw_ok,
    #   cited, sentinel, is_error, latency_s, tools, pass, state}, ...]}}
    raw = d["per_question"]
    q: list[dict] = []
    if isinstance(raw, dict):
        for qid, blob in raw.items():
            if isinstance(blob, dict) and isinstance(blob.get("cells"), list):
                for c in blob["cells"]:
                    q.append({**c, "qid": qid})
            elif isinstance(blob, list):
                q.extend({**c, "qid": qid} for c in blob if isinstance(c, dict))
    elif isinstance(raw, list):
        q = raw

    def _hit(r: dict, key: str) -> bool:
        """兼容两种字段名：grounded/gold_hit、kw_ok/kw_hit。"""
        if key == "gold_hit":
            return bool(r.get("gold_hit", r.get("grounded")))
        if key == "kw_hit":
            v = r.get("kw_hit")
            if isinstance(v, bool):
                return v
            return bool(r.get("kw_ok"))
        return bool(r.get(key))

    obs = {}
    for t in d["tracks"]:
        x = g[t]
        n = x["n"] or 1
        obs[t] = {
            "grounded": x["grounded"], "kw": x["kw_ok"], "cited": x["cited"],
            "cited_chunk": x["cited_chunk"],
            "lat": round(x["latency_avg_s"]), "cost": round(x["cost_usd_total"] / n, 2),
            "cost_total": x["cost_usd_total"], "tools": x["tools_avg"],
            "pass": x["pass"], "sentinel": x["sentinel"],
        }

    if args.tex:
        print("%% ==== 本轮实测（%s / %s）→ 可直接替换 main.tex:28-32 ====" %
              (m["run_id"], m.get("question_file") or m.get("qfile")))
        for t in TRACKS:
            o = obs[t]
            print(f"\\newcommand{{\\NUMgrounded{LABEL[t]}}}{{{o['grounded']}}}"
                  f"\\newcommand{{\\NUMkw{LABEL[t]}}}{{{o['kw']}}}"
                  f"\\newcommand{{\\NUMcite{LABEL[t]}}}{{{o['cited']}}}")
        for t in TRACKS:
            o = obs[t]
            print(f"\\newcommand{{\\NUMlat{LABEL[t]}}}{{{o['lat']}\\,s}}")
        for t in TRACKS:
            o = obs[t]
            print(f"\\newcommand{{\\NUMcost{LABEL[t]}}}{{\\${o['cost']:.2f}}}")
        return 0

    print(f"run      : {m['run_id']}  (commit {m['git_commit']} · {m['prompt_version']})")
    print(f"题集     : {m.get('question_file') or m.get('qfile')} · {m.get('n_rows')} 单元")
    print(f"总成本   : ${m.get('total_cost_usd')} · tokens_out {m.get('tokens_out_total')}")
    stab = d.get("stability") or {}
    if stab.get("cells"):
        print(f"稳定性   : {stab.get('ok_cells')}/{stab.get('cells')} 单元行为正确 · "
              f"车道契约 {stab.get('lane_ok_cells')}/{stab.get('cells')} · "
              f"中位 {stab.get('latency_median_s')}s（{stab.get('latency_min_s')}-"
              f"{stab.get('latency_max_s')}s）· ${stab.get('cost_usd_total')}")
    print()

    print("轨迹   指标        本轮      论文宏    判定")
    print("-" * 62)
    paper = {"grounded": {"a2": 10, "b": 10, "c": 8},
             "kw": {"a2": 10, "b": 8, "c": 6},
             "cited": {"a2": 9, "b": 6, "c": 1},
             "lat": {"a2": 116, "b": 48, "c": 41},
             "cost": {"a2": 0.55, "b": 0.63, "c": 0.28}}
    unit = {"grounded": "/10", "kw": "/10", "cited": "/10", "lat": "s", "cost": "$"}
    for key in ("grounded", "kw", "cited", "lat", "cost"):
        for t in TRACKS:
            o, pv = obs[t][key], paper[key][t]
            same = (o == pv)
            print(f"{LABEL[t]:>2}     {key:<10} {str(o) + unit[key]:<9} {str(pv) + unit[key]:<9} "
                  f"{'✓ 一致' if same else '✗ 需刷新'}")
    print()
    print("附注（不进论文的宏，但解释本轮发生了什么）")
    for t in TRACKS:
        o = obs[t]
        print(f"  {LABEL[t]} 轨：pass {o['pass']}/10 · 工具面中断 {o['sentinel']} · "
              f"平均工具调用 {o['tools']} · 成本合计 ${o['cost_total']} · "
              f"dense-chunk 标记 {o['cited_chunk']}/10")
    print()
    ca = obs["a2"]["cost_total"] / 10
    cb = obs["b"]["cost_total"] / 10
    cc = obs["c"]["cost_total"] / 10
    la = obs["a2"]["lat"]
    print("论文论断复核（这些是正文句子，不是宏）")
    print(f"  ① 「平台最慢」：A {la}s vs B {obs['b']['lat']}s vs C {obs['c']['lat']}s → "
          f"{'成立' if la > max(obs['b']['lat'], obs['c']['lat']) else '不成立'}")
    print(f"  ② 「平台不最贵」：A ${ca:.2f} vs B ${cb:.2f} vs C ${cc:.2f} → "
          f"{'成立' if ca < max(cb, cc) else '不成立（A 已是最贵）'}")
    n_miss = sum(1 for r in q if r.get("track") == "c" and not _hit(r, "gold_hit"))
    n_abort = sum(1 for r in q if r.get("track") == "c"
                  and not _hit(r, "gold_hit") and r.get("sentinel"))
    print(f"  ③ 「C 轨每次 grounding miss 都是工具不可用中止」：C miss {n_miss} 次，"
          f"其中哨兵 {n_abort} 次 → "
          f"{'成立' if n_miss and n_miss == n_abort else ('成立（本轮 C 轨无 miss）' if not n_miss else '不成立（存在非中止 miss）')}")
    print()
    print("逐题（只列未满分/状态异常；state ∈ pass|kw|gold|sentinel|error）")
    for r in q:
        kw = r.get("kw_hits")
        kw_s = f"{kw}/{r.get('kw_total')}" if kw is not None else str(r.get("kw_hit"))
        bad = (r.get("state") not in (None, "pass")) or r.get("sentinel") or r.get("is_error")
        if bad:
            print(f"  {LABEL.get(str(r.get('track')), r.get('track'))}/{r.get('qid')}: "
                  f"state={r.get('state')} kw={kw_s} gold={_hit(r, 'gold_hit')} "
                  f"sentinel={r.get('sentinel')} err={r.get('is_error')} "
                  f"{r.get('latency_s')}s tools={r.get('tools')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
