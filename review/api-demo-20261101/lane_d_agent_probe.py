# -*- coding: utf-8 -*-
"""Part D：对外 API 调用 Agent 实测。
  GET  /api/kb/agent/meta   —— 能力发现面（哪些 harness/权限模式可选）
  POST /api/kb/agent/chat   —— sync 模式全原生 Agent 一轮（自带 skill + 全部 MCP）
运行: uv run --no-sync --directory backend python D:/codes/ClaudeGPT/rag_project/rag-knowledge/review/api-demo-20261101/lane_d_agent_probe.py
"""
import json
import sys
import time
from pathlib import Path

import httpx

BASE = Path(__file__).resolve().parent
ART = BASE / "artifacts" / "lane_d"
ART.mkdir(parents=True, exist_ok=True)
REPO = BASE.parents[1]
WEB = "http://127.0.0.1:6789"

TOKEN = ""
for line in (REPO / ".env").read_text(encoding="utf-8").splitlines():
    if line.startswith("MCP_AUTH_TOKEN="):
        TOKEN = line.split("=", 1)[1].strip()
        break
H = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

cli = httpx.Client(trust_env=False, timeout=30, headers=H)

# d1 能力发现面
r = cli.get(f"{WEB}/api/kb/agent/meta")
meta = r.json() if r.status_code == 200 else {"raw": r.text[:300]}
(ART / "d1_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
engines = meta.get("engines") or meta.get("harnesses") or []
ids = [e.get("id") for e in engines] if isinstance(engines, list) else engines
print(f"[d1] GET /api/kb/agent/meta HTTP {r.status_code} chat-capable={ids}", flush=True)

# d2 sync 模式全原生 Agent 一轮（沙箱库在库）
PROMPT = ("基于知识库回答：北极光的绿色光主要来自哪种原子？发光高度大约是多少公里？"
          "要求：先检索知识库，答案给出引用的文档出处（doc_path），并逐字引用关键句。")
body = {"prompt": PROMPT, "harness": "claude", "permission": "bypassPermissions",
        "mode": "sync", "timeout_ms": 600000}
t0 = time.time()
pc = httpx.Client(trust_env=False, timeout=620, headers=H)
r = pc.post(f"{WEB}/api/kb/agent/chat", json=body)
dt = round(time.time() - t0, 1)
try:
    resp = r.json()
except Exception:
    resp = {"raw": r.text[:1000]}
(ART / "d2_agent_chat.json").write_text(
    json.dumps({"status": r.status_code, "seconds": dt, "body": resp},
               ensure_ascii=False, indent=2, default=str), encoding="utf-8")
print(f"[d2] POST /api/kb/agent/chat HTTP {r.status_code} {dt}s", flush=True)
text = json.dumps(resp, ensure_ascii=False)
print("answer head:", text[:600], flush=True)
