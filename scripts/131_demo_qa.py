#!/usr/bin/env python3
"""demo-qa 问答执行: 6 题走 soul_qdcvr_ask 真实链路, 结果存 JSON + MD 素材."""
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "benchmark-suite" / "scripts"))
from lib import McpClient  # noqa: E402

SOUL = "soul-demo-qa"
OUT = REPO / "review/demo-qa-20260927"

QUESTIONS = [
    ("Q1", "数字事实·长城", "长城到底有多长？请给出不同统计口径下的数字和出处年份。"),
    ("Q2", "误区辨析·长城", "从月球上用肉眼真的能看到长城吗？系统的知识库里是怎么说的？"),
    ("Q3", "事实·航天", "Voyager 1 是什么时候发射的？它现在处于什么状态？"),
    ("Q4", "事实·生物", "光合作用中，光反应和碳固定（Calvin 循环）分别发生在细胞/叶绿体的哪些部位？"),
    ("Q5", "大文档检索·论文", "Transformer 论文中 self-attention 的核心思想是什么？相比 RNN 和 CNN 有哪些优势？"),
    ("Q6", "库外陷阱·拒答", "布达拉宫红宫是哪一年建成的？请依据知识库回答。"),
]


def poll(mc, task_id, timeout_s=300, interval=6):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        r = mc.call("kb_task_status", {"task_id": task_id}, timeout=60)
        st = str(r.get("status", "")).lower()
        if st in ("done", "completed", "success", "finished", "failed", "error"):
            return r
        time.sleep(interval)
    return {"status": "poll-timeout"}


def main():
    mc = McpClient()
    rows = []
    for qid, qtype, q in QUESTIONS:
        t0 = time.perf_counter()
        r = mc.call("soul_qdcvr_ask",
                    {"query": q, "soul_kb_id": SOUL, "task_goal": "知识问答演示",
                     "task_type": "qa", "top_k": 4, "async_mode": True}, timeout=120)
        tid = r.get("task_id", "")
        if not tid:
            rows.append({"qid": qid, "type": qtype, "question": q, "error": str(r)[:200]})
            print(f"  {qid} SUBMIT-FAIL {str(r)[:100]}")
            continue
        fin = poll(mc, tid)
        res = fin.get("result") or {}
        ms = round((time.perf_counter() - t0) * 1000)
        row = {
            "qid": qid, "type": qtype, "question": q,
            "answer": res.get("answer", ""),
            "citations": res.get("citations", []),
            "pas_score": res.get("pas_score"),
            "evidence_count": res.get("evidence_count"),
            "selected_soul": res.get("selected_soul", ""),
            "status": fin.get("status"),
            "latency_ms": ms,
        }
        rows.append(row)
        n_cit = len(row["citations"]) if isinstance(row["citations"], list) else 0
        print(f"  {qid} {qtype} | {ms}ms | pas={row['pas_score']} | cit={n_cit} | "
              f"ans={len(str(row['answer']))}字")
    (OUT / "qa-results.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print("saved →", OUT / "qa-results.json")
    mc.close()


if __name__ == "__main__":
    main()
