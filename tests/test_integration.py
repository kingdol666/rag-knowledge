"""Full Integration Test: MCP → API → Backend → Storage chain verification.

This test verifies that:
1. Every MCP tool correctly dispatches to its API endpoint
2. Write path: MCP → Nuxt Proxy → Backend → disk + .tree-fs.json + .knowledge-base.yml (3-layer sync)
3. Read path: MCP tools read from the correct source (direct file vs API proxy)
4. End-to-end Skill workflow simulation: ingest → search → manage → graph → verify → cleanup
5. HTTP request routing: Nuxt proxy endpoints vs Backend direct endpoints
6. Vector index + graph index lifecycle (create → search → delete → verify cleanup)
7. Experience lifecycle (create → read → list → search → apply → review → update → delete)
8. File system operations (folder/file CRUD → 3-layer sync)
9. Document move chain (source KB → target KB, both .knowledge-base.yml updated)
10. Nuxt proxy ↔ backend route mapping for all proxy routes
"""
import asyncio
import json
import os
import sys
from pathlib import Path

KB_MCP_DIR = Path(__file__).parent.parent / "kb-mcp"
sys.path.insert(0, str(KB_MCP_DIR))

import yaml
config_path = KB_MCP_DIR.parent / "config.yml"
with open(config_path, encoding="utf-8") as f:
    cfg = yaml.safe_load(f) or {}
mode = os.environ.get("APP_MODE", "dev")
server_cfg = cfg.get("server", {}).get(mode, cfg.get("server", {}).get("prod", {}))
WEB_URL = f"http://localhost:{server_cfg.get('frontend_port', 6789)}"
BACKEND_URL = server_cfg.get("backend_url", "http://localhost:8765")
os.environ["WEB_URL"] = WEB_URL
os.environ["BACKEND_URL"] = BACKEND_URL

from server import mcp, _client
from kb_client import KbClient

import httpx
import logging
logging.getLogger("httpx").setLevel(logging.WARNING)

results = {"pass": 0, "fail": 0, "errors": []}
STORAGE_ROOT = Path(KB_MCP_DIR.parent / cfg.get("storage", {}).get("tree_fs_root", "./storage/tree-file-system"))


async def call_mcp(tool_name: str, **kwargs):
    """Call an MCP tool function directly."""
    tool = mcp._tool_manager._tools.get(tool_name)
    if not tool:
        raise ValueError(f"MCP tool not found: {tool_name}")
    result = await tool.fn(**kwargs)
    if isinstance(result, str):
        try:
            return json.loads(result)
        except:
            return result
    return result


async def call_api(method: str, url: str, **kwargs):
    """Call a REST API endpoint directly via httpx."""
    async with httpx.AsyncClient(timeout=30, trust_env=False) as client:
        resp = await client.request(method, url, **kwargs)
        ct = resp.headers.get("content-type", "")
        if "json" in ct:
            return resp.status_code, resp.json()
        return resp.status_code, resp.text


def check(label: str, condition: bool, detail: str = ""):
    if condition:
        results["pass"] += 1
        print(f"  + {label}: PASS" + (f" — {detail}" if detail else ""))
    else:
        results["fail"] += 1
        results["errors"].append(f"{label}: {detail}")
        print(f"  X {label}: FAIL — {detail}")


def jget(data, *keys, default=None):
    for k in keys:
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except:
                return default
        if isinstance(data, dict):
            data = data.get(k, default)
        else:
            return default
    return data


def read_tree_fs():
    p = STORAGE_ROOT / ".tree-fs.json"
    if p.exists():
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return {}


def read_kb_yml(kb_name: str):
    p = STORAGE_ROOT / kb_name / ".knowledge-base.yml"
    if p.exists():
        import yaml as y
        with open(p, encoding="utf-8") as f:
            return y.safe_load(f) or {}
    return {}


def doc_exists_on_disk(kb_name: str, doc_name: str):
    return (STORAGE_ROOT / kb_name / doc_name).exists()


