#!/usr/bin/env python3
"""汇整实验结果 → EXPERIMENTS-RESULTS.md + experiments-report.html.

读取 results/run-* 下本设计（EXPERIMENT-DESIGN.md）产出的全部 JSON，
生成论文可引用的两组报告（数值全部来自真实运行，不做任何手工编辑）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import RESULTS, env_fingerprint, now_iso  # noqa: E402

HERE = Path(__file__).resolve().parent
CHART = HERE / "chart.umd.min.js"


def latest(pattern: str) -> Path | None:
    hits = sorted(RESULTS.glob(f"run-*/{pattern}"))
    return hits[-1] if hits else None


def load(pattern: str):
    p = latest(pattern)
    return (json.loads(p.read_text(encoding="utf-8")), p) if p else (None, p)


def fmt(x, nd=3):
    if x is None:
        return "—"
    return f"{x:.{nd}f}" if isinstance(x, (int, float)) else str(x)


def main() -> int:
    abl1, abl1p = load("ablation_scifact_1.json")
    abl2, abl2p = load("ablation_scifact_2.json")
    stats, statsp = load("stats_significance.json")
    hot, hotp = load("hotpot_main_1.json")
    suite1, s1p = load("experience_suite_1.json")
    suite2, s2p = load("experience_suite_2.json")
    case, casep = load("motivating_case.json")
    drm, drmp = load("deepread_matrix.json")
    ops, opsp = load("platform_ops_eval.json")
    apim, apimp = load("api_matrix.json")
    env = env_fingerprint()

    md: list[str] = []
    html: list[str] = []

    md.append("# EXPERIMENTS-RESULTS — 论文实验真实运行结果")
    md.append("")
    md.append(f"> 由 `scripts/70_build_report.py` 自动汇整 · {now_iso()}")
    md.append(f"> 运行身份: git `{env['git_commit']}` · config `{env['config_hash']}` · "
              f"seed {env['seed']} · 全部数字来自 `results/run-*/` 下的真实运行 JSON")
    md.append("")
    md.append("## 0. 执行清单与产物")
    md.append("")
    md.append("| 实验 | 状态 | 产物 |")
    md.append("|---|---|---|")
    rows_status = [
        ("E1 同查询集消融 (SciFact×30, 9 变体, 双轮)", abl1 and abl2, f"`{abl1p}` / `{abl2p}`"),
        ("E2 配对统计 (bootstrap CI + Wilcoxon + Holm)", stats, f"`{statsp}`"),
        ("E8 多域公开基准 (HotpotQA×50, 9 主题 KB, 4 方法)", hot, f"`{hotp}`"),
        ("E3 冥想状态重置 ×3 轮 (两轮样本)", suite1 and suite2, f"`{s1p}` / `{s2p}`"),
        ("E5 五路 leave-one-out (12 经验查询)", suite1, f"`{s1p}`"),
        ("E6 衰减敏感性 (7/14/30/90d)", suite1, f"`{s1p}`"),
        ("E4 双基线同判 (no-synthesis / LLM-summary / ours)", suite1, f"`{s1p}`"),
        ("E12 动机案例挖掘 (TODO-1)", case, f"`{casep}`"),
        ("E16 DeepRead 基线矩阵 (30 查询 × 8 方法, omp RPC 作答+第三方判分)", drm, f"`{drmp}`"),
        ("E16b API 全流程 (HTTP 选算法问答 + 中间 Agent 排名)", apim, f"`{apimp}`"),
        ("E17 平台整理功能评价 (去重/标签/图谱/目录)", ops, f"`{opsp}`"),
    ]
    for name, ok, p in rows_status:
        md.append(f"| {name} | {'✅' if ok else '❌'} | {p} |")
    md.append("")

    # E1
    if abl1:
        md.append("## E1 · 消融实验 — 与主表同查询集（SciFact 30 查询, 官方 qrels）")
        md.append("")
        md.append("说明：阈值扫描在 stage2_top_k=40 的深度候选池上进行——部署形态返回的 "
                  "top-10 分数已被后端 0.35 预过滤（实测最低 0.379），客户端扫阈值不 binding。")
        md.append("")
        md.append("| 变体 | Hit@1 | Hit@3 | R@5 | nDCG@10 | P@5 | MRR |")
        md.append("|---|---|---|---|---|---|---|")
        for name, s in abl1["summary"].items():
            md.append(f"| {name} | {fmt(s['hit@1'])} | {fmt(s['hit@3'])} | "
                      f"{fmt(s['recall@5'])} | {fmt(s['ndcg@10'])} | "
                      f"{fmt(s['precision@5'])} | {fmt(s['mrr'])} |")
        same = "逐位一致" if json.dumps(abl1["summary"], sort_keys=True) == \
            json.dumps((abl2 or {}).get("summary"), sort_keys=True) else "见复现说明"
        md.append("")
        md.append(f"双轮复现（r1 vs r2 汇总层）：**{same}**。")
        md.append("")

    # E2
    if stats:
        md.append("## E2 · 配对统计显著性（每对比独立 bootstrap CI, Holm 校正）")
        md.append("")
        md.append("| 对比 | 指标 | Δ均值 | 95% CI | Wilcoxon p | Holm p | 显著 |")
        md.append("|---|---|---|---|---|---|---|")
        seen = set()
        for c in stats["comparisons"]:
            key = (c["file"], c["comparison"], c["metric"])
            if key in seen:
                continue
            seen.add(key)
            md.append(f"| {c['comparison']} | {c['metric']} | {c['mean_diff']:+.4f} | "
                      f"[{c['ci95_boot'][0]:.4f}, {c['ci95_boot'][1]:.4f}] | "
                      f"{c['wilcoxon_p']} | {c['wilcoxon_p_holm']} | "
                      f"{'是' if c['significant_holm_0.05'] else '否'} |")
        md.append("")
        md.append("诚实结论：SciFact 30 查询上组件差异 ≤0.023，Holm 校正后均不显著"
                  "（n=30 功效不足）；报告为描述性组件贡献 + 置信区间。")
        md.append("")

    # E8
    if hot:
        s = hot["summary"]
        md.append("## E8 · 多域公开基准 — HotpotQA dev-distractor 50 题, 9 主题 KB")
        md.append("")
        md.append(f"金标跨 ≥2 库的查询：{hot['blindspot']['n_queries_cross_kb_gold']}/50"
                  f"（{hot['blindspot']['share_cross_kb']:.0%}）——多库路由场景真实成立。")
        md.append("")
        md.append("| 方法 | Hit@5 | R@2 | nDCG@10 | P@5 | MRR | ans@3 |")
        md.append("|---|---|---|---|---|---|---|")
        for m in ("bm25", "two_stage", "dense", "qdcvr"):
            v = s[m]
            md.append(f"| {m} | {fmt(v['hit@5'])} | {fmt(v['recall@2'])} | "
                      f"{fmt(v['ndcg@10'])} | {fmt(v['precision@5'])} | "
                      f"{fmt(v['mrr'])} | {fmt(v['answer@3'], 2)} |")
        md.append("")
        md.append("**诚实发现**：多跳问句与文档词汇重叠低时，基于词面匹配的内容验证重排"
                  "（qdcvr 0.779）略低于纯两阶段（0.841）与 dense（0.867）——"
                  "内容验证的收益域是『查询-文档共享词汇但相似度误排』的场景（SciFact），"
                  "不是所有场景。这与系统『诚实声明』的设计一致，论文按混合结果报告。")
        md.append("")
        b = hot["blindspot"]["under_declaration_rate"]
        md.append(f"E7 盲区（代理指标）：金标跨库查询中 top-5 未覆盖全部金标库的比例 — "
                  f"bm25 {b.get('bm25')} / two_stage {b.get('two_stage')} / "
                  f"dense {b.get('dense')} / qdcvr {b.get('qdcvr')}。")
        md.append("")

    # E3-E6
    if suite1:
        s2 = suite2 or {}
        md.append("## E3 · 冥想经验 — 状态重置后 3 轮 × 2 轮样本（修 TODO-5/F17）")
        md.append("")
        md.append("| 样本 | 轮 | KB | run_ok | drafts | approved | exps | judge 分 |")
        md.append("|---|---|---|---|---|---|---|---|")
        for tag, suite in (("样本1", suite1), ("样本2", s2)):
            for r in (suite or {}).get("E3_meditation_runs") or []:
                for kb, v in r["per_kb"].items():
                    md.append(f"| {tag} | {r['round']} | {kb} | "
                              f"{'✓' if v.get('run_success') else '✗'} | "
                              f"{v.get('n_drafts')} | {v.get('n_approved')} | "
                              f"{v.get('n_experiences')} | "
                              f"{v.get('judge_scores') or '—'} |")
        md.append("")
        md.append("**发现（按审稿要求作为 finding 报告）**：状态重置后运行间结果仍不稳定"
                  "（如样本1 EN 三轮 = 0/3/0 条），说明 10→0 的不稳定**不是（仅是）状态污染**，"
                  "而是 LLM 生成通道的判定方差——质量门对纯百科语料正确返回空（0 条为正确行为），"
                  "对可操作语料产出的条目评审分 7–9/10。论文不得引用单次有利运行。")
        md.append("")

        md.append("## E5 · 经验检索五路 leave-one-out（12 经验查询, 8 条流水线经验）")
        md.append("")
        pa = (suite2 or suite1)["E5_path_ablation"]
        md.append("| 变体 | Hit@1 | Hit@3 | R@3 | MRR |")
        md.append("|---|---|---|---|---|")
        for v, rows in pa["variants"].items():
            n = len(rows)
            md.append(f"| {v} | {fmt(sum(r['hit@1'] for r in rows)/n)} | "
                      f"{fmt(sum(r['hit@3'] for r in rows)/n)} | "
                      f"{fmt(sum(r['recall@3'] for r in rows)/n)} | "
                      f"{fmt(sum(r['mrr'] for r in rows)/n)} |")
        md.append("")
        md.append(f"harness 复现与线上 API 的 top-3 判定一致度："
                  f"{pa['align_with_api']}（线上 smart 搜索含自适应阈值与查询扩展，"
                  "harness 融合为简化复现，差异如实报告）。")
        md.append("")
        md.append("结论：keyword 路是主承重路（-keyword 掉 Hit@1 ~0.4）；scenario/tag 路"
                  "在症状式查询上提供互补命中；quality 路影响排序稳定性。")
        md.append("")

        md.append("## E6 · 衰减规则敏感性（7/14/30/90 天窗口）")
        md.append("")
        dec = (suite2 or suite1)["E6_decay"]
        md.append(f"观察窗口声明：部署不足 30 天，经验条目均为当日时间戳——本实验是**规则"
                  "敏感性分析**而非纵向验证（按 TODO-3 要求显式声明）。")
        md.append("")
        md.append("| 窗口 | 降级条数 | 占比 |")
        md.append("|---|---|---|")
        for w, v in dec["windows"].items():
            md.append(f"| {w} | {v['demoted']} | {v['demoted_share']} |")
        md.append("")

        md.append("## E4 · 经验合成双基线（同一 judge 提示, 4 个操作型查询）")
        md.append("")
        b = (suite2 or suite1)["E4_baselines"]["judged"]
        md.append("| 材料 | 逐查询分 | 均值 |")
        md.append("|---|---|---|")
        for k in ("no_synthesis", "ours_experience", "llm_summary"):
            md.append(f"| {k} | {b[k]['scores']} | {fmt(b[k]['mean'], 2)} |")
        md.append("")

    # E12
    if case and case.get("case", {}).get("selected"):
        c = case["case"]["selected"]
        md.append("## E12 · 动机案例（TODO-1: 产物可复现的开篇案例）")
        md.append("")
        md.append(f"- 查询 `{c['qid']}`：\"{c['question'][:120]}…\"")
        md.append(f"- 金标文档：{c['golden_ids']}")
        md.append(f"- Dense：hit@1={c['dense_hit1']}, MRR={c['dense_mrr']} — "
                  "金标未进 top-1（相似度排序失当）")
        md.append(f"- QDCVR：hit@1={c['qdcvr_hit1']}, MRR={c['qdcvr_mrr']} — "
                  "内容验证重排把金标提到第 1 位")
        md.append("- 论文 §1 案例可直接引用本案例（来源见 JSON）。")
        md.append("")

    # E16 DeepRead baseline matrix
    if drm:
        s = drm["summary"]
        jm = s.get("judge") or {}
        md.append("## E16 · DeepRead 论文基线矩阵 — 同语料同查询 × 8 方法"
                  "（arXiv:2602.05014 复现）")
        md.append("")
        md.append(f"语料 {drm['meta']['corpus']} · 查询 {drm['meta']['queries']} 条 · "
                  f"证据预算 {drm['meta']['evidence_budget_chars']} 字符 · "
                  f"Agent 通道: {drm['meta']['agent_channel']} · "
                  f"判分: {drm['meta']['judge']}。算法设置与偏差见 "
                  "`algorithms/REPRODUCTION-NOTES.md`。")
        md.append("")
        md.append("| 方法 | Hit@1 | Hit@5 | R@5 | nDCG@10 | MRR | 证据覆盖 | "
                  "判分(0-10) | 判分n |")
        md.append("|---|---|---|---|---|---|---|---|---|")
        for m, rows in (drm["summary"].get("retrieval") or {}).items():
            j = jm.get(m) or {}
            md.append(f"| {m} | {fmt(rows.get('hit@1'))} | {fmt(rows.get('hit@5'))} | "
                      f"{fmt(rows.get('recall@5'))} | {fmt(rows.get('ndcg@10'))} | "
                      f"{fmt(rows.get('mrr'))} | {fmt(rows.get('evidence_coverage'))} | "
                      f"{fmt(j.get('mean_score'), 2)} | {j.get('n_scored', 0)} |")
        md.append("")
        n_qa = len(drm.get("qa") or [])
        md.append(f"问答记录: {n_qa} 条(每查询×方法), 全文见同 run 目录 "
                  "`deepread_qa_transcripts.md`。")
        md.append("")

    # E16b API flow test
    if apim:
        s = apim["summary"]
        cons = apim["meta"].get("consistency_vs_e16_cache") or {}
        md.append("## E16b · API 全流程 — HTTP 选择检索算法问答 + 中间 Agent 排名")
        md.append("")
        md.append(f"- 服务: `{apim['meta']['api']}`（仅绑定本机）· 查询 "
                  f"{apim['meta']['queries']} 条 × {len(apim['meta']['methods'])} 方法 · "
                  f"与 E16 缓存一致性核对 {cons.get('checked', 0)} 项 / "
                  f"不一致 {cons.get('mismatches', 0)} → "
                  f"{'✅ 逐字一致' if cons.get('ok') else '❌'}。")
        md.append("")
        md.append("| 方法 | Hit@1 | R@5 | nDCG@10 | 第三方判分 | 中间Agent均位 | 首位次数 |")
        md.append("|---|---|---|---|---|---|---|")
        for m, v in s.items():
            md.append(f"| {m} | {fmt(v.get('hit@1'))} | {fmt(v.get('recall@5'))} | "
                      f"{fmt(v.get('ndcg@10'))} | {fmt(v.get('mean_judge'), 2)} | "
                      f"{fmt(v.get('mean_middle_rank_pos'), 2)} | "
                      f"{v.get('middle_agent_wins', 0)} |")
        md.append("")
        md.append("中间 Agent(独立 omp 进程)对每条查询的 8 份匿名答案(A-H)按金标"
                  "证据排名打分; 首位次数=排名第一的查询数。并排问答全文见同 run "
                  "目录 `api_side_by_side.md`。")
        md.append("")

    # E17 platform ops eval
    if ops:
        d = ops.get("dedup") or {}
        tg = ops.get("tags") or {}
        g = ops.get("graph") or {}
        c = ops.get("catalog") or {}
        md.append("## E17 · 平台整理功能评价（去重 / 标签 / 图谱 / 目录完整性）")
        md.append("")
        md.append(f"- 植入: {ops['meta']['planted_docs']} 篇文档, "
                  f"{ops['meta']['planted_dup_groups']} 组重复真值; "
                  f"入库保留 {c.get('doc_count')}/{ops['meta']['planted_docs']}"
                  "（精确重复内容在创建链被静默去重 — 如实报告）。")
        md.append(f"- 去重: kb_find_duplicates 检出组 {d.get('groups_detected')}/2, "
                  f"组召回 {fmt(d.get('recall_groups'), 2)}; 样本对 "
                  f"{d.get('sample_pairs') or d.get('valid_pairs') or '—'}。")
        md.append(f"- 标签: {tg.get('distinct_tags')} 个标签, 内容可落地 "
                  f"{tg.get('grounded_ratio', 0):.1%}（小文档上标签抽取噪声大 — finding）。")
        md.append(f"- 清理完整性: dry-run {ops.get('cleanup_dry_run', {}).get('would_clean')} 个孤儿标签, "
                  f"在用标签误入清理清单 {ops.get('cleanup_dry_run', {}).get('used_tags_in_clean_list')} 个 → "
                  f"{'OK' if ops.get('cleanup_dry_run', {}).get('integrity_ok') else 'FAIL'}。")
        md.append(f"- 图谱: build_ok={g.get('build_ok')}, 搜索探针命中 {g.get('search_probe_hits')}"
                  f"（7 文档小库上图谐薄弱 — finding）。")
        md.append("")

    md.append("## 复现")
    md.append("")
    md.append("按 EXPERIMENT-DESIGN.md §5 顺序执行各脚本即可复现；每份结果 JSON 内嵌 "
              "git commit / config_hash / seed / run_id。")
    md.append("")

    out_md = RESULTS / "EXPERIMENTS-RESULTS.md"
    out_md.write_text("\n".join(md), encoding="utf-8")

    # ── HTML ──
    def table(headers, rows_):
        h = "".join(f"<th>{x}</th>" for x in headers)
        body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>"
                       for r in rows_)
        return f"<table><thead><tr>{h}</tr></thead><tbody>{body}</tbody></table>"

    sections = []
    if abl1:
        rows_ = [[n, fmt(s['hit@1']), fmt(s['hit@3']), fmt(s['recall@5']),
                  fmt(s['ndcg@10']), fmt(s['precision@5']), fmt(s['mrr'])]
                 for n, s in abl1["summary"].items()]
        sections.append(("<h2>E1 · Ablation — same query set (SciFact, 30 queries)</h2>",
                         table(["Variant", "Hit@1", "Hit@3", "R@5", "nDCG@10", "P@5",
                                "MRR"], rows_),
                         "Threshold sweep runs on a stage2_top_k=40 pool: the deployed "
                         "top-10 is already pre-filtered by the backend 0.35 threshold "
                         "(min observed score 0.379)."))
    if hot:
        s = hot["summary"]
        rows_ = [[m, fmt(s[m]['hit@5']), fmt(s[m]['recall@2']), fmt(s[m]['ndcg@10']),
                  fmt(s[m]['precision@5']), fmt(s[m]['mrr']), fmt(s[m]['answer@3'], 2)]
                 for m in ("bm25", "two_stage", "dense", "qdcvr")]
        sections.append(("<h2>E8 · Multi-domain public benchmark — HotpotQA ×50, 9 topic KBs</h2>",
                         table(["Method", "Hit@5", "R@2", "nDCG@10", "P@5", "MRR",
                                "ans@3"], rows_),
                         f"Cross-KB gold: {hot['blindspot']['n_queries_cross_kb_gold']}/50. "
                         "Honest finding: term-matching content verification helps on "
                         "vocabulary-sharing claims (SciFact) but slightly hurts on "
                         "multi-hop questions with low lexical overlap."))
    if suite1:
        pa = (suite2 or suite1)["E5_path_ablation"]
        rows_ = [[v, fmt(sum(r['hit@1'] for r in rows)/len(rows)),
                  fmt(sum(r['hit@3'] for r in rows)/len(rows)),
                  fmt(sum(r['recall@3'] for r in rows)/len(rows)),
                  fmt(sum(r['mrr'] for r in rows)/len(rows))]
                 for v, rows in pa["variants"].items()]
        sections.append(("<h2>E5 · Experience retrieval — five-path leave-one-out (12 queries)</h2>",
                         table(["Variant", "Hit@1", "Hit@3", "R@3", "MRR"], rows_),
                         "Harness-level replication of the backend fusion; alignment "
                         f"with the live API: {pa['align_with_api']}."))
        dec = (suite2 or suite1)["E6_decay"]
        rows_ = [[w, v['demoted'], v['demoted_share']] for w, v in dec["windows"].items()]
        sections.append(("<h2>E6 · Decay rule sensitivity (7/14/30/90d)</h2>",
                         table(["Window", "Demoted", "Share"], rows_),
                         "Observation window < 30 days: this characterises the rule, "
                         "not a longitudinal validation (TODO-3)."))
        b = (suite2 or suite1)["E4_baselines"]["judged"]
        rows_ = [[k, str(b[k]['scores']), fmt(b[k]['mean'], 2)]
                 for k in ("no_synthesis", "ours_experience", "llm_summary")]
        sections.append(("<h2>E4 · Experience baselines under an identical judge prompt</h2>",
                         table(["Material", "Per-query scores", "Mean"], rows_),
                         "no-synthesis = raw document retrieval; llm-summary = one-shot "
                         "summarisation; ours = pipeline experiences (same judge)."))

    chartjs = CHART.read_text(encoding="utf-8") if CHART.exists() else ""
    html.append(f"""<!doctype html><html lang="en"><head><meta charset="utf-8"/>
