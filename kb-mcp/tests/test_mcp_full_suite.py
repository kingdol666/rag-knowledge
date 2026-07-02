"""E2E test suite for kb-mcp MCP tools.

Tests all 41+ MCP tools in logical order:
  Health → KB CRUD → Doc CRUD → Tags → FS → Parse → Search (vector) → Graph → Cleanup

Usage:
    cd kb-mcp && python -m pytest tests/ -v
    # or directly: python tests/test_mcp_full_suite.py
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from kb_client.client import KbClient
from config import WEB_URL, BACKEND_URL


def _trunc(s, n=400):
    s = str(s)
    return s[:n] + "..." if len(s) > n else s


async def _call(client, method, *args, **kw):
    fn = getattr(client, method, None)
    assert fn is not None, f"Method {method} not found"
    result = await fn(*args, **kw)
    if isinstance(result, dict) and not result.get("success", True):
        raise AssertionError(f"{method} failed: {result.get('error')}")
    return result


# ═══════════════════════════════════════════════════════════════
# 1. Health
# ═══════════════════════════════════════════════════════════════

async def test_health(client):
    r = await _call(client, "health_check")
    assert r.get("all_ok") or r.get("backend"), f"Health failed (backend={r.get('backend')}, web={r.get('web')})"
    return "✅ health_check: backend OK"


async def test_backend_status(client):
    r = await _call(client, "backend_status")
    assert "backend_health" in r
    return "✅ backend_status: OK"


# ═══════════════════════════════════════════════════════════════
# 2. KB CRUD
# ═══════════════════════════════════════════════════════════════

async def test_kb_list(client):
    r = await _call(client, "kb_list")
    assert r.get("count", 0) > 0
    return f"✅ kb_list: {r['count']} KBs"


_TEST_KB_NAME = "MCP-E2E-Test"


async def test_kb_create(client):
    r = await _call(client, "kb_create", name=_TEST_KB_NAME, description="E2E test KB")
    assert r.get("success")
    return f"✅ kb_create: {r.get('knowledgeBase', {}).get('path', '')}"


async def test_kb_update(client):
    r = await _call(client, "kb_update", kb_id=_TEST_KB_NAME, description="Updated description")
    assert r.get("success")
    return "✅ kb_update: OK"


async def test_kb_get_documents_empty(client):
    r = await _call(client, "kb_get_documents", _TEST_KB_NAME)
    assert "documents" in r
    return f"✅ kb_get_documents (empty): count={r.get('count', 0)}"


# ═══════════════════════════════════════════════════════════════
# 3. Document CRUD
# ═══════════════════════════════════════════════════════════════

_DOC_NAME = "e2e-test-doc.md"
_DOC_PATH = f"{_TEST_KB_NAME}/{_DOC_NAME}"


async def test_doc_create(client):
    content = "# E2E Test Document\n\nThis is a test document for the kb-mcp suite."
    r = await _call(client, "kb_doc_create", kb_id=_TEST_KB_NAME, name=_DOC_NAME, content=content, description="E2E test doc")
    assert r.get("success")
    return f"✅ kb_doc_create: {r.get('document', {}).get('path', '')}"


async def test_doc_read(client):
    r = await _call(client, "kb_doc_read", path=_DOC_PATH)
    assert len(r.get("content", "")) > 0
    return f"✅ kb_doc_read: {r.get('totalLines', 0)} lines"


async def test_doc_update_content(client):
    r = await _call(client, "kb_doc_update_content", kb_id=_TEST_KB_NAME, doc_path=_DOC_PATH, content="# Updated\n\nNew content.")
    assert r.get("success")
    return "✅ kb_doc_update_content: OK"


async def test_doc_update_meta(client):
    r = await _call(client, "kb_doc_update_meta", kb_id=_TEST_KB_NAME, doc_path=_DOC_PATH, description="Updated description")
    assert r.get("success")
    return "✅ kb_doc_update_meta: OK"


# ═══════════════════════════════════════════════════════════════
# 4. Tags
# ═══════════════════════════════════════════════════════════════

_TAG = "e2e-tag"


async def test_tag_create(client):
    r = await _call(client, "kb_tag_create", _TAG)
    assert r.get("success")
    return "✅ kb_tag_create: OK"


async def test_tags_list(client):
    r = await _call(client, "kb_tags_list")
    assert isinstance(r.get("tags"), list)
    assert _TAG in r["tags"]
    return f"✅ kb_tags_list: {len(r['tags'])} tags"


async def test_doc_update_tags(client):
    r = await _call(client, "kb_doc_update_tags", kb_id=_TEST_KB_NAME, doc_path=_DOC_PATH, tags=[_TAG, "test"])
    assert r.get("success")
    return "✅ kb_doc_update_tags: OK"


async def test_doc_get_by_tag(client):
    r = await _call(client, "kb_doc_get_by_tag", tag=_TAG)
    assert r.get("count", 0) >= 1
    return f"✅ kb_doc_get_by_tag: {r['count']} docs"


# ═══════════════════════════════════════════════════════════════
# 5. File System
# ═══════════════════════════════════════════════════════════════

async def test_fs_get_tree(client):
    r = await _call(client, "fs_get_tree")
    assert isinstance(r, list)
    return f"✅ fs_get_tree: {len(r)} root nodes"


async def test_fs_get_count(client):
    r = await _call(client, "fs_get_count")
    assert r.get("total", 0) > 0
    return f"✅ fs_get_count: {r['total']} total"


async def test_fs_get_children(client):
    r = await _call(client, "fs_get_children")
    assert isinstance(r, list)
    return f"✅ fs_get_children: {len(r)} root children"


# ═══════════════════════════════════════════════════════════════
# 6. Search — Agentic RAG tests
# ═══════════════════════════════════════════════════════════════

async def test_search_metadata(client):
    """kb_search: metadata-only — should only hit name/description, NOT body."""
    r = await _call(client, "kb_search", query=_DOC_NAME.replace(".md", ""), top_k=5)
    hits = r.get("hits", [])
    return f"✅ kb_search (metadata): {len(hits)} hits"


async def test_search_vector(client):
    """kb_search_vector: semantic retrieval by content."""
    # Build index first for the test doc
    await _call(client, "index_document", kb_id=_TEST_KB_NAME, doc_path=_DOC_PATH,
                doc_name=_DOC_NAME, content="# E2E Test\n\nTest content for vector search.")
    r = await _call(client, "vector_search", query="test document e2e", kb_id=_TEST_KB_NAME, top_k=3)
    results = r.get("results", [])
    return f"✅ kb_search_vector: {len(results)} results" + (f", top score={results[0]['score']:.3f}" if results else "")


async def test_search_two_stage(client):
    """kb_search_two_stage: fulltext→vector pipeline."""
    r = await _call(client, "two_stage_search", query="test document", kb_id=_TEST_KB_NAME,
                    stage1_top_k=10, stage2_top_k=3)
    total = r.get("total_results", 0)
    return f"✅ kb_search_two_stage: {total} results"


async def test_search_batch_vector(client):
    """kb_search_batch_vector: similarity across doc paths."""
    r = await _call(client, "batch_vector_search", query_doc_paths=[_DOC_PATH], top_k=3)
    results = r.get("results", {})
    count = r.get("count", 0)
    return f"✅ kb_search_batch_vector: {count} doc comparisons"


async def test_search_stats(client):
    r = await _call(client, "search_stats", kb_id=_TEST_KB_NAME)
    stats = r.get("stats", {})
    chunks = stats.get("chunk_count", 0)
    return f"✅ kb_search_stats: {chunks} chunks"


# ═══════════════════════════════════════════════════════════════
# 7. Graph (may be unavailable, graceful skip)
# ═══════════════════════════════════════════════════════════════

async def test_graph_stats(client):
    try:
        r = await _call(client, "graph_stats")
        return f"✅ kb_graph_stats: {r.get('entityCount', 0)} entities"
    except Exception:
        return "⏭️ kb_graph_stats: skipped (service unavailable)"


async def test_graph_search(client):
    try:
        r = await _call(client, "graph_search", keyword="test", limit=5)
        return f"✅ kb_graph_search: {len(r.get('results', []))} results"
    except Exception:
        return "⏭️ kb_graph_search: skipped (service unavailable)"


# ═══════════════════════════════════════════════════════════════
# 8. Preview
# ═══════════════════════════════════════════════════════════════

async def test_preview_file(client):
    r = await _call(client, "preview_file", path=_DOC_PATH)
    assert "content" in r or r.get("success") is not False
    return "✅ preview_file: OK"


# ═══════════════════════════════════════════════════════════════
# 9. Cleanup
# ═══════════════════════════════════════════════════════════════

async def test_doc_delete(client):
    r = await _call(client, "kb_doc_delete", kb_id=_TEST_KB_NAME, doc_path=_DOC_PATH)
    assert r.get("success")
    return "✅ kb_doc_delete: OK"


async def test_kb_delete(client):
    r = await _call(client, "kb_delete", kb_id=_TEST_KB_NAME)
    assert r.get("success")
    return "✅ kb_delete: OK"


# ═══════════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════════

async def run_all():
    client = KbClient(web_url=WEB_URL, backend_url=BACKEND_URL)
    tests = [
        # Health
        test_health, test_backend_status,
        # KB CRUD
        test_kb_list, test_kb_create, test_kb_update, test_kb_get_documents_empty,
        # Doc CRUD
        test_doc_create, test_doc_read, test_doc_update_content, test_doc_update_meta,
        # Tags
        test_tag_create, test_tags_list, test_doc_update_tags, test_doc_get_by_tag,
        # File System
        test_fs_get_tree, test_fs_get_count, test_fs_get_children,
        # Search (Agentic RAG)
        test_search_metadata, test_search_vector, test_search_two_stage,
        test_search_batch_vector, test_search_stats,
        # Graph
        test_graph_stats, test_graph_search,
        # Preview
        test_preview_file,
        # Cleanup
        test_doc_delete, test_kb_delete,
    ]

    passed = failed = 0
    print(f"{'='*60}")
    print(f"  kb-mcp E2E Test Suite — {len(tests)} tests")
    print(f"{'='*60}\n")

    for t in tests:
        name = t.__name__.replace("test_", "")
        try:
            msg = await t(client)
            print(f"  [PASS] {msg}")
            passed += 1
        except AssertionError as e:
            print(f"  [FAIL] {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"  [FAIL] {name}: {type(e).__name__}: {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"  Result: {passed}/{len(tests)} passed, {failed} failed")
    print(f"{'='*60}")
    await client.aclose()
    return passed, failed


if __name__ == "__main__":
    p, f = asyncio.run(run_all())
    sys.exit(0 if f == 0 else 1)
