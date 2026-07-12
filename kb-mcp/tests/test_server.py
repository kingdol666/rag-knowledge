# -*- coding: utf-8 -*-
"""End-to-end test for the decoupled kb-mcp architecture."""
import asyncio
import json
import os
import sys

# 默认 dev 模式（web 6789 / backend 8765）；直接 `uv run python tests/test_server.py`
# 不带 APP_MODE 时避免回退 prod 打到 3000 端口（无服务）致全链路失败。
os.environ.setdefault("APP_MODE", "dev")

import server


async def run_tests():
    results = {}

    def check(name, ok, detail=""):
        results[name] = ok
        print(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}")

    # 1. health_check
    d = json.loads(await server.health_check())
    check("health_check", d.get("all_ok"), f"backend={d['backend']} mineru={d['mineru']} web={d['web']}")

    # 2. kb_list
    d = json.loads(await server.kb_list())
    check("kb_list", d.get("count", 0) > 0, f"{d.get('count')} KBs")

    # 3. kb_create
    d = json.loads(await server.kb_create("Decouple_Test_KB", "Testing decoupled architecture"))
    kb_path = d.get("knowledgeBase", {}).get("path", "")
    check("kb_create", d.get("success"), f"path={kb_path}")

    # 4. kb_update
    d = json.loads(await server.kb_update(kb_path, name="Decouple_Renamed", description="Renamed"))
    check("kb_update", d.get("success"))

    # 5. kb_doc_create
    d = json.loads(await server.kb_doc_create(kb_path, "test-doc", "# Decoupled Test\nVia kb_client.", "Test"))
    doc_path = d.get("document", {}).get("path", "")
    check("kb_doc_create", d.get("success"), f"path={doc_path}")

    # 6. dedup
    d = json.loads(await server.kb_doc_create(kb_path, "test-doc", "# Dup", "Dedup"))
    dedup_name = d.get("document", {}).get("name", "")
    dedup_path = d.get("document", {}).get("path", "")
    check("kb_doc_create_dedup", "(1)" in dedup_name, f"name={dedup_name}")

    # 7. kb_doc_read
    d = json.loads(await server.kb_doc_read(doc_path))
    check("kb_doc_read", len(d.get("content", "")) > 0, f"lines={d.get('totalLines')}")

    # 8. kb_doc_update_content
    d = json.loads(await server.kb_doc_update_content(kb_path, doc_path, "# Updated\nNew content."))
    check("kb_doc_update_content", d.get("success"))

    # 9. kb_doc_update_meta
    d = json.loads(await server.kb_doc_update_meta(kb_path, doc_path, description="Meta updated"))
    check("kb_doc_update_meta", d.get("success"))

    # 10. kb_get_documents
    d = json.loads(await server.kb_get_documents(kb_path))
    check("kb_get_documents", d.get("count", 0) >= 2, f"count={d.get('count')}")

    # 11. kb_search
    d = json.loads(await server.kb_search("test", 5))
    check("kb_search", d.get("count", 0) >= 0, f"hits={d.get('count')}")

    # 12. kb_doc_batch_delete
    d = json.loads(await server.kb_doc_batch_delete(kb_path, [dedup_path]))
    check("kb_doc_batch_delete", d.get("successful", 0) >= 1)

    # 13. fs_get_tree
    d = json.loads(await server.fs_get_tree())
    check("fs_get_tree", isinstance(d, list) and len(d) > 0, f"{len(d)} roots")

    # 14. fs_get_count
    d = json.loads(await server.fs_get_count())
    check("fs_get_count", d.get("total", 0) > 0, f"folders={d.get('folders')} files={d.get('files')}")

    # prompts_* tools were removed (FastMCP no longer exposes prompts in server.py).

    # 17. backend_status
    d = json.loads(await server.backend_status())
    bh = d.get("backend_health", {}).get("status")
    check("backend_status", bh == "healthy", f"health={bh}")

    # 18-19. cleanup
    d = json.loads(await server.kb_doc_delete(kb_path, doc_path))
    check("kb_doc_delete", d.get("success"))
    d = json.loads(await server.kb_delete(kb_path))
    check("kb_delete", d.get("success"))

    # Summary
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"\n=== {passed}/{total} PASSED ===")
    for name, ok in results.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")

    await server._client().aclose()
    sys.exit(0 if passed == total else 1)


asyncio.run(run_tests())
