# -*- coding: utf-8 -*-
"""Lane A（实机演示）：走 kb-mcp MCP 工具面（SSE :8000）做图库全生命周期。

  tools/list 证据 → kb_create → parse_doc_batch(3 PNG, OCR) → kb_doc_save_parsed ×3
  → kb_reindex → 图书管理员阶梯检索（catalog → shelf/descriptions → vector 宽网 → Laya 判卷）
  → 金标判分 → kb_doc_delete ×3 → 空库核验 → kb_delete → 目录核验

每步原始返回落盘 artifacts/lane_a/*.json，汇总结论写 lane_a_report.json。

运行: uv run --no-sync --directory kb-mcp python ../review/api-demo-20261101/lane_a_mcp_demo.py
（在 kb-mcp venv 内运行以复用已安装的 mcp SDK）
"""
import asyncio
import json
import sys
import time
from pathlib import Path

from mcp import ClientSession
from mcp.client.sse import sse_client

BASE = Path(__file__).resolve().parent
ART = BASE / "artifacts" / "lane_a"
ART.mkdir(parents=True, exist_ok=True)
GOLD = json.loads((BASE / "gallery" / "gold.json").read_text(encoding="utf-8"))

SSE_URL = "http://127.0.0.1:8000/sse"
KB_NAME = "图库演示-20261101-MCP车道"
KB_DESC = "2026-11-01 图库全生命周期实机演示沙箱库（MCP 车道）：解析-检索-删除，用后即删"
POLL_TIMEOUT = 420          # parse OCR 总超时
USED_TOOLS = ["kb_list", "kb_create", "kb_delete", "kb_get_documents",
              "parse_doc_batch", "parse_task_status", "kb_doc_save_parsed",
              "kb_reindex", "kb_search_vector", "kb_laya_judge", "kb_doc_delete"]

REPORT = {"lane": "A 实机演示（MCP 工具面 SSE:8000）", "steps": [], "started": ""}


def save(name, payload):
    (ART / f"{name}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8")


def step(name, ok, detail=""):
    REPORT["steps"].append({"step": name, "ok": bool(ok), "detail": str(detail)[:300]})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}  {detail}", flush=True)


def content_json(res):
    try:
        return json.loads(res.content[0].text)
    except Exception:
        return {"_raw": [getattr(c, "text", str(c)) for c in res.content],
                "isError": getattr(res, "isError", None)}


async def call(s, name, args, tag):
    t0 = time.time()
    res = await s.call_tool(name, args)
    data = content_json(res)
    dt = round(time.time() - t0, 1)
    save(tag, {"tool": name, "args": args, "seconds": dt, "result": data})
    return data, dt


async def poll_parse(s, task_id):
    t0 = time.time()
    while time.time() - t0 < POLL_TIMEOUT:
        data, _ = await call(s, "parse_task_status", {"task_id": task_id}, "04_parse_poll")
        st = str(data.get("status", "")).lower()
        if st in ("done", "completed", "success", "finished"):
            return data
        if st in ("error", "failed", "cancelled"):
            return data
        await asyncio.sleep(4)
    return {"status": "timeout", "success": False}


