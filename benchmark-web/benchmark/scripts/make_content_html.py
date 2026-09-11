#!/usr/bin/env python3
"""生成内容级基准（内容问答检索 + 入库归类）的自包含审稿 HTML 报告.

读取: results/contentqa/*.r1.json + *.r2.json, results/routing/routing.r{1,2}.json
输出: results/CONTENTQA-REPORT.html (图片以 base64 PNG 内嵌, 双击即看)
缺失的赛道以占位说明呈现, 不阻断生成.
"""
from __future__ import annotations

import base64
import io
import json
from datetime import datetime
from pathlib import Path

RESULTS = Path(__file__).resolve().parent.parent / "results"
CQA = RESULTS / "contentqa"
OUT = RESULTS / "CONTENTQA-REPORT.html"

DATASETS = ["contentqa", "hotpotqa", "triviaqa", "nq"]
METHODS = ["two_stage", "vector_flat"]
METHOD_LABEL = {
    "two_stage": "Two-Stage (生产主检索)",
    "vector_flat": "Flat Vector (稠密锚点)",
}
DATASET_LABEL = {
    "contentqa": "CorpusClozeQA (自建, 答案保证在库)",
    "hotpotqa": "HotpotQA (冻结子集, 真实问题)",
    "triviaqa": "TriviaQA (冻结子集, 真实问题)",
    "nq": "Natural Questions (冻结子集, 真实问题)",
}
METRIC_KEYS = [
    ("answer_recall@1", "AR@1"), ("answer_recall@3", "AR@3"),
    ("answer_recall@5", "AR@5"), ("answer_recall@10", "AR@10"),
    ("answer_mrr", "MRR"), ("evidence_hit@5", "EvHit@5"),
    ("kb_route@1", "KBRoute@1"), ("latency_mean_s", "延迟(s)"),
]


