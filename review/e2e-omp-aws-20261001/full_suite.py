"""Full-capability penetration suite, everything through /api/kb/agent/chat.

12 cells: R1 precise retrieval, R2 honest refusal, W1 create+ingest+index,
R3 new-KB retrieval, W2 doc update, R4 updated-fact retrieval, W3 experience,
R5 experience retrieval, W6 graph build+query, W7 organize audit, W8 verify.
Each cell resumes from its evidence JSON if present.

Pass criteria are deterministic gold checks; process = tools_used per cell.
"""
from __future__ import annotations

import json
from e2e_lib import agent_chat, agent_task, catalog  # noqa: F401
from pathlib import Path

OUT = Path(__file__).resolve().parent
KB = "e2e-agent-20261001"
summary: dict = {}

DOC_A_TITLE = "E2E-Agent 产线温控验证报告"
DOC_A = """# E2E-Agent 产线温控验证报告

产线 ln-e2e901，温控器 TT-90。
- 设定温度：160 摄氏度，实测带宽 ±0.4 摄氏度
- 采样周期：5 秒
- 验证批次：batch-e2e-a1
- 结论：温控器 TT-90 在 160 摄氏度工况连续 72 小时无越限记录。
"""

DOC_B_TITLE = "E2E-Agent 产线良率优化经验"
DOC_B = """# E2E-Agent 产线良率优化经验

产线 ln-e2e901（与《E2E-Agent 产线温控验证报告》同线）。
- 优化措施：保压压力 +1.2 bar，料筒温度 -3 摄氏度
- 良率变化：91.2% 提升至 94.6%
- 生效批次：batch-e2e-b1 起
"""


def ev(name):
    return OUT / f"{name}.json"


def done(name):
    return ev(name).exists()