async def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    REPORT["started"] = time.strftime("%Y-%m-%d %H:%M:%S")
    pngs = [str(BASE / "gallery" / img["file"]) for img in GOLD["images"]]

    async with sse_client(SSE_URL) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()

            # 00 tools/list —— 活体工具面证据
            tools = await s.list_tools()
            names = [t.name for t in tools.tools]
            schemas = {t.name: t.inputSchema for t in tools.tools if t.name in USED_TOOLS}
            save("00_tools_list", {"count": len(names), "names": names, "used_schemas": schemas})
            step("00 tools/list", len(names) >= 90, f"{len(names)} tools (expect >=90, memory says 95)")

            # 01 健康探针（backend_status = 注册工具；health_check 是内部函数未注册）
            data, _ = await call(s, "backend_status", {}, "01_backend_status")
            step("01 backend_status", data.get("success", False),
                 json.dumps({k: data.get(k) for k in list(data)[:5]}, ensure_ascii=False)[:200])

            # 02 建沙箱库
            data, _ = await call(s, "kb_create", {"name": KB_NAME, "description": KB_DESC}, "02_kb_create")
            kb_id = data.get("knowledgeBase", {}).get("id") or data.get("id") or data.get("kb_id") or ""
            step("02 kb_create", bool(kb_id), f"kb_id={kb_id}")
            if not kb_id:
                save("ABORT", REPORT); print(json.dumps(REPORT, ensure_ascii=False)); return

            # 03 图库解析（OCR，非阻塞任务）
            data, _ = await call(s, "parse_doc_batch", {"file_paths": pngs, "use_ocr": True}, "03_parse_doc_batch")
            task_id = data.get("task_id", "")
            step("03 parse_doc_batch submit", bool(task_id), f"task_id={task_id}")

            # 04 轮询解析结果
            data = await poll_parse(s, task_id)
            results = data.get("results") or (data.get("result") or {}).get("results") or []
            md_by_file, chars_by_file = {}, {}
            for r_ in results if isinstance(results, list) else []:
                src = r_.get("source_filename") or Path(r_.get("file_path") or r_.get("markdown_path") or "?").name
                md_by_file[src] = r_.get("markdown_path") or ""
                chars_by_file[src] = r_.get("markdown_chars") or len(r_.get("markdown") or "")
            ok3 = len([k for k in md_by_file if k]) >= 3
            step("04 parse poll done", ok3, f"files={list(md_by_file)} chars={chars_by_file}")

            # 05 入库：save_parsed 手动模式逐件存（每件带独立描述，供图书管理员描述层）
            # 返回形状（run1 实测）：{success, savedCount, files:[{id, name, path, ...}]}
            doc_paths = {}
            for img in GOLD["images"]:
                src = img["file"]
                md_path = md_by_file.get(src) or ""
                if not md_path:
                    step(f"05 save {src}", False, "no markdown_path"); continue
                data, _ = await call(s, "kb_doc_save_parsed",
                                     {"parent_id": kb_id, "markdown_path": md_path,
                                      "source_filename": src, "description": img["description"]},
                                     f"05_save_{src[:2]}")
                files = data.get("files") or []
                dp = (files[0].get("path") if files else "") or ""
                doc_paths[src] = dp
                step(f"05 save {src}", data.get("success", False) and bool(dp),
                     f"savedCount={data.get('savedCount')} doc_path={dp}")

            # 06 重建索引（向量 + 图谱）
            data, _ = await call(s, "kb_reindex", {"kb_id": kb_id}, "06_reindex")
            step("06 kb_reindex", data.get("success", False),
                 f"indexed={data.get('total_docs') or data.get('processed') or data.get('total_indexed')}")

            # 07 图书管理员阶梯 L1/L2：目录层 + 书架/文档描述层 + 抽样读正文验证 OCR
            data, _ = await call(s, "kb_list", {"lightweight": True}, "07a_kb_list_catalog")
            ours = [k for k in (data.get("catalog") or [])
                    if KB_NAME in str(k.get("name", ""))]
            step("07a catalog L1", len(ours) == 1, f"found={len(ours)} of {data.get('count', '?')} KBs")
            data, _ = await call(s, "kb_get_documents", {"kb_id": kb_id, "lightweight": True}, "07b_kb_get_documents")
            shelf_docs = data.get("documents") or []
            step("07b shelf L2 descriptions", data.get("count") == 3 or len(shelf_docs) == 3,
                 f"{data.get('count', len(shelf_docs))} docs with descriptions")
            data, _ = await call(s, "kb_doc_read", {"kb_id": kb_id, "doc_path": doc_paths[GOLD["images"][0]["file"]]},
                                 "07c_doc_read_sample")
            body = data.get("content") or ""
            gold0 = GOLD["images"][0]["gold_keywords"]
            hit_kw = [k for k in gold0 if k in body]
            step("07c OCR content check (doc_read)", len(hit_kw) >= 2,
                 f"gold keywords in OCR text: {hit_kw}/{gold0}, body_chars={len(body)}")

            # 08 宽网向量检索 ×3 题（图书管理员 L3 召回）
            vec_hits = {}
            for i, img in enumerate(GOLD["images"]):
                data, _ = await call(s, "kb_search_vector",
                                     {"query": img["query"], "kb_id": kb_id, "top_k": 8}, f"08_vec_q{i+1}")
                hits = data.get("results") or []
                vec_hits[img["file"]] = hits
                top1 = (hits[0] if hits else {}).get("doc_path") or (hits[0] if hits else {}).get("path") or ""
                step(f"08 vector q{i+1} ({img['file'][:2]})",
                     bool(hits) and img["expect_doc"][:2] in str(top1),
                     f"top1={top1 or 'EMPTY'} score={round((hits[0] if hits else {}).get('score', 0) or 0, 4)}")

            # 09 Laya 判卷（证据门，fail-closed）
            for i, img in enumerate(GOLD["images"]):
                docs_arg = json.dumps([{"kb_id": kb_id, "doc_path": doc_paths[im["file"]]}
                                       for im in GOLD["images"] if doc_paths.get(im["file"])], ensure_ascii=False)
                data, _ = await call(s, "kb_laya_judge",
                                     {"query": img["query"], "documents": docs_arg,
                                      "criterion": "auto", "include_text": False}, f"09_judge_q{i+1}")
                survivors = data.get("survivors") or []
                got = sorted({Path(str(sv.get("doc_path", sv) if isinstance(sv, dict) else sv)).name[:2]
                              for sv in survivors})
                step(f"09 laya judge q{i+1}", img["expect_doc"][:2] in got,
                     f"survivors={got} docs_with_yes={data.get('docs_with_yes')}")

            # 10 删除入库文档 ×3
            for i, img in enumerate(GOLD["images"]):
                dp = doc_paths.get(img["file"])
                if not dp:
                    step(f"10 delete {img['file'][:2]}", False, "no doc_path"); continue
                data, _ = await call(s, "kb_doc_delete", {"kb_id": kb_id, "doc_path": dp}, f"10_delete_{img['file'][:2]}")
                step(f"10 delete {img['file'][:2]}", data.get("success", False), str(data.get("message") or "")[:120])

            # 11 空库核验（total==0 才算空库）
            data, _ = await call(s, "kb_get_documents", {"kb_id": kb_id, "lightweight": True}, "11_verify_empty")
            n = data.get("count", -1)
            step("11 verify empty", n == 0, f"count={n}")

            # 12 删库 + 目录核验
            data, _ = await call(s, "kb_delete", {"kb_id": kb_id}, "12_kb_delete")
            step("12 kb_delete", data.get("success", False), str(data)[:120])
            data, _ = await call(s, "kb_list", {"lightweight": True}, "12b_kb_list_after")
            gone = KB_NAME not in json.dumps(data, ensure_ascii=False)
            step("12b verify KB gone from catalog", gone, "catalog clean" if gone else "STILL PRESENT")

    passed = sum(1 for x in REPORT["steps"] if x["ok"])
    REPORT["summary"] = f"{passed}/{len(REPORT['steps'])} PASS"
    (BASE / "lane_a_report.json").write_text(
        json.dumps(REPORT, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n=== Lane A done: {REPORT['summary']} ===")


if __name__ == "__main__":
    asyncio.run(main())
