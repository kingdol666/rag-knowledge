# -*- coding: utf-8 -*-
"""R3 复现轮 — 真实 Agent 验收车道（harness=omp，模型 omp 默认 ustc/deepseek-flash:max）。

与终版 s_agent_sample.py 同题集（AG1-AG6，可 1:1 对照 claude-harness 6/6），
另加 1 道 OOD 域外拒答探针（AG7-ood）。
运行: python omp_agent_run.py --only AG2        # 冒烟单题
      python omp_agent_run.py                    # 全套 7 题
"""
import argparse
import json
import sys
import time
from pathlib import Path

import httpx

BASE = Path(__file__).resolve().parent
ART = BASE
REPO = BASE.parents[3]
WEB = "http://127.0.0.1:6789"
TOKEN = ""
for line in (REPO / ".env").read_text(encoding="utf-8").splitlines():
    if line.startswith("MCP_AUTH_TOKEN="):
        TOKEN = line.split("=", 1)[1].strip()
H = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}

HARNESS = "omp"  # omp 引擎默认模型 = ustc/deepseek-flash:max（~/.omp/agent/config.yml）

SAMPLE = [
    dict(qid="AG1", question="个人有权撤回同意吗？撤回之后处理者应当怎么办？", kb_hint="法律"),
    dict(qid="AG2", question="数据安全法里重要数据的目录由谁来制定？", kb_hint="法律"),
    dict(qid="AG3", question="甄士隐资助贾雨村进京赶考时给了多少银子和衣物？", kb_hint="文学"),
    dict(qid="AG4", question="Which paper introduced deep residual learning for image recognition?",
         kb_hint="科学"),
    dict(qid="AG5", question="Which Kubernetes documentation chapter explains the Pod Security Standards profiles?",
         kb_hint="技术"),
    dict(qid="AG6", question="Which philosophy work in the corpus is The Prince?",
         kb_hint="哲学"),
    dict(qid="AG7-ood", question="What is the capital of Australia and its population in 2024?",
         kb_hint="（域外题，库内无解）"),
]


def run_one(cli, q, timeout_ms=600000, max_wait_s=900):
    prompt = (
        f"基于知识库回答（限定范围提示：优先在「{q['kb_hint']}」相关知识库中检索）：{q['question']} "
        "要求：按 QDCVR 流程（改写→kb_search_vector 宽网→kb_laya_judge 引用式判卷→kb_doc_read 逐字核验），"
        "答案给出引用文档 doc_path 并逐字引用关键句，标注可信度。若知识库中不存在答案，如实报告未找到，禁止编造。")
    t0 = time.time()
    r = cli.post(f"{WEB}/api/kb/agent/chat",
                 json={"prompt": prompt, "harness": HARNESS, "permission": "bypassPermissions",
                       "mode": "async", "timeout_ms": timeout_ms})
    d = r.json() if r.status_code == 200 else {"raw": r.text[:300]}
    tid = d.get("task_id")
    if not tid:
        (ART / f"{q['qid']}_submit_err.json").write_text(
            json.dumps({"status": r.status_code, "body": d}, ensure_ascii=False), encoding="utf-8")
        return {"qid": q["qid"], "status": "SUBMIT_FAIL", "detail": d}
    final = None
    for _ in range(max_wait_s // 10):
        time.sleep(10)
        t = cli.get(f"{WEB}/api/kb/agent/tasks/{tid}")
        td = t.json() if t.status_code == 200 else {}
        st = td.get("status")
        if st in ("done", "completed", "success", "finished", "error", "failed", "timeout"):
            final = td
            break
    dt = round(time.time() - t0, 1)
    (ART / f"{q['qid']}.json").write_text(
        json.dumps(dict(qid=q["qid"], harness=HARNESS, seconds=dt, final=final),
                   ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    reply = ((final or {}).get("result") or {}).get("reply", "")
    st = (final or {}).get("status")
    print(f"[{q['qid']}] {st} {dt}s reply_chars={len(reply)}", flush=True)
    print("   ", reply[:180].replace("\n", " "), flush=True)
    return {"qid": q["qid"], "status": st, "seconds": dt, "reply_chars": len(reply),
            "task_id": tid}


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="逗号分隔 qid 子集（默认全套）")
    args = ap.parse_args()
    only = {s.strip() for s in args.only.split(",") if s.strip()}
    cli = httpx.Client(trust_env=False, timeout=120, headers=H)
    results = []
    for q in SAMPLE:
        if only and q["qid"] not in only:
            continue
        results.append(run_one(cli, q))
    print(json.dumps(results, ensure_ascii=False, indent=1))