def load(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def repro_badge(r1: dict | None, r2: dict | None) -> str:
    if not r1 or not r2:
        return '<span class="badge pending">单轮/待跑</span>'
    a, b = r1["summary"], r2["summary"]
    ignore = {"round", "latency_mean_s", "latency_p95_s"}
    diffs = [k for k in a if k not in ignore and a.get(k) != b.get(k)]
    if diffs:
        return f'<span class="badge fail">复现失败: {", ".join(diffs)}</span>'
    return '<span class="badge pass">双轮逐位可复现 ✓</span>'


def fmt(v, n=3) -> str:
    if v is None:
        return "—"
    return f"{v:.{n}f}" if isinstance(v, float) else str(v)


def track_c_table() -> str:
    rows = ""
    any_row = False
    for ds in DATASETS:
        r1 = load(CQA / f"{ds}.two_stage.r1.json")
        r2 = load(CQA / f"{ds}.two_stage.r2.json")
        for m in METHODS:
            data = load(CQA / f"{ds}.{m}.r1.json")
            if not data:
                continue
            any_row = True
            s = data["summary"]
            bold = ' style="font-weight:700;background:#eaf2f8"' if m == "two_stage" else ""
            cells = "".join(
                f'<td>{fmt(s.get(k)) if not k.startswith("latency") else fmt(s.get(k), 2)}</td>'
                for k, _ in METRIC_KEYS)
            first = (f'<td rowspan="{2 if m == "two_stage" else 1}">{DATASET_LABEL[ds]}</td>'
                     if m == "two_stage" else "")
            badge_cell = (f'<td rowspan="2">{repro_badge(r1, r2)}</td>'
                          if m == "two_stage" else "<td></td>")
            rows += (f"<tr{bold}>{first}<td>{METHOD_LABEL[m]}</td>{cells}"
                     f"<td>{s.get('n_scorable','—')}/{s.get('n','—')}</td>{badge_cell}</tr>")
        if not any(r.get("summary", {}).get("dataset") == ds
                   for r in (r1,) if r):
            pass
    if not any_row:
        return "<p class='placeholder'>Track C 结果待正式运行后生成。</p>"
    head = "".join(f"<th>{label}</th>" for _, label in METRIC_KEYS)
    return (f"<table><thead><tr><th>数据集</th><th>方法</th>{head}"
            f"<th>可评分/总数</th><th>复现</th></tr></thead><tbody>{rows}</tbody></table>")


def track_r_section() -> str:
    rep = load(RESULTS / "routing" / "routing.r1.json")
    rep2 = load(RESULTS / "routing" / "routing.r2.json")
    if not rep:
        return "<p class='placeholder'>Track R 结果待正式运行后生成。</p>"
    s = rep["summary"]
    badge = repro_badge(rep, rep2)
    ing = rep.get("ingest", {})
    html = [f"""<table class="kv"><tbody>
<tr><th>收件库写入</th><td>计划 {ing.get('planned','—')} / 新建 {ing.get('created','—')} / 已存在 {ing.get('skipped_existing','—')} / 失败 {ing.get('failed','—')}</td></tr>
<tr><th>入库保真 round-trip Hit@1</th><td><b>{fmt(s.get('roundtrip_hit@1'))}</b></td></tr>
<tr><th>入库保真 round-trip Hit@5</th><td><b>{fmt(s.get('roundtrip_hit@5'))}</b></td></tr>
<tr><th>归类 Acc@1 — 跨库检索投票</th><td><b>{fmt(s.get('routing_vote_acc@1'))}</b></td></tr>
<tr><th>归类 Acc@1 — top-3 多数投票</th><td><b>{fmt(s.get('routing_vote_acc@top3'))}</b></td></tr>
<tr><th>归类 Acc@1 — 逐库向量扫描</th><td><b>{fmt(s.get('routing_scan_acc@1'))}</b></td></tr>
<tr><th>双轮复现</th><td>{badge}</td></tr>
</tbody></table>"""]

    per = rep.get("per_domain") or {}
    if per:
        rows = "".join(
            f"<tr><td>{dom}</td><td>{v.get('n')}</td>"
            f"<td>{fmt(v.get('vote_acc1'))}</td><td>{v.get('scan_top_pred','')}</td></tr>"
            for dom, v in sorted(per.items()))
        html.append(f"<table><thead><tr><th>域库</th><th>n</th>"
                    f"<th>vote Acc@1</th><th>scan 最常误判入</th></tr></thead>"
                    f"<tbody>{rows}</tbody></table>")

    conf = rep.get("confusion_vote") or {}
    if conf:
        domains = sorted(conf.keys())
        head = "".join(f"<th>{d.replace('KB-','')}</th>" for d in domains)
        rows = ""
        for gold in domains:
            cells = ""
            for pred in domains:
                cnt = conf[gold].get(pred, 0)
                style = ' style="background:#d5e8d4;font-weight:700"' if gold == pred and cnt else (
                    ' style="background:#f8cecc"' if cnt else "")
                cells += f"<td{style}>{cnt or ''}</td>"
            rows += f"<tr><th>{gold.replace('KB-','')}</th>{cells}</tr>"
        html.append(f"<p>混淆矩阵（行=金标域, 列=预测域, 跨库检索投票）:</p>"
                    f"<table class='conf'><thead><tr><th></th>{head}</tr></thead>"
                    f"<tbody>{rows}</tbody></table>")
    return "".join(html)


def figure_track_c() -> str:
    """AnswerRecall@5 分组柱状图 (r1)."""
    data = {}
    for ds in DATASETS:
        for m in METHODS:
            d = load(CQA / f"{ds}.{m}.r1.json")
            if d and d["summary"].get("answer_recall@5") is not None:
                data[(ds, m)] = d["summary"]["answer_recall@5"]
    if not data:
        return ""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return ""
    ds_list = [ds for ds in DATASETS if any((ds, m) in data for m in METHODS)]
    import numpy as np
    x = np.arange(len(ds_list))
    width = 0.35
    fig, ax = plt.subplots(figsize=(7.2, 3.4), dpi=150)
    for i, m in enumerate(METHODS):
        vals = [data.get((ds, m), 0) for ds in ds_list]
        ax.bar(x + (i - 0.5) * width, vals, width, label=METHOD_LABEL[m])
    ax.set_xticks(x)
    ax.set_xticklabels([ds for ds in ds_list], fontsize=8)
    ax.set_ylabel("AnswerRecall@5")
    ax.set_ylim(0, 1.05)
    ax.set_title("Content-grounded QA: answer present in retrieved chunks")
    ax.legend(fontsize=8)
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png")
    plt.close(fig)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f'<img class="fig" src="data:image/png;base64,{b64}" alt="track-c-recall"/>'


def main() -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    html = f"""<!doctype html>
<html lang="zh"><head><meta charset="utf-8"/>
<title>内容级基准报告 · 内容问答检索 + 入库归类</title>
<style>
 body{{font-family:'Segoe UI',system-ui,sans-serif;max-width:1080px;margin:24px auto;padding:0 16px;color:#1a1a2e;line-height:1.55}}
 h1{{font-size:1.5em;border-bottom:3px solid #2c5f8a;padding-bottom:8px}}
 h2{{font-size:1.2em;color:#2c5f8a;margin-top:1.8em}}
 table{{border-collapse:collapse;width:100%;font-size:.86em;margin:12px 0}}
 th,td{{border:1px solid #c8d0d8;padding:6px 8px;text-align:center}}
 th{{background:#2c5f8a;color:#fff}}
 td:first-child,th:first-child{{text-align:left}}
 table.kv td:first-child{{font-weight:600;background:#f0f4f8;width:280px}}
 .badge{{padding:2px 10px;border-radius:10px;font-size:.8em;white-space:nowrap}}
 .badge.pass{{background:#d5e8d4;color:#1e6b34}}
 .badge.fail{{background:#f8cecc;color:#8a1f1f}}
 .badge.pending{{background:#fff2cc;color:#7a5c00}}
 .fig{{max-width:100%;margin:12px 0;border:1px solid #e0e0e0}}
 .placeholder{{background:#fffbe6;border:1px dashed #d0b000;padding:10px;color:#7a5c00}}
 .meta{{color:#667;font-size:.85em}}
 .conf th{{background:#5a7a9a}}
</style></head><body>
<h1>内容级基准报告 — 真实内容问答检索 + 入库归类能力</h1>
<p class="meta">生成时间 {now} · 协议: 检索命中 chunk 正文含金答案串(SQuAD 归一化) ·
与 Track1(文档级排序 P@5/MRR)互补, 直接度量"给定问题能否把含答案的内容检索回来"与
"入库文档能否凭内容归回正确的库"</p>

<h2>Track C · 内容问答检索 (content-grounded QA)</h2>
<p>指标: <b>AnswerRecall@k</b> — top-k 命中 chunk 正文中出现任一金答案串的问题占比;
<b>MRR</b> — 首个含答案 chunk 排名倒数均值; <b>EvHit@5</b> — 金文档进 top-5(仅含 golden_titles 的集);
<b>KBRoute@1</b> — top-1 命中所库==金库(仅自建集)。</p>
<p>方法: two_stage 为前端同款生产检索(服务端默认参数); vector_flat 为全库平面稠密检索锚点。</p>
{track_c_table()}
{figure_track_c()}

<h2>Track R · 入库归类 (ingest → organize)</h2>
<p>协议: 将冻结语料中已知域归属的 golden 页面副本写入未归类收件库 KB-Inbox-Organize,
再仅用生产检索 API 做两种归类决策(跨库检索投票 / 逐库向量扫描), 金标为语料划分协议的冻结域标签;
round-trip 用文档自身首句检索应取回原文档(入库保真下界)。</p>
{track_r_section()}

<h2>协议与复现凭证</h2>
<ul>
<li>答案命中判定: SQuAD 归一化(小写/去标点/去冠词/压空白)后子串匹配; 归一化后 &lt;3 字符的答案不可评分, 从分母剔除(计数见"可评分/总数")。</li>
<li>双轮复现: 同参数重跑, 全部指标逐位一致判 PASS(延迟为系统态观测值, 不参与比对)。</li>
<li>自建集构建: build_content_qa.py — 确定性抽取(仅 golden 页/剥离标题前缀/答案不在标题区), 金答案逐字存在于入库正文。</li>
<li>脚本: benchmark-web/benchmark/scripts/{{build_content_qa,run_content_qa,run_ingest_routing}}.py; 结果: results/{{contentqa,routing}}/。</li>
</ul>
</body></html>"""
    OUT.write_text(html, encoding="utf-8")
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
