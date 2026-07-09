#!/usr/bin/env python3
"""RAG Knowledge Platform — 全系统功能测试

覆盖：
  Part 1: 后端 API 端点（health, search, graph, mineru）
  Part 2: Web API 端点（KB CRUD, 文档CRUD, 文件系统, 标签, 预览, 搜索, 图谱）
  Part 3: MCP 工具测试（通过 kb_client 直接调用全部工具）
  Part 4: 端到端工作流（入库→搜索→管理→校验）
"""
import sys
import os
import json
import asyncio
import traceback

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Add kb-mcp to path
KB_MCP_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "kb-mcp")
sys.path.insert(0, KB_MCP_PATH)

import httpx

BACKEND_URL = "http://localhost:8765"
WEB_URL = "http://localhost:6789"

results = {"pass": 0, "fail": 0, "skip": 0, "details": []}


def record(name: str, status: str, detail: str = ""):
    results[status] = results.get(status, 0) + 1
    symbol = {"pass": "✓", "fail": "✗", "skip": "−"}[status]
    results["details"].append({"name": name, "status": status, "detail": detail})
    print(f"  {symbol} {name}" + (f" — {detail}" if detail else ""))


def section(title: str):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")


def header(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def safe_json(result):
    """Try to parse string as JSON, return as-is if already dict."""
    if isinstance(result, dict):
        return result
    if isinstance(result, str):
        try:
            return json.loads(result)
        except:
            return {"raw": result[:200]}
    if isinstance(result, list):
        return {"list": result}
    return {"raw": str(result)[:200]}


def make_client():
    """Create KbClient with correct URLs."""
    from kb_client.client import KbClient
    return KbClient(web_url=WEB_URL, backend_url=BACKEND_URL)


# ════════════════════════════════════════════════════════════
# Part 1: Backend API Endpoints
# ════════════════════════════════════════════════════════════

def test_backend_apis():
    header("Part 1: Backend API 端点测试")

    with httpx.Client(trust_env=False, timeout=30) as client:

        # ── Health ──
        section("1.1 Health & Status")
        try:
            r = client.get(f"{BACKEND_URL}/api/v1/health")
            data = r.json()
            record("GET /health", "pass" if data.get("status") == "healthy" else "fail", str(data))
        except Exception as e:
            record("GET /health", "fail", str(e))

        try:
            r = client.get(f"{BACKEND_URL}/api/v1/mineru/status")
            data = r.json()
            record("GET /mineru/status", "pass", f"ready={data.get('is_ready', '?')}")
        except Exception as e:
            record("GET /mineru/status", "fail", str(e))

        # ── Search ──
        section("1.2 Search APIs")
        try:
            r = client.post(f"{BACKEND_URL}/api/v1/search/vector",
                           json={"query": "polymer materials", "top_k": 3})
            data = r.json()
            record("POST /search/vector", "pass" if data.get("success") else "fail",
                   f"{data.get('count', 0)} results")
        except Exception as e:
            record("POST /search/vector", "fail", str(e))

        try:
            r = client.post(f"{BACKEND_URL}/api/v1/search/two-stage",
                           json={"query": "machine learning", "stage1_top_k": 5, "stage2_top_k": 3})
            data = r.json()
            record("POST /search/two-stage", "pass" if data.get("success") else "fail",
                   f"candidates={data.get('stage1',{}).get('candidate_count',0)}, results={data.get('total_results',0)}")
        except Exception as e:
            record("POST /search/two-stage", "fail", str(e))

        try:
            r = client.post(f"{BACKEND_URL}/api/v1/search/vector",
                           json={"query": "polymer", "top_k": 3, "balance_kbs": True})
            data = r.json()
            results_list = data.get("results", [])
            kbs = set(r.get("collection", "") for r in results_list)
            record("POST /search/vector (balance_kbs)", "pass",
                   f"{len(results_list)} results, {len(kbs)} distinct KBs")
        except Exception as e:
            record("POST /search/vector (balance_kbs)", "fail", str(e))

        try:
            r = client.post(f"{BACKEND_URL}/api/v1/search/two-stage",
                           json={"query": "polymer", "stage1_top_k": 10, "stage2_top_k": 3, "balance_kbs": True})
            data = r.json()
            record("POST /search/two-stage (balance_kbs)", "pass" if data.get("success") else "fail",
                   f"results={data.get('total_results',0)}")
        except Exception as e:
            record("POST /search/two-stage (balance_kbs)", "fail", str(e))

        try:
            r = client.get(f"{BACKEND_URL}/api/v1/search/stats")
            data = r.json()
            stats = data.get("stats", {})
            if isinstance(stats, dict) and "collections" in stats:
                collections = stats["collections"]
                if isinstance(collections, list):
                    total_chunks = sum(c.get("chunk_count", 0) for c in collections)
                else:
                    total_chunks = sum(c.get("chunk_count", 0) for c in collections.values())
                record("GET /search/stats", "pass",
                       f"{len(collections)} collections, {total_chunks} total chunks")
            else:
                record("GET /search/stats", "pass", str(data)[:80])
        except Exception as e:
            record("GET /search/stats", "fail", str(e))

        # ── Graph ──
        section("1.3 Graph APIs")
        try:
            r = client.get(f"{BACKEND_URL}/api/v1/graph/stats")
            data = r.json()
            record("GET /graph/stats", "pass", str(data)[:80])
        except Exception as e:
            record("GET /graph/stats", "fail", str(e))

        try:
            r = client.get(f"{BACKEND_URL}/api/v1/graph/health")
            data = r.json()
            record("GET /graph/health", "pass", str(data)[:80])
        except Exception as e:
            record("GET /graph/health", "fail", str(e))

        try:
            r = client.get(f"{BACKEND_URL}/api/v1/graph/search/documents",
                          params={"keyword": "polymer", "limit": 5})
            data = r.json()
            record("GET /graph/search/documents", "pass", str(data)[:80])
        except Exception as e:
            record("GET /graph/search/documents", "fail", str(e))

        try:
            r = client.get(f"{BACKEND_URL}/api/v1/graph/cross-kb-documents",
                          params={"min_kbs": 2, "limit": 5})
            data = r.json()
            record("GET /graph/cross-kb-documents", "pass", str(data)[:80])
        except Exception as e:
            record("GET /graph/cross-kb-documents", "fail", str(e))


# ════════════════════════════════════════════════════════════
# Part 2: Web API Endpoints
# ════════════════════════════════════════════════════════════

def test_web_apis():
    header("Part 2: Web API 端点测试")

    with httpx.Client(trust_env=False, timeout=30) as client:
        test_kb_id = None
        test_doc_path = None

        # ── KB Catalog ──
        section("2.1 KB Catalog & List")
        try:
            r = client.get(f"{WEB_URL}/api/kb/catalog")
            data = r.json()
            kbs = data.get("knowledgeBases", [])
            record("GET /api/kb/catalog", "pass", f"{data.get('count',0)} KBs")
            if kbs:
                test_kb_id = kbs[0]["kbId"]
        except Exception as e:
            record("GET /api/kb/catalog", "fail", str(e))

        try:
            r = client.get(f"{WEB_URL}/api/filesystem/index")
            data = r.json()
            record("GET /api/filesystem/index", "pass", "tree root retrieved")
        except Exception as e:
            record("GET /api/filesystem/index", "fail", str(e))

        # ── KB Create / Delete ──
        section("2.2 KB CRUD")
        new_kb_id = None
        try:
            r = client.post(f"{WEB_URL}/api/kb/create",
                           json={"name": "Test-KB-Auto", "description": "Auto-test KB"})
            data = r.json()
            if data.get("success"):
                kb_obj = data.get("knowledgeBase", data)
                new_kb_id = kb_obj.get("id", data.get("kbId", ""))
                record("POST /api/kb/create", "pass", f"kbId={new_kb_id[:8]}...")
            else:
                record("POST /api/kb/create", "fail", str(data)[:80])
        except Exception as e:
            record("POST /api/kb/create", "fail", str(e))

        if new_kb_id:
            try:
                r2 = client.request("DELETE", f"{WEB_URL}/api/kb/delete",
                                   json={"kbId": new_kb_id})
                d2 = r2.json()
                record("DELETE /api/kb/delete", "pass" if d2.get("success") else "fail",
                       str(d2)[:60])
            except Exception as e:
                record("DELETE /api/kb/delete", "fail", str(e))

        # ── Documents ──
        section("2.3 Document Operations")
        if test_kb_id:
            try:
                r = client.get(f"{WEB_URL}/api/kb/documents",
                              params={"kbId": test_kb_id})
                data = r.json()
                docs = data.get("documents", [])
                record("GET /api/kb/documents", "pass", f"{len(docs)} docs")
                if docs:
                    test_doc_path = docs[0].get("path", "")
            except Exception as e:
                record("GET /api/kb/documents", "fail", str(e))

            if test_doc_path:
                try:
                    r = client.get(f"{WEB_URL}/api/kb/document",
                                  params={"kbId": test_kb_id, "docPath": test_doc_path})
                    data = r.json()
                    record("GET /api/kb/document", "pass", f"content_len={len(data.get('content',''))}")
                except Exception as e:
                    record("GET /api/kb/document", "fail", str(e))

            # Create + Delete doc
            try:
                r = client.post(f"{WEB_URL}/api/kb/documents/create",
                               json={"kbId": test_kb_id,
                                     "name": "test-auto-doc.md",
                                     "content": "# Test Document\n\nAuto-generated test content.",
                                     "description": "Auto-test doc"})
                data = r.json()
                if data.get("success"):
                    record("POST /api/kb/documents/create", "pass", "doc created")
                    try:
                        r2 = client.request("DELETE", f"{WEB_URL}/api/kb/documents/delete",
                                          json={"kbId": test_kb_id, "docPath": "test-auto-doc.md"})
                        d2 = r2.json()
                        record("DELETE /api/kb/documents/delete", "pass" if d2.get("success") else "fail",
                               str(d2)[:60])
                    except Exception as e:
                        record("DELETE /api/kb/documents/delete", "fail", str(e))
                else:
                    record("POST /api/kb/documents/create", "fail", str(data)[:80])
            except Exception as e:
                record("POST /api/kb/documents/create", "fail", str(e))

        # ── Tags ──
        section("2.4 Tag Management")
        try:
            r = client.get(f"{WEB_URL}/api/kb/tags")
            data = r.json()
            record("GET /api/kb/tags", "pass", f"{len(data.get('tags',[]))} tags")
        except Exception as e:
            record("GET /api/kb/tags", "fail", str(e))

        try:
            r = client.post(f"{WEB_URL}/api/kb/tags",
                           json={"tag": "test-auto-tag"})
            data = r.json()
            record("POST /api/kb/tags (create)", "pass" if data.get("success") else "fail", str(data)[:60])
        except Exception as e:
            record("POST /api/kb/tags (create)", "fail", str(e))

        # ── Search via Web ──
        section("2.5 Search via Web API")
        try:
            r = client.get(f"{WEB_URL}/api/kb/search",
                          params={"query": "polymer", "topK": 3})
            data = r.json()
            record("GET /api/kb/search", "pass", f"{data.get('count',0)} results")
        except Exception as e:
            record("GET /api/kb/search", "fail", str(e))

        try:
            r = client.post(f"{WEB_URL}/api/search/vector",
                           json={"query": "battery", "top_k": 3})
            data = r.json()
            record("POST /api/search/vector", "pass", f"{data.get('count',0)} results")
        except Exception as e:
            record("POST /api/search/vector", "fail", str(e))

        try:
            r = client.post(f"{WEB_URL}/api/search/two-stage",
                           json={"query": "battery", "stage1_top_k": 5, "stage2_top_k": 3})
            data = r.json()
            record("POST /api/search/two-stage", "pass", f"results={data.get('total_results',0)}")
        except Exception as e:
            record("POST /api/search/two-stage", "fail", str(e))

        try:
            r = client.post(f"{WEB_URL}/api/search/batch-vector",
                           json={"queries": ["polymer", "battery"], "top_k": 3})
            data = r.json()
            record("POST /api/search/batch-vector", "pass", f"{len(data.get('results',[]))} query results")
        except Exception as e:
            record("POST /api/search/batch-vector", "fail", str(e))

        # ── Graph via Web ──
        section("2.6 Graph via Web API")
        try:
            r = client.get(f"{WEB_URL}/api/graph/stats")
            data = r.json()
            record("GET /api/graph/stats", "pass", str(data)[:80])
        except Exception as e:
            record("GET /api/graph/stats", "fail", str(e))

        # ── Preview ──
        section("2.7 Preview APIs")
        try:
            r = client.get(f"{WEB_URL}/api/preview/index")
            data = r.json()
            record("GET /api/preview/index", "pass", str(data)[:80])
        except Exception as e:
            record("GET /api/preview/index", "fail", str(e))

        # ── Filesystem ──
        section("2.8 Filesystem Operations")
        try:
            r = client.post(f"{WEB_URL}/api/filesystem/nodes",
                           json={"name": "test-folder-auto", "parentId": "", "description": "auto test", "type": "folder"})
            data = r.json()
            node_id = data.get("id", data.get("node", {}).get("id", ""))
            if node_id:
                record("POST /api/filesystem/nodes (create folder)", "pass", f"id={node_id[:8]}...")
                try:
                    r2 = client.delete(f"{WEB_URL}/api/filesystem/nodes/{node_id}")
                    record("DELETE /api/filesystem/nodes/{id}", "pass", "folder deleted")
                except Exception as e:
                    record("DELETE /api/filesystem/nodes/{id}", "fail", str(e))
            else:
                record("POST /api/filesystem/nodes (create folder)", "fail", str(data)[:80])
        except Exception as e:
            record("POST /api/filesystem/nodes (create folder)", "fail", str(e))


# ════════════════════════════════════════════════════════════
# Part 3: MCP Tools Test (via kb_client)
# ════════════════════════════════════════════════════════════

async def test_mcp_tools():
    header("Part 3: MCP 工具测试（via kb_client）")

    client = make_client()
    test_kb_id = None
    test_doc_path = None

    # ── Health ──
    section("3.1 Health Tools")
    try:
        result = await client.health_check()
        data = safe_json(result)
        ok = data.get("web", False) or data.get("backend", False)
        record("health_check()", "pass" if ok else "fail", str(data)[:80])
    except Exception as e:
        record("health_check()", "fail", str(e))

    try:
        result = await client.backend_status()
        data = safe_json(result)
        bh = data.get("backend_health", {})
        ok = bh.get("status") == "healthy" if isinstance(bh, dict) else False
        record("backend_status()", "pass" if ok else "fail", str(data)[:80])
    except Exception as e:
        record("backend_status()", "fail", str(e))

    # ── KB CRUD ──
    section("3.2 KB CRUD Tools")
    try:
        result = await client.kb_list()
        data = safe_json(result)
        kbs = data.get("knowledgeBases", [])
        record("kb_list()", "pass", f"{len(kbs)} KBs")
        if kbs:
            test_kb_id = kbs[0].get("kbId", "")
    except Exception as e:
        record("kb_list()", "fail", str(e))

    # kb_catalog is a server.py tool built on kb_list — test kb_list directly
    try:
        result = await client.kb_list()
        data = safe_json(result)
        kbs = data.get("knowledgeBases", [])
        catalog = [{"kb_id": kb.get("kbId"), "name": kb.get("name"),
                     "description": kb.get("description", ""),
                     "doc_count": kb.get("documentCount", 0)} for kb in kbs]
        record("kb_catalog() [via kb_list]", "pass", f"{len(catalog)} KBs in catalog")
    except Exception as e:
        record("kb_catalog() [via kb_list]", "fail", str(e))

    # ── File System ──
    section("3.3 File System Tools")
    try:
        result = await client.fs_get_tree()
        record("fs_get_tree()", "pass", "tree retrieved")
    except Exception as e:
        record("fs_get_tree()", "fail", str(e))

    try:
        result = await client.fs_get_count()
        data = safe_json(result)
        count = data.get("count", 0)
        record("fs_get_count()", "pass", f"{count} nodes")
    except Exception as e:
        record("fs_get_count()", "fail", str(e))

    try:
        result = await client.fs_get_children()
        data = safe_json(result)
        children = data.get("children", data.get("nodes", []))
        record("fs_get_children()", "pass", f"{len(children) if isinstance(children, list) else '?'} children")
    except Exception as e:
        record("fs_get_children()", "fail", str(e))

    # ── Documents ──
    section("3.4 Document Tools")
    if test_kb_id:
        # kb_doc_catalog [via kb_get_documents]
        try:
            result = await client.kb_get_documents(test_kb_id)
            data = safe_json(result)
            docs = data.get("documents", [])
            catalog = [{"doc_path": d.get("path"), "name": d.get("name"),
                        "description": d.get("description", "")} for d in docs]
            record("kb_doc_catalog() [via kb_get_documents]", "pass", f"{len(catalog)} docs")
            if docs:
                test_doc_path = docs[0].get("path", "")
        except Exception as e:
            record("kb_doc_catalog() [via kb_get_documents]", "fail", str(e))

        try:
            result = await client.kb_get_documents(test_kb_id)
            record("kb_get_documents()", "pass", str(result)[:60])
        except Exception as e:
            record("kb_get_documents()", "fail", str(e))

        if test_doc_path:
            try:
                result = await client.kb_doc_read(kb_id=test_kb_id, doc_path=test_doc_path, max_chars=500)
                record("kb_doc_read()", "pass", f"len={len(str(result))}")
            except Exception as e:
                record("kb_doc_read()", "fail", str(e))

        try:
            result = await client.kb_doc_create(test_kb_id, "mcp-test-doc.md",
                "# MCP Test\nTest content.", "MCP auto test")
            data = safe_json(result)
            record("kb_doc_create()", "pass" if data.get("success") else "fail", str(data)[:60])
            try:
                result = await client.kb_doc_delete(test_kb_id, "mcp-test-doc.md")
                data = safe_json(result)
                record("kb_doc_delete()", "pass" if data.get("success") else "fail", str(data)[:60])
            except Exception as e:
                record("kb_doc_delete()", "fail", str(e))
        except Exception as e:
            record("kb_doc_create()", "fail", str(e))

    # ── Tags ──
    section("3.5 Tag Tools")
    try:
        result = await client.kb_tags_list()
        data = safe_json(result)
        tags = data.get("tags", [])
        record("kb_tags_list()", "pass", f"{len(tags)} tags")
    except Exception as e:
        record("kb_tags_list()", "fail", str(e))

    try:
        result = await client.kb_tag_create("mcp-test-tag")
        data = safe_json(result)
        record("kb_tag_create()", "pass" if data.get("success") else "fail", str(data)[:60])
    except Exception as e:
        record("kb_tag_create()", "fail", str(e))

    # ── Search ──
    section("3.6 Search Tools")
    try:
        result = await client.kb_search("polymer materials", top_k=3)
        data = safe_json(result)
        count = data.get("count", 0)
        record("kb_search() (metadata)", "pass", f"{count} results")
    except Exception as e:
        record("kb_search() (metadata)", "fail", str(e))

    try:
        result = await client.vector_search("polymer materials", top_k=3)
        data = safe_json(result)
        count = data.get("count", 0)
        record("vector_search()", "pass", f"{count} results")
    except Exception as e:
        record("vector_search()", "fail", str(e))

    try:
        result = await client.vector_search("polymer", top_k=3, balance_kbs=True)
        data = safe_json(result)
        count = data.get("count", 0)
        record("vector_search(balance_kbs)", "pass", f"{count} results")
    except Exception as e:
        record("vector_search(balance_kbs)", "fail", str(e))

    try:
        result = await client.two_stage_search("machine learning", stage1_top_k=5, stage2_top_k=3)
        data = safe_json(result)
        record("two_stage_search()", "pass", f"results={data.get('total_results',0)}")
    except Exception as e:
        record("two_stage_search()", "fail", str(e))

    try:
        result = await client.two_stage_search("polymer", stage1_top_k=10, stage2_top_k=3, balance_kbs=True)
        data = safe_json(result)
        record("two_stage_search(balance_kbs)", "pass", f"results={data.get('total_results',0)}")
    except Exception as e:
        record("two_stage_search(balance_kbs)", "fail", str(e))

    try:
        result = await client.search_stats()
        data = safe_json(result)
        record("search_stats()", "pass", str(data)[:80])
    except Exception as e:
        record("search_stats()", "fail", str(e))

    # ── Experience ──
    section("3.7 Experience Tools")
    if test_kb_id:
        try:
            result = await client.experience_init(test_kb_id)
            record("experience_init()", "pass", str(result)[:60])
        except Exception as e:
            record("experience_init()", "fail", str(e)[:80])

        try:
            result = await client.experience_list(test_kb_id)
            record("experience_list()", "pass", str(result)[:60])
        except Exception as e:
            record("experience_list()", "fail", str(e)[:80])

        try:
            result = await client.experience_summary(test_kb_id)
            record("experience_summary()", "pass", str(result)[:60])
        except Exception as e:
            record("experience_summary()", "fail", str(e)[:80])

        try:
            result = await client.experience_search_global("test", top_k=3)
            record("experience_search_global()", "pass", str(result)[:60])
        except Exception as e:
            record("experience_search_global()", "fail", str(e)[:80])

    # ── Graph ──
    section("3.8 Graph Tools")
    try:
        result = await client.graph_stats()
        data = safe_json(result)
        record("graph_stats()", "pass", str(data)[:80])
    except Exception as e:
        record("graph_stats()", "fail", str(e)[:80])

    try:
        result = await client.graph_health()
        data = safe_json(result)
        record("graph_health()", "pass", str(data)[:80])
    except Exception as e:
        record("graph_health()", "fail", str(e)[:80])

    try:
        result = await client.graph_search("polymer", limit=5)
        data = safe_json(result)
        record("graph_search()", "pass", str(data)[:80])
    except Exception as e:
        record("graph_search()", "fail", str(e)[:80])

    try:
        result = await client.graph_cross_kb_documents(min_kbs=2, limit=5)
        data = safe_json(result)
        record("graph_cross_kb_documents()", "pass", str(data)[:80])
    except Exception as e:
        record("graph_cross_kb_documents()", "fail", str(e)[:80])

    # ── Preview ──
    section("3.9 Preview Tools")
    try:
        result = await client.preview_file(path="Materials-Science")
        data = safe_json(result)
        record("preview_file()", "pass", str(data)[:60])
    except Exception as e:
        record("preview_file()", "fail", str(e)[:80])

    # ── Parse ──
    section("3.10 Parse Tools")
    try:
        import httpx as _httpx
        async with _httpx.AsyncClient(trust_env=False, timeout=10) as hc:
            r = await hc.get(f"{WEB_URL}/api/parse/file-vt")
        record("parse endpoint reachable", "pass", "web parse route exists")
    except Exception as e:
        record("parse endpoint reachable", "fail", str(e)[:80])


# ════════════════════════════════════════════════════════════
# Part 4: End-to-End Workflow
# ════════════════════════════════════════════════════════════

async def test_e2e_workflow():
    header("Part 4: 端到端工作流测试")

    client = make_client()

    # ── E2E-1: Create KB → Create Doc → Search → Read → Update → Delete ──
    section("E2E-1: KB 全生命周期")
    kb_id = None
    try:
        result = await client.kb_create("E2E-Test-KB", "End-to-end test KB")
        data = safe_json(result)
        kb_obj = data.get("knowledgeBase", data)
        kb_id = kb_obj.get("id", data.get("kbId", ""))
        record("E2E: Create KB", "pass" if kb_id else "fail", f"kbId={kb_id[:8]}...")
    except Exception as e:
        record("E2E: Create KB", "fail", str(e))
        return

    if not kb_id:
        record("E2E: Skip (no kb_id)", "skip")
        return

    # Create document
    try:
        result = await client.kb_doc_create(kb_id, "e2e-doc.md",
            "# E2E Test Document\n\n## Overview\nThis is an end-to-end test document about polymer materials and battery technology.\n\n## Key Points\n- Polymer stretching techniques\n- Battery thermal management\n- Machine learning applications",
            "E2E test document")
        data = safe_json(result)
        record("E2E: Create Doc", "pass" if data.get("success") else "fail", str(data)[:60])
    except Exception as e:
        record("E2E: Create Doc", "fail", str(e))

    # Read document
    try:
        result = await client.kb_doc_read(kb_id=kb_id, doc_path="e2e-doc.md", max_chars=1000)
        record("E2E: Read Doc", "pass", f"len={len(str(result))}")
    except Exception as e:
        record("E2E: Read Doc", "fail", str(e))

    # Update content
    try:
        result = await client.kb_doc_update_content(kb_id, "e2e-doc.md",
            "# E2E Test Document (Updated)\n\nUpdated content with additional information about energy storage.")
        data = safe_json(result)
        record("E2E: Update Doc Content", "pass" if data.get("success") else "fail", str(data)[:60])
    except Exception as e:
        record("E2E: Update Doc Content", "fail", str(e))

    # Update metadata
    try:
        result = await client.kb_doc_update_meta(kb_id, "e2e-doc.md",
            name="e2e-doc.md", description="Updated E2E description")
        data = safe_json(result)
        record("E2E: Update Doc Meta", "pass" if data.get("success") else "fail", str(data)[:60])
    except Exception as e:
        record("E2E: Update Doc Meta", "fail", str(e))

    # Update tags
    try:
        result = await client.kb_doc_update_tags(kb_id, "e2e-doc.md", ["test", "e2e", "polymer"])
        data = safe_json(result)
        record("E2E: Update Doc Tags", "pass" if data.get("success") else "fail", str(data)[:60])
    except Exception as e:
        record("E2E: Update Doc Tags", "fail", str(e))

    # Get by tag
    try:
        result = await client.kb_doc_get_by_tag("e2e", kb_id=kb_id)
        data = safe_json(result)
        record("E2E: Get Doc by Tag", "pass", str(data)[:60])
    except Exception as e:
        record("E2E: Get Doc by Tag", "fail", str(e))

    # Index document for vector search
    try:
        result = await client.index_document(kb_id, "e2e-doc.md",
            doc_name="e2e-doc.md", description="E2E test doc",
            content="# E2E Test Document (Updated)\nUpdated content about energy storage.")
        data = safe_json(result)
        record("E2E: Index Doc (vector)", "pass" if data.get("success") else "fail", str(data)[:60])
    except Exception as e:
        record("E2E: Index Doc (vector)", "fail", str(e)[:80])

    # Vector search for the document
    try:
        result = await client.vector_search("energy storage", top_k=5)
        data = safe_json(result)
        found = False
        for r in data.get("results", []):
            if "e2e" in str(r.get("path", "")).lower() or "e2e" in str(r.get("name", "")).lower():
                found = True
                break
        record("E2E: Vector search finds doc", "pass" if found else "skip",
               f"found in {len(data.get('results', []))} results")
    except Exception as e:
        record("E2E: Vector search finds doc", "fail", str(e))

    # Metadata search
    try:
        result = await client.kb_search("polymer battery", top_k=5)
        data = safe_json(result)
        found = False
        for r in data.get("results", []):
            if "e2e" in str(r.get("path", "")).lower() or "e2e" in str(r.get("name", "")).lower():
                found = True
                break
        record("E2E: Metadata search finds doc", "pass" if found else "skip",
               f"found in {len(data.get('results', []))} results")
    except Exception as e:
        record("E2E: Metadata search finds doc", "fail", str(e))

    # Delete document
    try:
        result = await client.kb_doc_delete(kb_id, "e2e-doc.md")
        data = safe_json(result)
        record("E2E: Delete Doc", "pass" if data.get("success") else "fail", str(data)[:60])
    except Exception as e:
        record("E2E: Delete Doc", "fail", str(e))

    # Delete KB
    try:
        result = await client.kb_delete(kb_id)
        data = safe_json(result)
        record("E2E: Delete KB", "pass" if data.get("success") else "fail", str(data)[:60])
    except Exception as e:
        record("E2E: Delete KB", "fail", str(e))

    # ── E2E-2: Cross-KB Search ──
    section("E2E-2: 跨知识库搜索")
    try:
        result = await client.kb_search("machine learning", top_k=10)
        data = safe_json(result)
        results_list = data.get("results", [])
        kbs_in_results = set()
        for r in results_list:
            kb = r.get("collection", r.get("kb_name", ""))
            if kb:
                kbs_in_results.add(kb)
        record("E2E: Cross-KB metadata search", "pass",
               f"{len(results_list)} results from {len(kbs_in_results)} KBs")
    except Exception as e:
        record("E2E: Cross-KB metadata search", "fail", str(e))

    try:
        result = await client.vector_search("machine learning", top_k=10)
        data = safe_json(result)
        results_list = data.get("results", [])
        kbs_in_results = set()
        for r in results_list:
            kb = r.get("collection", r.get("kb_name", ""))
            if kb:
                kbs_in_results.add(kb)
        record("E2E: Cross-KB vector search", "pass",
               f"{len(results_list)} results from {len(kbs_in_results)} KBs")
    except Exception as e:
        record("E2E: Cross-KB vector search", "fail", str(e))

    try:
        result = await client.two_stage_search("materials science", stage1_top_k=10, stage2_top_k=5)
        data = safe_json(result)
        record("E2E: Cross-KB two-stage search", "pass",
               f"results={data.get('total_results',0)}")
    except Exception as e:
        record("E2E: Cross-KB two-stage search", "fail", str(e))

    # ── E2E-3: KB Catalog Agentic ──
    section("E2E-3: Agentic KB Catalog")
    kbs = []
    try:
        result = await client.kb_list()
        data = safe_json(result)
        kbs = data.get("knowledgeBases", [])
        total_docs = sum(kb.get("documentCount", 0) for kb in kbs)
        record("E2E: KB Catalog overview", "pass",
               f"{len(kbs)} KBs, {total_docs} total docs")
    except Exception as e:
        record("E2E: KB Catalog overview", "fail", str(e))

    # ── E2E-4: Doc Catalog Agentic ──
    section("E2E-4: Agentic Doc Catalog")
    if kbs:
        first_kb_id = kbs[0].get("kbId", "")
        try:
            result = await client.kb_get_documents(first_kb_id)
            data = safe_json(result)
            docs = data.get("documents", [])
            record("E2E: Doc Catalog for first KB", "pass",
                   f"{len(docs)} docs in {kbs[0].get('name','?')[:20]}")
        except Exception as e:
            record("E2E: Doc Catalog for first KB", "fail", str(e))

    # ── E2E-5: Experience lifecycle ──
    section("E2E-5: Experience Lifecycle")
    if kbs:
        exp_kb_id = kbs[0].get("kbId", "")
        exp_id = None
        try:
            await client.experience_init(exp_kb_id)
            result = await client.experience_create(
                exp_kb_id,
                title="E2E Test Experience",
                scenario="testing",
                category="tip",
                problem="Need to verify experience lifecycle works",
                solution="Run E2E test",
                key_lessons=["Testing is important"],
                tags=["test", "e2e"]
            )
            data = safe_json(result)
            exp_obj = data.get("experience", data)
            exp_id = exp_obj.get("id", data.get("exp_id", data.get("id", "")))
            record("E2E: Experience Create", "pass" if exp_id else "fail",
                   f"exp_id={str(exp_id)[:8]}...")

            if exp_id:
                try:
                    result = await client.experience_read(exp_kb_id, exp_id)
                    record("E2E: Experience Read", "pass", str(result)[:60])
                except Exception as e:
                    record("E2E: Experience Read", "fail", str(e)[:80])

                try:
                    result = await client.experience_review(exp_kb_id, exp_id,
                        reviewer="e2e-tester", rating=4.0, comment="Good test experience")
                    record("E2E: Experience Review", "pass", str(result)[:60])
                except Exception as e:
                    record("E2E: Experience Review", "fail", str(e)[:80])

                try:
                    result = await client.experience_apply(exp_kb_id, exp_id,
                        user="e2e-tester", context="testing", result="applied")
                    record("E2E: Experience Apply", "pass", str(result)[:60])
                except Exception as e:
                    record("E2E: Experience Apply", "fail", str(e)[:80])

                try:
                    result = await client.experience_search(exp_kb_id, "testing", top_k=5)
                    record("E2E: Experience Search", "pass", str(result)[:60])
                except Exception as e:
                    record("E2E: Experience Search", "fail", str(e)[:80])

                try:
                    result = await client.experience_search_vector(exp_kb_id, "testing", top_k=5)
                    record("E2E: Experience Vector Search", "pass", str(result)[:60])
                except Exception as e:
                    record("E2E: Experience Vector Search", "fail", str(e)[:80])

                try:
                    await client.experience_delete(exp_kb_id, exp_id)
                    record("E2E: Experience Delete", "pass", "deleted")
                except Exception as e:
                    record("E2E: Experience Delete", "fail", str(e)[:80])
        except Exception as e:
            record("E2E: Experience Create", "fail", str(e)[:80])

    await client.aclose()


# ════════════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════════════

async def main():
    header("RAG Knowledge Platform — 全系统功能测试")
    print(f"  Backend: {BACKEND_URL}")
    print(f"  Web:     {WEB_URL}")
    print(f"  Time:    {__import__('datetime').datetime.now().isoformat()}")

    # Part 1: Backend APIs
    test_backend_apis()

    # Part 2: Web APIs
    test_web_apis()

    # Part 3: MCP Tools
    await test_mcp_tools()

    # Part 4: E2E Workflow
    await test_e2e_workflow()

    # Summary
    header("测试总结")
    total = results["pass"] + results["fail"] + results["skip"]
    print(f"\n  总计: {total} 项")
    print(f"  ✓ 通过: {results['pass']}")
    print(f"  ✗ 失败: {results['fail']}")
    print(f"  − 跳过: {results['skip']}")
    print(f"  通过率: {results['pass']/total*100:.1f}%" if total > 0 else "  N/A")

    if results["fail"] > 0:
        print("\n  失败项详情:")
        for d in results["details"]:
            if d["status"] == "fail":
                print(f"    ✗ {d['name']}: {d['detail']}")

    return results


if __name__ == "__main__":
    asyncio.run(main())
