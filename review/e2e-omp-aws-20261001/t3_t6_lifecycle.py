"""T3-T6: sandbox-KB full lifecycle through web /api/kb/agent/chat (async).

T3 create KB + ingest doc + index     T4 experience write
T5 re-retrieval (fact + experience)   T6 organize audit
"""
from __future__ import annotations

import json
import re
import time
from e2e_lib import WEB, _request_json, agent_chat, agent_task, chat  # noqa: F401
from pathlib import Path

OUT = Path(__file__).resolve().parent
KB = "e2e-omp-20261001"

DOC_TITLE = "QDCVR-7 Solid-State Electrolyte Membrane Validation Report"
DOC_BODY = """# QDCVR-7 固态电解质膜验证报告

发布机构：RAG 平台验证实验室（2026 年 3 月）。

## 关键参数
- 工作电压：3.7 V
- 离子电导率：8.4 mS/cm（25 摄氏度）
- 循环寿命：12,000 次（容量保持率 82%）
- 低温性能：-20 摄氏度下容量保持率 91%

## 测试结论
QDCVR-7 膜在 25 摄氏度标准工况下连续 500 小时无短路记录；低温预处理
30 分钟后测量可显著提升数据稳定性。
"""

results: dict = {}


def step(name, ok, detail=""):
    results[name] = {"pass": bool(ok), "detail": str(detail)[:400]}
    print(f"[{name}] pass={ok} {str(detail)[:160]}")


# ---- T3 create + ingest + index (async) ----
t3 = agent_chat(
    f"请完成知识库操作并逐步执行：1) 创建知识库「{KB}」（描述：E2E OMP lifecycle "
    f"test sandbox）。2) 将下面这篇文档入库到该库（标题：{DOC_TITLE}），入库后建立"
    f"向量索引。3) 完成后用向量检索验证「离子电导率」能命中该文档，并报告命中文档标题、"
    f"知识库 id 与文档 id。\n\n文档正文：\n{DOC_BODY}",
    mode="async", tag="t3_ingest_submit")
if t3.get("task_id"):
    t3f = agent_task(t3["task_id"], timeout_s=600, tag="t3_ingest_final")
    reply = str((t3f.get("final") or {}).get("result", {}).get("reply") or "")
else:
    reply = t3.get("reply") or t3.get("error") or ""
print("T3 reply head:", reply[:300].replace(chr(10), " "))
kb_id = None
for m in re.finditer(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", reply):
    kb_id = m.group(0)
    break
# 库 id 可能与文档 id 混在一起：优先用 catalog 按名字查
if not kb_id:
    try:
        from e2e_lib import token
        status, cat = _request_json(WEB + "/api/kb/catalog", "GET", None,
                                    {"Authorization": f"Bearer {token()}"}, 20)
        kbs = cat.get("data", cat)
        if isinstance(kbs, dict):
            kbs = kbs.get("kbs") or kbs.get("list") or []
        for k in kbs or []:
            if isinstance(k, dict) and KB in str(k.get("name", "")):
                kb_id = k.get("id")
                break
    except Exception as e:  # noqa: BLE001
        print("catalog lookup failed:", str(e)[:120])
step("t3_ingest", bool(reply) and kb_id is not None, f"kb_id={kb_id}")

# ---- T4 experience write (async) ----
t4 = agent_chat(
    f"在知识库「{KB}」中沉淀一条经验：标题《固态电解质膜低温测试经验》，类别「材料"
    f"测试」，问题「-20 摄氏度下离子电导率测试数据不稳定」，解决方案「测试前对样品做"
    f"30 分钟恒温预处理，再连续采样三次取中位数」，关联文档「{DOC_TITLE}」。",
    mode="async", tag="t4_exp_submit")
if t4.get("task_id"):
    t4f = agent_task(t4["task_id"], timeout_s=600, tag="t4_exp_final")
    r4 = str((t4f.get("final") or {}).get("result", {}).get("reply") or "")
else:
    r4 = t4.get("reply") or ""
print("T4 reply head:", r4[:220].replace(chr(10), " "))
step("t4_experience", bool(r4) and ("经验" in r4 or "experience" in r4.lower()
     or "已" in r4))

# ---- T5 re-retrieval: fact via chat-api+OMP pinned to sandbox; experience via all-KB ----
time.sleep(3)
t5a = chat("QDCVR-7 固态电解质膜的离子电导率是多少？只依据知识库回答，并给出文档名。",
           kb_ids=[kb_id] if kb_id else None, tag="t5a_fact")
a5 = t5a.get("answer") or ""
step("t5a_fact_retrieval", ("8.4" in a5), a5[:160].replace(chr(10), " "))

t5b = chat("知识库经验里，针对「-20 摄氏度下离子电导率测试数据不稳定」的解决方案"
           "是什么？只依据知识库经验库回答。", tag="t5b_experience")
a5b = t5b.get("answer") or ""
step("t5b_experience_retrieval",
     ("预处理" in a5b or "恒温" in a5b or "中位数" in a5b), a5b[:160].replace(chr(10), " "))

# ---- T6 organize audit (async) ----
t6 = agent_chat(
    f"对知识库「{KB}」做一次整理体检：查重、描述质量与三层一致性审计，"
    f"返回结论摘要（文档数、重复对数、描述是否可检索）。",
    mode="async", tag="t6_organize_submit")
if t6.get("task_id"):
    t6f = agent_task(t6["task_id"], timeout_s=600, tag="t6_organize_final")
    r6 = str((t6f.get("final") or {}).get("result", {}).get("reply") or "")
else:
    r6 = t6.get("reply") or ""
print("T6 reply head:", r6[:220].replace(chr(10), " "))
step("t6_organize", bool(r6) and ("重复" in r6 or "一致" in r6 or "文档" in r6
     or "audit" in r6.lower()))

results["kb_id"] = kb_id
results_path = Path(__file__).resolve().parent / "t3_t6_verdict.json"
results_path.write_text(json.dumps(results, ensure_ascii=False, indent=1),
                        encoding="utf-8")
print(json.dumps(results, ensure_ascii=False, indent=1))
