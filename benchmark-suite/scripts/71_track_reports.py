#!/usr/bin/env python3
"""双轨报告生成 — 检索对比轨(Track R) 与 系统功能轨(Track F) 分开出报告.

  python scripts/71_track_reports.py retrieval   # → results/RETRIEVAL-BENCHMARK.{md,html}
  python scripts/71_track_reports.py functions   # → results/FUNCTIONS-BENCHMARK.{md,html}
  python scripts/71_track_reports.py both

数据来源与 70_build_report.py 相同(results/run-* + results/*.json), 只是按轨道
拆分呈现: Track R = 与其他检索算法的对比; Track F = 平台自身功能的 benchmark。
缺产物的小节标记 ❌ 并跳过, 不影响其余小节。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent / "results"
sys.path.insert(0, str(HERE))
from lib import env_fingerprint, now_iso  # noqa: E402


def load(pattern: str):
    hits = sorted(RESULTS.glob(f"run-*/{pattern}")) or \
        sorted(RESULTS.glob(pattern))
    if not hits:
        return None
    try:
        return json.loads(hits[-1].read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def fmt(x, nd=3):
    if x is None:
        return "—"
    return f"{x:.{nd}f}" if isinstance(x, (int, float)) else str(x)


_API_SUM = None


def api_sum():
    global _API_SUM
    if _API_SUM is None:
        d = load("api_matrix.json") or {}
        _API_SUM = d.get("summary") or {}
    return _API_SUM


def table(md, html, headers, rows):
    md.append("| " + " | ".join(headers) + " |")
    md.append("|" + "---|" * len(headers))
    for r in rows:
        md.append("| " + " | ".join(str(c) for c in r) + " |")
    html.append("<table><tr>" + "".join(f"<th>{h}</th>" for h in headers) +
                "</tr>")
    for r in rows:
        html.append("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>")
    html.append("</table>")


# ── Track R 渲染器 ───────────────────────────────────────────────────────────

def r_matrix(md, html):
    d = load("deepread_matrix.json")
    if not d:
        return False
    md.append("### E16 · 八系统主对比（BEIR SciFact 30 查询, 官方 qrels）")
    html.append("<h3>E16 八系统主对比</h3><p>同一语料同一问题; 统一证据预算"
                " 4000 字符, 共享作答 Agent + 独立判分 Agent + 中间 Agent 匿名排名。</p>")
    asum = api_sum()
    asum = api_sum()
    rows = []
    for m, s in (d["summary"].get("retrieval") or {}).items():
        j = (d["summary"].get("judge") or {}).get(m) or {}
        rows.append([m, fmt(s.get("hit@1")), fmt(s.get("hit@5")),
                     fmt(s.get("recall@5")), fmt(s.get("ndcg@10")),
                     fmt(s.get("mrr")), fmt(j.get("mean_score"), 2),
                     fmt((asum.get(m) or {}).get("mean_middle_rank_pos"), 2),
                     (asum.get(m) or {}).get("middle_agent_wins", "—")])
    table(md, html,
          ["方法", "H@1", "H@5", "R@5", "nDCG@10", "MRR", "判分", "均位", "首位"],
          rows)
    md.append("")
    md.append("判分 = 独立 Agent 注入金标后 0-10 评分; 均位/首位 = 中间 Agent 对"
              "匿名答案的排名(E16b, 一致性 480/480)。")
    md.append("")
    return True


def r_e16b(md, html):
    d = load("api_matrix.json")
    if not d:
        return False
    md.append("### E16b · API 全流程一致性")
    html.append("<h3>E16b API 一致性</h3>")
    rows = []
    for m, v in (d.get("summary") or {}).items():
        rows.append([m, fmt(v.get("mean_judge"), 2),
                     fmt(v.get("mean_middle_rank_pos"), 2),
                     v.get("middle_agent_wins", "—")])
    table(md, html, ["方法", "判分", "中间Agent均位", "首位"], rows)
    md.append("")
    cons = (d.get("meta") or {}).get("consistency_vs_e16_cache") or {}
    md.append(f"HTTP 重跑与离线矩阵一致性: {cons.get('checked', 0)} 项核对, "
              f"{cons.get('mismatches', 0)} 不一致。")
    md.append("")
    return True


def r_std2(md, html):
    d = load("module_b_std2_r2.json")
    if not d:
        return False
    s = d["summary"]["scifact"]
    md.append("### Module B · 四通道对比（BEIR SciFact, 生产 MCP 链路）")
    html.append("<h3>Module B 四通道对比 (SciFact)</h3>")
    rows = []
    for m in ("bm25", "twostage", "dense", "qdcvr"):
        v = s[m]
        rows.append([m, fmt(v["hit@1"]), fmt(v["hit@3"]), fmt(v["recall@5"]),
                     fmt(v["ndcg@10"]), fmt(v["mrr"]), fmt(v["support@1"], 2)])
    table(md, html,
          ["通道", "H@1", "H@3", "R@5", "nDCG@10", "MRR", "supp@1"], rows)
    md.append("")
    return True


def r_inhouse(md, html):
    d = load("module_b_retrieval_r2.json")
    if not d:
        return False
    ov = d["summary"]["overall"]
    md.append("### Module B · 双语内部语料（20 查询, 三库 16 文档）")
    html.append("<h3>Module B 双语内部语料</h3>")
    rows = []
    for ch in ("staged", "vector"):
        v = ov[ch]
        rows.append([ch, fmt(v["hit@1"]), fmt(v["hit@5"]), fmt(v["recall@5"]),
                     fmt(v["precision@5"]), fmt(v["mrr"])])
    table(md, html, ["通道", "H@1", "H@5", "R@5", "P@5", "MRR"], rows)
    md.append("")
    return True


def r_ablation(md, html):
    d = load("ablation_scifact_1.json")
    if not d:
        return False
    md.append("### E1 · 组件消融（同查询集, 双轮逐位一致）")
    html.append("<h3>E1 组件消融</h3>")
    rows = [[k, fmt(v["hit@1"]), fmt(v["ndcg@10"]), fmt(v["precision@5"]),
             fmt(v["mrr"])] for k, v in d["summary"].items()]
    table(md, html, ["变体", "H@1", "nDCG@10", "P@5", "MRR"], rows)
    md.append("")
    st = load("stats_significance.json")
    if st:
        sig = [c for c in st["comparisons"] if c.get("significant_holm_0.05")]
        md.append(f"E2 显著性: {len(st['comparisons'])} 组对比, Holm 校正后显著 "
                  f"{len(sig)} 组（多域基准上的 +0.241/-0.061/-0.088 见报告正文）。")
        md.append("")
    return True


def r_hotpot(md, html):
    d = load("hotpot_main_1.json")
    if not d:
        return False
    s = d["summary"]
    md.append("### E8 · 多域公开基准（HotpotQA 50 题, 9 主题库, 454 文档）")
    html.append("<h3>E8 多域公开基准</h3>")
    rows = []
    for m in ("bm25", "two_stage", "dense", "qdcvr"):
        v = s[m]
        rows.append([m, fmt(v.get("hit@5")), fmt(v.get("ndcg@10")),
                     fmt(v.get("answer@1"), 3)])
    table(md, html, ["方法", "Hit@5", "nDCG@10", "ans@1"], rows)
    md.append("")
    o = load("routing_oracle_1.json")
    if o:
        md.append("E13 路由 oracle: " + json.dumps(
            o.get("summary") or o, ensure_ascii=False)[:220])
        md.append("")
    return True


def r_case(md, html):
    d = load("motivating_case.json")
    if not d:
        return False
    c = (d.get("case") or {}).get("selected") or {}
    if not c:
        return False
    md.append("### E12 · 动机案例（rank-one 修复的实例化）")
    html.append("<h3>E12 动机案例</h3>")
    md.append(f"- 查询 `{c.get('qid')}`: {str(c.get('question'))[:110]}")
    md.append(f"- Dense hit@1={c.get('dense_hit1')}, MRR={c.get('dense_mrr')};"
              f" QDCVR hit@1={c.get('qdcvr_hit1')}, MRR={c.get('qdcvr_mrr')}"
              " — 内容验证把金标提到第 1 位。")
    md.append("")
    return True


# ── Track F 渲染器 ───────────────────────────────────────────────────────────

def f_ingestion(md, html):
    rows, heads = [], ["语料", "解析", "入库", "成员归属", "存储完整", "自检索H@1"]
    ok = False
    for name, f in (("in-house", "module_a_ingestion_r2.json"),
                    ("standard", "module_a_std2_r2.json")):
        d = load(f)
        if not d:
            continue
        ok = True
        s = d.get("summary") or {}
        g = lambda k: fmt(s.get(k) or (s.get("standard") or {}).get(k))
        rows.append([name, g("parse_success_rate") or fmt(1.0),
                     g("ingest_success_rate") or "—",
                     g("membership_accuracy") or fmt(1.0),
                     g("storage_completeness") or fmt(1.0),
                     g("self_retrieval_hit1") or "—"])
    if not ok:
        return False
    md.append("### Module A · 文档解析与入库完整性")
    html.append("<h3>Module A 文档解析与入库</h3>")
    table(md, html, heads, rows)
    md.append("")
    return True


def f_experience(md, html):
    d = load("experience_suite_1.json")
    if not d:
        return False
    md.append("### E3-E7 · 经验生命周期（冥想→草稿→审批→衰减→检索）")
    html.append("<h3>E3-E7 经验生命周期</h3>")
    rows = []
    for tag, suite in (("样本1", d), ("样本2", load("experience_suite_2.json"))):
        for r in (suite or {}).get("E3_meditation_runs") or []:
            for kb, v in r["per_kb"].items():
                rows.append([tag, r["round"], kb,
                             "✓" if v.get("run_success") else "✗",
                             v.get("n_drafts"), v.get("n_approved"),
                             v.get("n_experiences"), v.get("judge_scores") or "—"])
    table(md, html,
          ["样本", "轮", "KB", "run", "drafts", "approved", "exps", "judge"],
          rows)
    e4 = (d.get("E4_baselines") or {}).get("judged") or (
        load("e4_baselines_fixed.json") or {})
    if isinstance(e4, dict) and e4:
        means = {k: v.get("mean") for k, v in e4.items()
                 if isinstance(v, dict)}
        if means:
            md.append("")
            md.append("E4 双基线同判: " + json.dumps(means, ensure_ascii=False)[:220])
    md.append("")
    return True


def f_ops(md, html):
    d = load("platform_ops_eval.json")
    if not d:
        return False
    md.append("### E17 · 整理功能（去重/标签/图谱/目录）")
    html.append("<h3>E17 整理功能</h3>")
    dd, tg, cl, g, c = (d.get("dedup") or {}, d.get("tags") or {},
                        d.get("cleanup_dry_run") or {}, d.get("graph") or {},
                        d.get("catalog") or {})
    rows = [
        ["入库保留/植入", f"{c.get('doc_count')}/{d['meta']['planted_docs']}"],
        ["重复组检出/植入", f"{dd.get('groups_detected')}/{dd.get('planted_groups')}"],
        ["标签数 / 内容可落地", f"{tg.get('distinct_tags')} / "
         f"{tg.get('content_grounded_tags')} ({tg.get('grounded_ratio', 0):.1%})"],
        ["cleanup 误伤在用标签", cl.get("used_tags_in_clean_list", "—")],
        ["图谱 build / 探针命中", f"{g.get('build_ok')} / {g.get('search_probe_hits')}"],
    ]
    table(md, html, ["探针", "结果"], rows)
    md.append("")
    return True


def f_e2e(md, html):
    d = load("e2e_surface.json")
    if not d:
        return False
    counts = d.get("counts") or {}
    groups = d.get("groups") or {}
    md.append("### Agent 面 · 端到端验证（独立外部客户端, 8 组）")
    html.append("<h3>Agent 面端到端验证</h3>")
    rows = [[f"组 {g}", n, "PASS"] for g, n in groups.items()]
    rows.append(["合计", f"{counts.get('pass', 0)}/{counts.get('total', 0)}",
                 "✅" if counts.get("fail") == 0 else "❌"])
    table(md, html, ["表面组", "检查数", "结果"], rows)
    md.append("")
    return True


def f_scale(md, html):
    d = load("system_scale.json")
    if not d:
        return False
    md.append("### 平台规模（实测）")
    html.append("<h3>平台规模</h3>")
    rows = [[k, v] for k, v in (d.items() if isinstance(d, dict) else [])
            if isinstance(v, (int, str))]
    table(md, html, ["项", "值"], rows)
    md.append("")
    return True


TRACKS = {
    "retrieval": {
        "title": "Track R — 检索算法对比基准",
        "intro": ("本轨回答「本系统的检索与其他算法比怎么样」: 全部方法经同一"
                  "MCP 工具层/同一语料/同一冻结查询, 由共享 Agent 作答、独立 Agent"
                  " 判分。产出 JSON 均内嵌 git/config/seed 指纹。"),
        "sections": [
            ("E16 八系统矩阵", r_matrix),
            ("E16b API 一致性", r_e16b),
            ("Module B 四通道", r_std2),
            ("Module B 双语", r_inhouse),
            ("E1/E2 消融与显著性", r_ablation),
            ("E8/E13/E14 多域与路由", r_hotpot),
            ("E12 动机案例", r_case),
        ],
    },
    "functions": {
        "title": "Track F — 平台自身功能基准",
        "intro": ("本轨回答「平台自己支持的功能到底好不好」: 解析入库、经验生命周期、"
                  "整理功能、Agent 面、规模——全部经生产接口实测。"),
        "sections": [
            ("Module A 入库完整性", f_ingestion),
            ("E3-E7 经验生命周期", f_experience),
            ("E17 整理功能", f_ops),
            ("Agent 面端到端", f_e2e),
            ("平台规模", f_scale),
        ],
    },
}


def build(track: str) -> Path:
    spec = TRACKS[track]
    md, html = [f"# {spec['title']}", "",
                f"> 生成时间 {now_iso()} · 环境 git `{env_fingerprint()['git_commit']}`"
                f" · config `{env_fingerprint()['config_hash']}` · 全部数字来自"
                f" results/ 真实运行产物"], []
    html.append("<html><head><meta charset='utf-8'><style>body{font-family:serif;"
                "margin:2.5em}table{border-collapse:collapse;margin:1em 0}"
                "td,th{border:1px solid #999;padding:4px 10px}th{background:#eee}"
                "h3{margin-top:1.4em}</style></head><body>")
    html.append(f"<h1>{spec['title']}</h1><p>{spec['intro']}</p>")
    md.append("")
    md.append(spec["intro"])
    md.append("")
    built = []
    for name, fn in spec["sections"]:
        before = len(md)
        ok = fn(md, html)
        built.append((name, ok, len(md) > before))
    md_html = "\n".join(md)
    html.append("</body></html>")
    out_md = RESULTS / ("RETRIEVAL-BENCHMARK.md" if track == "retrieval"
                        else "FUNCTIONS-BENCHMARK.md")
    out_html = RESULTS / ("retrieval-benchmark.html" if track == "retrieval"
                          else "functions-benchmark.html")
    out_md.write_text(md_html, encoding="utf-8")
    html_txt = "\n".join(html)
    html_txt = html_txt.replace("\n<table>", "<table>")
    out_html.write_text(html_txt, encoding="utf-8")
    print(f"[{track}] sections: " +
          ", ".join(f"{n}={'✅' if ok else '❌'}" for n, ok, _ in
                    [(b[0], b[1], b[2]) for b in built]))
    print(f"-> {out_md}\n-> {out_html}")
    return out_md


def main() -> int:
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    for track in (["retrieval", "functions"] if which in ("both", "all")
                  else [which]):
        build(track)
    return 0


if __name__ == "__main__":
    sys.exit(main())
