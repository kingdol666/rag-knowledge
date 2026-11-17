# -*- coding: utf-8 -*-
"""omp×claude 成对并行单题检索（每回合 1 题，双 harness 同题各答）。"""
import json
import sys
import threading
import time
from pathlib import Path

import httpx

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[3]
WEB = "http://127.0.0.1:6789"
KB_NAME = "演示-R1论文-20261112"
TOKEN = ""
for line in (REPO / ".env").read_text(encoding="utf-8").splitlines():
    if line.startswith("MCP_AUTH_TOKEN="):
        TOKEN = line.split("=", 1)[1].strip()
H = {}
if TOKEN:
    H = {"Authorization": "Bearer " + TOKEN}

QUESTIONS = [
    ("Q1", "DeepSeek-R1 在 AIME 2024 上的 pass@1 成绩是多少？MATH-500 呢？"),
    ("Q2", "DeepSeek-R1 的强化学习框架是什么算法？为什么不用神经网络奖励模型？"),
    ("Q3", "DeepSeek-R1-Zero 是纯强化学习训练的吗？它有什么可读性方面的问题？"),
    ("Q4-ood", "DeepSeek-R1 的训练总共花了论文记录的多少美元电费？"),
]

TMPL = (
    "基于知识库「" + KB_NAME + "」（库中是 DeepSeek-R1 论文, arXiv 2501.12948）回答下面这一道题。"
    "按 QDCVR 流程：改写 → kb_search_vector → kb_laya_judge → kb_doc_read 逐字核验。"
    "答案必须给出 doc_path、逐字引用关键句、可信度标注；检索不到的如实报告未找到，禁止编造。"
    "单题作答，直奔主线，不要读大文件。问题："
)


def worker(harness, qid, question):
    cli = httpx.Client(trust_env=False, timeout=120, headers=H)
    prompt = TMPL + question
    r = cli.post(WEB + "/api/kb/agent/chat",
                 json={"prompt": prompt, "harness": harness,
                       "permission": "bypassPermissions", "mode": "async",
                       "timeout_ms": 1100000})
    d = {}
    if r.status_code == 200:
        d = r.json()
    tid = d.get("task_id")
    if not tid:
        rec = {"qid": qid, "harness": harness, "status": "SUBMIT_FAIL"}
        (BASE / ("qa_" + harness + "_" + qid + ".json")).write_text(
            json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
        print("[" + harness + "] " + qid + " SUBMIT_FAIL", flush=True)
        return
    t0 = time.time()
    final = None
    for _ in range(75):
        time.sleep(10)
        t = cli.get(WEB + "/api/kb/agent/tasks/" + tid)
        td = {}
        if t.status_code == 200:
            td = t.json()
        st = td.get("status")
        if st in ("done", "completed", "success", "finished", "error", "failed", "timeout"):
            final = td
            break
    dt = round(time.time() - t0, 1)
    result = final.get("result") if final else None
    reply = ""
    if isinstance(result, dict):
        reply = result.get("reply") or ""
    rec = {"qid": qid, "harness": harness, "status": final.get("status") if final else "?",
           "seconds": dt, "task_id": tid, "reply_chars": len(reply), "reply": reply}
    (BASE / ("qa_" + harness + "_" + qid + ".json")).write_text(
        json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    print("[" + harness + "] " + qid + " " + str(rec["status"]) + " " + str(dt) + "s chars=" + str(len(reply)), flush=True)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    for qid, q in QUESTIONS:
        t1 = threading.Thread(target=worker, args=("omp", qid, q))
        t2 = threading.Thread(target=worker, args=("claude", qid, q))
        t1.start()
        t2.start()
        t1.join()
        t2.join()
    print("ALL PAIRS DONE")
