# -*- coding: utf-8 -*-
"""Lane C-0：重建沙箱语料（纯机械，无检索/判卷语义——检索全流程由 agent 按
skill 契约经 scripts/mcp_call.py 逐步执行）。

  kb_create → parse_doc_batch(3 PNG) → kb_doc_save_parsed ×3 → kb_reindex
输出 kb_id 到 lane_c_kb.json 供后续步骤使用。

运行: uv run --no-sync --directory kb-mcp python D:/codes/ClaudeGPT/rag_project/rag-knowledge/review/api-demo-20261101/lane_c_ingest.py
"""
import asyncio
import json
import sys
import time
from pathlib import Path

from mcp import ClientSession
from mcp.client.sse import sse_client

BASE = Path(__file__).resolve().parent
GOLD = json.loads((BASE / "gallery" / "gold.json").read_text(encoding="utf-8"))
SSE_URL = "http://127.0.0.1:8000/sse"
KB_NAME = "图库演示-20261101-C全流程"
KB_DESC = "2026-11-01 QDCVR 全流程契约测试沙箱库（Lane C）：改写→宽网→判卷→读原文→增强回答，用后即删"


def content_json(res):
    try:
        return json.loads(res.content[0].text)
    except Exception:
        return {"_raw": [getattr(c, "text", str(c)) for c in res.content]}


async def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    pngs = [str(BASE / "gallery" / img["file"]) for img in GOLD["images"]]
    async with sse_client(SSE_URL) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            res = await s.call_tool("kb_create", {"name": KB_NAME, "description": KB_DESC})
            d = content_json(res)
            kb_id = (d.get("knowledgeBase") or {}).get("id") or d.get("id") or ""
            print(f"kb_create ok={bool(kb_id)} kb_id={kb_id}", flush=True)

            res = await s.call_tool("parse_doc_batch", {"file_paths": pngs, "use_ocr": True})
            task_id = content_json(res).get("task_id", "")
            print(f"parse task_id={task_id}", flush=True)
            md_by_file = {}
            for _ in range(100):
                await asyncio.sleep(4)
                res = await s.call_tool("parse_task_status", {"task_id": task_id})
                d = content_json(res)
                st = str(d.get("status", "")).lower()
                if st in ("done", "completed", "success", "finished", "error", "failed"):
                    # 实测形状：{task_id, status, result:{results:[...]}, success}
                    for r_ in (((d.get("result") or {}) if isinstance(d.get("result"), dict) else {}).get("results")
                               or d.get("results") or []):
                        src = r_.get("source_filename") or ""
                        md_by_file[src] = r_.get("markdown_path") or ""
                    break
            print(f"parse done files={list(md_by_file)}", flush=True)

            saved = 0
            for img in GOLD["images"]:
                src = img["file"]
                if not md_by_file.get(src):
                    print(f"save {src} SKIP (no md)", flush=True); continue
                res = await s.call_tool("kb_doc_save_parsed",
                                        {"parent_id": kb_id, "markdown_path": md_by_file[src],
                                         "source_filename": src, "description": img["description"]})
                d = content_json(res)
                saved += 1 if d.get("success") else 0
            print(f"saved={saved}/3", flush=True)

            res = await s.call_tool("kb_reindex", {"kb_id": kb_id})
            d = content_json(res)
            print(f"reindex ok={d.get('success', False)}", flush=True)

            out = {"kb_id": kb_id, "kb_name": KB_NAME, "task_id": task_id,
                   "md_by_file": md_by_file, "saved": saved,
                   "doc_paths": {img["file"]: f"{KB_NAME}\\{img['file'].replace('.png', '.md')}"
                                 for img in GOLD["images"]}}
            (BASE / "lane_c_kb.json").write_text(
                json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"WROTE {BASE / 'lane_c_kb.json'}")


if __name__ == "__main__":
    asyncio.run(main())
