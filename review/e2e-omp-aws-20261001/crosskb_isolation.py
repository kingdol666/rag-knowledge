"""Cross-KB per-line isolation test (2026-10-01).

Two product lines -> two separate KBs, each with its own facts. Then ask
line-specific questions WITHOUT naming a KB; the layered retrieval must
route catalog -> correct KB -> correct facts, with zero cross-line bleed.

Everything goes through /api/kb/agent/chat (the AWS kb_agent surface).
"""
from __future__ import annotations

import json
from e2e_lib import WEB, _request_json, agent_chat, agent_task, catalog, token  # noqa: F401
from pathlib import Path

OUT = Path(__file__).resolve().parent
KB_A = "e2e-lnA2-温控模块产线-r3"
KB_B = "e2e-lnB2-注塑单元产线-r3"

DOC_A = """# PX-777 温控模块产线验证记录（r3 专用）

线体：ln-E2A-r3；产品：PX-777 温控模块。
- 设定温度：172 摄氏度，实测带宽 ±0.25 摄氏度
- 采样周期：2 秒
- 验证批次：batch-lnA-01
- 结论：PX-777 产线温控在 172 摄氏度工况下连续 48 小时稳定。
"""

DOC_B = """# PY-888 注塑单元产线调参记录（r3 专用）

线体：ln-E2B-r3；产品：PY-888 注塑单元。
- 保压压力：58 bar
- 成品克重：33.05 g
- 成型周期：28 秒
- 调参结论：PY-888 产线在 58 bar 保压下克重连续 200 模稳定。
"""

DOC_A_TITLE = "PX-777 温控模块产线验证记录 r3"
DOC_B_TITLE = "PY-888 注塑单元产线调参记录 r3"
results: dict = {}


def step(name, ok, detail=""):
    results[name] = {"pass": bool(ok), "detail": str(detail)[:400]}
    print(f"[{name}] pass={ok} {str(detail)[:160]}")


def create_and_ingest(kb_name, desc, title, body, tag):
    sub = agent_chat(
        f"逐步执行：1) 创建知识库「{kb_name}」（描述：{desc}）。2) 入库文档"
        f"（标题：{title}），正文必须逐字使用下面给出的原文，不得改写或补充：\n"
        f"{body}\n"
        f"3) 建立向量索引。4) 向量检索「{desc[:12]}」自验命中并回报"
        f" kb_id 与 doc_id。不要派发子 agent，直接在本会话执行。",
        mode="async", tag=f"{tag}_submit")
    if sub.get("task_id"):
        fin = agent_task(sub["task_id"], timeout_s=720, tag=f"{tag}_final")
        return str((fin.get("final") or {}).get("result", {}).get("reply") or "")
    return sub.get("reply") or sub.get("error") or ""


# ---- W-A / W-B: two lines, two KBs ----
r_a = create_and_ingest(KB_A, "PX-777 温控模块产线的验证与温控记录",
                        "PX-777 温控模块产线验证记录", DOC_A, "wa_lineA")
step("r3wa_lineA", bool(r_a) and ("index" in r_a.lower() or "索引" in r_a or "命中" in r_a),
     r_a[:200])

r_b = create_and_ingest(KB_B, "PY-888 注塑单元产线的调参与克重记录",
                        "PY-888 注塑单元产线调参记录", DOC_B, "wb_lineB")
step("r3wb_lineB", bool(r_b) and ("index" in r_b.lower() or "索引" in r_b or "命中" in r_b),
     r_b[:200])

# resolve kb ids by name
ids = {}
for k in catalog():
    if k.get("name") == KB_A:
        ids["A"] = k.get("kbId")
    if k.get("name") == KB_B:
        ids["B"] = k.get("kbId")
print("resolved:", ids)
results["kb_ids"] = ids

# ---- Q1: line A question, NO KB specified ----
q1 = agent_chat(
    "PX-777 温控模块的设定温度和实测带宽是多少？只依据知识库回答，"
    "并说明你查的是哪个知识库。" + "不要派发子 agent，直接在本会话执行。",
    mode="sync", timeout_s=480, tag="r2q1_lineA")
a1 = q1.get("reply") or ""
q1_gold = ("172" in a1 and "0.25" in a1) and ("PX-777" in a1 or "r3" in a1 or "lnA2-r3" in a1 or "r3" in a1)
q1_contam = [x for x in ("58 bar", "33.05", "28 秒") if x in a1]
step("r3q1_lineA_route", q1_gold and not q1_contam,
     f"gold={q1_gold} contam={q1_contam} kb-mentioned={KB_A in a1 or '温控' in a1}")

# ---- Q2: line B question, NO KB specified ----
q2 = agent_chat(
    "PY-888 注塑单元的保压压力、成品克重和成型周期是多少？只依据知识库回答，"
    "并说明你查的是哪个知识库。" + "不要派发子 agent，直接在本会话执行。",
    mode="sync", timeout_s=480, tag="r2q2_lineB")
a2 = q2.get("reply") or ""
q2_gold = ("58" in a2 and "33.05" in a2 and "28" in a2) and ("PY-888" in a2 or "r3" in a2 or "lnB2-r3" in a2 or "r3" in a2)
q2_contam = [x for x in ("172", "±0.25", "0.25 摄氏度", "TT-90") if x in a2]
step("r3q2_lineB_route", q2_gold and not q2_contam,
     f"gold={q2_gold} contam={q2_contam} kb-mentioned={KB_B in a2 or '注塑' in a2}")

(OUT / "crosskb_verdict.json").write_text(
    json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(results, ensure_ascii=False, indent=1))
