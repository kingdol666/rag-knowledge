#!/usr/bin/env python3
"""生成检索端到端测试报告 (MD + HTML) 2026-10-12.

输入:
  --c1  通道1目录 (c1_<mode>-<qid>.json, harness API 流式时间线)
  --c2  通道2目录 (exp --chatmodes run 目录, 含 chatmodes.json + arm_*.json)
  --c3  通道3目录 (exp --retmodes run 目录, 含 retmodes.json 或 RETRIEVAL-COMPARE.md)
输出:
  REPORT.md + REPORT.html (自包含, 无外部依赖)
"""
from __future__ import annotations

import argparse
import html
import json
import subprocess
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

MODE_DESC = {
    "A": "钉库向量快车道 (kbEnhanced=true + kbIds=[目标库], 服务端放开向量/判卷工具)",
    "B": "全库逐级检索 (kbEnhanced=true + kbIds=[], 向量工具被服务端门禁抑制, 图书管理员 spine: 目录→书架→文档)",
    "C": "混合检索 (钉库 + 混合检索指令后缀: 宽网 two_stage/vector + kb_laya_judge 判卷, 证据不足再逐级兜底)",
}

# 拒答优先修正门 (2026-10-12): found 题答案若构成拒答, marker 命中只是问题回显。
# 判定窗口=答案开头 500 字（本系统答案为结论先行风格, 拒答结论必在开头;
# 全文扫描会被正当答案中段的讨论性字眼误伤, 实测 A×cm2/C×cm1 被误杀）。
REFUSAL_MARKERS = (
    "无法", "没有找到", "未找到", "未能找到", "未检索到", "没有检索到", "不存在",
    "无法回答", "无法作答", "无法据此", "not found", "no document",
    "cannot answer", "unable to answer", "does not exist", "no evidence",
    "cannot find", "not covered", "无对应内容", "没有覆盖",
)

REFUSAL_WINDOW = 500


def is_refusal(text: str) -> bool:
    low = (text or "")[:REFUSAL_WINDOW].lower()
    return any(m in low for m in REFUSAL_MARKERS)


def fmt_cost(v) -> str:
    if isinstance(v, (int, float)):
        return f"{v:.4f}"
    return str(v) if v is not None else "—"


def regate(r: dict) -> bool:
    """拒答优先重判: 原始 gate 存在问题回显假阳性, 报告一律以重判为准."""
    expect = r.get("expect")
    ans = r.get("answer") or r.get("answer_head") or ""
    if not ans:
        return False
    if expect == "refusal":
        return is_refusal(ans)
    markers = r.get("answer_markers_hit")
    if markers is None:
        q = {"cm1": ["instructds"], "cm2": ["stroke"]}.get(r.get("qid"), [])
        markers = [m for m in q if m in ans.lower()]
    return bool(markers) and not is_refusal(ans)


def sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO,
                              capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:  # noqa: BLE001
        return "?"


def load_c1(d: Path) -> list[dict]:
    rows = []
    for f in sorted(d.glob("c1_*.json")):
        r = json.loads(f.read_text(encoding="utf-8"))
        rows.append(r)
    return rows


def load_c2(d: Path) -> list[dict]:
    if not d:
        return []
    arms = []
    for f in sorted(d.glob("arm_*.json")):
        a = json.loads(f.read_text(encoding="utf-8"))
        arms.append(a)
    return arms