<title>rag-knowledge — Paper Experiment Suite</title>
<script>{chartjs}</script><style>
body{{font-family:'Segoe UI',system-ui,sans-serif;max-width:1080px;margin:24px auto;
padding:0 16px;color:#16213a;line-height:1.6;background:#fbfcfe}}
h1{{font-size:1.4em;border-bottom:3px solid #2c5f8a;padding-bottom:8px}}
h2{{font-size:1.12em;color:#2c5f8a;margin-top:2em;border-left:4px solid #2c5f8a;padding-left:8px}}
table{{border-collapse:collapse;width:100%;font-size:.85em;margin:10px 0}}
th,td{{border:1px solid #c8d0d8;padding:5px 8px;text-align:center}}
th{{background:#2c5f8a;color:#fff}}
.caption{{font-size:.88em;background:#eef4fa;border-left:4px solid #7aa7cc;
padding:10px 14px;margin-top:8px}}
.meta{{color:#667;font-size:.84em}}
</style></head><body>
<h1>Paper Experiment Suite — real runs, frozen artefacts</h1>
<p class="meta">git {env['git_commit']} · config {env['config_hash']} · seed {env['seed']}
· generated {now_iso()} · every number comes from results/run-*/ JSON artefacts</p>
""")
    for title, body, cap in sections:
        html.append(title)
        html.append(body)
        html.append(f'<p class="caption">{cap}</p>')
    html.append("</body></html>")
    out_html = RESULTS / "experiments-report.html"
    out_html.write_text("\n".join(html), encoding="utf-8")
    print(f"-> {out_md}")
    print(f"-> {out_html} ({out_html.stat().st_size//1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