async def run_tests():
    client = _client()

    # ═══ Pre-cleanup: Remove leftover test KBs ═══
    existing = await call_mcp("kb_list")
    for kb in existing.get("knowledgeBases", []):
        kb_name = kb.get("name", "")
        if kb_name in ("Integration-Test-KB", "Integration-Target-KB", "DebugFS",
                       "VecSearchDebug", "FullTest_Ingest"):
            try:
                await call_mcp("kb_delete", kb_id=kb.get("kbId") or kb.get("path"))
                print(f"  [cleanup] Deleted leftover KB: {kb_name}")
            except:
                pass

    # ═══════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("INTEGRATION 1: MCP → API Routing Verification")
    print("=" * 70)

    h = await call_mcp("health_check")
    check("health_check calls backend", h.get("backend") == True, f"backend={h.get('backend')}")
    check("health_check calls web", h.get("web") == True, f"web={h.get('web')}")

    kl = await call_mcp("kb_list")
    check("kb_list via Nuxt proxy", kl.get("success") == True and "knowledgeBases" in kl,
          f"count={kl.get('count')}")

    tl = await call_mcp("kb_tags_list")
    check("kb_tags_list via Nuxt proxy", tl.get("success") == True, f"tags={len(tl.get('tags', []))}")

    ft = await call_mcp("fs_get_tree", include_files=False, max_depth=1)
    check("fs_get_tree via Nuxt proxy", isinstance(ft, list) and len(ft) > 0,
          f"top_level_nodes={len(ft)}")

    bs = await call_mcp("backend_status")
    check("backend_status via Backend",
          jget(bs, "backend_health", "status") == "healthy" or jget(bs, "mineru_status", "running") == True,
          f"backend={jget(bs, 'backend_health', 'status')}, mineru_running={jget(bs, 'mineru_status', 'running')}")

    vs = await call_mcp("kb_search_vector", query="test", top_k=2)
    check("kb_search_vector via Backend", vs.get("success") == True, f"results={len(vs.get('results', []))}")

    ts = await call_mcp("kb_search_two_stage", query="test", stage1_top_k=10, stage2_top_k=2)
    check("kb_search_two_stage via Backend", ts.get("success") == True, f"total_results={ts.get('total_results')}")

    gs = await call_mcp("kb_graph_stats")
    check("kb_graph_stats via Backend", gs.get("success") == True, f"nodes={jget(gs, 'stats', 'node_count')}")

    gh = await call_mcp("kb_graph_health")
    check("kb_graph_health via Backend", jget(gh, "health", "available") == True,
          f"available={jget(gh, 'health', 'available')}")

    ss = await call_mcp("kb_search_stats")
    check("kb_search_stats via Backend", ss.get("success") == True,
          f"collections={len(jget(ss, 'stats', 'collections', default=[]))}")

    cat = await call_mcp("kb_catalog")
    check("kb_catalog returns lightweight catalog", cat.get("success") == True, f"count={cat.get('count')}")

    fcat = await call_mcp("fs_catalog_all", include_files=False)
    check("fs_catalog_all returns flat catalog", fcat.get("success") == True, f"count={fcat.get('count')}")

    # ═══════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("INTEGRATION 2: Write Path — 3-Layer Metadata Sync")
    print("=" * 70)

    test_kb_name = "Integration-Test-KB"
    kb_raw = await call_mcp("kb_create", name=test_kb_name,
        description="Integration test KB for 3-layer sync verification")
    kb_id = jget(kb_raw, "knowledgeBase", "id") or ""
    check("kb_create returns UUID", bool(kb_id), f"kb_id={kb_id}")

    tree = read_tree_fs()
    check("KB in .tree-fs.json after create", any(f.get("id") == kb_id for f in tree.get("folders", [])))
    check("KB directory on disk", (STORAGE_ROOT / test_kb_name).exists())
    yml = read_kb_yml(test_kb_name)
    check(".knowledge-base.yml created", yml.get("name") == test_kb_name or bool(yml))

    doc_content = """# Integration Test Verification Document

This document is specifically designed for integration test verification of the MCP tool chain.
It covers machine learning integration testing, knowledge base management verification,
and three-layer metadata synchronization across disk, tree-fs.json, and knowledge-base.yml.

The integration test verifies that the MCP layer correctly dispatches HTTP requests
to the backend API, which then writes to both the vector database and the file system.
This ensures end-to-end data integrity for the knowledge base platform.

Keywords: integration test, verification, MCP, API, backend, vector search, knowledge base.
"""
    doc_raw = await call_mcp("kb_doc_create", kb_id=kb_id,
        name="integration-test.md", content=doc_content,
        description="Integration test document for 3-layer sync verification — MCP tool chain end-to-end")
    doc_path = jget(doc_raw, "document", "path") or ""
    doc_id = jget(doc_raw, "document", "id") or ""
    doc_name = Path(doc_path).name if doc_path else ""
    check("kb_doc_create returns path+id", bool(doc_path) and bool(doc_id),
          f"path={doc_path}, id={doc_id}")

    tree = read_tree_fs()
    check("Doc in .tree-fs.json after create", any(f.get("id") == doc_id for f in tree.get("files", [])))

    yml = read_kb_yml(test_kb_name)
    docs_in_yml = yml.get("documents", [])
    check("Doc in .knowledge-base.yml after create",
          any(doc_name in d.get("path", "") for d in docs_in_yml))
    check("Doc file on disk", doc_exists_on_disk(test_kb_name, doc_name))

    read_raw = await call_mcp("kb_doc_read", path=doc_path, max_chars=500)
    check("Content matches after create", "Integration Test Verification" in jget(read_raw, "content", default=""))

    await call_mcp("kb_doc_update_tags", kb_id=kb_id, doc_path=doc_path,
        tags=["integration-test", "3-layer-sync", "verification"])
    yml = read_kb_yml(test_kb_name)
    doc_yml = next((d for d in yml.get("documents", []) if doc_name in d.get("path", "")), {})
    yml_tags = doc_yml.get("tags", [])
    check("Tags synced to .knowledge-base.yml",
          "integration-test" in yml_tags and "3-layer-sync" in yml_tags, f"tags={yml_tags}")

    new_content = """# Updated Integration Test Content

Content was updated via MCP kb_doc_update_content tool.
This verifies that content updates sync to disk, .tree-fs.json (fileSize), and .knowledge-base.yml.
The integration test verification document now has updated content for testing.
"""
    await call_mcp("kb_doc_update_content", kb_id=kb_id, doc_path=doc_path, content=new_content)
    disk_path = STORAGE_ROOT / test_kb_name / doc_name
    disk_content = disk_path.read_text(encoding="utf-8") if disk_path.exists() else ""
    check("Content update synced to disk", "Updated Integration Test Content" in disk_content)

    tree = read_tree_fs()
    file_node = next((f for f in tree.get("files", []) if f.get("id") == doc_id), {})
    check("File size synced in .tree-fs.json", file_node.get("fileSize", 0) > 0,
          f"size={file_node.get('fileSize')}")

    # ═══════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("INTEGRATION 3: Vector Index Chain (MCP → Backend → ChromaDB)")
    print("=" * 70)

    idx = await call_mcp("kb_index_document", kb_id=kb_id, doc_path=doc_path)
    check("kb_index_document via Backend", idx.get("success") == True,
          f"chunks={jget(idx, 'vector_index', 'total_chunks')}")

    yml = read_kb_yml(test_kb_name)
    doc_yml = next((d for d in yml.get("documents", []) if doc_name in d.get("path", "")), {})
    vi = doc_yml.get("vector_index", {})
    check("vector_index synced to .knowledge-base.yml",
          bool(vi.get("collection")) and vi.get("total_chunks", 0) > 0,
          f"collection={vi.get('collection')}, chunks={vi.get('total_chunks')}")

    sv = await call_mcp("kb_search_vector", query="integration test verification MCP tool chain", top_k=5)
    found = any(doc_name in r.get("doc_path", "") for r in sv.get("results", []))
    check("Vector search finds indexed doc", found,
          f"results={len(sv.get('results', []))}, top_score={sv.get('results', [{}])[0].get('score', '?') if sv.get('results') else 'N/A'}")

    bv = await call_mcp("kb_search_batch_vector", query_doc_paths=[doc_path], top_k=3, score_threshold=0.1)
    check("kb_search_batch_vector via Backend", bv.get("success") == True)

    ts2 = await call_mcp("kb_search_two_stage", query="integration test verification", stage1_top_k=15, stage2_top_k=3)
    check("Two-stage search returns results", ts2.get("success") == True, f"total_results={ts2.get('total_results')}")

    stats = await call_mcp("kb_search_stats", kb_id=kb_id)
    check("Search stats for KB", stats.get("success") == True)

    # ═══════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("INTEGRATION 4: Graph Chain (MCP → Backend → Neo4j)")
    print("=" * 70)

    gb = await call_mcp("kb_graph_build_kb", kb_id=kb_id, force=True)
    check("kb_graph_build_kb via Backend", gb.get("success") == True,
          f"docs={jget(gb, 'result', 'docs_processed')}")

    check("Graph stats accessible", (await call_mcp("kb_graph_stats")).get("success") == True)
    check("kb_graph_search works", (await call_mcp("kb_graph_search", keyword="integration", limit=10)).get("success") == True)
    check("kb_graph_search_kbs works", (await call_mcp("kb_graph_search_kbs", keyword="integration", limit=10)).get("success") == True)
    check("kb_graph_search_tags works", (await call_mcp("kb_graph_search_tags", keyword="integration", limit=10)).get("success") == True)
    check("kb_graph_document view", (await call_mcp("kb_graph_document", doc_path=doc_path)).get("success") == True)
    check("kb_graph_document_related", (await call_mcp("kb_graph_document_related", doc_path=doc_path)).get("success") == True)
    check("kb_graph_documents_by_tag", (await call_mcp("kb_graph_documents_by_tag", tag_name="integration-test")).get("success") == True)
    check("kb_graph_kb_overview", (await call_mcp("kb_graph_kb_overview", kb_id=kb_id)).get("success") == True)
    check("kb_graph_cross_kb_documents", (await call_mcp("kb_graph_cross_kb_documents", min_kbs=2, limit=10)).get("success") == True)
    check("kb_graph_central_documents", (await call_mcp("kb_graph_central_documents", kb_id=kb_id, top_n=5)).get("success") == True)
    check("kb_graph_delete_document", (await call_mcp("kb_graph_delete_document", doc_path=doc_path)).get("success") == True)

    # ═══════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("INTEGRATION 5: Experience Chain (MCP → Backend → Disk)")
    print("=" * 70)

    ec = await call_mcp("experience_create",
        kb_id=kb_id, title="Integration test experience",
        scenario="integration-testing", category="tip",
        problem="Testing the full integration chain between MCP, API, and Backend",
        solution="Run this comprehensive test suite to verify all endpoints",
        result="success", key_lessons=["Always verify 3-layer sync", "Use longer content for vector tests"],
        tags=["integration-test"], severity="normal")
    exp_id = jget(ec, "experience", "id") or ""
    check("experience_create via Backend", ec.get("success") == True and bool(exp_id), f"exp_id={exp_id}")

    if exp_id:
        check("experience_read", (await call_mcp("experience_read", kb_id=kb_id, exp_id=exp_id)).get("success") == True)
        check("experience_list", (await call_mcp("experience_list", kb_id=kb_id)).get("success") == True)
        check("experience_find_by_scenario", (await call_mcp("experience_find_by_scenario", kb_id=kb_id, scenario="integration-testing")).get("success") == True)
        check("experience_search", (await call_mcp("experience_search", kb_id=kb_id, query="integration")).get("success") == True)
        check("experience_search_vector", (await call_mcp("experience_search_vector", kb_id=kb_id, query="testing chain", top_k=3)).get("success") == True)
        check("experience_apply", (await call_mcp("experience_apply", kb_id=kb_id, exp_id=exp_id, user="test", context="integration", result="success")).get("success") == True)
        check("experience_review", (await call_mcp("experience_review", kb_id=kb_id, exp_id=exp_id, reviewer="tester", rating=5, comment="Perfect")).get("success") == True)
        check("experience_summary", (await call_mcp("experience_summary", kb_id=kb_id)).get("success") == True)
        check("experience_update", (await call_mcp("experience_update", kb_id=kb_id, exp_id=exp_id, title="Updated")).get("success") == True)
        check("experience_search_global", (await call_mcp("experience_search_global", query="integration", top_k=5)).get("success") == True)
        check("experience_delete", (await call_mcp("experience_delete", kb_id=kb_id, exp_id=exp_id)).get("success") == True)

    # ═══════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("INTEGRATION 6: File System Operations (MCP → Nuxt → 3-layer sync)")
    print("=" * 70)

    folder_raw = await call_mcp("fs_create_folder", name="test-folder", parent_id=kb_id, description="Test folder")
    folder_id = folder_raw.get("id") if isinstance(folder_raw, dict) else ""
    check("fs_create_folder", bool(folder_id), f"folder_id={folder_id}")

    if folder_id:
        file_raw = await call_mcp("fs_create_file", name="test-file.md", parent_id=folder_id, description="Test file")
        file_id = file_raw.get("id") if isinstance(file_raw, dict) else ""
        check("fs_create_file (creates empty file on disk)", bool(file_id), f"file_id={file_id}")

        file_disk_path = STORAGE_ROOT / test_kb_name / "test-folder" / "test-file.md"
        check("fs_create_file writes empty file to disk", file_disk_path.exists())

        node = await call_mcp("fs_get_node", node_id=file_id)
        check("fs_get_node returns node", isinstance(node, dict) and node.get("id") == file_id)

        children = await call_mcp("fs_get_children", parent_id=folder_id)
        check("fs_get_children returns list", isinstance(children, list))

        upd = await call_mcp("fs_update_node", node_id=file_id, name="test-file-renamed.md", description="Updated")
        check("fs_update_node", isinstance(upd, dict) and upd.get("id") == file_id)

        check("fs_delete_node (file)", isinstance(await call_mcp("fs_delete_node", node_id=file_id), dict))
        check("fs_delete_node (folder)", isinstance(await call_mcp("fs_delete_node", node_id=folder_id), dict))

    count = await call_mcp("fs_get_count")
    check("fs_get_count returns counts", isinstance(count, dict) and "total" in count,
          f"total={count.get('total') if isinstance(count, dict) else '?'}")

    # ═══════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("INTEGRATION 7: Document Move Chain (MCP → Nuxt → 3-layer sync on both KBs)")
    print("=" * 70)

    target_kb_raw = await call_mcp("kb_create", name="Integration-Target-KB", description="Target KB for move test")
    target_kb_id = jget(target_kb_raw, "knowledgeBase", "id") or ""
    check("Target KB created for move test", bool(target_kb_id))

    move_raw = await call_mcp("kb_doc_move", doc_path=doc_path, target_kb_id=target_kb_id)
    check("kb_doc_move via Nuxt proxy", move_raw.get("success") == True,
          f"new_path={jget(move_raw, 'document', 'path')}")

    yml_src = read_kb_yml(test_kb_name)
    check("Doc removed from source KB .knowledge-base.yml",
          not any(doc_name in d.get("path", "") for d in yml_src.get("documents", [])))

    yml_tgt = read_kb_yml("Integration-Target-KB")
    check("Doc added to target KB .knowledge-base.yml",
          any(doc_name in d.get("path", "") for d in yml_tgt.get("documents", [])))

    check("Doc file exists in target KB on disk", doc_exists_on_disk("Integration-Target-KB", doc_name))
    check("Doc file removed from source KB on disk", not doc_exists_on_disk(test_kb_name, doc_name))

    moved_doc_path = jget(move_raw, "document", "path") or doc_path
    read_moved = await call_mcp("kb_doc_read", path=moved_doc_path, max_chars=200)
    check("Read moved doc via new path", read_moved.get("success") == True,
          f"content_preview={jget(read_moved, 'content', default='')[:50]}")

    doc_path = moved_doc_path

    # ═══════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("INTEGRATION 8: Skill Workflow Simulation (End-to-End)")
    print("=" * 70)

    # Ingest A1: Survey
    check("Ingest A1: survey kb_list", (await call_mcp("kb_list")).get("success") == True)
    check("Ingest A1: survey kb_tags_list", (await call_mcp("kb_tags_list")).get("success") == True)
    check("Ingest A1: survey fs_get_tree", isinstance(await call_mcp("fs_get_tree", include_files=True, max_depth=2), list))

    # Ingest A7: Verify
    verify_docs = await call_mcp("kb_get_documents", kb_id=target_kb_id)
    check("Ingest A7: kb_get_documents verifies doc", verify_docs.get("count", 0) >= 1)
    verify_tags = await call_mcp("kb_doc_get_by_tag", tag="integration-test")
    check("Ingest A7: kb_doc_get_by_tag verifies tags", verify_tags.get("count", 0) >= 1)
    verify_read = await call_mcp("kb_doc_read", path=doc_path, max_chars=200)
    check("Ingest A7: kb_doc_read verifies content",
          "Updated Integration Test" in jget(verify_read, "content", default=""))

    # Search VFCR
    search_result = await call_mcp("kb_search_two_stage", query="integration test verification", stage1_top_k=15, stage2_top_k=3)
    check("Search VFCR: two-stage search", search_result.get("success") == True)

    candidates = jget(search_result, "stage1", "candidates", default=[])
    content_verified = False
    verified_path = ""
    for cand in candidates[:5]:  # Try top 5 candidates
        top_doc = cand.get("doc_path", "")
        if top_doc:
            content_check = await call_mcp("kb_doc_read", path=top_doc, max_chars=1000)
            if content_check.get("success") == True:
                content_verified = True
                verified_path = top_doc
                break
    check("Search VFCR: content verification read", content_verified,
          f"candidates={len(candidates)}, verified={verified_path}")

    # Manage M1: Rename
    rename_raw = await call_mcp("kb_doc_update_meta", kb_id=target_kb_id, doc_path=doc_path,
        name="integration-test-renamed.md", description="Renamed by manage skill")
    new_doc_path = jget(rename_raw, "document", "path") or doc_path
    new_doc_name = Path(new_doc_path).name
    check("Manage M1: rename doc", rename_raw.get("success") == True, f"new_path={new_doc_path}")
    check("Manage M1: renamed file on disk", doc_exists_on_disk("Integration-Target-KB", new_doc_name))
    check("Manage M1: old file removed from disk", not doc_exists_on_disk("Integration-Target-KB", doc_name))

    yml_tgt = read_kb_yml("Integration-Target-KB")
    check("Manage M1: path updated in .knowledge-base.yml",
          any(new_doc_name in d.get("path", "") for d in yml_tgt.get("documents", [])))

    # Verify V1/V4
    check("Verify V1: health check", (await call_mcp("health_check")).get("all_ok") == True)
    check("Verify V4: vector stats", (await call_mcp("kb_search_stats", kb_id=target_kb_id)).get("success") == True)
    check("Verify V4: graph health", jget(await call_mcp("kb_graph_health"), "health", "available") == True)

    # Preview
    pv = await call_mcp("preview_file", path=new_doc_path)
    check("preview_file via Nuxt proxy", pv.get("success") == True or "content" in str(pv))

    # ═══════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("INTEGRATION 9: Nuxt Proxy ↔ Backend Route Mapping")
    print("=" * 70)

    nuxt_gh = await call_api("GET", f"{WEB_URL}/api/graph/health")
    backend_gh = await call_api("GET", f"{BACKEND_URL}/api/v1/graph/health")
    check("Nuxt graph/health → backend", nuxt_gh[0] == 200 and backend_gh[0] == 200)

    check("Nuxt graph/stats → backend", (await call_api("GET", f"{WEB_URL}/api/graph/stats"))[0] == 200)
    check("Nuxt graph/document → backend",
          (await call_api("GET", f"{WEB_URL}/api/graph/document", params={"doc_path": new_doc_path}))[0] == 200)

    nuxt_ts = await call_api("POST", f"{WEB_URL}/api/search/two-stage", json={"query": "test", "stage2_top_k": 2})
    backend_ts = await call_api("POST", f"{BACKEND_URL}/api/v1/search/two-stage", json={"query": "test", "stage2_top_k": 2})
    check("Nuxt search/two-stage → backend", nuxt_ts[0] == 200 and backend_ts[0] == 200)

    check("Nuxt search/vector → backend",
          (await call_api("POST", f"{WEB_URL}/api/search/vector", json={"query": "test", "top_k": 2}))[0] == 200)
    check("Nuxt search/reindex → backend",
          (await call_api("POST", f"{WEB_URL}/api/search/reindex", json={"kb_id": target_kb_id, "force": False}))[0] == 200)
    check("Nuxt search/batch-vector → backend",
          (await call_api("POST", f"{WEB_URL}/api/search/batch-vector", json={"query_doc_paths": [new_doc_path], "top_k": 2}))[0] == 200)
    check("Nuxt kb/catalog → backend", (await call_api("GET", f"{WEB_URL}/api/kb/catalog"))[0] == 200)
    check("Nuxt kb/search → backend",
          (await call_api("GET", f"{WEB_URL}/api/kb/search", params={"query": "test", "top_k": 5}))[0] == 200)

    # ═══════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("INTEGRATION 10: Delete Cleanup + 3-Layer Sync Verification")
    print("=" * 70)

    # Graph cleanup for moved doc
    check("Graph cleanup for moved doc", (await call_mcp("kb_graph_delete_document", doc_path=new_doc_path)).get("success") == True)

    # Delete doc
    del_result = await call_mcp("kb_doc_delete", kb_id=target_kb_id, doc_path=new_doc_path)
    check("kb_doc_delete", del_result.get("success") == True)

    tree = read_tree_fs()
    check("Doc removed from .tree-fs.json", not any(f.get("id") == doc_id for f in tree.get("files", [])))

    yml_tgt = read_kb_yml("Integration-Target-KB")
    check("Doc removed from .knowledge-base.yml",
          not any(new_doc_name in d.get("path", "") for d in yml_tgt.get("documents", [])))
    check("Doc file removed from disk", not doc_exists_on_disk("Integration-Target-KB", new_doc_name))

    # Delete target KB
    check("kb_delete (target KB)", (await call_mcp("kb_delete", kb_id=target_kb_id)).get("success") == True)
    tree = read_tree_fs()
    check("Target KB removed from .tree-fs.json", not any(f.get("id") == target_kb_id for f in tree.get("folders", [])))
    check("Target KB directory removed from disk", not (STORAGE_ROOT / "Integration-Target-KB").exists())

    # Delete source KB
    check("kb_delete (source KB)", (await call_mcp("kb_delete", kb_id=kb_id)).get("success") == True)
    tree = read_tree_fs()
    check("Source KB removed from .tree-fs.json", not any(f.get("id") == kb_id for f in tree.get("folders", [])))
    check("Source KB directory removed from disk", not (STORAGE_ROOT / test_kb_name).exists())

    try:
        await client.aclose()
    except:
        pass

    # ═══════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print(f"INTEGRATION TEST SUMMARY: {results['pass']} passed, {results['fail']} failed")
    print("=" * 70)

    if results["errors"]:
        print("\nFailed tests:")
        for err in results["errors"]:
            print(f"  X {err}")

    total = results["pass"] + results["fail"]
    if total > 0:
        print(f"\nPass rate: {results['pass'] / total * 100:.1f}%")

    return results


if __name__ == "__main__":
    asyncio.run(run_tests())
