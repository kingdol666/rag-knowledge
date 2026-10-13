#!/usr/bin/env python3
r"""Render the final paper-grade benchmark evidence into ONE self-contained HTML report.

Input  : results/paper_report.json  (contract v1, written by 161_final_evidence.py)
Output : results/paper-report-<run_id>/report.html   (default)
         plus a copy at results/PAPER-REPORT.html for convenient opening

Design rules (why this file exists):
  * 离线单文件 —— 无 CDN / 无 JS 依赖 / 无字体下载；断网双击即可打开，图全部是内联 SVG。
  * 数字全部来自 paper_report.json，脚本只做渲染，不计算、不补零、不美化。
    「论文可写入性」由 161 的自检（verification.checks）保证，本脚本把自检也画进报告。
  * 每题都展示判分依据（gold id 命中位置、关键词命中列表、引用标记）与可折叠的原始答案，
    评审可以顺着证据链复核到原始输出。

用法
    python scripts/162_paper_report_html.py                      # 读 results/paper_report.json
    python scripts/162_paper_report_html.py --in results/paper_report.json --out results/PAPER-REPORT.html
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

SUITE = Path(__file__).resolve().parent.parent
RESULTS = SUITE / "results"

# 论文对账 claim 名 → main.tex 宏名（供刷新工单直接给出可粘贴的 \newcommand）
MACRO_OF = {
    "groundedA2": "NUMgroundedA", "groundedB": "NUMgroundedB", "groundedC": "NUMgroundedC",
    "kwA2": "NUMkwA", "kwB": "NUMkwB", "kwC": "NUMkwC",
    "citedA2": "NUMciteA", "citedB": "NUMciteB", "citedC": "NUMciteC",
    "latA2": "NUMlatA", "latB": "NUMlatB", "latC": "NUMlatC",
    "costA2": "NUMcostA", "costB": "NUMcostB", "costC": "NUMcostC",
}


def newcommand(macro: str, val: str) -> str:
    v = str(val).strip()
    if macro.startswith("NUMlat"):
        v = re.sub(r"s$", "", v).strip() + "\\,s"
    elif macro.startswith("NUMcost") and not v.startswith("$"):
        v = "\\$" + v.lstrip("$")
    return f"\\newcommand{{\\{macro}}}{{{v}}}"

TRACK_LABEL = {"a2": "A · 平台全工具面", "b": "B · 裸 Agent 文件工具",
               "c": "C · 稠密检索单工具"}
TRACK_NOTE = {
    "a2": "kb_* 全套读接口（两层检索 + Laya 证据门 + 全文读取）",
    "b": "同一模型 + 导出论文上的 Read/Grep 文件工具",
    "c": "仅一个向量检索工具，检索 100 篇论文的 800 字分块副本",
}
TASK_LABEL = {"attention": "可回答（注意力公式）",
              "seismology": "语料未覆盖（地震波分类）",
              "pickles": "语料外（四川泡菜）"}
LANE_LABEL = {"A": "A 快车道", "B": "B 馆员车道", "C": "C 融合车道"}


def _e(x) -> str:
    return html.escape(str(x if x is not None else "—"))


def _num(x, nd: int = 1, dash: str = "—") -> str:
    try:
        return f"{float(x):.{nd}f}"
    except (TypeError, ValueError):
        return dash


def _pct(x) -> str:
    try:
        return f"{100 * float(x):.0f}%"
    except (TypeError, ValueError):
        return "—"


def _mark(v) -> str:
    if v is True:
        return '<span class="ok">✓</span>'
    if v is False:
        return '<span class="no">✗</span>'
    return '<span class="muted">–</span>'


def _bar(rate, color: str, width: int = 132) -> str:
    if rate is None:
        return '<span class="muted">—</span>'
    pct = max(0.0, min(1.0, float(rate))) * 100
    return (f'<span class="bar" style="--w:{width}px">'
            f'<i style="width:{pct:.1f}%;background:{color}"></i>'
            f'<em>{pct:.0f}%</em></span>')


def _svg_grouped(tracks: list[str], series: dict[str, dict], colors: dict[str, str],
                 maxv: float, unit: str, fmt: str = "{:.0f}") -> str:
    """Grouped horizontal bar chart (pure SVG)."""
    lab_w, right = 96, 46
    rowh, gap = 22, 8
    w = 470
    plot_w = w - lab_w - right
    rows = len(tracks)
    h = rows * (len(series) * rowh + gap) + 8
    out = [f'<svg class="chart" viewBox="0 0 {w} {h}" width="100%" role="img">']
    y = 4
    for tk in tracks:
        for name, vals in series.items():
            v = vals.get(tk)
            bw = 0.0 if v is None else max(1.0, plot_w * (float(v) / maxv))
            out.append(f'<text x="0" y="{y + 15}" class="cl">{_e(TRACK_LABEL.get(tk, tk))}</text>')
            out.append(
                f'<rect x="{lab_w}" y="{y + 4}" width="{bw:.1f}" height="{rowh - 6}" '
                f'rx="2" fill="{colors.get(name, "#0F6E56")}"></rect>')
            txt = "—" if v is None else fmt.format(float(v)) + unit
            out.append(f'<text x="{lab_w + bw + 6:.1f}" y="{y + 15}" class="cv">{_e(txt)}'
                       f'<tspan class="cn"> {_e(name)}</tspan></text>')
            y += rowh
        y += gap
    out.append("</svg>")
    return "".join(out)


def _svg_per_question(questions: list[dict], order: list[str], colors: dict) -> str:
    """Per-question stacked bar (latency length, fill = pass/keyword/fail)."""
    if not questions:
        return '<p class="muted">无逐题数据</p>'
    qids = [q["qid"] for q in questions]
    lats = {q["qid"]: float(q.get("latency_s") or 0) for q in questions}
    maxlat = max(lats.values()) or 1.0
    rowh, gap = 26, 8
    lab_w, right = 58, 150
    w, h = 620, len(qids) * (rowh + gap) + 6
    plot_w = w - lab_w - right
    out = [f'<svg class="chart" viewBox="0 0 {w} {h}" width="100%" role="img">']
    y = 3
    for q in questions:
        qid = q["qid"]
        bw = max(2.0, plot_w * (lats[qid] / maxlat))
        state = q.get("state")
        fill = colors.get(state, "#888780")
        out.append(f'<text x="0" y="{y + 17}" class="cl">{_e(qid)}</text>')
        out.append(f'<rect x="{lab_w}" y="{y + 4}" width="{bw:.1f}" height="{rowh - 8}" '
                   f'rx="3" fill="{fill}" opacity="0.92"></rect>')
        badge = {"pass": "✓ 通过", "kw": "△ 仅关键词缺", "fail": "✗ 未通过",
                 "sentinel": "⚠ 工具面中断", "error": "✗ 执行错误"}.get(state, "—")
        out.append(f'<text x="{lab_w + bw + 8:.1f}" y="{y + 17}" class="cv">'
                   f'{_num(lats[qid])}s <tspan class="cn">{_e(badge)}</tspan></text>')
        y += rowh + gap
    out.append("</svg>")
    return "".join(out)


def _svg_stability(rows: list[dict]) -> str:
    if not rows:
        return '<p class="muted">未运行稳定性套件</p>'
    tasks = list(dict.fromkeys(r["task"] for r in rows))
    lanes = list(dict.fromkeys(r["lane"] for r in rows))
    cell = {(r["task"], r["lane"]): r for r in rows}
    maxlat = max((float(r.get("wall_s") or 0) for r in rows), default=1.0) or 1.0
    out = ['<table class="tbl stab"><thead><tr><th>任务</th>'
           + "".join(f"<th>{_e(LANE_LABEL.get(l, l))}</th>" for l in lanes)
           + "</tr></thead><tbody>"]
    for t in tasks:
        out.append(f'<tr><td>{_e(TASK_LABEL.get(t, t))}</td>')
        for l in lanes:
            r = cell.get((t, l))
            if not r:
                out.append('<td class="muted">—</td>')
                continue
            ok = r.get("ok")
            cls = "ok" if ok else ("no" if ok is False else "muted")
            pct = 100 * float(r.get("wall_s") or 0) / maxlat
            out.append(f'<td><span class="cellok {cls}">{_mark(ok)}</span> '
                       f'{_num(r.get("wall_s"))}s'
                       f'<span class="spark"><i style="width:{pct:.0f}%"></i></span>'
                       f'<span class="cn"> {_e(str(r.get("verdict") or "")[:34])}</span></td>')
        out.append("</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def _question_card(q: dict, tracks: list[str]) -> str:
    by = {c["track"]: c for c in q.get("cells", [])}
    cells = []
    for tk in tracks:
        c = by.get(tk)
        if not c:
            cells.append(f'<td class="muted">—</td>')
            continue
        cells.append(
            f'<td>'
            f'<div class="cbadges">{_mark(c.get("grounded"))} 金标 '
            f'{_mark(c.get("kw_ok"))} 关键词({c.get("kw_hits")}/{c.get("kw_total")}) '
            f'{_mark(c.get("cited"))} 引用</div>'
            f'<div class="cmeta">{_num(c.get("latency_s"))}s · {_e(c.get("tools"))} 工具 · '
            f'${_num(c.get("cost_usd"), 3)}</div>'
            f'</td>')
    ans = []
    for tk in tracks:
        c = by.get(tk)
        if not c:
            continue
        body = c.get("answer") or ""
        ans.append(
            f'<details class="ans"><summary>{_e(TRACK_LABEL.get(tk, tk))} · '
            f'{len(body)} 字 · {_e(c.get("tools"))} 工具 · {_num(c.get("latency_s"))}s</summary>'
            f'<div class="evid">引用标记：{_e("、".join(c.get("cite_markers") or []) or "无")}'
            f'　关键词命中：{_e("、".join(c.get("kw_list") or []) or "无")}'
            f'　金标位置：{_e(c.get("gold_where") or "未命中")}</div>'
            f'<pre class="raw">{_e(body)}</pre></details>')
    return (f'<section class="qcard" id="q-{_e(q["qid"])}">'
            f'<h3><span class="qid">{_e(q["qid"])}</span> {_e(q.get("question"))}</h3>'
            f'<div class="qmeta">金标论文 <code>{_e(q.get("gold"))}</code> · '
            f'关键词 {_e(q.get("kw_total"))} 个 · 最高相似度 '
            f'{_num(q.get("top_sim"), 2)}</div>'
            f'<table class="tbl q"><tbody><tr>{"".join(cells)}</tr></tbody></table>'
            f'{"".join(ans)}</section>')


def render(p: dict) -> str:
    meta = p.get("meta") or {}
    corpus = p.get("corpus") or {}
    tracks = p.get("tracks") or []
    grades = p.get("grades") or {}
    pq = p.get("per_question") or {}
    ver = p.get("verification") or {}
    stab = p.get("stability") or {}
    base = p.get("baselines") or {}

    total_cost = sum(float((grades.get(t) or {}).get("cost_usd_total") or 0) for t in tracks)
    total_cells = sum(int((grades.get(t) or {}).get("n") or 0) for t in tracks)
    checks = ver.get("checks") or []
    n_bad = sum(1 for c in checks if not c.get("ok"))
    a2 = grades.get("a2") or {}
    n_aborts = sum(int((grades.get(t) or {}).get("sentinel") or 0) for t in tracks)

    kpis = [
        ("三轨总分", f"{sum(int((grades.get(t) or {}).get('pass') or 0) for t in tracks)}"
                     f"/{total_cells}", "grounded ∧ 关键词"),
        ("平台闸门支撑", f"{a2.get('grounded', '—')}/10 · {a2.get('kw_ok', '—')}/10",
         "金标命中 · 关键词 ≥60%"),
        ("引用可复核", f"{a2.get('cited', '—')}/10", "部分/章节/表格标记"),
        ("工具面中断", n_aborts, "0 = 无降级单元"),
        ("稳定性", f"{stab.get('ok_cells', '—')}/{stab.get('cells', '—')}",
         "三车道 × 三轮"),
        ("证据自检", f"{len(checks) - n_bad}/{len(checks)}",
         "全部通过" if n_bad == 0 else f"{n_bad} 项未通过"),
    ]
    kpi_html = "".join(
        f'<div class="kpi"><div class="kpi-v">{_e(v)}</div>'
        f'<div class="kpi-k">{_e(k)}</div><div class="kpi-s">{_e(s)}</div></div>'
        for k, v, s in kpis)

    # ── 轨道主表 ────────────────────────────────────────────────────────────
    trows = []
    colors = {"a2": "#0F6E56", "b": "#4C6EF5", "c": "#C2410C"}
    for t in tracks:
        g = grades.get(t) or {}
        trows.append(
            f'<tr><td><span class="pill p-{_e(t)}">{_e(TRACK_LABEL.get(t, t))}</span>'
            f'<div class="cn">{_e(TRACK_NOTE.get(t, ""))}</div></td>'
            f'<td class="n">{_e(g.get("grounded"))}/{_e(g.get("n"))}</td>'
            f'<td class="n">{_e(g.get("kw_ok"))}/{_e(g.get("n"))}</td>'
            f'<td class="n">{_e(g.get("cited"))}/{_e(g.get("n"))}</td>'
            f'<td class="n">{_e(g.get("pass"))}/{_e(g.get("n"))}</td>'
            f'<td class="n">{_num(g.get("latency_avg_s"))}</td>'
            f'<td class="n">${_num(g.get("cost_usd_total"), 3)}</td>'
            f'<td class="n">{_num(g.get("tools_avg"))}</td>'
            f'<td class="n">{_e(g.get("sentinel", 0))}</td></tr>')

    qlist = [pq[k] for k in sorted(pq)]
    qcards = "".join(_question_card(q, tracks) for q in qlist)

    # ── baseline 对照（可选） ───────────────────────────────────────────────
    if base:
        brows = []
        for m, a in sorted(base.items()):
            brows.append(
                f'<tr><td><code>{_e(m)}</code></td>'
                f'<td class="n">{_e(a.get("grounded"))}/{_e(a.get("n"))}</td>'
                f'<td class="n">{_e(a.get("kw_ok"))}/{_e(a.get("n"))}</td>'
                f'<td class="n">{_e(a.get("abstain"))}</td>'
                f'<td class="n">{_num(a.get("latency_avg_s"), 2)}</td></tr>')
        base_block = (
            '<h2 id="baselines">基线与项目臂对照</h2>'
            '<p class="lead">同题集、同判分器。检索基线（BM25 / 稠密向量 / RRF）只做检索，'
            '不生成答案，因此 grounded 一栏按「是否检索到金标文档」计。</p>'
            '<table class="tbl"><thead><tr><th>方法</th><th>金标检索</th><th>关键词</th>'
            '<th>拒答</th><th>时延 s</th></tr></thead><tbody>'
            + "".join(brows) + "</tbody></table>")
    else:
        base_block = ""

    # ── 自检 + 论文宏工单 ────────────────────────────────────────────────────
    crows = "".join(
        f'<tr class="{"crow-info" if c.get("informational") else ("crow-ok" if c.get("ok") else "crow-no")}">'
        f'<td>{"·" if c.get("informational") else _mark(c.get("ok"))}</td>'
        f'<td><code>{_e(c.get("name"))}</code></td>'
        f'<td>{_e(c.get("detail"))}</td></tr>' for c in checks)
    drift = [c for c in checks if c.get("informational")]
    if drift:
        rows = []
        for c in drift:
            m = re.match(r"论文宏待刷新 · (\S+)\s*(.*)", str(c.get("name")))
            claim = m.group(1) if m else str(c.get("name"))
            det = str(c.get("detail") or "")
            d2 = re.match(r"论文现值\s*(\S+)\s*→\s*本轮实测\s*(\S+)", det)
            macro = MACRO_OF.get(claim)
            rows.append(
                f'<tr><td><code>{_e(claim)}</code></td>'
                f'<td>{_e(macro or "—")}</td>'
                f'<td class="n">{_e(d2.group(1) if d2 else "—")}</td>'
                f'<td class="n">{_e(d2.group(2) if d2 else "—")}</td>'
                f'<td><code>{_e(newcommand(macro, d2.group(2)) if (macro and d2) else "")}</code></td>'
                f'</tr>')
        macro_block = (
            '<h2 id="macros">论文宏刷新工单</h2>'
            '<p class="lead">下面每一行都是「论文 <code>main.tex</code> 里的旧值 → 本轮实测值」。'
            '把第五列的 <code>\\newcommand</code> 覆盖掉对应行，论文实验节即与本报告一致；'
            '判定口径（grounded / 关键词 ≥60% / 引用标记）与论文正文完全相同。</p>'
            '<table class="tbl"><thead><tr><th>指标</th><th>宏</th><th class="n">论文现值</th>'
            '<th class="n">本轮实测</th><th>建议替换为</th></tr></thead><tbody>'
            + "".join(rows) + "</tbody></table>")
    else:
        macro_block = ""

    lat_chart = _svg_grouped(
        tracks,
        {"时延 s": {t: (grades.get(t) or {}).get("latency_avg_s") for t in tracks}},
        {"时延 s": "#0F6E56"}, max([(grades.get(t) or {}).get("latency_avg_s") or 0
                                    for t in tracks] + [1]) * 1.18, " s")
    cost_chart = _svg_grouped(
        tracks,
        {"成本 $": {t: (grades.get(t) or {}).get("cost_usd_total") for t in tracks}},
        {"成本 $": "#C2410C"}, max([(grades.get(t) or {}).get("cost_usd_total") or 0
                                    for t in tracks] + [0.01]) * 1.25, " USD",
        fmt="{:.3f}")
    pass_chart = _svg_grouped(
        tracks,
        {"总通过": {t: (grades.get(t) or {}).get("pass") for t in tracks},
         "关键词通过": {t: (grades.get(t) or {}).get("kw_ok") for t in tracks},
         "金标命中": {t: (grades.get(t) or {}).get("grounded") for t in tracks}},
        {"总通过": "#0F6E56", "关键词通过": "#4C6EF5", "金标命中": "#94A3B8"},
        max([(grades.get(t) or {}).get("n") or 10 for t in tracks]) * 1.25, " /10")
    pq_chart = _svg_per_question(
        qlist, tracks, {"pass": "#0F6E56", "kw": "#D97706", "fail": "#DC2626",
                        "sentinel": "#DC2626", "error": "#7C2D12"})

    state_legend = ("<div class='legend'>"
                    "<span><i style='background:#0F6E56'></i>通过</span>"
                    "<span><i style='background:#D97706'></i>关键词未达 60%</span>"
                    "<span><i style='background:#DC2626'></i>未通过 / 工具面中断</span>"
                    "</div>")

    corpus_rows = "".join(
        f'<tr><td>{_e(k)}</td><td class="n">{_e(v)}</td></tr>'
        for k, v in (corpus.get("detail") or {}).items())
    nav = ("<nav><a href='#verdict'>结论</a><a href='#tracks'>三轨主表</a>"
           "<a href='#questions'>逐题证据</a>"
           + ("<a href='#baselines'>基线对照</a>" if base else "")
           + "<a href='#stability'>稳定性</a><a href='#corpus'>语料与流水线</a>"
           "<a href='#verify'>证据自检</a>"
           + ("<a href='#macros'>论文宏工单</a>" if drift else "")
           + "<a href='#repro'>复现</a></nav>")

    verdict_bits = []
    if a2:
        verdict_bits.append(
            f'平台轨在 10 道固定题上金标命中 <b>{_e(a2.get("grounded"))}/10</b>、'
            f'关键词达标 <b>{_e(a2.get("kw_ok"))}/10</b>、'
            f'引用标记 <b>{_e(a2.get("cited"))}/10</b>，'
            f'平均 {_num(a2.get("latency_avg_s"))}s / ${_num(a2.get("cost_usd_total"), 3)}。')
    b_ = grades.get("b") or {}
    c_ = grades.get("c") or {}
    if b_ and c_:
        verdict_bits.append(
            f'同模型同题的裸 Agent 轨 {_e(b_.get("grounded"))}/10 金标、'
            f'{_e(b_.get("kw_ok"))}/10 关键词，单工具稠密轨 '
            f'{_e(c_.get("grounded"))}/10、{_e(c_.get("kw_ok"))}/10——'
            f'三轨共用同一判分器，差异只来自检索可及性。')
    if stab.get("cells"):
        verdict_bits.append(
            f'稳定性套件 {_e(stab.get("ok_cells"))}/{_e(stab.get("cells"))} 单元行为正确'
            f'（{_e(stab.get("rounds"))} 轮 × {_e(stab.get("lanes"))} 车道 × '
            f'{_e(stab.get("tasks"))} 任务），中位时延 '
            f'{_num(stab.get("latency_median_s"))}s。')
    if n_aborts == 0:
        verdict_bits.append('本轮 <b>0 个工具面中断单元</b>：没有任何一题因 MCP 工具缺席而降级作答。')

    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>QDCVR 检索评测报告 · {_e(meta.get('run_id'))}</title>
<style>
:root{{--bg:#F7F6F2;--card:#FFFFFF;--ink:#1B1B18;--mut:#6B6B63;--line:#E3E1D9;
--accent:#0F6E56;--accent2:#4C6EF5;--warn:#D97706;--bad:#DC2626;
--mono:ui-monospace,SFMono-Regular,"JetBrains Mono",Consolas,monospace}}
html[data-theme=dark]{{--bg:#14140F;--card:#1D1D18;--ink:#EDEBE3;--mut:#9C9A8E;
--line:#33322A;--accent:#2FA37F;--accent2:#829BFF;--warn:#E0A32E;--bad:#F26B5E}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.6 -apple-system,"Segoe UI","Noto Sans SC",system-ui,sans-serif}}
.wrap{{max-width:1180px;margin:0 auto;padding:34px 26px 90px}}
header.top{{display:flex;flex-wrap:wrap;gap:14px;align-items:flex-end;
justify-content:space-between;border-bottom:2px solid var(--ink);padding-bottom:16px}}
h1{{font-size:27px;margin:0;letter-spacing:-.3px}}
.sub{{color:var(--mut);font-size:13.5px;margin-top:6px}}
.chips{{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}}
.chip{{border:1px solid var(--line);background:var(--card);border-radius:999px;
padding:3px 10px;font-size:12px;font-family:var(--mono);color:var(--mut)}}
button.theme{{border:1px solid var(--line);background:var(--card);color:var(--ink);
border-radius:8px;padding:7px 12px;cursor:pointer;font-size:13px}}
nav{{position:sticky;top:0;z-index:5;background:color-mix(in srgb,var(--bg) 88%,transparent);
backdrop-filter:blur(8px);border-bottom:1px solid var(--line);margin:0 -26px 22px;
padding:9px 26px;display:flex;gap:14px;flex-wrap:wrap}}
nav a{{color:var(--mut);text-decoration:none;font-size:13.5px}}
nav a:hover{{color:var(--accent)}}
h2{{font-size:19px;margin:38px 0 10px;scroll-margin-top:60px}}
h3{{font-size:15.5px;margin:0 0 6px}}
p.lead{{color:var(--mut);margin:6px 0 14px;max-width:80ch}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(168px,1fr));gap:12px;margin:20px 0 6px}}
.kpi{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:13px 15px}}
.kpi-v{{font-size:23px;font-weight:650;letter-spacing:-.5px;font-variant-numeric:tabular-nums}}
.kpi-k{{font-size:13px;margin-top:3px}}
.kpi-s{{font-size:11.5px;color:var(--mut);margin-top:2px}}
.verdict{{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--accent);
border-radius:10px;padding:16px 19px;margin-top:16px}}
.verdict li{{margin:6px 0}}
table.tbl{{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);
border-radius:10px;overflow:hidden;font-size:13.5px}}
table.tbl th{{text-align:left;background:color-mix(in srgb,var(--line) 45%,var(--card));
padding:9px 11px;font-weight:600;font-size:12.5px;color:var(--mut);white-space:nowrap}}
table.tbl td{{padding:9px 11px;border-top:1px solid var(--line);vertical-align:top}}
td.n,th.n{{text-align:right;font-variant-numeric:tabular-nums;font-family:var(--mono);font-size:12.8px}}
.pill{{display:inline-block;border-radius:6px;padding:2px 8px;font-size:12px;font-weight:600;
color:#fff;background:var(--accent)}}
.p-b{{background:var(--accent2)}}.p-c{{background:#C2410C}}
.cn{{color:var(--mut);font-size:11.5px}}
.ok{{color:var(--accent);font-weight:700}}.no{{color:var(--bad);font-weight:700}}
.muted{{color:var(--mut)}}
.bar{{position:relative;display:inline-block;width:var(--w);height:16px;
background:color-mix(in srgb,var(--line) 60%,var(--card));border-radius:4px;overflow:hidden;
vertical-align:middle}}
.bar i{{position:absolute;left:0;top:0;bottom:0}}
.bar em{{position:relative;font-style:normal;font-size:11.5px;line-height:16px;padding-left:6px;
font-family:var(--mono)}}
.chart{{margin:8px 0 2px}}
.cl{{font-size:11.5px;fill:var(--mut);font-family:var(--mono)}}
.cv{{font-size:12px;fill:var(--ink);font-family:var(--mono)}}
.cn-t{{font-size:11px;fill:var(--mut)}}
.charts{{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:16px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}}
.card h4{{margin:0 0 4px;font-size:13.5px;color:var(--mut);font-weight:600}}
.qcard{{background:var(--card);border:1px solid var(--line);border-radius:12px;
padding:15px 18px;margin:12px 0}}
.qcard h3 code{{font-size:12px}}
.qid{{font-family:var(--mono);font-size:12.5px;background:color-mix(in srgb,var(--line) 60%,var(--card));
border-radius:6px;padding:2px 7px;margin-right:7px}}
.qmeta{{color:var(--mut);font-size:12.5px;margin-bottom:9px}}
table.q td{{border-top:none;border-left:1px solid var(--line);width:33%}}
table.q td:first-child{{border-left:none}}
.cbadges{{font-size:12.5px}}.cmeta{{color:var(--mut);font-size:12px;font-family:var(--mono)}}
details.ans{{margin-top:9px;border:1px solid var(--line);border-radius:9px;
background:color-mix(in srgb,var(--bg) 55%,var(--card))}}
details.ans summary{{cursor:pointer;padding:8px 12px;font-size:12.5px;color:var(--mut)}}
.evid{{padding:0 12px 6px;font-size:12px;color:var(--mut);font-family:var(--mono);
border-bottom:1px dashed var(--line)}}
pre.raw{{margin:0;padding:11px 13px;white-space:pre-wrap;word-break:break-word;
font-family:var(--mono);font-size:12.2px;line-height:1.55;max-height:460px;overflow:auto}}
table.stab td{{font-family:var(--mono);font-size:12.3px}}
.cellok{{margin-right:4px}}
.spark{{display:inline-block;width:54px;height:5px;border-radius:3px;margin-left:6px;
background:color-mix(in srgb,var(--line) 70%,var(--card));vertical-align:middle;overflow:hidden}}
.spark i{{display:block;height:100%;background:var(--accent2)}}
.legend{{display:flex;gap:14px;flex-wrap:wrap;color:var(--mut);font-size:12px;margin-top:4px}}
.legend i{{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:5px}}
.crow-ok td:first-child{{color:var(--accent)}}.crow-no{{background:#DC262618}}
.crow-info td{{color:var(--mut)}}
.crow-info code{{background:transparent}}
code{{font-family:var(--mono);font-size:12.3px;
background:color-mix(in srgb,var(--line) 45%,var(--card));padding:1px 5px;border-radius:5px}}
footer{{margin-top:44px;color:var(--mut);font-size:12.5px;border-top:1px solid var(--line);
padding-top:14px}}
</style></head><body><div class="wrap">
<header class="top"><div>
<h1>QDCVR · 检索与证据链评测报告</h1>
<div class="sub">三轨固定题集 · 同一 harness／模型／中性提示词 · 判分器可复算</div>
<div class="chips">
<span class="chip">run {_e(meta.get('run_id'))}</span>
<span class="chip">commit {_e(meta.get('git_commit'))}</span>
<span class="chip">prompt {_e(meta.get('prompt_version'))}</span>
<span class="chip">config {_e(meta.get('config_hash'))}</span>
<span class="chip">生成 {_e(meta.get('generated_utc'))}</span>
</div></div><button class="theme" onclick="var h=document.documentElement;
h.dataset.theme=h.dataset.theme==='dark'?'':'dark'">◐ 明/暗</button></header>
{nav}
<div class="kpis">{kpi_html}</div>
<h2 id="verdict">结论</h2>
<div class="verdict"><ul>{''.join(f'<li>{b}</li>' for b in verdict_bits)}</ul>
<p class="lead" style="margin-bottom:0">判分口径（与论文一致）：<b>grounded</b>＝答案或工具轨迹中出现该题指定论文的 arXiv 号；
<b>keyword-verified</b>＝固定金标关键事实命中 ≥60%（词边界匹配）；<b>cited</b>＝答案中出现部分／章节／表格等可复核定位标记。
本轮所有数字均由脚本从保存的原始单元复算，逐题依据见下。</p></div>
<h2 id="tracks">三轨主表</h2>
<p class="lead">三轨共用同一模型与中性提示词，唯一差别是检索可及性与权限。{_e(total_cells)} 个计分单元，
总成本 ${_num(total_cost, 2)}。</p>
<table class="tbl"><thead><tr><th>轨道</th><th class="n">金标命中</th><th class="n">关键词达标</th>
<th class="n">引用标记</th><th class="n">总通过</th><th class="n">平均时延 s</th>
<th class="n">总成本 $</th><th class="n">平均工具数</th><th class="n">工具面中断</th>
</tr></thead><tbody>{''.join(trows)}</tbody></table>
<div class="charts" style="margin-top:16px">
<div class="card"><h4>平均时延（秒 / 题）</h4>{lat_chart}</div>
<div class="card"><h4>该轨总成本（USD / 10 题）</h4>{cost_chart}</div>
<div class="card"><h4>通过数对比（题数）</h4>{pass_chart}</div>
<div class="card"><h4>逐题时延与判分状态（平台轨 A）</h4>{pq_chart}{state_legend}</div>
</div>
<h2 id="questions">逐题证据</h2>
<p class="lead">每题给出三轨的判分明细、金标命中位置、引用标记与可折叠的完整原始答案——
评审可沿「问题 → 判分 → 原文」链路复核。</p>
{qcards}
{base_block}
<h2 id="stability">稳定性套件</h2>
<p class="lead">{_e(stab.get('description') or '三任务 × 三车道 × 多轮，验证检索一致性、诚实拒答与车道契约。')}</p>
{_svg_stability(stab.get('rows') or [])}
<h2 id="corpus">语料与流水线证据</h2>
<p class="lead">实验所依赖的语料与索引状态（同一轮采集，避免「数出自不同版本」）。</p>
<table class="tbl"><tbody>{corpus_rows}</tbody></table>
<h2 id="verify">证据自检</h2>
<p class="lead">这些断言决定「能不能写进论文」：任何一项失败都意味着对应数字不可引用。</p>
<table class="tbl"><thead><tr><th style="width:34px"></th><th style="width:220px">断言</th>
<th>实测</th></tr></thead><tbody>{crows}</tbody></table>
{macro_block}
<h2 id="repro">复现方式</h2>
<div class="card"><pre class="raw">{_e(meta.get('repro') or '')}</pre></div>
<footer>本报告由 <code>scripts/162_paper_report_html.py</code> 从
<code>results/paper_report.json</code> 渲染；数据由 <code>scripts/161_final_evidence.py</code>
采集与自检。所有原始单元保存在 <code>results/runs/{_e(meta.get('run_id'))}/</code>。</footer>
</div></body></html>"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", default=str(RESULTS / "paper_report.json"))
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    src = Path(args.src)
    if not src.exists():
        print(f"[fail] 找不到输入：{src}（先跑 scripts/161_final_evidence.py）")
        return 1
    payload = json.loads(src.read_text(encoding="utf-8"))
    out = Path(args.out) if args.out else (
        RESULTS / f"paper-report-{payload.get('meta', {}).get('run_id', 'run')}" / "report.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(payload), encoding="utf-8")
    (RESULTS / "PAPER-REPORT.html").write_text(out.read_text(encoding="utf-8"),
                                               encoding="utf-8")
    print(f"[done] {out}")
    print(f"[done] {RESULTS / 'PAPER-REPORT.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
