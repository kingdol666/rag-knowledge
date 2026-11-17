# -*- coding: utf-8 -*-
"""续传任务：omp 第三回合完成剩余卷入库（try2 已入 Part 1）。"""
import json
import sys
import time
from pathlib import Path

import httpx

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[3]
WEB = "http://127.0.0.1:6789"
KB_ID = "2f63d95f-e3e1-4242-bfdf-9191a3c535a3"
PDF = str((BASE / "deepseek_r1.pdf").resolve())
TOKEN = ""
for line in (REPO / ".env").read_text(encoding="utf-8").splitlines():
    if line.startswith("MCP_AUTH_TOKEN="):
        TOKEN = line.split("=", 1)[1].strip()
H = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}

prompt = (
    "续传任务：知识库「演示-R1论文-20261112」（id 2f63d95f-e3e1-4242-bfdf-9191a3c535a3）中，"
    "论文 PDF（" + PDF + "）的解析已完成、Part 1 已入库（59,184 字节）。请：\n"
    "1) kb_get_documents 查看已入库卷（不要重复入库 Part 1）；\n"
    "2) 把剩余的卷（Part 2-5，解析结果已有）继续用 kb_doc_save_parsed 入库，每卷写一句内容归纳摘要描述；\n"
    "3) 已入库但未索引的卷显式 kb_index_document；\n"
    "4) 回查：关键词 'GRPO' 与向量检索 'R1 的强化学习算法' 各一次确认命中；\n"
    "5) 报告最终文档清单与 chunks 数。只操作这个库。直奔主线，不要读大文件。"
)

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    cli = httpx.Client(trust_env=False, timeout=120, headers=H)
    t0 = time.time()
    r = cli.post(f"{WEB}/api/kb/agent/chat",
                 json={"prompt": prompt, "harness": "omp", "permission": "bypassPermissions",
                       "mode": "async", "timeout_ms": 1100000})
    tid = (r.json() or {}).get("task_id")
    print("submitted", tid, flush=True)
    final = None
    for _ in range(120):
        time.sleep(10)
        t = cli.get(f"{WEB}/api/kb/agent/tasks/{tid}")
        td = t.json() if t.status_code == 200 else {}
        if td.get("status") in ("done", "completed", "success", "finished", "error", "failed", "timeout"):
            final = td
            break
    dt = round(time.time() - t0, 1)
    (BASE / "ingest_omp_try3.json").write_text(
        json.dumps({"seconds": dt, "task_id": tid, "final": final},
                   ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    res = (final or {}).get("result") or {}
    reply = res.get("reply", "") if isinstance(res, dict) else ""
    print(f"[try3] {final.get('status') if final else '?'} {dt}s reply={len(reply)}")
    print(reply[:800])
