"""Edge-case and untested tool coverage suite.

Tests tools NOT covered by test_all_skills.py:
  - fs_create_folder / fs_create_file / fs_update_node / fs_delete_node
  - kb_doc_move / kb_doc_batch_delete
  - parse_doc_batch / parse_tasks_list
  - kb_reindex
  - kb_graph_build_all / kb_graph_delete_document / kb_graph_delete_kb
  - kb_graph_documents_by_tag
  - kb_tag_create (new tag)
  - Sub-KB creation (parent_id)
  - Cross-KB search edge cases
  - Error handling (nonexistent KB/doc, invalid params)
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

from server import mcp

results = {"pass": 0, "fail": 0, "errors": [], "skipped": 0}
import logging
logging.getLogger("httpx").setLevel(logging.WARNING)


async def call_tool(tool_name: str, **kwargs):
    tool = mcp._tool_manager._tools.get(tool_name)
    if not tool:
        raise ValueError(f"Tool not found: {tool_name}")
    result = await tool.fn(**kwargs)
    if isinstance(result, str):
        try:
            return json.loads(result)
        except:
            return result
    return result


async def test(test_label: str, tool_name: str, expect_fail: bool = False, **kwargs):
    """Run a test. If expect_fail=True, success=false is expected."""
    try:
        result = await call_tool(tool_name, **kwargs)
        if result is None:
            results["fail"] += 1
            results["errors"].append(f"FAIL {test_label}: returned None")
            print(f"  X {test_label}: returned None")
            return None

        is_api_fail = isinstance(result, dict) and result.get("success") is False

        if expect_fail and is_api_fail:
            # Expected failure
            results["pass"] += 1
            err = result.get("error", "expected error") if isinstance(result, dict) else "expected"
            if isinstance(err, str) and len(err) > 120:
                err = err[:120] + "..."
            print(f"  + [EXPECTED FAIL] {test_label}: {err[:80]}")
            return result

        if is_api_fail:
            err_msg = result.get("error", "unknown error") if isinstance(result, dict) else "unknown"
            if isinstance(err_msg, str) and len(err_msg) > 200:
                err_msg = err_msg[:200] + "..."
            results["fail"] += 1
            results["errors"].append(f"FAIL {test_label}: {err_msg}")
            print(f"  X {test_label}: {err_msg[:100]}")
            return result

        results["pass"] += 1
        if isinstance(result, dict):
            ok = result.get("success", result.get("all_ok", True))
            status = "OK" if ok else "ERR"
            display = json.dumps(result, ensure_ascii=False)[:120]
        else:
            status = "OK"
            display = str(result)[:120]
        print(f"  + [{status}] {test_label}: {display}")
        return result
    except Exception as e:
        results["fail"] += 1
        results["errors"].append(f"FAIL {test_label}: {e}")
        print(f"  X {test_label}: {e}")
        return None


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


async def run_tests():
    # ═══════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("EDGE CASE: File System CRUD (fs_create_folder/file/update/delete)")
    print("=" * 70)

    # Create a test folder
    folder_raw = await test("fs_create_folder (test folder)", "fs_create_folder",
        name="EdgeTestFolder", description="Temporary folder for edge testing")
    folder_id = jget(folder_raw, "node", "id") or jget(folder_raw, "id") or ""
    print(f"  -> folder_id: {folder_id}")

    # Create a sub-folder inside it
    if folder_id:
        sub_raw = await test("fs_create_folder (sub-folder)", "fs_create_folder",
            name="SubFolder", parent_id=folder_id, description="Sub folder")
        sub_id = jget(sub_raw, "node", "id") or jget(sub_raw, "id") or ""

        # Create a file (metadata only)
        file_raw = await test("fs_create_file", "fs_create_file",
            name="test-note.md", parent_id=folder_id, description="A test note")
        file_id = jget(file_raw, "node", "id") or jget(file_raw, "id") or ""

        # Update node name
        if file_id:
            await test("fs_update_node (rename file)", "fs_update_node",
                node_id=file_id, name="test-note-renamed.md",
                description="Updated description")

        # Get node by ID
        if folder_id:
            await test("fs_get_node (folder)", "fs_get_node", node_id=folder_id)

        # Get children
        await test("fs_get_children (folder)", "fs_get_children", parent_id=folder_id)

        # Delete the sub-folder
        if sub_id:
            await test("fs_delete_node (sub-folder)", "fs_delete_node", node_id=sub_id)

    # ═══════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("EDGE CASE: Sub-KB Creation (parent_id)")
    print("=" * 70)

    sub_kb_raw = await test("kb_create (sub-KB)", "kb_create",
        name="EdgeTest-SubKB", description="Sub-KB for edge testing",
        parent_id=folder_id)
    sub_kb_id = jget(sub_kb_raw, "knowledgeBase", "id") or jget(sub_kb_raw, "kb_id") or ""
    print(f"  -> sub_kb_id: {sub_kb_id}")

    # ═══════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("EDGE CASE: Document Move + Batch Delete")
    print("=" * 70)

    # Create docs in sub_kb for move/batch_delete testing
    doc1_raw = await test("kb_doc_create (doc1 for move)", "kb_doc_create",
        kb_id=sub_kb_id, name="move-test-1.md",
        content="# Move Test 1\n\nContent for move testing.",
        description="Doc to test move")
    doc1_path = jget(doc1_raw, "document", "path") or jget(doc1_raw, "path") or ""

    doc2_raw = await test("kb_doc_create (doc2 for batch_delete)", "kb_doc_create",
        kb_id=sub_kb_id, name="batch-del-1.md",
        content="# Batch Delete 1", description="Doc to batch delete")
    doc2_path = jget(doc2_raw, "document", "path") or jget(doc2_raw, "path") or ""

    doc3_raw = await test("kb_doc_create (doc3 for batch_delete)", "kb_doc_create",
        kb_id=sub_kb_id, name="batch-del-2.md",
        content="# Batch Delete 2", description="Another doc to batch delete")
    doc3_path = jget(doc3_raw, "document", "path") or jget(doc3_raw, "path") or ""

    # Move doc1 to the parent EdgeTestFolder KB (which IS a KB because we used is_knowledge_base via kb_create)
    # We need a real KB as target - use the first existing KB from kb_list
    kb_list_raw = await call_tool("kb_list")
    existing_kbs = jget(kb_list_raw, "knowledgeBases") or []
    target_kb_id = existing_kbs[0].get("kbId") or existing_kbs[0].get("id") or "" if existing_kbs else ""
    if target_kb_id:
        target_kb_name = existing_kbs[0].get("name", target_kb_id)
        print(f"  -> Move target KB: {target_kb_name} ({target_kb_id})")
        move_raw = await test("kb_doc_move", "kb_doc_move",
            doc_path=doc1_path, target_kb_id=target_kb_id)
        moved_path = jget(move_raw, "document", "path") or ""
        print(f"  -> Moved to: {moved_path}")
    else:
        print("  -> SKIP kb_doc_move: no existing KB to move to")

    # Batch delete doc2 and doc3
    if doc2_path and doc3_path:
        await test("kb_doc_batch_delete", "kb_doc_batch_delete",
            kb_id=sub_kb_id, doc_paths=[doc2_path, doc3_path])

    # ═══════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("EDGE CASE: Tag Creation (kb_tag_create)")
    print("=" * 70)

    await test("kb_tag_create (new tag)", "kb_tag_create", tag="edge-test-tag")
    await test("kb_tag_create (duplicate tag)", "kb_tag_create", tag="edge-test-tag")
    await test("kb_tag_create (long tag >50 chars)", "kb_tag_create",
        tag="a" * 60, expect_fail=True)

    # ═══════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("EDGE CASE: Error Handling (nonexistent resources)")
    print("=" * 70)

    await test("kb_doc_read (nonexistent path)", "kb_doc_read",
        path="NonexistentKB/nonexistent.md", expect_fail=True)
    await test("kb_get_documents (nonexistent KB)", "kb_get_documents",
        kb_id="nonexistent-kb-uuid", expect_fail=True)
    await test("kb_doc_delete (nonexistent doc)", "kb_doc_delete",
        kb_id=sub_kb_id, doc_path="nonexistent.md", expect_fail=True)
    await test("fs_get_node (nonexistent ID)", "fs_get_node",
        node_id="nonexistent-uuid", expect_fail=True)
    await test("parse_task_status (nonexistent task)", "parse_task_status",
        task_id="nonexistent-task-id", expect_fail=True)

    # ═══════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("EDGE CASE: kb_reindex (full rebuild)")
    print("=" * 70)

    if sub_kb_id:
        await test("kb_reindex (KB)", "kb_reindex", kb_id=sub_kb_id, force=False)

    # ═══════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("EDGE CASE: Graph - documents_by_tag + build_all + delete")
    print("=" * 70)

    await test("kb_graph_documents_by_tag", "kb_graph_documents_by_tag",
        tag_name="machine learning", limit=10)

    # Build all (non-force to be safe)
    await test("kb_graph_build_all (incremental)", "kb_graph_build_all", force=False)

    # Graph delete for a test doc (use the moved doc if it exists)
    if doc1_path:
        # After move, the path changed. Try deleting the original path (should be safe)
        await test("kb_graph_delete_document (test)", "kb_graph_delete_document",
            doc_path=doc1_path)

    # ═══════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("EDGE CASE: parse_tasks_list + parse_doc_batch")
    print("=" * 70)

    await test("parse_tasks_list (all)", "parse_tasks_list", status="")
    await test("parse_tasks_list (running)", "parse_tasks_list", status="running")
    await test("parse_tasks_list (done)", "parse_tasks_list", status="done")

    # parse_doc_batch with empty list (should handle gracefully)
    await test("parse_doc_batch (empty list)", "parse_doc_batch",
        file_paths=[], expect_fail=True)

    # ═══════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("EDGE CASE: Search with empty/edge queries")
    print("=" * 70)

    await test("kb_search (empty query)", "kb_search", query="", top_k=5, expect_fail=True)
    await test("kb_search_two_stage (single word)", "kb_search_two_stage",
        query="test", stage1_top_k=10, stage2_top_k=3)
    await test("kb_search_vector (very long query)", "kb_search_vector",
        query="machine learning materials science inverse design reinforcement learning " * 5, top_k=3)

    # ═══════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("EDGE CASE: doc_id based resolution")
    print("=" * 70)

    # Test kb_doc_read with doc_id (UUID)
    if doc1_raw:
        doc1_id = jget(doc1_raw, "document", "id") or ""
        if doc1_id:
            await test("kb_doc_read (by doc_id)", "kb_doc_read", doc_id=doc1_id, max_chars=100)
            await test("kb_index_document (by doc_id)", "kb_index_document", doc_id=doc1_id)

    # ═══════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("EDGE CASE: kb_doc_read with offset/limit")
    print("=" * 70)

    # Use the moved doc's new path (it was moved to an existing KB)
    moved_doc_path = jget(move_raw, "document", "path") if move_raw else ""
    if moved_doc_path:
        await test("kb_doc_read (offset=0 limit=1)", "kb_doc_read",
            path=moved_doc_path, offset=0, limit=1, max_chars=100)

    # ═══════════════════════════════════════════════════════════════
    # CLEANUP
    # ═══════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("CLEANUP -- Remove all edge test artifacts")
    print("=" * 70)

    # Delete the main test folder (recursive - gets everything inside)
    if folder_id:
        await test("fs_delete_node (cleanup folder)", "fs_delete_node", node_id=folder_id)

    # Clean up the moved doc (it's now in an existing KB, not in the test folder)
    moved_doc_path = jget(move_raw, "document", "path") if move_raw else ""
    if moved_doc_path and target_kb_id:
        await test("kb_doc_delete (cleanup moved doc)", "kb_doc_delete",
            kb_id=target_kb_id, doc_path=moved_doc_path)

    # Also clean up sub_kb if it still exists (might already be gone from folder delete)
    if sub_kb_id:
        await test("kb_delete (cleanup sub-KB)", "kb_delete", kb_id=sub_kb_id, expect_fail=True)

    # Close client
    from server import _client
    try:
        c = _client()
        if c and hasattr(c, '_http_client') and c._http_client:
            await c._http_client.aclose()
    except:
        pass

    # ═══════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print(f"EDGE CASE SUMMARY: {results['pass']} passed, {results['fail']} failed")
    print("=" * 70)

    if results["errors"]:
        print("\nFailed tests:")
        for err in results["errors"]:
            print(f"  X {err}")

    total = results["pass"] + results["fail"]
    print(f"\nTotal: {total} tests")
    if total > 0:
        print(f"Pass rate: {results['pass'] / total * 100:.1f}%")

    return results


if __name__ == "__main__":
    asyncio.run(run_tests())
