# -*- coding: utf-8 -*-
"""真实 Agent 执行检索+增强回答采样（/api/kb/agent/chat，async 模式）。

6 题（跨 6 域）由**原生 Agent（claude harness，全原生工具面+skill）**执行完整 QDCVR：
改写→宽网→引用式判卷→doc_read 逐字核验→带 doc_path 溯源的增强回答。
对照臂（A0 机械执行）同题结果在 s4 traces 中，可作 agent vs 机械一致性观察。

运行: uv run --no-sync --directory backend python .../s_agent_sample.py
"""
import json
import sys
import time
from pathlib import Path

import httpx

BASE = Path(__file__).resolve().parent
ART = BASE.parent / "artifacts" / "agent_sample"
ART.mkdir(parents=True, exist_ok=True)
REPO = BASE.parents[2]
WEB = "http://127.0.0.1:6789"
TOKEN = ""
for line in (REPO / ".env").read_text(encoding="utf-8").splitlines():
    if line.startswith("MCP_AUTH_TOKEN="):
        TOKEN = line.split("=", 1)[1].strip()
        break
H = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}

# 跨 6 域采样（金标来自 questions.jsonl 同源，判据一致）
SAMPLE = [
    dict(qid="AG1", question="个人有权撤回同意吗？撤回之后处理者应当怎么办？", kb_hint="法律"),
    dict(qid="AG2", question="数据安全法里重要数据的目录由谁来制定？", kb_hint="法律"),
    dict(qid="AG3", question="甄士隐资助贾雨村进京赶考时给了多少银子和衣物？", kb_hint="文学"),
    dict(qid="AG4", question="Which paper introduced deep residual learning for image recognition?",
         kb_hint="科学"),
    dict(
        qid="AG5",
        question="Which Kubernetes documentation chapter explains the Pod Security Standards profiles?",
        kb_hint="技术"),
    dict(qid="AG6", question="Which philosophy work in the corpus is The Prince?",
         kb_hint="哲学"),
]

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    cli = httpx.Client(trust_env=False, timeout=60, headers=H)
    for q in SAMPLE:
        prompt = (
            f"基于知识库回答（限定范围提示：优先在「{q['kb_hint']}」相关知识库中检索）：{q['question']} "
            "要求：按 QDCVR 流程（改写→kb_search_vector 宽网→kb_laya_judge 引用式判卷→kb_doc_read 逐字核验），"
            "答案给出引用文档 doc_path 并逐字引用关键句，标注可信度。")
        t0 = time.time()
        r = cli.post("http://127.0.0.1:6789/api/kb/agent/chat",
                     json={"prompt": prompt, "harness": "claude", "permission": "bypassPermissions",
                           "mode": "async", "timeout_ms": 600000})
        d = r.json() if r.status_code == 200 else {"raw": r.text[:200]}
        tid = d.get("task_id")
        if not tid:
            (ART / f"{q['qid']}_submit_err.json").write_text(
                json.dumps({"status": r.status_code, "body": d}, ensure_ascii=False), encoding="utf-8")
            print(f"[{q['qid']}] submit FAIL {str(d)[:120]}")
            continue
        final = None
        for _ in range(70):  # 最长 ~11.5 分钟
            time.sleep(10)
            t = cli.get(f"http://127.0.0.1:6789/api/kb/agent/tasks/{tid}")
            td = t.json() if t.status_code == 200 else {}
            st = td.get("status")
            if st in ("done", "completed", "success", "finished", "error", "failed", "timeout"):
                final = td
                break
        dt = round(time.time() - t0, 1)
        (ART / f"{q['qid']}.json").write_text(
            json.dumps(dict(qid=q["qid"], seconds=dt, final=final),
                       ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        reply = ((final or {}).get("result") or {}).get("reply", "")
        print(f"[{q['qid']}] {st} {dt}s reply_chars={len(reply)}")
        print("   ", reply[:150].replace("\n", " "), flush=True)
