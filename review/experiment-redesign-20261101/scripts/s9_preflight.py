# -*- coding: utf-8 -*-
"""优化轮预检（s9）：kb_list 十库核对 + 判卷引擎 liveness（参考模式 & inline 模式）。

- 校验 kb_list 中 MD语料-* 恰好 10 个（评测范围），A3无描述-* 孪生/生产库仅记录不使用。
- 判卷 liveness：临时 KB 两篇微文档 → kb_laya_judge（参考模式 ref+inline 模式各一次）
  → real_engine 必须 true → 删除临时 KB。
用法: uv run --no-sync python s9_preflight.py   （kb-mcp venv 或装有 mcp 包的解释器）
"""
import asyncio
import json
import sys
import time
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

BASE = Path(__file__).resolve().parent
KBMCP_DIR = BASE.parents[2] / "kb-mcp"
STDIO_CMD = ["uv", "run", "--no-sync", "--directory", str(KBMCP_DIR), "python", str(KBMCP_DIR / "server.py")]


def cj(res):
    try:
        return json.loads(res.content[0].text)
    except Exception:
        return {"_raw": [getattr(c, "text", str(c)) for c in res.content]}


async def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ts = time.strftime("%H%M%S")
    async with stdio_client(StdioServerParameters(command=STDIO_CMD[0], args=STDIO_CMD[1:])) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            d = cj(await s.call_tool("kb_list", {"lightweight": True}))
            catalog = d.get("catalog") or []
            md_u = {}
            for k in catalog:
                if str(k.get("name", "")).startswith("MD语料-"):
                    md_u.setdefault(k["kb_id"], k.get("name"))
            a3 = [k for k in catalog if str(k.get("name", "")).startswith("A3无描述-")]
            print(f"kb_list: total={len(catalog)} MD语料-*unique={len(md_u)} A3无描述-*rows={len(a3)}")
            for kid, name in sorted(md_u.items(), key=lambda x: str(x[1])):
                print(f"  MD {kid}  {name}")
            ok = len(md_u) == 10
            print(f"TEN_MD_KBS={'OK' if ok else 'FAIL'}")

            # throwaway KB for judge liveness
            d = cj(await s.call_tool("kb_create", {
                "name": f"judge-liveness-{ts}", "description": "判卷 liveness 探针，用完即删"}))
            kb_id = (d.get("knowledgeBase") or {}).get("id") or d.get("id") or ""
            c1 = cj(await s.call_tool("kb_doc_create", {
                "kb_id": kb_id, "name": "probe-a.md",
                "content": "# 探针A\n\n个人信息保护法规定处理个人信息应当具有明确、合理的目的。",
                "description": "liveness 探针 A"}))
            c2 = cj(await s.call_tool("kb_doc_create", {
                "kb_id": kb_id, "name": "probe-b.md",
                "content": "# 探针B\n\n数据安全法由国家数据安全工作协调机制统筹协调有关部门制定重要数据目录。",
                "description": "liveness 探针 B"}))
            p1 = ((c1.get("files") or [{}])[0].get("path") or "probe-a.md")
            p2 = ((c2.get("files") or [{}])[0].get("path") or "probe-b.md")
            await s.call_tool("kb_index_document", {"kb_id": kb_id, "doc_path": p1})
            await s.call_tool("kb_index_document", {"kb_id": kb_id, "doc_path": p2})
            await asyncio.sleep(3)

            # 1) reference mode（server 自取——liveness 门禁同旧轮）
            jd = cj(await s.call_tool("kb_laya_judge", {
                "query": "重要数据目录由谁制定？",
                "documents": json.dumps([{"kb_id": kb_id, "doc_path": p1},
                                         {"kb_id": kb_id, "doc_path": p2}], ensure_ascii=False),
                "criterion": "auto", "include_text": False}))
            print(f"reference_mode: real_engine={jd.get('real_engine')} "
                  f"survivors={jd.get('survivor_count')} status={jd.get('status')} "
                  f"errors={jd.get('errors')}")
            # 2) inline content mode（A0f/A0h/PD 采用的方案）
            jd2 = cj(await s.call_tool("kb_laya_judge", {
                "query": "重要数据目录由谁制定？",
                "documents": json.dumps([
                    {"kb_id": kb_id, "doc_path": p1,
                     "content": "# 探针A\n\n个人信息保护法规定处理个人信息应当具有明确、合理的目的。"},
                    {"kb_id": kb_id, "doc_path": p2,
                     "content": "# 探针B\n\n数据安全法由国家数据安全工作协调机制统筹协调有关部门制定重要数据目录。"}],
                    ensure_ascii=False),
                "criterion": "auto", "include_text": False,
                "max_evidence_chars": 250000}))
            print(f"inline_mode: real_engine={jd2.get('real_engine')} "
                  f"survivors={jd2.get('survivor_count')} status={jd2.get('status')} "
                  f"pack_chars={len(jd2.get('evidence_pack') or '')} errors={jd2.get('errors')}")
            dl = cj(await s.call_tool("kb_delete", {"kb_id": kb_id}))
            print(f"throwaway deleted: {dl.get('success', dl)}")
            verdict = {"ten_md_kbs": ok,
                       "judge_reference_real_engine": jd.get("real_engine"),
                       "judge_inline_real_engine": jd2.get("real_engine")}
            print("PREFLIGHT_" + ("PASS" if (ok and jd.get("real_engine") and jd2.get("real_engine")) else "FAIL"))
            print(json.dumps(verdict, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
