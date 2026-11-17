# -*- coding: utf-8 -*-
"""R2 演示：omp harness 双任务入库（LoRA PDF → 演示-LoRA论文-R2；Wiki MD → 演示-WikiLLM-R2）。"""
import json
import sys
import time
from pathlib import Path

import httpx

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[4]
WEB = "http://127.0.0.1:6789"
PDF = str((BASE / "lora.pdf").resolve())
MD = str((BASE / "wiki_llm.md").resolve())
TOKEN = ""
for line in (REPO / ".env").read_text(encoding="utf-8").splitlines():
    if line.startswith("MCP_AUTH_TOKEN="):
        TOKEN = line.split("=", 1)[1].strip()
H = {}
if TOKEN:
    H = {"Authorization": "Bearer " + TOKEN}

TASKS = {
    "lora": (
        "解析入库任务。目标知识库「演示-LoRA论文-R2」（id 606dbf27-64ab-49f0-981e-0f841e54a26a，已建好、空库，直接用，勿重建）。"
        "PDF 绝对路径：" + PDF + "（LoRA 论文，arXiv 2106.09685，26 页）。"
        "时间预算紧（回合上限 10 分钟），直奔主线，不要读大文件：\n"
        "1) MinerU 解析 PDF（parse_doc）；确认字符数>60000 且无乱码；\n"
        "2) 入库到「演示-LoRA论文-R2」：超 60K 按结构感知分卷，每卷写一句内容归纳描述（含章节范围）；\n"
        "3) 每卷显式 kb_index_document，确认 chunks>=1；\n"
        "4) 回查：关键词 'Low-Rank Adaptation' 与向量检索 'LoRA 参数高效微调' 各一次确认命中；\n"
        "5) 报告：文档清单（名称/字数/chunks）、回查结果。只操作这个库。"),
    "wiki": (
        "入库任务。目标知识库「演示-WikiLLM-R2」（id 0d632603-362c-4270-89a6-05ea9f67fb77，已建好、空库，直接用，勿重建）。"
        "MD 文件绝对路径：" + MD + "（Wikipedia Large language model 条目全文，约 55K 字符，单卷即可）。"
        "直奔主线：\n"
        "1) 读该 MD 文件（这是入库素材，允许读）；\n"
        "2) 用 kb_doc_create 入库到「演示-WikiLLM-R2」，名称 wiki_llm.md，写一句内容归纳描述；\n"
        "3) 显式 kb_index_document，确认 chunks>=1；\n"
        "4) 回查：向量检索 'large language model fine-tuning' 一次确认命中；\n"
        "5) 报告：文档名/字数/chunks、回查结果。只操作这个库。"),
}


def run(task, out, max_wait_s=900):
    cli = httpx.Client(trust_env=False, timeout=120, headers=H)
    t0 = time.time()
    r = cli.post(WEB + "/api/kb/agent/chat",
                 json={"prompt": TASKS[task], "harness": "omp", "permission": "bypassPermissions",
                       "mode": "async", "timeout_ms": 1100000})
    d = r.json() if r.status_code == 200 else {"raw": r.text[:200]}
    tid = d.get("task_id")
    if not tid:
        print("SUBMIT FAIL", str(d)[:150])
        return
    print("[" + out + "] submitted " + tid, flush=True)
    final = None
    for _ in range(max_wait_s // 10):
        time.sleep(10)
        t = cli.get(WEB + "/api/kb/agent/tasks/" + tid)
        td = t.json() if t.status_code == 200 else {}
        if td.get("status") in ("done", "completed", "success", "finished", "error", "failed", "timeout"):
            final = td
            break
    dt = round(time.time() - t0, 1)
    res = final.get("result") if final else None
    reply = res.get("reply", "") if isinstance(res, dict) else ""
    (BASE / (out + ".json")).write_text(
        json.dumps({"task": task, "seconds": dt, "task_id": tid, "final": final},
                   ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("[" + out + "] " + str(final.get("status") if final else "?") + " " + str(dt) + "s chars=" + str(len(reply)), flush=True)
    print(reply[:400], flush=True)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    import threading
    t1 = threading.Thread(target=run, args=("lora", "ingest_lora"))
    t2 = threading.Thread(target=run, args=("wiki", "ingest_wiki"))
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    print("BOTH DONE")
