# -*- coding: utf-8 -*-
"""LoRA 入库续传回合：解析已由上一回合完成（MinerU 任务缓存），本回合只做入库+索引+回查。"""
import json
import sys
import time
from pathlib import Path

import httpx

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[4]
WEB = "http://127.0.0.1:6789"
PDF = str((BASE / "lora.pdf").resolve())
TOKEN = ""
for line in (REPO / ".env").read_text(encoding="utf-8").splitlines():
    if line.startswith("MCP_AUTH_TOKEN="):
        TOKEN = line.split("=", 1)[1].strip()
H = {}
if TOKEN:
    H = {"Authorization": "Bearer " + TOKEN}

prompt = (
    "续传入库任务。知识库「演示-LoRA论文-R2」（id 606dbf27-64ab-49f0-981e-0f841e54a26a，空库）。"
    "PDF（" + PDF + "）上一回合已完成 MinerU 解析（parse_task 已存在/已缓存，约 82K 字符）——"
    "用 parse_task_status 或 parse_doc 直接取已完成结果，【不要重新解析】。然后：\n"
    "1) 入库到「演示-LoRA论文-R2」：超 60K 按结构感知分卷（预计 2 卷），每卷写一句内容归纳描述；\n"
    "2) 每卷显式 kb_index_document，确认 chunks>=1；\n"
    "3) 回查：关键词 'Low-Rank Adaptation' 与向量检索 'LoRA 参数高效微调' 各一次确认命中；\n"
    "4) 报告：文档清单（名称/字数/chunks）、回查结果。只操作这个库。直奔主线，不要读大文件。"
)

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    cli = httpx.Client(trust_env=False, timeout=120, headers=H)
    t0 = time.time()
    r = cli.post(WEB + "/api/kb/agent/chat",
                 json={"prompt": prompt, "harness": "omp", "permission": "bypassPermissions",
                       "mode": "async", "timeout_ms": 1100000})
    tid = r.json().get("task_id")
    print("submitted", tid, flush=True)
    final = None
    for _ in range(75):
        time.sleep(10)
        t = cli.get(WEB + "/api/kb/agent/tasks/" + tid)
        td = t.json() if t.status_code == 200 else {}
        if td.get("status") in ("done", "completed", "success", "finished", "error", "failed", "timeout"):
            final = td
            break
    dt = round(time.time() - t0, 1)
    (BASE / "ingest_lora_try2.json").write_text(
        json.dumps({"seconds": dt, "task_id": tid, "final": final},
                   ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    res = final.get("result") if final else None
    reply = res.get("reply", "") if isinstance(res, dict) else ""
    print("[lora-try2]", final.get("status") if final else "?", str(dt) + "s chars=" + str(len(reply)))
    print(reply[:600])
