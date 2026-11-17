# -*- coding: utf-8 -*-
"""A3 对照库就绪探针：每库向量必须先有命中才允许 A3 臂开跑（防 reindex 未追平假 0 命中）。

读 artifacts/s4_a3_kbids.json（--prepare-a3 产物），对每库用域内探针词做向量检索，
循环等待至 hits>0（上限 12 分钟/库），报告就绪表。纯 httpx，无子进程。
"""
import json
import sys
import time
from pathlib import Path

import httpx

ART = Path(r"D:/codes/ClaudeGPT/rag_project/rag-knowledge/review/experiment-redesign-20261101/artifacts")
ROOT = Path(r"D:/codes/ClaudeGPT/rag_project/rag-knowledge")

PROBE_Q = {
    "law-zh": "个人信息 数据安全 法律",
    "gov-zh": "政府工作报告 经济增长",
    "literature-zh": "红楼梦 宝玉",
    "literature-en": "Pride and Prejudice novel",
    "science-en": "attention mechanism transformer",
    "medicine-en": "sepsis biomarkers review",
    "tech-en": "kubernetes cluster node",
    "history-zh": "史记 项羽",
    "philosophy-en": "philosophy stoicism meditations",
    "economics-en": "economics wealth labour market",
}

TOKEN = ""
for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
    if line.startswith("MCP_AUTH_TOKEN="):
        TOKEN = line.split("=", 1)[1].strip()
        break
H = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    kb_ids = json.loads((ART / "s4_a3_kbids.json").read_text(encoding="utf-8"))
    cli = httpx.Client(trust_env=False, timeout=60, headers=H)
    not_ready = []
    for slug, kid in kb_ids.items():
        q = PROBE_Q.get(slug, slug)
        deadline = time.time() + 720
        hits = 0
        while time.time() < deadline:
            try:
                r = cli.post("http://127.0.0.1:8771/api/v1/search/vector",
                             json={"query": q, "kb_id": kid, "top_k": 3, "score_threshold": 0.2})
                hits = len(r.json().get("results") or [])
            except Exception as e:
                hits = 0
            if hits > 0:
                break
            time.sleep(12)
        status = "READY" if hits > 0 else "TIMEOUT"
        if hits == 0:
            not_ready.append(slug)
        print(f"[{status}] {slug}: hits={hits} ({kid[:8]})", flush=True)
    print("A3 readiness:", "ALL-READY" if not not_ready else f"NOT-READY {not_ready}")
    return 0 if not not_ready else 1


if __name__ == "__main__":
    sys.exit(main())