def run(name, prompt, *, mode="sync", timeout_s=540.0, task_timeout=600.0):
    if done(name):
        d = json.loads(ev(name).read_text(encoding="utf-8"))
        print(f"[{name}] resume: pass={d.get('pass')}")
        return d.get("reply", ""), d
    # full API evidence (payload incl. session_id/cost) lands in {name}_call;
    # the slim judged record lands in {name}
    cell = agent_chat(prompt, mode=mode, timeout_s=timeout_s, tag=f"{name}_call")
    reply = cell.get("reply") or ""
    payload = cell.get("response") or {}
    tools = payload.get("tools_used") or []
    session_id = payload.get("session_id")
    if mode == "async":
        if cell.get("task_id"):
            fin = agent_task(cell["task_id"], timeout_s=task_timeout,
                             tag=f"{name}_final")
            final = fin.get("final") or {}
            reply = str(final.get("result", {}).get("reply") or "")
            tools = final.get("tools_used") or tools
            session_id = final.get("session_id") or session_id
        else:
            reply = cell.get("reply") or f"submit-error: {cell.get('error')}"
    rec = {"reply": reply, "tools_used": tools, "session_id": session_id,
           "wall_s": cell.get("wall_s"), "http": cell.get("http"),
           "cost_usd": cell.get("cost_usd"), "num_turns": cell.get("num_turns")}
    if not reply and cell.get("error"):
        rec["error"] = cell["error"]
    ev(name).write_text(json.dumps(rec, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    return reply, rec


def judge(name, ok, gold="", note=""):
    d = json.loads(ev(name).read_text(encoding="utf-8"))
    d["pass"] = bool(ok)
    d["gold"] = gold
    if note:
        d["note"] = note
    ev(name).write_text(json.dumps(d, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    summary[name] = {"pass": bool(ok), "tools": len(d.get("tools_used") or []),
                     "wall_s": d.get("wall_s")}
    print(f"[{name}] pass={ok} tools={len(d.get('tools_used') or [])} "
          f"wall={d.get('wall_s')}s")
    return d


NOD = "不要派发子 agent，直接在本会话执行。"

# ---------- R1 precise retrieval on aw-industrial ----------
if not done("r1_line_window"):
    run("r1_line_window",
        "注塑产线 ln-b0413f88 保压压力链式爬坡：最终入窗时刻、入窗时克重、"
        "第 8 步压力值分别是多少？精确引用数值和文档名。" + NOD, mode="sync")
r1 = json.loads(ev("r1_line_window").read_text(encoding="utf-8")).get("reply") or ""
judge("r1_line_window", "32.36" in r1 and "61.2" in r1,
      gold="克重 32.36 g、第 8 步 61.2 bar、入窗 14:40:00")

# ---------- R2 honest refusal ----------
if not done("r2_refusal"):
    run("r2_refusal",
        "量子引力波在咖啡拉花中的干涉效应应该如何量化？只依据知识库回答。" + NOD,
        mode="sync")
r2 = json.loads(ev("r2_refusal").read_text(encoding="utf-8")).get("reply") or ""
refusal_marks = ("无法", "没有找到", "未找到", "未检索到", "不存在", "no evidence",
                 "not found", "未覆盖", "未涵盖", "知识库中无")
judge("r2_refusal", any(m in r2 or m in r2.lower() for m in refusal_marks),
      gold="honest not-found, no fabrication")

# ---------- W1 create KB + ingest 2 docs + index ----------
if not done("w1_create_ingest"):
    run("w1_create_ingest",
        f"逐步执行并回报：1) 创建知识库「{KB}」（描述：E2E agent full-capability "
        f"sandbox）。2) 入库文档一（标题：{DOC_A_TITLE}，tags：温控/验证/e2e），正文：\n"
        f"{DOC_A}\n3) 入库文档二（标题：{DOC_B_TITLE}，tags：良率/优化/e2e），正文：\n"
        f"{DOC_B}\n4) 两篇都建立向量索引，并回报两个 doc_id 与索引状态。" + NOD,
        mode="async", task_timeout=900)
w1 = json.loads(ev("w1_create_ingest").read_text(encoding="utf-8")).get("reply") or ""
judge("w1_create_ingest", bool(w1) and ("索引" in w1 or "index" in w1.lower()),
      gold="2 docs ingested + index status", note=w1[:200])

KB_ID = None
for k in catalog():
    if k.get("name") == KB:
        KB_ID = k.get("kbId")
        break
print("KB_ID:", KB_ID)

# ---------- R3 new-KB retrieval (vector proves ingest) ----------
if not done("r3_newkb_fact"):
    run("r3_newkb_fact",
        f"知识库「{KB}」里，产线 ln-e2e901 温控器 TT-90 的设定温度、实测带宽、采样"
        f"周期是多少？只依据该库回答并给出文档名。" + NOD, mode="sync")
r3 = json.loads(ev("r3_newkb_fact").read_text(encoding="utf-8")).get("reply") or ""
judge("r3_newkb_fact", "160" in r3 and "0.4" in r3 and "TT-90" in r3,
      gold="160℃ / ±0.4℃ / 5s / TT-90")

# ---------- W2 update doc + R4 updated-fact retrieval ----------
if not done("w2_update_doc"):
    run("w2_update_doc",
        f"更新知识库「{KB}」中《{DOC_A_TITLE}》这篇文档：在文末追加一节"
        f"「2026-10 追加验证」，内容为：追加验证批次 batch-e2e-a2 通过，循环寿命"
        f"上调至 15,000 次。更新后重建向量索引并回报状态。" + NOD,
        mode="async", task_timeout=600)
w2 = json.loads(ev("w2_update_doc").read_text(encoding="utf-8")).get("reply") or ""
judge("w2_update_doc", bool(w2) and ("15,000" in w2 or "更新" in w2 or
      "index" in w2.lower()), gold="update + reindex acknowledged")

if not done("r4_updated_fact"):
    run("r4_updated_fact",
        f"知识库「{KB}」里，TT-90 的循环寿命追加验证结果是多少？只依据该库最新"
        f"内容回答。" + NOD, mode="sync")
r4 = json.loads(ev("r4_updated_fact").read_text(encoding="utf-8")).get("reply") or ""
judge("r4_updated_fact", "15,000" in r4 or "15000" in r4,
      gold="循环寿命 15,000 次（update→reindex→retrieve closed）")

# ---------- W3 experience + R5 experience retrieval ----------
if not done("w3_experience"):
    run("w3_experience",
        f"在知识库「{KB}」沉淀经验：标题《产线良率提升三要素》，类别 optimization，"
        f"问题「良率长期低于 92%」，解决方案「保压 +1.2 bar、料筒 -3 摄氏度、以"
        f" batch-e2e-b1 起观察两周」，关联文档《{DOC_B_TITLE}》。回报 experience id。" + NOD,
        mode="sync", timeout_s=420)
w3 = json.loads(ev("w3_experience").read_text(encoding="utf-8")).get("reply") or ""
judge("w3_experience", bool(w3) and ("experience" in w3.lower() or "经验" in w3),
      gold="experience id acknowledged")

if not done("r5_exp_retrieval"):
    run("r5_exp_retrieval",
        f"知识库经验里，良率提升的三个要素/措施是什么？给出经验标题。只依据知识库经验。" + NOD,
        mode="sync")
r5 = json.loads(ev("r5_exp_retrieval").read_text(encoding="utf-8")).get("reply") or ""
judge("r5_exp_retrieval", ("保压" in r5 or "+1.2" in r5) and ("良率" in r5),
      gold="保压 +1.2 bar / 良率提升经验")

# ---------- W6 graph build + query ----------
if not done("w6_graph"):
    run("w6_graph",
        f"为知识库「{KB}」构建知识图谱（基于文档元数据/标签），然后查询：《"
        f"E2E-Agent 产线温控验证报告》和《{DOC_B_TITLE}》在图谱中是什么关系？"
        f"回报图的节点数与边数。" + NOD,
        mode="async", task_timeout=600)
w6 = json.loads(ev("w6_graph").read_text(encoding="utf-8")).get("reply") or ""
judge("w6_graph", bool(w6) and ("节点" in w6 or "nodes" in w6.lower() or
      "关系" in w6 or "边" in w6), gold="graph built + relation queried")

# ---------- W7 organize audit ----------
if not done("w7_organize"):
    run("w7_organize",
        f"对知识库「{KB}」做整理体检：查重、描述质量、三层一致性，回报摘要。" + NOD,
        mode="async", task_timeout=600)
w7 = json.loads(ev("w7_organize").read_text(encoding="utf-8")).get("reply") or ""
judge("w7_organize", bool(w7) and ("重复" in w7 or "一致" in w7 or "文档" in w7),
      gold="organize audit summary")

# ---------- W8 verify ----------
if not done("w8_verify"):
    run("w8_verify",
        f"对知识库「{KB}」做完整性核验（磁盘/元数据/向量三层一致性），回报结论。" + NOD,
        mode="async", task_timeout=600)
w8 = json.loads(ev("w8_verify").read_text(encoding="utf-8")).get("reply") or ""
judge("w8_verify", bool(w8), gold="verify conclusion reported")

# ---------- summary ----------
n_pass = sum(1 for v in summary.values() if v["pass"])
print(f"\n==== SUITE: {n_pass}/{len(summary)} PASS ====")
for k, v in summary.items():
    print(f"  {'PASS' if v['pass'] else 'FAIL'}  {k}  tools={v['tools']}  "
          f"wall={v['wall_s']}s")
(OUT / "suite_summary.json").write_text(
    json.dumps({"kb_id": KB_ID, "n_pass": n_pass, "cells": summary},
               ensure_ascii=False, indent=1), encoding="utf-8")