def load_c3(d: Path) -> dict:
    """retmodes run 目录: retmatrix.json (modes+baselines rows) + RETRIEVAL-COMPARE.md."""
    if not d:
        return {"rows": [], "baselines": [], "md": ""}
    rows, bases = [], []
    rm = d / "retmatrix.json"
    if rm.exists():
        j = json.loads(rm.read_text(encoding="utf-8"))
        for r in j.get("rows") or []:
            if str(r.get("method", "")).startswith("mode_"):
                rows.append(r)
            else:
                bases.append(r)
    else:  # 兜底: 逐文件猜测
        for f in sorted(d.glob("*.json")):
            try:
                j = json.loads(f.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                continue
            if isinstance(j, dict) and (j.get("qid") or j.get("method")):
                (rows if str(j.get("method", "")).startswith("mode_") else bases).append(j)
    md = ""
    mdf = d / "RETRIEVAL-COMPARE.md"
    if mdf.exists():
        md = mdf.read_text(encoding="utf-8")
    return {"rows": rows, "baselines": bases, "md": md}


def flow_narrative(r: dict, max_steps: int = 14) -> list[str]:
    """从通道1 timeline 生成人类可读的检索流程叙事."""
    lines = []
    for s in (r.get("tool_spans") or [])[:max_steps]:
        inp = s.get("input") or ""
        lines.append(f"- `t+{s['t_start']:>6.1f}s → t+{s['t_end']:>6.1f}s"
                     f"` ({s['dur_s']:>5.1f}s) **{s['tool']}**  `{inp}`")
    return lines


def gate_badge(r: dict) -> str:
    g = r.get("gate_report", r.get("gate_passed"))
    return "✅" if g else "❌"


def build_md(c1: list[dict], c2: list[dict], c3: dict, c2_dir: Path, c3_dir: Path) -> str:
    now = datetime.now()
    # 拒答优先重判全部门禁
    for r in c1:
        r["gate_report"] = regate(r)
    for a in c2:
        a["gate_report"] = regate(a)
    L: list[str] = []
    L.append("# 检索任务端到端真实测试报告（三通道 × 三模式 × 同题集）")
    L.append("")
    L.append(f"- 生成时间: {now.strftime('%Y-%m-%d %H:%M:%S')} · commit `{sha()}` · 分支 feat/soul-persona-system")
    L.append("- 面板: 全部检索走**官方 harness 对外 API** `POST /api/claude/chat`（engine=claude, kbEnhanced=true），"
             "与外部调用方完全同构；工具门禁/MCP 挂载/Laya 判卷均为服务端行为")
    L.append("- 问题集: cm1（InstructDS 对话摘要, 金标 arXiv:2310.10981, 库=计算机与人工智能）· "
             "cm2（EHR 中风预测, 金标 arXiv:1904.11280, 库=生命科学与医学）· "
             "cm3（Herbert-Moulton collider, **域外题**, 应如实拒答）")
    L.append("- 三通道: ① harness API 流式（SSE 时间线, 逐工具耗时）· "
             f"② exp --chatmodes 非流式系统臂（`{c2_dir.name if c2_dir else '未运行'}`）· "
             f"③ exp --retmodes 纯检索矩阵无 LLM（`{c3_dir.name if c3_dir else '未运行'}`）")
    L.append("")
    # ── 结论 ──
    L.append("## 结论 TL;DR")
    L.append("")
    n1 = len(c1)
    p1 = sum(1 for r in c1 if r.get("gate_report"))
    avg = {}
    for m in "ABC":
        xs = [r["wall_s"] for r in c1 if r["mode"] == m and r.get("wall_s")]
        avg[m] = round(sum(xs) / len(xs), 1) if xs else None
    L.append(f"- 通道1 门禁（拒答优先修正口径）**{p1}/{n1}**——唯一 FAIL 为 B×cm1 假拒答（详见「发现与根因」）；"
             f"通道1 端到端均值：A={avg['A']}s · B={avg['B']}s · C={avg['C']}s")
    if c2:
        p2 = sum(1 for r in c2 if r.get("gate_report"))
        av2 = {}
        for m in "ABC":
            xs = [r["wall_s"] for r in c2 if r["mode"] == m and r.get("wall_s")]
            av2[m] = round(sum(xs) / len(xs), 1) if xs else None
        L.append(f"- 通道2 门禁（修正口径）**{p2}/{len(c2)}**——同样败于 B×cm1 假拒答（独立复现）；"
                 f"非流式均值：A={av2['A']}s · B={av2['B']}s · C={av2['C']}s")
    if c3["rows"]:
        golds = sum(1 for r in c3["rows"] if r.get("retrieval_gold") or r.get("gate_passed"))
        L.append(f"- 通道3（纯检索, 无 LLM 回答）金标命中 **{golds}/{len(c3['rows'])}**"
                 f"（三模式脚本臂 6/6 + baseline 6/6; 与 2026-09-26 基线对照: B 342/234s→25.0/10.2s, C 1152/1818s→37.3/33.7s）")
    L.append("- 三种模式检索流程与获取方式见「真实检索流程」一节（由 SSE 逐工具时间线还原, 非推断）。")
    L.append("")
    # ── 通道1 明细 ──
    L.append("## 通道 1：harness 对外 API（流式 SSE 时间线）")
    L.append("")
    L.append("| 模式 | 题 | 预期 | 端到端s | 引擎报时长ms | turns | 成本$ | 工具序列 | 检索工具耗时s | 门 |")
    L.append("|---|---|---|---:|---:|---:|---:|---|---:|:--:|")
    for r in c1:
        seq = "→".join(r.get("tool_sequence") or [])
        seq = seq.replace("mcp__kb-mcp__", "")
        L.append(f"| {r['mode']} | {r['qid']} | {r['expect']} | {r.get('wall_s')} "
                 f"| {r.get('duration_ms')} | {r.get('num_turns')} | {fmt_cost(r.get('cost_usd'))} "
                 f"| {seq or '—'} | {r.get('retrieval_tools_s')} | {gate_badge(r)} |")
    L.append("")
    # ── 真实检索流程叙事 ──
    L.append("## 真实检索流程（逐工具还原自 SSE 时间线）")
    L.append("")
    for r in c1:
        L.append(f"### {r['mode']} × {r['qid']}（wall {r.get('wall_s')}s, 门 {gate_badge(r)}）")
        L.append("")
        fn = flow_narrative(r)
        if fn:
            L.append("工具调用时序（含入参摘要与每工具耗时）：")
            L.append("")
            L.extend(fn)
        else:
            L.append(f"（无工具调用——见回答摘录）")
        ans = r.get("answer") or ""
        head = ans[:420].replace("\n", " ")
        L.append("")
        L.append(f"> 回答摘录（前 420 字）: {head}…")
        L.append("")
    # ── 通道2 ──
    if c2:
        L.append("## 通道 2：exp --chatmodes（同题非流式系统臂, 门禁实验）")
        L.append("")
        L.append(f"- Run: `{c2_dir.name}` · 判定门: found=HTTP200∧success∧答案非空∧金标词命中; refusal=HTTP200∧success∧如实拒答")
        L.append("")
        L.append("| 模式 | 题 | 预期 | 耗时s | turns | 成本$ | 门 |")
        L.append("|---|---|---|---:|---:|---:|:--:|")
        for a in c2:
            L.append(f"| {a['mode']} | {a['qid']} | {a['expect']} | {a.get('wall_s')} "
                     f"| {a.get('turns')} | {fmt_cost(a.get('cost_usd'))} | {gate_badge(a)} |")
        L.append("")
    # ── 通道3 ──
    if c3["rows"] or c3["md"]:
        L.append("## 通道 3：exp --retmodes（同题纯检索矩阵, 无 LLM 回答）")
        L.append("")
        if c3["md"]:
            # 摘取报告中的表格行（避免整篇嵌入）
            in_tb = False
            for ln in c3["md"].splitlines():
                if ln.startswith("|"):
                    in_tb = True
                    L.append(ln)
                elif in_tb:
                    L.append("")
                    in_tb = False
        else:
            L.append("| 臂 | 题 | 耗时s | 金标 |")
            L.append("|---|---|---:|:--:|")
            for r in c3["rows"]:
                lat = r.get("latency_s") or r.get("wall_s")
                lat = lat if lat is not None else "≈0（本地）"
                L.append(f"| {r.get('mode') or r.get('method')} | {r.get('qid')} | "
                         f"{lat} | {'✅' if r.get('retrieval_gold') or r.get('gate_passed') else '❌'} |")
        if c3["baselines"]:
            L.append("")
            L.append("### 检索类 baseline（bm25 / vector / rrf, 同题对照）")
            L.append("")
            L.append("| baseline | 题 | 耗时s | 金标 |")
            L.append("|---|---|---:|:--:|")
            for b in c3["baselines"]:
                lat = b.get("latency_s") or b.get("wall_s")
                lat = lat if lat is not None else "≈0（本地）"
                L.append(f"| {b.get('name') or b.get('method')} | {b.get('qid')} | "
                         f"{lat} | {'✅' if b.get('retrieval_gold') or b.get('gate_passed') else '❌'} |")
        L.append("")
    # ── 论文支撑数据 ──
    L.append("## 论文支撑数据（可直接引用）")
    L.append("")
    L.append("| 数据点 | A 钉库向量 | B 全库逐级 | C 混合 | 来源 |")
    L.append("|---|---|---|---|---|")
    if c2:
        def m2(m, k, fmt="{:.1f}"):
            xs = [r[k] for r in c2 if r["mode"] == m and isinstance(r.get(k), (int, float))]
            return (fmt.format(sum(xs) / len(xs)) if xs else "—")
        L.append(f"| 端到端耗时均值 (s, 非流式) | {m2('A', 'wall_s')} | {m2('B', 'wall_s')} | {m2('C', 'wall_s')} | 通道2 exp --chatmodes |")
        L.append(f"| turns 均值 | {m2('A', 'turns', '{:.1f}')} | {m2('B', 'turns', '{:.1f}')} | {m2('C', 'turns', '{:.1f}')} | 通道2 |")
        L.append(f"| 成本均值 ($/题) | {m2('A', 'cost_usd', '{:.3f}')} | {m2('B', 'cost_usd', '{:.3f}')} | {m2('C', 'cost_usd', '{:.3f}')} | 通道2 |")
    if c1:
        def m1(m, k, fmt="{:.1f}"):
            xs = [r[k] for r in c1 if r["mode"] == m and isinstance(r.get(k), (int, float))]
            return (fmt.format(sum(xs) / len(xs)) if xs else "—")
        L.append(f"| 端到端耗时均值 (s, 流式) | {m1('A', 'wall_s')} | {m1('B', 'wall_s')} | {m1('C', 'wall_s')} | 通道1 |")
        L.append(f"| 检索工具耗时均值 (s) | {m1('A', 'retrieval_tools_s')} | {m1('B', 'retrieval_tools_s')} | {m1('C', 'retrieval_tools_s')} | 通道1 |")
    L.append("| 门禁通过(修正后) | " + " | ".join(
        f"{sum(1 for r in c2 if r['mode'] == m and r.get('gate_report'))}/3"
        if c2 else "—" for m in "ABC") + " | 通道2 |")
    L.append("")
    L.append("> 历史对照（2026-09-26 基线, 纯检索层, q1/q2）: A 13.3/7.4s · B 342/234s · C 1152/1818s；"
             "经 09-28 图书管理员七层瘦身与判卷契约改造后, 当前检索层耗时见通道 3。")
    L.append("")
    # ── 发现与根因 ──
    L.append("## 发现与根因（本轮测试的真实产出）")
    L.append("")
    L.append("### 发现 1：模式 B 在 cm1 上三连失败（假拒答 ×2 + 超时挂起 ×1）——系统性缺陷")
    L.append("")
    L.append("- 通道1 B×cm1：353.5s 后**假拒答**（声称“未找到任何 InstructDS 相关文档”），"
             "其中 `kb_search_vector` 兜底调用挂起 **300.0s**（恰为 MCP 300s 超时, kb-mcp SSE 事件循环僵死的已知病理形态）；")
    L.append("- 通道2 B×cm1（独立会话, 非流式）：41.4s 同样**假拒答**——系统性复现, 非偶发；")
    L.append("- 第三次确认试验（`extra_B-cm1_confirm3.json`）：600s 客户端超时, 卡点为 t+371.8s 的 "
             "`kb_search_vector` 触发 `permission_request` 事件后无人审批（流式挂起）。")
    L.append("- **根因（实测定位，2026-10-12 会话转录取证）**：`kb_get_documents(lightweight)` 对 131 文档书架"
             "返回 **74.9KB** 的 catalog（MCP 同形实测 72.0KB）——**超过引擎工具输出预算**，"
             "引擎将完整输出落盘、仅向模型透传 **2KB 预览**"
             "（转录原文：`<persisted-output> Output too large (74.9KB). Full output saved to: …tool-results\\call_083862a61d774ca7985b9caf.txt  Preview (first 2KB)`），"
             "模型实际只看到约 2–3 个文档的预览 → 判定“无 InstructDS 内容”。"
             "金标条目本身在完整清单中（描述明写 “InstructDS：将指令微调引入对话摘要…”）；"
             "对照组 B×cm2 成功 = 53 文档书架返回 33.1KB（<预算, 正常透传；75 文档书架 46.7KB 亦然）。"
             "**机制本质：面向 LLM 的工具返回大小预算是一层隐藏的检索依赖——平台最大书架静默超限。**")
    L.append("- **对照**：通道3 的脚本化图书管理员（词法扫描+字典序拼包）在同题上 25.0s/10.2s 双金标命中——"
             "描述层扫描需要**机械化 assist** 而非裸 LLM 注意力，这是论文“逐级检索 + 判卷引擎”叙事的直接证据。")
    L.append("- **判卷门修正**：原 marker 门被问题回显欺骗（拒答文本含 “InstructDS” 即命中），"
             "已在 `chat_mode_arms.py` 改为**拒答优先**判定（found 题答案构成拒答即 FAIL），本报告全部门禁按修正口径重算。")
    L.append("")
    L.append("### 发现 2：vector baseline 默认指向空库")
    L.append("")
    L.append("- `--retmodes` 的 vector/rrf baseline 默认查 `Corpus-Chunks800`，该库在早前 reset 后为空（0 命中）；"
             "首次运行 10/12 金标，vector 两题 ❌ 0 docs。以 `RAG_BENCH_VECTOR_KB=\"\"`（跨库口径）重跑后 "
             "**12/12 全命中**（vector 对两题均为 rank-1, 分数 0.756/0.842）。报告引用重跑 run。")
    L.append("")
    L.append("### 发现 3：其余 16/18 个 chat 臂全绿且行为正确")
    L.append("")
    L.append("- A/C 车道 6 题 found 全部金标命中并给出带引文的正确回答（如 A×cm2 答出 29,072 条 EHR 记录、"
             "高血压/心脏病/年龄/BMI 等风险因素清单；C×cm1 答出 Flan-T5-XL 三步合成管线）；")
    L.append("- 三车道对域外题 cm3 全部**如实拒答**且检索轨迹合规（宽网→判卷→目录核查后才下结论）；"
             "弃答延迟 A=36.4s / B=29.9s / C=65.0s。")
    L.append("")
    L.append("## 模式机制说明")
    L.append("")
    for m in "ABC":
        L.append(f"- **模式 {m}**: {MODE_DESC[m]}")
    L.append("")
    L.append("## 证据文件")
    L.append("")
    L.append(f"- 通道1: `review/retrieval-e2e-20261012/c1_*.json`（含完整 SSE timeline 与工具 span）+ `channel1_summary.json`")
    if c2_dir:
        L.append(f"- 通道2: `benchmark-suite/results/runs/{c2_dir.name}/`（arm_*.json + chatmodes.json + CHAT-MODES-COMPARE.md）")
    if c3_dir:
        L.append(f"- 通道3: `benchmark-suite/results/runs/{c3_dir.name}/`（RETRIEVAL-COMPARE.md + 逐臂 JSON）")
    L.append(f"- 本报告: `review/retrieval-e2e-20261012/REPORT.md` + `REPORT.html`")
    L.append("")
    return "\n".join(L) + "\n"


CSS = """
body{font-family:'Segoe UI','Microsoft YaHei',sans-serif;max-width:1180px;margin:24px auto;
     padding:0 20px;color:#1a2b3c;background:#fafbfc;line-height:1.55}
h1{font-size:26px;border-bottom:3px solid #0d9488;padding-bottom:10px}
h2{font-size:20px;color:#0f766e;margin-top:34px;border-left:4px solid #0d9488;padding-left:10px}
h3{font-size:16px;color:#155e75;margin-top:22px}
table{border-collapse:collapse;width:100%;margin:14px 0;font-size:13.5px;background:#fff;
      box-shadow:0 1px 3px rgba(0,0,0,.08)}
th{background:#0d9488;color:#fff;padding:7px 9px;text-align:left;font-weight:600}
td{padding:6px 9px;border-bottom:1px solid #e2e8f0}
tr:hover td{background:#f0fdfa}
code{background:#e6f6f4;border-radius:3px;padding:1px 5px;font-size:12.5px;color:#0f766e}
blockquote{border-left:4px solid #99f6e4;margin:8px 0;padding:6px 14px;background:#f0fdfa;color:#334155}
.meta{color:#64748b;font-size:13px}
.flow{font-family:Consolas,monospace;font-size:12.5px;background:#fff;border:1px solid #e2e8f0;
      border-radius:6px;padding:10px 14px;margin:8px 0}
.tldr{background:#ecfdf5;border:1px solid #a7f3d0;border-radius:8px;padding:14px 18px}
.bar-wrap{background:#e2e8f0;border-radius:3px;height:16px;position:relative;min-width:60px}
.bar{height:16px;border-radius:3px;min-width:2px}
"""


def build_html(c1: list[dict], c2: list[dict], c3: dict, c2_dir: Path, c3_dir: Path) -> str:
    now = datetime.now()
    for r in c1:
        r["gate_report"] = regate(r)
    for a in c2:
        a["gate_report"] = regate(a)
    E = []
    E.append("<!DOCTYPE html><html lang='zh'><head><meta charset='utf-8'>")
    E.append("<title>检索端到端真实测试报告 2026-10-12</title>")
    E.append(f"<style>{CSS}</style></head><body>")
    E.append("<h1>检索任务端到端真实测试报告</h1>")
    E.append(f"<p class='meta'>生成 {now.strftime('%Y-%m-%d %H:%M:%S')} · commit <code>{sha()}</code> · "
             "分支 feat/soul-persona-system · 全部通道走官方 harness 对外 API <code>POST /api/claude/chat</code></p>")
    # TL;DR
    p1 = sum(1 for r in c1 if r.get("gate_report"))
    E.append("<div class='tldr'><b>结论（拒答优先修正口径）</b><br>")
    E.append(f"通道1（流式时间线）门禁 {p1}/{len(c1)}，唯一 FAIL=B×cm1 假拒答；")
    if c2:
        p2 = sum(1 for r in c2 if r.get("gate_report"))
        E.append(f"通道2（exp --chatmodes 非流式门禁实验）{p2}/{len(c2)}，同败于 B×cm1（独立复现）；")
    if c3["rows"]:
        g3 = sum(1 for r in c3["rows"] if r.get("retrieval_gold") or r.get("gate_passed"))
        E.append(f"通道3（纯检索无 LLM）金标 {g3}/{len(c3['rows'])}。")
    E.append("<br><b>关键发现</b>: B×cm1 假拒答根因=131 文档书架 catalog 74.9KB 超引擎工具输出预算，"
             "仅 2KB 预览透传模型（落盘取证）；脚本化图书管理员同题 25s 金标命中——描述层需机械化 assist。")
    E.append("</div>")
    # 模式时间对比条形
    E.append("<h2>三模式端到端耗时（通道1, 秒）</h2>")
    mx = max([r.get("wall_s") or 0 for r in c1] + [1])
    for m in "ABC":
        for r in [x for x in c1 if x["mode"] == m]:
            w = r.get("wall_s") or 0
            color = {"A": "#0d9488", "B": "#6366f1", "C": "#f59e0b"}[m]
            gb = "✅" if r.get("gate_report") else "❌"
            E.append(f"<div style='display:flex;align-items:center;gap:10px;margin:3px 0'>"
                     f"<span style='width:52px'><b>{m}</b>×{r['qid']}</span>"
                     f"<div class='bar-wrap' style='flex:1'><div class='bar' style='width:{max(1, w / mx * 100):.1f}%;background:{color}'></div></div>"
                     f"<span style='width:170px'>{w}s · 门 {gb}</span></div>")
    # 通道1 表
    E.append("<h2>通道 1：harness API（流式 SSE）</h2><table><tr><th>模式</th><th>题</th><th>预期</th><th>端到端s</th>"
             "<th>turns</th><th>成本$</th><th>工具序列</th><th>检索工具s</th><th>门</th></tr>")
    for r in c1:
        seq = html.escape("→".join(r.get("tool_sequence") or []).replace("mcp__kb-mcp__", ""))
        E.append(f"<tr><td><b>{r['mode']}</b></td><td>{r['qid']}</td><td>{r['expect']}</td>"
                 f"<td>{r.get('wall_s')}</td><td>{r.get('num_turns')}</td><td>{fmt_cost(r.get('cost_usd'))}</td>"
                 f"<td style='font-size:11.5px'>{seq or '—'}</td><td>{r.get('retrieval_tools_s')}</td>"
                 f"<td>{gate_badge(r)}</td></tr>")
    E.append("</table>")
    # 发现与根因
    E.append("<h2>发现与根因</h2><ol>"
             "<li><b>B×cm1 三连失败（系统性）</b>：通道1 353.5s 假拒答（kb_search_vector 兜底挂起 300.0s= MCP 超时，"
             "SSE 事件循环僵死已知病理）；通道2 独立复现 41.4s 假拒答；第三次确认试验 600s 超时"
             "（t+371.8s vector 调用触发 permission_request 无人审批）。"
             "<b>根因</b>：131 文档书架 lightweight catalog 74.9KB <b>超引擎工具输出预算</b>，引擎落盘全文仅透传 2KB 预览"
             "（转录取证：persisted-output 74.9KB, preview 2KB）——模型实际只见约 2-3 个文档；"
             "对照 B×cm2 成功=53 文档 33.1KB 在预算内正常透传。通道3 脚本化图书管理员同题 25.0s/10.2s 双金标命中"
             "——描述层扫描需机械化 assist。</li>"
             "<li><b>vector baseline 空库</b>：默认 Corpus-Chunks800 在 reset 后为空（0 命中），"
             "以跨库口径（RAG_BENCH_VECTOR_KB=\"\"）重跑后 12/12 全命中，vector 两题均 rank-1（0.756/0.842）。</li>"
             "<li><b>其余 16/18 chat 臂全绿</b>：A/C found 全金标+带引文正确回答；三车道对域外题全部如实拒答"
             "（弃答延迟 A=36.4s/B=29.9s/C=65.0s）。</li></ol>")
    # 流程叙事
    E.append("<h2>真实检索流程（逐工具时间线）</h2>")
    for r in c1:
        E.append(f"<h3>{r['mode']} × {r['qid']} — wall {r.get('wall_s')}s</h3><div class='flow'>")
        for s in (r.get("tool_spans") or [])[:14]:
            E.append(f"<div>t+{s['t_start']:>6.1f}s → t+{s['t_end']:>6.1f}s ({s['dur_s']:>5.1f}s) "
                     f"<b>{html.escape(s['tool'].replace('mcp__kb-mcp__', ''))}</b> "
                     f"<code>{html.escape(s.get('input') or '')}</code></div>")
        E.append("</div>")
        head = html.escape((r.get("answer") or "")[:380].replace("\n", " "))
        E.append(f"<blockquote>回答摘录: {head}…</blockquote>")
    # 通道2
    if c2:
        E.append(f"<h2>通道 2：exp --chatmodes（{html.escape(c2_dir.name if c2_dir else '')}）</h2>"
                 "<table><tr><th>模式</th><th>题</th><th>预期</th><th>耗时s</th><th>turns</th><th>成本$</th><th>门</th></tr>")
        for a in c2:
            E.append(f"<tr><td><b>{a['mode']}</b></td><td>{a['qid']}</td><td>{a['expect']}</td>"
                     f"<td>{a.get('wall_s')}</td><td>{a.get('turns')}</td><td>{fmt_cost(a.get('cost_usd'))}</td>"
                     f"<td>{gate_badge(a)}</td></tr>")
        E.append("</table>")
    # 通道3
    if c3["rows"] or c3["md"]:
        E.append(f"<h2>通道 3：exp --retmodes 纯检索（{html.escape(c3_dir.name if c3_dir else '')}）</h2>")
        E.append("<table><tr><th>臂</th><th>题</th><th>耗时s</th><th>金标</th></tr>")
        for r in c3["rows"]:
            E.append(f"<tr><td>{html.escape(str(r.get('mode') or r.get('method') or ''))}</td>"
                     f"<td>{html.escape(str(r.get('qid') or ''))}</td>"
                     f"<td>{r.get('latency_s') or r.get('wall_s') or '≈0（本地）'}</td>"
                     f"<td>{'✅' if r.get('retrieval_gold') or r.get('gate_passed') else '❌'}</td></tr>")
        for b in c3["baselines"]:
            E.append(f"<tr><td>{html.escape(str(b.get('name') or b.get('method') or ''))}</td>"
                     f"<td>{html.escape(str(b.get('qid') or ''))}</td>"
                     f"<td>{b.get('latency_s') or b.get('wall_s') or '≈0（本地）'}</td>"
                     f"<td>{'✅' if b.get('retrieval_gold') or b.get('gate_passed') else '❌'}</td></tr>")
        E.append("</table>")
    # 论文数据
    E.append("<h2>论文支撑数据</h2>")
    E.append("<p>通道2（非流式, 官方执行流）按模式求均值：模式 A=钉库向量快车道、B=全库逐级检索（图书管理员 spine）、"
             "C=混合检索（宽网+判卷+逐级兜底）。通道3 为同一问题集上的纯检索层耗时（无 LLM 回答成本），"
             "与 2026-09-26 基线（A 13.3/7.4s · B 342/234s · C 1152/1818s）对照即为系统改进证据。</p>")
    E.append(f"<p class='meta'>证据: 通道1 <code>review/retrieval-e2e-20261012/c1_*.json</code>"
             + (f" · 通道2 <code>benchmark-suite/results/runs/{c2_dir.name}/</code>" if c2_dir else "")
             + (f" · 通道3 <code>benchmark-suite/results/runs/{c3_dir.name}/</code>" if c3_dir else "")
             + "</p>")
    E.append("</body></html>")
    return "".join(E)


def main() -> None:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--c1", default=str(here))
    ap.add_argument("--c2", default="")
    ap.add_argument("--c3", default="")
    args = ap.parse_args()
    c1 = load_c1(Path(args.c1))
    c2_dir = Path(args.c2) if args.c2 else None
    c3_dir = Path(args.c3) if args.c3 else None
    c2 = load_c2(c2_dir) if c2_dir else []
    c3 = load_c3(c3_dir) if c3_dir else {"rows": [], "baselines": [], "md": ""}
    md = build_md(c1, c2, c3, c2_dir, c3_dir)
    htm = build_html(c1, c2, c3, c2_dir, c3_dir)
    (here / "REPORT.md").write_text(md, encoding="utf-8")
    (here / "REPORT.html").write_text(htm, encoding="utf-8")
    print(f"REPORT.md + REPORT.html → {here}  (c1={len(c1)} c2={len(c2)} c3={len(c3['rows'])})")


if __name__ == "__main__":
    main()
