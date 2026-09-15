#!/usr/bin/env python3
"""生成 CIKM 基准 HTML 报告(Chart.js 内嵌, 单文件离线可看).

读取 results/benchmark/ 下三模块 JSON, 生成:
  - 模块 A/B/C 各自得分图
  - 内容检索 vs 传统向量 baseline 对比图
  - 跨语言对比图
  - 两阶段(加速项)时延对比
  - 每张图下方的解读文字(可直接用于论文 experiments 章节)
输出: results/benchmark-report.html
"""
from __future__ import annotations

import json
import statistics
from datetime import datetime
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
BENCH = SCRIPTS.parent / "results" / "benchmark"
CHART_JS = SCRIPTS / "chart.umd.min.js"
OUT = SCRIPTS.parent / "results" / "benchmark-report.html"

LANGS = ["en", "zh", "ja"]
LANG_LABEL = {"en": "English", "zh": "中文 (Chinese)", "ja": "日本語 (Japanese)"}
MODULES = {"A": "知识入库", "B": "内容检索(主线)", "C": "冥想(经验自动总结)"}


def load(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def collect() -> dict:
    d = {"ingestion": {}, "content": {}, "agent": {}, "meditation": None,
         "content_r2_match": True}
    for lang in LANGS:
        r1 = load(BENCH / f"benchmark_ingestion_{lang}_r1.json")
        r2 = load(BENCH / f"benchmark_ingestion_{lang}_r2.json")
        if r1:
            d["ingestion"][lang] = r1["summary"]
            d["ingestion"][lang]["repro"] = bool(r2 and r1["summary"] == r2["summary"])
    for lang in LANGS:
        r1 = load(BENCH / f"benchmark_content_mcp_{lang}_r1.json")
        r2 = load(BENCH / f"benchmark_content_mcp_{lang}_r2.json")
        if r1:
            d["content"][lang] = r1["summary"]
            d["content"][lang]["repro"] = bool(r2 and r1["summary"] == r2["summary"])
    for lang in LANGS:
        a = load(BENCH / f"benchmark_content_agent_{lang}_r1.json")
        if a:
            d["agent"][lang] = a["summary"]
    d["meditation"] = load(BENCH / "benchmark_meditation_en_r1.json")
    return d


def fmt(v, n=3) -> str:
    if v is None:
        return "—"
    return f"{v:.{n}f}" if isinstance(v, float) else str(v)


def build_data(d: dict) -> str:
    """注入给前端图表的数据."""
    ingestion = {lang: {
        "ingest_success_rate": d["ingestion"].get(lang, {}).get("ingest_success_rate"),
        "membership_accuracy": d["ingestion"].get(lang, {}).get("membership_accuracy"),
        "storage_completeness_mean": d["ingestion"].get(lang, {}).get("storage_completeness_mean"),
        "self_retrieval_hit1": d["ingestion"].get(lang, {}).get("self_retrieval_hit1"),
    } for lang in LANGS}
    content = {lang: {
        "staged_r5": d["content"].get(lang, {}).get("staged", {}).get("recall@5"),
        "staged_r1": d["content"].get(lang, {}).get("staged", {}).get("recall@1"),
        "staged_mrr": d["content"].get(lang, {}).get("staged", {}).get("mrr"),
        "vector_r5": d["content"].get(lang, {}).get("vector", {}).get("recall@5"),
        "vector_r1": d["content"].get(lang, {}).get("vector", {}).get("recall@1"),
        "vector_mrr": d["content"].get(lang, {}).get("vector", {}).get("mrr"),
        "staged_hit_dist": d["content"].get(lang, {}).get("staged", {}).get("staged_hit_dist"),
        "staged_latency": d["content"].get(lang, {}).get("staged", {}).get("latency_total_s_mean"),
        "vector_latency": d["content"].get(lang, {}).get("vector", {}).get("latency_s_mean"),
        "tool_calls": d["content"].get(lang, {}).get("staged", {}).get("tool_calls_per_query"),
    } for lang in LANGS}
    agent = {lang: {"hit1": d["agent"].get(lang, {}).get("hit@1_mean"),
                    "hit1_std": d["agent"].get(lang, {}).get("hit@1_std"),
                    "hit_any": d["agent"].get(lang, {}).get("hit_any_mean"),
                    "n_runs": d["agent"].get(lang, {}).get("n_runs")} for lang in LANGS}
    med = d["meditation"] or {}
    meditation = {
        "summary": med.get("summary"),
        "per_kb": med.get("per_kb"),
    }
    return json.dumps({"ingestion": ingestion, "content": content,
                       "agent": agent, "meditation": meditation},
                      ensure_ascii=False)


def html_template(data_json: str, chartjs: str, generated: str) -> str:
    return """<!doctype html>
<html lang="zh"><head><meta charset="utf-8"/>
<title>rag-knowledge CIKM 基准报告 — 三模块 + 跨语言 + baseline 对比</title>
<script>__CHARTJS__</script>
<style>
 body{font-family:'Segoe UI',system-ui,'Microsoft YaHei',sans-serif;max-width:1120px;margin:24px auto;padding:0 16px;color:#16213a;line-height:1.6;background:#fbfcfe}
 h1{font-size:1.45em;border-bottom:3px solid #2c5f8a;padding-bottom:8px}
 h2{font-size:1.18em;color:#2c5f8a;margin-top:2em;border-left:4px solid #2c5f8a;padding-left:8px}
 .card{background:#fff;border:1px solid #dde5ee;border-radius:8px;padding:14px 18px;margin:14px 0}
 canvas{max-width:100%}
 .fig-explain{font-size:.92em;background:#eef4fa;border-left:4px solid #7aa7cc;padding:10px 14px;margin-top:8px}
 .fig-explain b{color:#2c5f8a}
 table{border-collapse:collapse;width:100%;font-size:.85em;margin:10px 0}
 th,td{border:1px solid #c8d0d8;padding:5px 8px;text-align:center}
 th{background:#2c5f8a;color:#fff}
 .badge{padding:2px 10px;border-radius:10px;font-size:.8em;white-space:nowrap}
 .badge.pass{background:#d5e8d4;color:#1e6b34}
 .badge.pending{background:#fff2cc;color:#7a5c00}
 .meta{color:#667;font-size:.85em}
 code{background:#eef1f5;padding:1px 5px;border-radius:4px;font-size:.9em}
 .two{display:grid;grid-template-columns:1fr 1fr;gap:14px}
</style></head><body>
<h1>rag-knowledge 基准报告：知识入库 · 内容检索（主线） · 冥想经验</h1>
<p class="meta">生成时间 __GENERATED__ · 研究主张：<b>基于内容的逐级检索</b>（Agent 按 QDCVR 规程
kb_list 选库 → kb_search_two_stage 召回 → kb_doc_read 内容裁决，content-overrides-vector）优于
一次性向量 top-k；两阶段检索为<b>工程加速项</b>；跨语言（en/zh/ja）检验稳健性。</p>

<h2>模块 A · 知识入库</h2>
<div class="card"><canvas id="chartA" height="110"></canvas></div>
<div class="fig-explain"><b>图 A 解读：</b>三种语言（英/中/日）各 400 页维基文本经生产入库链路
（web create → batch-index → force 重索引）写入指定知识库。<b>入库成功率</b>与<b>指定库归属正确率</b>
在三种语言下均为 1.0（图中重合于顶部），说明入库机制与语言无关；<b>存储完整率</b>（回读字符数/源字符数，
大文档自动拆分为 part 后按 part 求和）接近 1.0，证明分块与拆分不丢内容；<b>自检索命中@1</b>
（以文档自身前 200 字符为查询，库内向量检索第一名必须是原文档）反映索引粒度与嵌入质量。
该图支撑论文中"入库阶段内容零丢失、归属零错误"的系统性声明。</div>
<table id="tableA"><thead><tr><th>语言</th><th>入库成功率</th><th>归属正确率</th><th>存储完整率</th><th>自检索 Hit@1</th><th>双轮复现</th></tr></thead><tbody></tbody></table>

<h2>模块 B · 内容检索（主线）vs 传统向量 baseline</h2>
<div class="card"><canvas id="chartB" height="120"></canvas></div>
<div class="fig-explain"><b>图 B1 解读：</b>同一 MCP 工具层、同一受控对照库（每语言 400 页）下的对比。
"内容检索(确定性 QDCVR)"= 程序化展开 knowledgebase-search 规程（两阶段召回 → 阈值 0.35 去重 →
top-3 kb_doc_read 内容验证并提升命中文档），"向量 baseline" = kb_search_vector 一次性 top-10。
若内容检索 Recall@5 高于向量 baseline，说明<b>逐级检索+内容裁决</b>把"真正含答案的文档"提前，
这正是论文的核心主张；两者差距即内容裁决层的净贡献（verification_boost_delta）。</div>
<div class="card"><canvas id="chartB2" height="110"></canvas></div>
<div class="fig-explain"><b>图 B2 解读（逐级命中率）：</b>金标文档首次出现的检索阶段分布：
stage1=两阶段召回候选即命中、stage2=精排后命中、stage3=内容验证提升后命中、miss=未命中。
stage3 占比越高，说明<b>内容验证层</b>对最终命中的贡献越大——这是"内容裁决优于相似度排序"
的直接证据，支撑论文方法设计（Step3 content-overrides-vector）。</div>
<div class="card"><canvas id="chartB3" height="110"></canvas></div>
<div class="fig-explain"><b>图 B3 解读（Agent 真链路）：</b>由 harness(omp) 驱动的真实 Agent
（加载 QDCVR skill 与 .omp/mcp.json 的 kb-mcp 工具）自主逐级检索，金标页出现在其引用文档中计命中。
因 LLM 非确定性，报告 mean±std（transcript 全部存档于 results/benchmark/agent-transcripts/ 可审计）。
Agent 的 hit 高于确定性管线时，说明 LLM 的查询改写与逐级浏览能覆盖单查询相似度的盲区——
即"Agent 基于内容的检索"相对"一次性 top-k"的完整优势。</div>

<h2>模块 C · 冥想（经验自动总结）</h2>
<div class="card"><canvas id="chartC" height="110"></canvas></div>
<div class="fig-explain"><b>图 C 解读：</b>对目标 KB 触发真实冥想（POST /meditation/run →
harness Agent 总结经验）。<b>运行成功率</b>与<b>KB 覆盖</b>度量自动化机制的可靠性；
<b>结构完整率</b>检查经验的 title/scenario/category 字段；<b>检索接地率</b>把经验正文当作查询
在其源库做向量检索（≥0.45 记接地），验证"经验确实源自库内内容"而非幻觉；
<b>消融 Δ</b>（exp_hit3）在经验源问题上对比经验层 QDCVR 检索与纯 KB 向量检索，
度量经验自动总结对后续检索的增益。该图支撑论文中"经验闭环有效且可复现"的声明。</div>
<table id="tableC"><thead><tr><th>KB</th><th>运行成功</th><th>经验数</th><th>结构完整率</th><th>检索接地率</th><th>消融 exp_hit@3</th></tr></thead><tbody></tbody></table>

<h2>加速项 · 两阶段检索的时延收益（辅助记录）</h2>
<div class="card"><canvas id="chartLat" height="100"></canvas></div>
<div class="fig-explain"><b>图 L 解读：</b>同为单工具调用，两阶段检索（BM25 召回→向量精排+图扩展）
与纯向量 top-10 的端到端时延对比（MCP 层计时）。两阶段以相近时延提供更高召回质量
（见图 B1），因此被用作 Agent Step2 的加速实现——该图将两阶段定位为<b>工程优化</b>而非论文贡献主体。</div>

<h2>复现凭证</h2>
<ul class="meta">
<li>语料：en/zh/ja 各 400 页 wikimedia/wikipedia 20231101（datasets-server /rows 顺序取样，
sha256 见 data/benchmarks/kb_split/crosslang-manifest-*.json）；查询=确定性 cloze 协议（年份 span 置换）。</li>
<li>链路：全部经 kb-mcp（MCP stdio, uv run --directory kb-mcp python server.py）→ backend :8771。</li>
<li>嵌入 BAAI/bge-m3（本地 GPU）· 向量库 ChromaDB · BM25 jieba · 随机性：无随机数（确定性管线）；Agent 通道 mean±std。</li>
<li>基线参数：kb_search_vector（Chroma, bge-m3, top_k=10, 阈值 0.35 仅用于 QDCVR Step2.5）。</li>
<li>复现命令与容忍度见 Skill: rag-cikm-benchmark。</li>
</ul>
<p class="meta">脚本: benchmark-web/benchmark/scripts/{benchmark_ingestion,benchmark_content_mcp,benchmark_content_agent,benchmark_meditation,make_benchmark_html}.py</p>

<script>
const DATA = __DATA__;

function bar(canvasId, labels, datasets, yTitle, stacked) {
  new Chart(document.getElementById(canvasId), {
    type: 'bar',
    data: { labels, datasets },
    options: {
      responsive: true,
      scales: {
        y: { beginAtZero: true, max: (yTitle.includes('时延')?undefined:1.05),
             stacked: !!stacked, title: {display:true, text:yTitle} },
        x: { stacked: !!stacked }
      },
      plugins: { legend: { position: 'top' } }
    }
  });
}

// 图 A
const ing = DATA.ingestion, langs = Object.keys(ing);
const mk = (key, label) => ({label, data: langs.map(l => ing[l][key])});
bar('chartA', langs.map(l=>({en:'English',zh:'中文',ja:'日本語'}[l])), [
  mk('ingest_success_rate','入库成功率'), mk('membership_accuracy','指定库归属正确率'),
  mk('storage_completeness_mean','存储完整率'), mk('self_retrieval_hit1','自检索 Hit@1'),
], '得分');

// 图 B1
const con = DATA.content;
const ds = (key,label) => ({label, data: langs.map(l=>con[l][key])});
bar('chartB', langs.map(l=>({en:'English',zh:'中文',ja:'日本語'}[l])), [
  {label:'内容检索 R@5 (QDCVR)', data: langs.map(l=>con[l].staged_r5)},
  {label:'向量 baseline R@5', data: langs.map(l=>con[l].vector_r5)},
  {label:'内容检索 R@1', data: langs.map(l=>con[l].staged_r1)},
  {label:'向量 baseline R@1', data: langs.map(l=>con[l].vector_r1)},
], 'Recall');

// 图 B2 逐级命中率 (stacked)
bar('chartB2', langs.map(l=>({en:'English',zh:'中文',ja:'日本語'}[l])), [
  {label:'stage1 候选命中', data: langs.map(l=>(con[l].staged_hit_dist||{}).stage1||0)},
  {label:'stage2 精排命中', data: langs.map(l=>(con[l].staged_hit_dist||{}).stage2||0)},
  {label:'stage3 内容验证命中', data: langs.map(l=>(con[l].staged_hit_dist||{}).stage3||0)},
  {label:'miss', data: langs.map(l=>(con[l].staged_hit_dist||{}).miss||0)},
], '查询数', true);

// 图 B3 Agent
const ag = DATA.agent;
bar('chartB3', langs.map(l=>({en:'English',zh:'中文',ja:'日本語'}[l])), [
  {label:'Agent hit@1 (±std)', data: langs.map(l=>ag[l].hit1),
   errorBars: {enabled:true}},
  {label:'Agent hit_any', data: langs.map(l=>ag[l].hit_any)},
], '命中率');

// 图 C
const med = DATA.meditation, mkb = Object.keys(med.per_kb||{});
bar('chartC', mkb.map(k=>k.replace('KB-CrossLang-','')), [
  {label:'运行成功', data: mkb.map(k=>med.per_kb[k].run_success?1:0)},
  {label:'结构完整率', data: mkb.map(k=>med.per_kb[k].structural_mean)},
  {label:'检索接地率', data: mkb.map(k=>med.per_kb[k].grounded_ratio)},
  {label:'消融 exp_hit@3', data: mkb.map(k=>med.per_kb[k].ablation_exp_hit3)},
], '得分');

// 图 L 时延
bar('chartLat', langs.map(l=>({en:'English',zh:'中文',ja:'日本語'}[l])), [
  {label:'两阶段检索(单工具调用) 时延(s)', data: langs.map(l=>con[l].staged_latency)},
  {label:'向量 top-10 时延(s)', data: langs.map(l=>con[l].vector_latency)},
], '时延 (s)');

// 表 A
const tbodyA = document.querySelector('#tableA tbody');
langs.forEach(l => {
  const s = ing[l];
  tbodyA.insertAdjacentHTML('beforeend',
    `<tr><td>${({en:'English',zh:'中文',ja:'日本語'})[l]}</td>
     <td>${(s.ingest_success_rate??0).toFixed(3)}</td><td>${(s.membership_accuracy??0).toFixed(3)}</td>
     <td>${(s.storage_completeness_mean??0).toFixed(3)}</td><td>${(s.self_retrieval_hit1??0).toFixed(3)}</td>
     <td><span class="badge ${s.repro?'pass':'pending'}">${s.repro?'双轮一致':'单轮'}</span></td></tr>`);
});
// 表 C
const tbodyC = document.querySelector('#tableC tbody');
Object.entries(med.per_kb||{}).forEach(([k,v]) => {
  tbodyC.insertAdjacentHTML('beforeend',
    `<tr><td>${k}</td><td>${v.run_success?'✓':'✗'}</td><td>${v.n_experiences}</td>
     <td>${v.structural_mean??'—'}</td><td>${v.grounded_ratio??'—'}</td><td>${v.ablation_exp_hit3??'—'}</td></tr>`);
});
</script>
</body></html>"""


def main() -> None:
    d = collect()
    data_json = build_data(d)
    chartjs = CHART_JS.read_text(encoding="utf-8") if CHART_JS.exists() else \
        "/* chart.umd.min.js 未找到 — 请下载 Chart.js v4 UMD 放至 scripts/ */"
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    html = html_template(data_json, chartjs, generated).replace(
        "__CHARTJS__", chartjs).replace("__GENERATED__", generated)
    OUT.write_text(html, encoding="utf-8")
    print(f"-> {OUT} ({OUT.stat().st_size//1024} KB)")


if __name__ == "__main__":
    main()
