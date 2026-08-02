# -*- coding: utf-8 -*-
"""
kb-mcp MCP Server
=================
Thin MCP tool layer over kb_client.KbClient.

This server defines MCP tools. Each tool is a one-liner that
delegates to the matching KbClient method. All HTTP logic lives in
kb_client/client.py ??this file contains zero HTTP code.

Long-running parse jobs (parse_doc / parse_doc_batch)
are NON-BLOCKING: they hand the slow work to an in-process background
task (task_registry) and return a task_id immediately. Poll results with
parse_task_status(task_id).

Run:
  python server.py            # stdio mode (for Agent harness)
  python server.py --http     # SSE mode
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys

from mcp.server.fastmcp import FastMCP

from kb_client import KbClient

import task_registry
import project_manager

mcp = FastMCP("kb-mcp")

# Singleton client (shared across all tool calls for connection pooling)
_kb: KbClient | None = None


def _client() -> KbClient:
    global _kb
    if _kb is None:
        import config
        _kb = KbClient(
            web_url=config.WEB_URL,
            backend_url=config.BACKEND_URL
        )
    return _kb


def _j(data) -> str:
    """Serialize to compact JSON string."""
    return json.dumps(data, ensure_ascii=False)


def _require_kb(kb_id: str) -> str | None:
    """MCP tool input validation: return error JSON if kb_id is empty, None otherwise.

    Prevents empty kb_id from producing double-slash URLs (/api/.../{empty}//...)
    that result in opaque HTTP 404 errors for the calling agent.
    """
    if not kb_id or not kb_id.strip():
        return _j({"success": False, "error": "kb_id is required and cannot be empty", "status": 400})
    return None


def _require_param(name: str, value: str) -> str | None:
    """MCP tool input validation: return error JSON if value is empty, None otherwise."""
    if not value or not value.strip():
        return _j({"success": False, "error": f"{name} is required and cannot be empty", "status": 400})
    return None


async def _auto_index_doc(kb_id: str, doc_path: str) -> None:
    """Fire-and-forget: index a document (vector + graph) after create/update.

    Runs in background via task_registry.submit(). Silently catches errors
    so a failed index never blocks the create/update response."""
    try:
        await _client().index_document(kb_id, doc_path)
    except Exception as exc:
        print(f"[auto-index] WARNING: index failed for {kb_id}/{doc_path}: {exc}", file=sys.stderr)

async def _auto_unindex_doc(kb_id: str, doc_path: str) -> None:
    """Fire-and-forget: clean graph + vectors for a deleted document.

    Runs in background; silently catches errors so cleanup failure
    never blocks the delete response."""
    try:
        await _client().delete_document_vectors(kb_id, doc_path)
    except Exception as exc:
        print(f"[auto-unindex] WARNING: vector cleanup failed for {kb_id}/{doc_path}: {exc}", file=sys.stderr)
    try:
        await _client().graph_delete_document(doc_path)
    except Exception as exc:
        print(f"[auto-unindex] WARNING: graph cleanup failed for {kb_id}/{doc_path}: {exc}", file=sys.stderr)

async def _auto_unindex_kb(kb_id: str) -> None:
    """Fire-and-forget: clean graph + vectors for a deleted KB.

    Runs in background; silently catches errors so cleanup failure
    never blocks the delete response."""
    try:
        await _client().delete_kb_vectors(kb_id)
    except Exception as exc:
        print(f"[auto-unindex] WARNING: vector cleanup failed for KB {kb_id}: {exc}", file=sys.stderr)
    try:
        await _client().graph_delete_kb(kb_id)
    except Exception as exc:
        print(f"[auto-unindex] WARNING: graph cleanup failed for KB {kb_id}: {exc}", file=sys.stderr)


def _norm(s: str) -> str:
    return (s or "").replace("\\", "/").strip().lower()


async def _resolve_kb_aliases(client, kb_id: str) -> set[str]:
    """Resolve a kb_id to the set of all its identifiers (UUID, path, name).

    The backend's experience search returns hits keyed by ``kb_path``, but
    callers may pass any of UUID/path/name as ``kb_id``. Returning all forms
    lets the scope filter match regardless of which form the caller used.
    Falls back to just the normalised kb_id if the catalog fetch fails.
    """
    aliases = {_norm(kb_id)}
    try:
        # Allow tests to inject a precomputed catalog via attribute hook.
        catalog = getattr(client, "_kb_aliases", None)
        if catalog is None:
            data = await client.kb_list()
            catalog = data.get("knowledgeBases", []) if isinstance(data, dict) else []
        for kb in catalog:
            ids = [kb.get("kbId"), kb.get("kb_id"), kb.get("id"), kb.get("path"), kb.get("name")]
            if _norm(kb_id) in {_norm(x) for x in ids if x}:
                for x in ids:
                    if x:
                        aliases.add(_norm(x))
                break
    except Exception:
        pass
    return aliases


async def _kb_exists(client, kb_id: str) -> bool:
    """Check if a kb_id (UUID or path) corresponds to a known KB (root or sub)."""
    if not kb_id or not kb_id.strip():
        return False
    kb_id_norm = _norm(kb_id)
    try:
        data = await client.kb_list()
        if isinstance(data, dict):
            for kb in data.get("knowledgeBases", []):
                if (_norm(kb.get("kbId", "")) == kb_id_norm or
                    _norm(kb.get("id", "")) == kb_id_norm or
                    _norm(kb.get("path", "")) == kb_id_norm or
                    _norm(kb.get("name", "")) == kb_id_norm):
                    return True
        tree = await client.fs_get_tree()
        def _find_in_tree(nodes):
            if not isinstance(nodes, list):
                return False
            for n in nodes:
                if not isinstance(n, dict):
                    continue
                if n.get("isKnowledgeBase") or n.get("is_knowledge_base"):
                    nid = n.get("id") or n.get("node_id", "")
                    npath = n.get("path") or n.get("name", "")
                    if (_norm(nid) == kb_id_norm or
                        _norm(npath) == kb_id_norm or
                        _norm(n.get("name", "")) == kb_id_norm):
                        return True
                if _find_in_tree(n.get("children", [])):
                    return True
            return False
        tree_list = tree if isinstance(tree, list) else ([tree] if isinstance(tree, dict) else [])
        if _find_in_tree(tree_list):
            return True
    except Exception:
        pass
    return False


def _matches_any_alias(exp: dict, aliases: set[str]) -> bool:
    """True if the experience's kb_id/kb_path matches any alias."""
    for field in ("kb_id", "kb_path", "kb_name"):
        if _norm(exp.get(field, "")) in aliases:
            return True
    return False


def _exists(file_path: str) -> bool:
    from pathlib import Path
    return bool(file_path) and Path(file_path).exists()


def _running_payload(task_id: str, kind: str, detail: dict | None = None,
                     message: str = "parsing task is running; call parse_task_status to get the result") -> str:
    """Immediate 'task is running' reply returned for non-blocking tools."""
    payload = {
        "success": True,
        "status": "running",
        "message": message,
        "task_id": task_id,
        "kind": kind,
    }
    if detail:
        payload.update(detail)
    return _j(payload)


# ────────────────────────────────────────────────────────────────
# NOTE: All MCP tools are ATOMIC operations.
# Each tool does ONE thing only. Complex workflows (parse → upload → index)
# are orchestrated by skills, NOT by the API layer.
# ────────────────────────────────────────────────────────────────


# ============================================================
# HEALTH
# ============================================================

async def health_check() -> str:
    """Combined health check for backend, web, and MinerU services.

    Returns {backend, web, mineru, all_ok} as a JSON string.
    Convenience wrapper for the E2E test and internal diagnostics;
    agents should use the backend_status MCP tool instead.
    """
    return _j(await _client().health_check())

# ============================================================
# KNOWLEDGE BASE MANAGEMENT (CRUD)
# ============================================================

@mcp.tool()
async def kb_list(lightweight: bool = False) -> str:
    """List all knowledge bases with id, name, description, and document count.

    Set lightweight=True for a minimal catalog [{kb_id, name, description, doc_count, path, parent_id}]
    that keeps agent context clean (no file_size/tags/vector_index metadata).
    Default lightweight=False returns the full backend response enriched with sub-KBs."""
    client = _client()
    data = await client.kb_list()
    top_kbs = (data.get("knowledgeBases", []) if isinstance(data, dict) else [])

    # Fetch sub-KBs from the full tree (kb_list alone returns only root KBs)
    sub_kbs = []
    try:
        tree = await client.fs_get_tree()
        def _collect_kb_nodes(nodes):
            if not isinstance(nodes, list):
                return
            for n in nodes:
                if not isinstance(n, dict):
                    continue
                if n.get("isKnowledgeBase") or n.get("is_knowledge_base"):
                    nid = n.get("id") or n.get("node_id")
                    parent_id = n.get("parentId") or n.get("parent_id") or ""
                    if nid and parent_id:
                        sub_kbs.append({
                            "kbId": nid,
                            "path": n.get("path") or n.get("name", ""),
                            "name": n.get("name") or n.get("path", ""),
                            "description": "",
                            "documentCount": 0,
                            "parentId": parent_id,
                        })
                _collect_kb_nodes(n.get("children", []))
        tree_list = tree if isinstance(tree, list) else ([tree] if isinstance(tree, dict) else [])
        _collect_kb_nodes(tree_list)
    except Exception:
        pass

    if lightweight:
        if not isinstance(data, dict) or not data.get("success"):
            return _j(data)
        catalog = [{
            "kb_id": kb.get("kbId") or kb.get("path"),
            "name": kb.get("name") or kb.get("path"),
            "description": kb.get("description", ""),
            "doc_count": kb.get("documentCount", 0),
            "path": kb.get("path", ""),
            "parent_id": kb.get("parentId", ""),
        } for kb in top_kbs]
        for skb in sub_kbs:
            catalog.append({
                "kb_id": skb["kbId"],
                "name": skb["name"],
                "description": skb.get("description", ""),
                "doc_count": skb.get("documentCount", 0),
                "path": skb.get("path", ""),
                "parent_id": skb.get("parentId", ""),
            })
        return _j({"success": True, "count": len(catalog), "catalog": catalog})

    if isinstance(data, dict) and "knowledgeBases" in data:
        for skb in sub_kbs:
            data["knowledgeBases"].append(skb)
        data["count"] = len(data["knowledgeBases"])
    return _j(data)


@mcp.tool()
async def kb_create(name: str, description: str = "", parent_id: str = "") -> str:
    """Create a new knowledge base. parent_id is an optional tree folder UUID for nesting (omit for root). Returns knowledgeBase with id (UUID) and path -- both work as kb_id in other tools."""
    return _j(await _client().kb_create(name, description, parent_id))


@mcp.tool()
async def kb_update(kb_id: str, name: str = "", description: str = "") -> str:
    """Update a knowledge base's name and/or description. kb_id accepts path or UUID."""
    if (err := _require_kb(kb_id)): return err
    return _j(await _client().kb_update(kb_id, name, description))


@mcp.tool()
async def kb_delete(kb_id: str) -> str:
    """Delete an entire knowledge base and all its contents (irreversible). kb_id accepts either the path string or the UUID returned by kb_create."""
    if (err := _require_kb(kb_id)): return err
    result = await _client().kb_delete(kb_id)
    # Fire-and-forget: clean up graph + vectors
    asyncio.create_task(_auto_unindex_kb(kb_id))
    return _j(result)


@mcp.tool()
async def kb_search(query: str, top_k: int = 10) -> str:
    """Search KB metadata by keyword across ALL knowledge bases. Scans only document
    name and description (NOT the full document body or path). Returns ranked hits
    with scores where name match > description match.

    USE CASE: quick metadata lookup when you already have a specific doc name in
    mind and want to find which KB it lives in. For semantic content retrieval,
    prefer kb_search_vector or kb_search_two_stage.

    This is NOT a full-text content search. It does NOT read document bodies."""
    return _j(await _client().kb_search(query, top_k))


@mcp.tool()
async def kb_get_documents(kb_id: str, lightweight: bool = False) -> str:
    """List all documents inside a knowledge base. kb_id accepts path or UUID.

    Set lightweight=True for a minimal catalog [{doc_path, name, description}]
    that keeps agent context clean (no file_size/tags/vector_index metadata).
    Default lightweight=False returns the full backend response."""
    if (err := _require_kb(kb_id)): return err
    client = _client()
    if not await _kb_exists(client, kb_id):
        return _j({"success": False, "error": f"knowledge base not found: {kb_id}"})
    if lightweight:
        data = await client.kb_get_documents(kb_id)
        if not isinstance(data, dict) or not data.get("success"):
            return _j(data)
        catalog = [{
            "doc_path": d.get("path"),
            "name": d.get("name"),
            "description": d.get("description", ""),
        } for d in data.get("documents", [])]
        return _j({"success": True, "kb_id": kb_id, "count": len(catalog), "catalog": catalog})
    return _j(await client.kb_get_documents(kb_id))


# ============================================================
# DOCUMENT MANAGEMENT (CRUD)
# ============================================================

@mcp.tool()
async def kb_doc_read(kb_id: str = "", doc_path: str = "", path: str = "", doc_id: str = "", max_chars: int = 20000, offset: int = 0, limit: int = 200) -> str:
    """Read the content of a document (Markdown body, paginated).

    Accepts one of:
    - doc_id: document UUID (preferred, resolves automatically)
    - kb_id+doc_path (bare filename or relative, e.g. kb_id="uuid" doc_path="readme.md")
    - path (full relative path, e.g. "test/readme.md")

    max_chars limits response size."""
    return _j(await _client().kb_doc_read(kb_id, doc_path, path, max_chars, offset, limit, doc_id))


@mcp.tool()
async def kb_doc_create(kb_id: str, name: str, content: str, description: str = "") -> str:
    """Create a new Markdown document in a KB. Auto-dedup on name collision.

    **Atomic**: ONLY creates the document (file + .tree-fs.json + .knowledge-base.yml with file ID).
    Automatically triggers background indexing (vector + graph) after creation.
    Indexing is fire-and-forget: the create returns immediately while indexing runs in background.
    Use kb_index_document to force re-index if needed."""
    if (err := _require_kb(kb_id)): return err
    result = await _client().kb_doc_create(kb_id, name, content, description)
    # Fire-and-forget auto-indexing
    if isinstance(result, dict) and result.get("success"):
        doc = result.get("document", {})
        doc_path = doc.get("path", "")
        if doc_path:
            task_id = task_registry.submit(
                _auto_index_doc(kb_id, doc_path),
                kind="auto-index",
                meta={"kb_id": kb_id, "doc_path": doc_path, "action": "create"}
            )
            result["_auto_index"] = {"triggered": True, "task_id": task_id, "note": "Background indexing (vector+graph) started. Check with parse_task_status if needed."}
    return _j(result)


@mcp.tool()
async def kb_doc_update_meta(kb_id: str, doc_path: str, name: str = "", description: str = "") -> str:
    """Update a document's metadata (name, description)."""
    if (err := _require_kb(kb_id)): return err
    if (err := _require_param("doc_path", doc_path)): return err
    return _j(await _client().kb_doc_update_meta(kb_id, doc_path, name, description))


@mcp.tool()
async def kb_doc_update_content(kb_id: str, doc_path: str, content: str) -> str:
    """Overwrite a document's content.

    **Atomic**: ONLY updates the file content + syncs .tree-fs.json + .knowledge-base.yml.
    Automatically triggers background re-indexing (vector + graph) after update.
    Indexing is fire-and-forget: the update returns immediately while indexing runs in background.
    Use kb_index_document to force re-index if needed."""
    if (err := _require_kb(kb_id)): return err
    if (err := _require_param("doc_path", doc_path)): return err
    result = await _client().kb_doc_update_content(kb_id, doc_path, content)
    # Fire-and-forget auto-reindexing
    if isinstance(result, dict) and result.get("success"):
        task_id = task_registry.submit(
            _auto_index_doc(kb_id, doc_path),
            kind="auto-index",
            meta={"kb_id": kb_id, "doc_path": doc_path, "action": "update"}
        )
        result["_auto_index"] = {"triggered": True, "task_id": task_id, "note": "Background re-indexing (vector+graph) started. Check with parse_task_status if needed."}
    return _j(result)


@mcp.tool()
async def kb_doc_delete(kb_id: str, doc_path: str) -> str:
    """Delete a single document.

    Removes file from disk + .tree-fs.json + .knowledge-base.yml.
    Automatically cleans up vector chunks and graph nodes (fire-and-forget)."""
    if (err := _require_kb(kb_id)): return err
    if (err := _require_param("doc_path", doc_path)): return err
    result = await _client().kb_doc_delete(kb_id, doc_path)
    # Fire-and-forget: clean up graph + vectors (don't block the response)
    asyncio.create_task(_auto_unindex_doc(kb_id, doc_path))
    return _j(result)


@mcp.tool()
async def kb_doc_batch_delete(kb_id: str, doc_paths: list) -> str:
    """Delete multiple documents at once."""
    result = await _client().kb_doc_batch_delete(kb_id, doc_paths)
    # Fire-and-forget: clean up graph + vectors for each doc
    for dp in doc_paths:
        asyncio.create_task(_auto_unindex_doc(kb_id, dp))
    return _j(result)


@mcp.tool()
async def kb_doc_move(doc_path: str, target_kb_id: str) -> str:
    """Move a document to a different knowledge base.

    Moves the file on disk, syncs .tree-fs.json + .knowledge-base.yml (both
    source and target KB), and automatically triggers reindexing:
    - Deletes old vector chunks + graph node at the original path
    - Indexes the document at the new path (vector + graph)

    The reindex is fire-and-forget (non-blocking). For critical moves, verify
    with kb_search_vector or kb_graph_document afterward."""
    if (err := _require_param("doc_path", doc_path)): return err
    if (err := _require_kb(target_kb_id)): return err
    return _j(await _client().kb_doc_move(doc_path, target_kb_id))


# ============================================================
# FILE SYSTEM OPERATIONS
# ============================================================

@mcp.tool()
async def fs_get_tree(include_files: bool = True, max_depth: int = 0) -> str:
    """Get the full file system tree of knowledge bases and their contents.

    Returns the complete tree-schema starting from root folders, with
    recursive nesting. Set include_files=False to see only folder structure.
    Set max_depth>0 to limit nesting depth (1=root KBs only, 2=KB+first
    level children, etc.). 0 means unlimited.
    Response includes _stats: {folders, files, total} count metadata."""
    tree = await _client().fs_get_tree()
    count_data = await _client().fs_get_count()

    def _filter(nodes, depth=1):
        out = []
        for n in nodes:
            node_type = n.get("type", "")
            if not include_files and node_type == "file":
                continue
            copy = {k: v for k, v in n.items() if k != "children"}
            children = n.get("children", [])
            if not include_files:
                children = [c for c in children if c.get("type") == "folder"]
            if len(children) > 0 and (0 == max_depth or depth < max_depth):
                copy["children"] = _filter(children, depth + 1)
            elif len(children) == 0:
                copy["children"] = []
            out.append(copy)
        return out

    result = _filter(tree)
    if isinstance(count_data, dict):
        result_with_stats = {"tree": result, "_stats": count_data}
    else:
        result_with_stats = {"tree": result}
    return _j(result_with_stats)


@mcp.tool()
async def fs_get_children(parent_id: str = "") -> str:
    """Get immediate children (folders + files) of a folder."""
    client = _client()
    if parent_id and parent_id.strip():
        import uuid as _uuid_mod
        try:
            _uuid_mod.UUID(parent_id)
        except ValueError:
            try:
                tree = await client.fs_get_tree()
                def _find_folder(nodes, target):
                    if not isinstance(nodes, list):
                        return None
                    for n in nodes:
                        if not isinstance(n, dict):
                            continue
                        npath = _norm(n.get("path") or n.get("name", ""))
                        if npath == _norm(target):
                            return n.get("id") or n.get("node_id")
                        found = _find_folder(n.get("children", []), target)
                        if found:
                            return found
                    return None
                tree_list = tree if isinstance(tree, list) else ([tree] if isinstance(tree, dict) else [])
                resolved = _find_folder(tree_list, parent_id)
                if resolved:
                    return _j(await client.fs_get_children(resolved))
                return _j({"success": False, "error": f"folder not found: {parent_id}"})
            except Exception as e:
                return _j({"success": False, "error": f"folder resolution failed: {e}"})
    return _j(await client.fs_get_children(parent_id))


@mcp.tool()
async def fs_upload_file(file_path: str, parent_id: str = "", description: str = "") -> str:
    """Upload a local file into the file system tree. file_path is an absolute local disk path. parent_id is a tree folder UUID (empty = root).

    **Atomic**: ONLY uploads the file + writes .tree-fs.json + .knowledge-base.yml (with file ID).
    Does NOT index. Use kb_index_document separately if needed."""
    return _j(await _client().fs_upload_file(file_path, parent_id, description))


# ============================================================
# PREVIEW
# ============================================================

# ============================================================
# DOCUMENT PARSING  (NON-BLOCKING)
# The MinerU OCR engine runs alongside the backend — no manual
# startup needed. Each parse call returns a task_id immediately;
# poll parse_task_status(task_id) for the result.
# Supported formats: .pdf .png .jpg .jpeg .docx .xlsx
# ============================================================

@mcp.tool()
async def parse_doc(file_path: str, use_ocr: bool = True) -> str:
    """Parse a document (PDF / Image / Word / Excel) into Markdown.

    **Atomic**: ONLY parses the file and returns the markdown content + paths.
    Does NOT save to KB, does NOT index.
    After parsing, use kb_doc_create or fs_upload_file to save the markdown,
    then kb_index_document to index.

    NON-BLOCKING: returns a task_id immediately; poll with parse_task_status.

    Supported formats: .pdf .png .jpg .jpeg .docx .xlsx

    Returns {success, status:'running', task_id} right away.
    When done, result holds {markdown, markdown_path, images_dir, ...}.
    """
    if not _exists(file_path):
        return _j({"success": False, "error": f"file not found: {file_path}"})
    client = _client()
    meta = {"file_path": file_path, "use_ocr": use_ocr}

    async def _work():
        result = await client.parse_doc(file_path, use_ocr=use_ocr)
        if isinstance(result, dict) and result.get("success"):
            return {
                "success": True,
                "source_filename": result.get("source_filename"),
                "markdown_path": result.get("markdown_path"),
                "images_dir": result.get("images_dir") or result.get("image_dir"),
                "image_count": result.get("image_count"),
                "markdown": result.get("markdown", ""),
                "markdown_chars": len(result.get("markdown", "") or ""),
                "parse_method": result.get("parse_method"),
            }
        return result

    task_id = task_registry.submit(_work(), "parse_doc", meta)
    return _running_payload(task_id, "parse_doc", {"file_path": file_path})


@mcp.tool()
async def parse_doc_batch(file_paths: list, use_ocr: bool = True) -> str:
    """Batch: parse multiple documents (PDF / Image / Word / Excel) into Markdown.

    **Atomic**: ONLY parses files and returns markdown results.
    Does NOT save to KB, does NOT index, does NOT auto-describe.
    After parsing, use kb_doc_create or fs_upload_file for each file,
    then kb_batch_index to index.

    NON-BLOCKING: all files parse sequentially in ONE background task.
    Poll with parse_task_status(task_id).
    When done the result is {total, successful, results:[...]}.

    Supported formats: .pdf .png .jpg .jpeg .docx .xlsx"""
    missing = [fp for fp in file_paths if not _exists(fp)]
    if missing:
        return _j({"success": False, "error": "file(s) not found", "missing": missing})
    client = _client()
    meta = {"file_paths": list(file_paths), "use_ocr": use_ocr}

    async def _batch_work():
        """Parse batch only — no save, no index, no quality check."""
        parse_result = await client.parse_doc_batch(file_paths, use_ocr=use_ocr)
        return parse_result

    task_id = task_registry.submit(
        _batch_work(),
        "parse_doc_batch",
        meta,
    )
    return _running_payload(
        task_id, "parse_doc_batch", {"file_count": len(file_paths)}
    )


@mcp.tool()
async def parse_task_status(task_id: str) -> str:
    """Check the status of a non-blocking parse task.

    status is 'running', 'done', or 'error'. When done, result holds the
    parse summary (markdown_path, image_count, ...). When error, error
    holds the message. Use this to poll tasks from parse_doc* tools.

    Full markdown content is omitted from the response to keep it compact;
    use kb_doc_save_parsed(task_id) to persist the parsed content into a KB.
    """
    rec = task_registry.get(task_id)
    if rec is None:
        return _j({"success": False, "error": f"unknown task_id: {task_id}"})
    view = task_registry.public_view(rec)
    # Slim: strip full markdown from parse results; keep stats only
    if isinstance(view, dict) and view.get("status") == "done":
        result = view.get("result")
        if isinstance(result, dict) and "markdown" in result:
            slimmed = {}
            for k, v in result.items():
                if k == "markdown":
                    slimmed["markdown_omitted"] = True
                    slimmed["markdown_length"] = len(v) if isinstance(v, str) else 0
                elif k in ("markdown_path", "image_count", "source_filename",
                           "method", "chars", "pages", "status", "kind"):
                    slimmed[k] = v
                else:
                    slimmed[k] = v
            view["result"] = slimmed
    view["success"] = True
    return _j(view)

@mcp.tool()
async def kb_task_status(task_id: str) -> str:
    """Check the status of ANY non-blocking background task (kb_reindex, kb_graph_build).

    status is 'running', 'done', or 'error'. When done, result holds the task output
    (reindex stats, graph relations, etc.). Works for all task_registry tasks including
    parse_doc and meditation_run — use this as the universal task poller.
    Parse task results have markdown content omitted (use kb_doc_save_parsed for full content).
    """
    rec = task_registry.get(task_id)
    if rec is None:
        return _j({"success": False, "error": f"unknown task_id: {task_id}"})
    view = task_registry.public_view(rec)
    # Slim parse results: omit full markdown
    if isinstance(view, dict) and view.get("status") == "done":
        result = view.get("result")
        if isinstance(result, dict) and "markdown" in result:
            slimmed = {}
            for k, v in result.items():
                if k == "markdown":
                    slimmed["markdown_omitted"] = True
                    slimmed["markdown_length"] = len(v) if isinstance(v, str) else 0
                elif k in ("markdown_path", "image_count", "source_filename",
                           "method", "chars", "pages", "status", "kind"):
                    slimmed[k] = v
                else:
                    slimmed[k] = v
            view["result"] = slimmed
    view["success"] = True
    return _j(view)


@mcp.tool()
async def kb_doc_save_parsed(
    parent_id: str,
    task_id: str = "",
    markdown: str = "",
    markdown_path: str = "",
    images_dir: str = "",
    source_filename: str = "",
    description: str = "",
    parse_method: str = "",
) -> str:
    """Save parsed markdown (FULL content + images) into a knowledge base.

    This is the PREFERRED way to store parsed documents — it writes the
    complete markdown content (not truncated) AND copies all parsed images
    to the KB's images/ folder. Use this instead of kb_doc_create for
    parse-path documents.

    Two modes:
    1. **task_id mode** (recommended): pass task_id from parse_doc/parse_doc_batch.
       The tool reads the full parse result (markdown + images_dir + source_filename)
       from the task registry automatically.
    2. **manual mode**: pass markdown/markdown_path/images_dir/source_filename directly.

    Args:
        parent_id: Target KB or folder UUID.
        task_id: Parse task ID from parse_doc() (preferred — auto-extracts all fields).
        markdown: Full parsed markdown content (manual mode; omit if using task_id).
        markdown_path: Path to .md file on disk (manual mode fallback).
        images_dir: Path to parsed images directory (manual mode).
        source_filename: Original filename, e.g. "paper.pdf" (manual mode).
        description: Document description (from content analysis).
        parse_method: Parse method used (auto, ocr, etc.).

    Returns:
        {success, savedCount, files: [{id, name, path, fileSize, imageCount, ...}]}

    After saving, call kb_index_document(kb_id, doc_path) to build vector+graph index,
    then kb_doc_update_tags(kb_id, doc_path, tags) to assign tags.
    """
    # If task_id is provided, extract full parse result from task registry
    if task_id:
        rec = task_registry.get(task_id)
        if rec is None:
            return _j({"success": False, "error": f"unknown task_id: {task_id}"})
        result = task_registry.public_view(rec)
        if result.get("status") != "done":
            return _j({"success": False, "error": f"task not done (status={result.get('status')})",
                        "task_id": task_id})
        inner = result.get("result", {})

        # Batch parse result: {total, successful, results: [...]}
        # Iterate through each individual result and save all files in one call.
        if isinstance(inner, dict) and "results" in inner and isinstance(inner["results"], list):
            batch_results = []
            for item in inner["results"]:
                if not isinstance(item, dict) or not item.get("success"):
                    continue
                batch_results.append({
                    "success": True,
                    "markdown": item.get("markdown", ""),
                    "markdown_path": item.get("markdown_path", ""),
                    "images_dir": item.get("images_dir") or item.get("image_dir", ""),
                    "image_dir": item.get("images_dir") or item.get("image_dir", ""),
                    "source_filename": item.get("source_filename") or item.get("file", ""),
                    "filename": item.get("source_filename") or item.get("file", ""),
                    "description": description,
                    "parse_method": item.get("parse_method", ""),
                })
            if not batch_results:
                return _j({"success": False, "error": "No successful parse results in batch task"})
            return _j(await _client().save_parsed_files(parent_id, batch_results))

        # Single parse result
        if not markdown:
            markdown = inner.get("markdown", "")
        if not markdown_path:
            markdown_path = inner.get("markdown_path", "")
        if not images_dir:
            images_dir = inner.get("images_dir", "")
        if not source_filename:
            source_filename = inner.get("source_filename", "")
        if not parse_method:
            parse_method = inner.get("parse_method", "")

    if not markdown and not markdown_path:
        return _j({"success": False, "error": "No markdown content: provide task_id or markdown/markdown_path"})

    parse_result = {
        "success": True,
        "markdown": markdown,
        "markdown_path": markdown_path,
        "images_dir": images_dir,
        "image_dir": images_dir,  # compat alias
        "source_filename": source_filename,
        "filename": source_filename,
        "description": description,
        "parse_method": parse_method,
    }

    return _j(await _client().save_parsed_files(parent_id, [parse_result]))


# ============================================================
# TAGS MANAGEMENT
# ============================================================

@mcp.tool()
async def kb_tags_list() -> str:
    """List all registered tags in the system."""
    return _j(await _client().kb_tags_list())


@mcp.tool()
async def kb_doc_update_tags(kb_id: str, doc_path: str, tags: list) -> str:
    """Update a document's tags. kb_id accepts UUID; doc_path accepts full path or bare filename."""
    if (err := _require_kb(kb_id)): return err
    if (err := _require_param("doc_path", doc_path)): return err
    return _j(await _client().kb_doc_update_tags(kb_id, doc_path, tags))


@mcp.tool()
async def kb_tags_cleanup(dry_run: bool = True) -> str:
    """Detect and clean up orphan tags (tags referenced by 0 documents).

    Iterates all tags, checks reference counts via kb_doc_get_by_tag, marks 0-reference tags as orphan.
    dry_run=True (default): only lists orphan tags and their count.
    dry_run=False: removes orphan tags from the tag vocabulary (irreversible).

    Blacklist protection: the following tag patterns are never cleaned: domain vocabulary (PET/PVA/polymer etc.), existing KB domain tags.

    Returns:
        dry_run=True: {success, total_tags, referenced, orphan, orphan_tags, orphan_tag_names}
        dry_run=False: {success, total_tags, cleaned, cleaned_tag_names, skipped, errors}
    """
    client = _client()

    # 1. Fetch all tags
    tags_resp = await client.kb_tags_list()
    all_tags = (tags_resp.get("tags", []) if isinstance(tags_resp, dict) else [])
    total = len(all_tags)

    # 2. Blacklist: domain core terms are never cleaned
    protected_patterns = [
        # Polymer/materials core terms
        "pet", "pva", "pp", "pe", "pla", "pa6", "pa56", "bopet", "bopa6", "bopp",
        "uhmwpe", "pvdf", "pmma", "ptfe", "peek", "pc", "pbs", "ps", "sebs",
        "frp", "psp", "sio2", "tio₂", "mxene", "bge-m3",
        # Method/technology core terms
        "深度学习", "机器学习", "强化学习", "transformer", "attention",
        "rag", "graphrag", "self-rag", "llm", "nlp", "dqn", "adam", "shap",
        # Knowledge base domain terms
        "polymer", "双向拉伸", "双轴拉伸", "biaxial-stretching", "高分子",
        "锂离子电池", "钠离子电池", "固态电池", "超级电容器",
        "石墨烯", "2d材料", "超材料", "纳米压痕",
        "医学影像", "医疗器械", "可穿戴设备", "生物材料", "药物递送",
        "电催化", "光催化", "多相催化",
        "行为经济学", "因果推断", "金融风险",
        "缺陷检测", "薄膜", "逆设计", "半导体激光",
        "具身智能", "vla", "世界模型", "人形机器人", "sim-to-real",
        "创造性思维", "creative-thinking", "prism",
        "家常菜", "中式烹饪", "菜谱",
        "经验", "knowledge graph", "知识图谱",
        "e2e", "e2e-test", "integration-test",
    ]

    def _is_protected(tag: str) -> bool:
        tl = tag.lower().strip()
        # Blacklist match (case-insensitive)
        for p in protected_patterns:
            if tl == p.lower():
                return True
        # Length >= 3 and pure Chinese/English academic concept -> protect
        # Length < 3 or contains special characters -> can clean
        return False

    # 3. One-pass analysis: single HTTP call scans all .knowledge-base.yml
    # once (O(M) = ~31 file reads) and returns the full referenced/orphan
    # classification. Replaces the old O(N×M) pattern of N concurrent HTTP
    # probes to kb_doc_get_by_tag (~150 tags × 31 KBs = ~4650 file reads,
    # which reliably exceeded the 30s MCP tool timeout).
    analysis = await client.kb_tags_analysis()
    if not isinstance(analysis, dict) or not analysis.get("success"):
        return _j({"success": False, "error": "tag analysis failed", "detail": str(analysis)[:200]})

    backend_orphan = analysis.get("orphan_tags", [])
    backend_referenced = analysis.get("referenced", [])

    # 4. Domain-protection overlay (pure in-memory, no I/O): rescue protected
    # domain-vocabulary tags from the orphan list even if currently 0 refs.
    # The backend already classifies generic garbage (isGarbageTag); this
    # layer adds deployment-specific domain terms (PET/PVA/具身智能 etc.).
    orphan_tags: list = []
    orphan_tag_names: list = []
    referenced = len(backend_referenced)
    for entry in backend_orphan:
        tag = entry.get("tag", "")
        if _is_protected(tag):
            referenced += 1
            continue
        orphan_tags.append(entry)
        orphan_tag_names.append(tag)

    if dry_run:
        orphan_count = len(orphan_tags)
        return _j({
            "success": True,
            "dry_run": True,
            "total_tags": total,
            "checked": total,
            "referenced": referenced,
            "orphan": orphan_count,
            "orphan_tags": orphan_tags,
            "orphan_tag_names": orphan_tag_names,
            "hint": f"Found {orphan_count} orphan tags (0-referenced / garbage pattern). Use dry_run=False to clean (irreversible)."
        })
    else:
        # dry_run=False: actually remove orphan + garbage tags from the registry.
        # K3 fix: delegates to web DELETE endpoint which purges .tags.json in one pass.
        cleanup_result = await client.kb_tags_cleanup_orphans()
        removed_tags: list = []
        removed_count = 0
        errors: list = []
        if isinstance(cleanup_result, dict) and cleanup_result.get("success"):
            removed_tags = cleanup_result.get("removed", [])
            removed_count = cleanup_result.get("removed_count", len(removed_tags))
        else:
            errors.append({"error": str(cleanup_result)})

        return _j({
            "success": True,
            "dry_run": False,
            "total_tags": total,
            "checked": total,
            "cleaned": removed_count,
            "cleaned_tag_names": removed_tags,
            "skipped": max(total - removed_count, 0),
            "errors": errors,
            "hint": f"Removed {removed_count} orphan/garbage tags from the registry. "
                    f"Next kb_tags_list() returns only live, non-garbage tags.",
        })


@mcp.tool()
async def kb_doc_get_by_tag(tag: str, kb_id: str = "") -> str:
    """Find documents by tag across all KBs (or one KB if kb_id given)."""
    return _j(await _client().kb_doc_get_by_tag(tag, kb_id))

@mcp.tool()
async def kb_find_duplicates(kb_id: str = "", threshold: float = 0.90) -> str:
    """Find duplicate / near-duplicate documents via content hash + vector similarity.

    Two-layer detection:
      1. EXACT: SHA256 of normalized content (whitespace-trimmed, lowercase).
      2. NEAR: vector similarity >= threshold (default 0.90) within the same KB.

    Args:
        kb_id: scope to one KB (path or UUID). Empty = scan ALL KBs (slower).
        threshold: vector similarity cutoff for near-dup (0.85-0.95 recommended).

    Returns grouped duplicate clusters with recommendation (keep newest, merge tags).
    """
    import hashlib

    client = _client()

    # 1. Gather all KBs to scan. For a parent KB, also include its sub-KBs.
    kbs_to_scan: list = []
    if kb_id:
        # Direct docs of the specified KB
        kbs_to_scan.append((kb_id, await client.kb_get_documents(kb_id)))
        # If it has sub-KBs, include their docs too (parent KBs have 0 direct docs)
        try:
            overview = await client.graph_kb_overview(kb_id)
            if isinstance(overview, dict) and overview.get("success"):
                for sub in overview.get("overview", {}).get("sub_kbs", []):
                    sub_id = sub.get("kb_id", "")
                    if sub_id and sub_id != kb_id:
                        kbs_to_scan.append((sub_id, await client.kb_get_documents(sub_id)))
        except Exception:
            pass  # not a parent KB or graph unavailable
    else:
        list_resp = await client.kb_list()
        if isinstance(list_resp, dict):
            for kb in list_resp.get("knowledgeBases", []):
                kid = kb.get("kbId") or kb.get("id") or kb.get("path", "")
                if not kid: continue
                kbs_to_scan.append((kid, await client.kb_get_documents(kid)))

    # 2. Phase A: exact-hash dedup — read content, normalize, hash.
    # OPTIMIZATION: pre-filter by file_size so we only read content for
    # size-similar candidates. 170 docs → ~10-20 candidates instead of 170.
    size_buckets: dict[int, list[tuple]] = {}  # rounded_size -> [(kid, dp, dname, fsize)]
    all_docs: list[tuple] = []  # (kb_id, doc_path, doc_name, file_size)

    for kid, resp in kbs_to_scan:
        if not isinstance(resp, dict) or not resp.get("success"): continue
        for doc in resp.get("documents", []):
            dp = doc.get("path", "")
            if not dp or doc.get("file_type") == "knowledge-base": continue
            fsize = doc.get("file_size", 0)
            all_docs.append((kid, dp, doc.get("name", ""), fsize))
            # Bucket by rounded size (±5% tolerance via integer division)
            if fsize > 0:
                bucket = max(1, round(fsize / 50) * 50)  # 50-byte buckets
                size_buckets.setdefault(bucket, []).append((kid, dp, doc.get("name", ""), fsize))

    hash_groups: dict[str, list] = {}
    exact_dup_pairs: list = []

    # Only hash docs that share a size bucket with at least one other doc
    candidates = set()
    for bucket, docs in size_buckets.items():
        if len(docs) > 1:
            for d in docs:
                candidates.add((d[0], d[1]))

    for kid, dp, dname, fsize in all_docs:
        if (kid, dp) not in candidates:
            continue  # unique size → cannot be exact dup, skip content read
        try:
            read_resp = await client.kb_doc_read(kb_id=kid, doc_path=dp, max_chars=5000)
            if not isinstance(read_resp, dict): continue
            content = read_resp.get("content", "")
            if not content or len(content) < 50: continue
            normalized = " ".join(content.lower().split())
            h = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
            hash_groups.setdefault(h, []).append({"kb_id": kid, "doc_path": dp.replace("\\", "/"), "name": dname})
        except Exception:
            continue

    for h, group in hash_groups.items():
        if len(group) > 1:
            exact_dup_pairs.append({
                "type": "exact",
                "similarity": 1.0,
                "documents": group,
                "recommendation": f"Identical content (SHA256 match). Keep one, delete {len(group)-1}.",
            })

    # 3. Phase B: near-dup vector detection — CONCURRENT vector search.
    # OPTIMIZATION: was N sequential (read+search) HTTP round-trips (~170 for
    # 77 docs → 30s MCP timeout). Now all probes fire concurrently via gather.
    exact_paths = set()
    for pair in exact_dup_pairs:
        for d in pair["documents"]:
            exact_paths.add((d["kb_id"], d["doc_path"]))

    near_dup_pairs: list = []
    seen_pairs: set = set()

    # Phase B step 1: concurrently read content + vector-search for all candidates
    async def _near_dup_probe(kid, dp, dname):
        if (kid, dp) in exact_paths:
            return None
        try:
            read_resp = await client.kb_doc_read(kb_id=kid, doc_path=dp, max_chars=500)
            if not isinstance(read_resp, dict):
                return None
            probe_content = read_resp.get("content", "")
            if not probe_content or len(probe_content) < 50:
                return None
            search_resp = await client.vector_search(probe_content[:500], kb_id=kid, top_k=5, score_threshold=threshold)
            if not isinstance(search_resp, dict):
                return None
            return (kid, dp, dname, search_resp.get("results", []))
        except Exception:
            return None

    probe_results = await asyncio.gather(*[_near_dup_probe(k, d, n) for k, d, n, _ in all_docs])

    # Phase B step 2: collect near-dup pairs from concurrent results
    for result in probe_results:
        if result is None:
            continue
        kid, dp, dname, hits = result
        for hit in hits:
            hit_path = hit.get("doc_path", "").replace("\\", "/")
            my_path = dp.replace("\\", "/")
            if hit_path == my_path:
                continue
            score = hit.get("score", 0)
            if score < threshold:
                continue
            pair_key = tuple(sorted([my_path, hit_path]))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)
            near_dup_pairs.append({
                "type": "near",
                "similarity": round(score, 4),
                "documents": [
                    {"kb_id": kid, "doc_path": my_path, "name": dname},
                    {"kb_id": kid, "doc_path": hit_path, "name": hit.get("doc_path", "").replace("\\", "/").split("/")[-1]},
                ],
                "recommendation": f"High vector similarity ({score:.2%}). Read both to confirm, keep the more complete version.",
            })

    all_dups = exact_dup_pairs + near_dup_pairs
    return _j({
        "success": True,
        "kb_id": kb_id or "(all)",
        "docs_scanned": len(all_docs),
        "exact_duplicates": len(exact_dup_pairs),
        "near_duplicates": len(near_dup_pairs),
        "total_duplicate_groups": len(all_dups),
        "duplicate_groups": all_dups,
        "hint": f"Found {len(all_dups)} duplicate group(s). Use kb_doc_delete to remove confirmed duplicates." if all_dups
                else "No duplicates found.",
    })

# ============================================================
# EXPERIENCE MANAGEMENT
# ============================================================

def _detect_query_type(query: str) -> str:
    """Detect query intent type from keywords. No LLM needed."""
    ql = query.lower()
    troubleshoot_kw = ["怎么", "如何", "故障", "报错", "失败", "修复", "排查", "解决",
                        "how to", "fix", "error", "fail", "troubleshoot", "debug", "bug",
                        "不工作", "出问题", "异常", "crash", "timeout"]
    decision_kw = ["选", "对比", "选择", "推荐", "哪个好", "评估", "which", "compare",
                   "recommend", "best option", "方案对比", "优缺点"]
    best_practice_kw = ["最佳实践", "经验", "practice", "pattern", "规范", "标准流程",
                        "best way", "推荐做法", "标准做法"]

    if any(kw in ql for kw in troubleshoot_kw):
        return "troubleshooting"
    if any(kw in ql for kw in decision_kw):
        return "decision"
    if any(kw in ql for kw in best_practice_kw):
        return "best_practice"
    return "learning"


def _tokenize_for_match(text: str) -> list:
    """Tokenize text for matching. Supports CJK bigram + English words."""
    text = text.lower().strip()
    tokens = []
    for part in text.split():
        if not part:
            continue
        has_cjk = any('一' <= ch <= '鿿' for ch in part)
        if has_cjk:
            cjk_chars = [ch for ch in part if '一' <= ch <= '鿿' or ch.isalnum()]
            for i in range(len(cjk_chars) - 1):
                tokens.append("".join(cjk_chars[i:i+2]))
        for w in part.replace('/', ' ').replace('-', ' ').split():
            if len(w) >= 2:
                tokens.append(w)
    seen = set()
    result = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            result.append(t)
    return result


def _compute_match_details(query: str, exp: dict) -> dict:
    """Compute detailed match information for retrieval transparency."""
    query_tokens = _tokenize_for_match(query)
    title = exp.get("title", "").lower()
    scenario = exp.get("scenario", "").lower()
    tags = [t.lower() for t in exp.get("tags", [])]

    combined = f"{title} {scenario} {' '.join(tags)}"
    domain_match = [t for t in query_tokens if t in combined]
    problem_match = [t for t in query_tokens if t in exp.get("problem", "").lower()]

    return {
        "domain_match": domain_match[:5],
        "problem_match": problem_match[:5],
        "coverages": {
            "domain": round(len(domain_match) / max(len(query_tokens), 1), 2),
            "problem": round(len(problem_match) / max(len(query_tokens), 1), 2),
        }
    }


def _compute_ranking_reason(exp: dict) -> str:
    """Generate human-readable ranking reason."""
    parts = []
    tier = exp.get("tier", "")
    rating = exp.get("rating_avg", 0)
    applied = exp.get("applied_count", 0)
    vector_score = exp.get("vector_score", 0)
    content_score = exp.get("content_score", 0)

    if vector_score >= 0.65:
        parts.append("high-semantic-match")
    if content_score >= 6:
        parts.append("high-content-relevance")
    if rating >= 4:
        parts.append(f"high-rating({rating})")
    if applied >= 2:
        parts.append(f"verified({applied}x)")
    if tier == "P0":
        parts.insert(0, "P0-strong-evidence")

    return "; ".join(parts) if parts else f"tier={tier}"


@mcp.tool()
async def experience_create(kb_id: str, title: str, scenario: str = "",
    category: str = "tip", problem: str = "", solution: str = "",
    result: str = "success", key_lessons: list = None, tags: list = None,
    severity: str = "normal", related_docs: list = None,
    prerequisites: list = None, metrics: str = "") -> str:
    """Create an experience record.

    An experience is reusable knowledge distilled from practice. Compared to documents, experiences have rating, application records, scenario binding, etc.
    Each experience includes: problem description, solution, key lessons (actionable items list), result (success/failure),
    severity (critical/important/normal/tip), scenario identifier, related documents, etc.

    Args:
        kb_id: Knowledge base ID or path
        title: Experience title
        scenario: Scenario identifier (e.g. "coal-mill-fault-prediction"), used for scenario-based retrieval
        category: Category (best_practice, troubleshooting, lesson_learned, optimization, tip, workflow, decision)
        problem: Description of the problem to solve
        solution: Solution or operation steps
        result: Result (success, partial, failed, inconclusive)
        key_lessons: List of key lessons — each should be an independently actionable item
        tags: List of tags
        severity: Severity (critical, important, normal, tip)
        related_docs: List of related document paths (e.g. ["Thermal-Power/doc1.md"])
        prerequisites: List of prerequisites
        metrics: JSON string of custom quantitative metrics (e.g. '{"effectiveness": 95, "difficulty": 60}')

    Returns:
        {success, experience: {id, title, path, scenario, ...}}
    """
    if (err := _require_kb(kb_id)): return err
    if metrics:
        try:
            parsed_metrics = json.loads(metrics)
        except (json.JSONDecodeError, TypeError):
            return _j({"success": False, "error": "Invalid metrics: not valid JSON"})
    else:
        parsed_metrics = {}
    return _j(await _client().experience_create(
        kb_id, title, scenario, category, problem, solution, result,
        key_lessons or [], tags or [], severity, related_docs or [],
        prerequisites or [], parsed_metrics
    ))


@mcp.tool()
async def experience_read(kb_id: str, exp_id: str) -> str:
    """Read full experience information (metadata + content body).

    Args:
        kb_id: Knowledge base ID or path
        exp_id: Experience ID (e.g. "exp-xxxxxxxxxxxx" returned on creation)

    Returns:
        {success, experience: {id, title, ...}, content: "markdown body"}
    """
    if (err := _require_kb(kb_id)): return err
    if (err := _require_param("exp_id", exp_id)): return err
    return _j(await _client().experience_read(kb_id, exp_id))


@mcp.tool()
async def experience_list(kb_id: str, scenario: str = "",
    category: str = "", tag: str = "") -> str:
    """List experiences in a knowledge base, supports filtering by scenario/category/tag. Results sorted by rating descending.

    Args:
        kb_id: Knowledge base ID or path
        scenario: Optional, filter by scenario identifier
        category: Optional, filter by category (best_practice/troubleshooting/lesson_learned/...)
        tag: Optional, filter by tag

    Returns:
        {success, count, experiences: [{id, title, scenario, rating_avg, ...}]}
    """
    if (err := _require_kb(kb_id)): return err
    return _j(await _client().experience_list(kb_id, scenario, category, tag))


@mcp.tool()
async def experience_update(kb_id: str, exp_id: str, title: str = "",
    scenario: str = "", category: str = "", problem: str = "",
    solution: str = "", result: str = "", key_lessons: list = None,
    tags: list = None, severity: str = "", status: str = "",
    related_docs: list = None, prerequisites: list = None,
    metrics: str = "") -> str:
    """Update an experience record. Only pass fields to update; omitted fields stay unchanged.

    Args:
        kb_id: Knowledge base ID or path
        exp_id: Experience ID
        title: New title
        scenario: New scenario identifier
        category: New category
        problem: New problem description
        solution: New solution
        result: New result
        key_lessons: New list of key lessons
        tags: New list of tags
        severity: New severity
        status: New status (draft, published, archived)
        related_docs: New list of related documents
        prerequisites: New list of prerequisites
        metrics: JSON string, new metrics

    Returns:
        {success, experience: {id, title, ...}}
    """
    if (err := _require_kb(kb_id)): return err
    if (err := _require_param("exp_id", exp_id)): return err
    kwargs = {}
    for k, v in [("title", title), ("scenario", scenario), ("category", category),
                 ("problem", problem), ("solution", solution), ("result", result),
                 ("severity", severity), ("status", status)]:
        if v: kwargs[k] = v
    if key_lessons: kwargs["key_lessons"] = key_lessons
    if tags: kwargs["tags"] = tags
    if related_docs: kwargs["related_docs"] = related_docs
    if prerequisites: kwargs["prerequisites"] = prerequisites
    if metrics:
        try:
            kwargs["metrics"] = json.loads(metrics)
        except (json.JSONDecodeError, TypeError):
            return _j({"success": False, "error": "Invalid metrics: not valid JSON"})
    return _j(await _client().experience_update(kb_id, exp_id, **kwargs))


@mcp.tool()
async def experience_delete(kb_id: str, exp_id: str) -> str:
    """Permanently delete an experience. Irreversible.

    Args:
        kb_id: Knowledge base ID or path
        exp_id: Experience ID

    Returns:
        {success, deleted_id}
    """
    if (err := _require_kb(kb_id)): return err
    if (err := _require_param("exp_id", exp_id)): return err
    return _j(await _client().experience_delete(kb_id, exp_id))


@mcp.tool()
async def experience_apply(kb_id: str, exp_id: str, user: str = "",
    context: str = "", result: str = "", notes: str = "") -> str:
    """Mark an experience as applied. Records the user, context, and effect. Each call increments applied_count.

    Args:
        kb_id: Knowledge base ID or path
        exp_id: Experience ID
        user: User identifier (e.g. employee ID, username)
        context: Application context description (e.g. "#3 Unit CNN-LSTM deviation 0.8")
        result: Application result (success, partial, failed)
        notes: Additional notes

    Returns:
        {success, experience: {..., applied_count, ...}, apply_record: {user, context, result, notes}}
    """
    if (err := _require_kb(kb_id)): return err
    if (err := _require_param("exp_id", exp_id)): return err
    return _j(await _client().experience_apply(kb_id, exp_id, user, context, result, notes))


@mcp.tool()
async def experience_review(kb_id: str, exp_id: str, reviewer: str = "",
    rating: float = 5.0, comment: str = "") -> str:
    """Review an experience with a rating (0-5) and comment. Automatically updates the experience's average rating and review count.

    Args:
        kb_id: Knowledge base ID or path
        exp_id: Experience ID
        reviewer: Reviewer name
        rating: Rating 0-5 (0=useless, 5=very useful)
        comment: Review comment

    Returns:
        {success, experience: {..., rating_avg, review_count, ...}, review_record}
    """
    if (err := _require_kb(kb_id)): return err
    if (err := _require_param("exp_id", exp_id)): return err
    return _j(await _client().experience_review(kb_id, exp_id, reviewer, rating, comment))

@mcp.tool()
async def experience_summary(kb_id: str) -> str:
    """Get experience statistics summary, including total count, distribution by category, distribution by severity, total applications, average rating, top 5 experiences.

    Args:
        kb_id: Knowledge base ID or path

    Returns:
        {success, summary: {total, by_category, by_severity, total_applied, avg_rating, top_experiences}}
    """
    if (err := _require_kb(kb_id)): return err
    return _j(await _client().experience_summary(kb_id))


@mcp.tool()
async def experience_search_global(query: str, top_k: int = 10,
                                     score_threshold: float = None,
                                     verify_content: bool = True) -> str:
    """Cross-KB global experience search -- QDCVR pipeline (isomorphic with document search).

    Vector recall -> hard threshold -> experience-level dedup -> content verification -> credibility tiering -> honest empty return.
    Vector handles "speed", content handles "accuracy"; no confirmed experience means honest declaration, no bluffing.

    Suitable for: "how did we handle similar X problem before", "what Y-related experiences does the whole plant have".
    Fault/operations queries should prioritize this tool.

    Args:
        query: Natural language query (Chinese or English; dual vector + keyword matching)
        top_k: Result cap (default 10)
        score_threshold: Vector hard threshold; None=0.45 (precision 0.55 / recall 0.35)
        verify_content: True=read body to verify (default); False=vector score only

    Returns:
        {success, query, count, experiences: [{id, title, scenario, problem, solution,
         vector_score, content_score, tier[P0/P1/P2], tier_reason, ...}],
         vector_recall, tier_counts, message}
        When count=0, message explains the blind spot.
    """
    return _j(await _client().experience_search_global(
        query, top_k, score_threshold=score_threshold, verify_content=verify_content))


@mcp.tool()
async def experience_search_smart(query: str, top_k: int = 10,
                                   score_threshold: float = None,
                                   verify_content: bool = True,
                                   kb_id: str = "") -> str:
    """Intelligent multi-path experience retrieval -- the RECOMMENDED entry point for experience search.

    Enhances experience_search_global with:
    - Query intent analysis (troubleshooting/learning/best_practice/decision)
    - Adaptive thresholding (stricter for troubleshooting 0.55, relaxed for learning 0.35)
    - Multi-round retrieval with automatic query expansion (up to 3 rounds)
    - Retrieval transparency (match_details, retrieval_paths, ranking_reason per result)

    Rounds: Round1=original threshold, Round2=threshold*0.7 if 0 results, Round3=threshold*0.5+skip content verify.

    Args:
        query: Natural language query (Chinese or English)
        top_k: Result cap (default 10)
        score_threshold: Vector hard threshold; None=adaptive (type-based, recommended)
        verify_content: True=content verification (default, recommended for first 2 rounds)

    Returns:
        {success, query, query_type, count, rounds, degraded,
         adaptive_threshold, effective_threshold,
         experiences: [{..., match_details, retrieval_paths, ranking_reason}],
         tier_counts, message}
    """
    # 1. Query understanding
    query_type = _detect_query_type(query)

    # 2. Adaptive threshold
    type_thresholds = {"troubleshooting": 0.55, "decision": 0.50, "best_practice": 0.45, "learning": 0.35}
    adaptive = type_thresholds.get(query_type, 0.45)
    threshold = score_threshold if score_threshold is not None else adaptive

    # 3. Single-pass call to backend (backend handles its own multi-round degradation)
    client = _client()
    result = await client.experience_search_global(
        query, top_k=top_k * 2, score_threshold=threshold, verify_content=verify_content)
    # Scope to a single KB when kb_id is provided (default remains cross-KB/global).
    # The backend response carries ``kb_path`` (and sometimes ``kb_id``), so we
    # must resolve the requested kb_id to ALL of its aliases (UUID / path /
    # name) and match any of them — otherwise passing a UUID silently drops
    # every hit because UUID ∉ kb_path (E2E BUG-2).
    if kb_id and isinstance(result, dict):
        aliases = await _resolve_kb_aliases(client, kb_id)
        _kept = [e for e in result.get("experiences", [])
                 if _matches_any_alias(e, aliases)]
        result["experiences"] = _kept
        result["count"] = len(_kept)
        result["scoped_kb_id"] = kb_id
        # Recompute tier_counts and message to reflect kb-scoped results
        tier_counts = {"P0": 0, "P1": 0, "P2": 0, "discarded": 0}
        for r in _kept:
            tier = r.get("tier", "")
            if tier in tier_counts:
                tier_counts[tier] += 1
        result["tier_counts"] = tier_counts
        vec_count = result.get("vector_recall", 0)
        kw_count = result.get("keyword_recall", 0)
        result["message"] = (
            f"向量{vec_count}+关键词{kw_count}召回 -> "
            f"经验级过滤 -> 返回{len(_kept)} "
            f"(P0:{tier_counts['P0']} P1:{tier_counts['P1']} P2:{tier_counts['P2']}, "
            f"scoped to {kb_id})"
        )

    # Backend already reports rounds/degraded/threshold in its response;
    # we enrich with retrieval transparency but do NOT add our own rounds.
    if isinstance(result, dict):
        result["query_type"] = query_type
        result["adaptive_threshold"] = adaptive
        result["effective_threshold"] = result.get("threshold", threshold)
        # Add match_details and ranking_reason for each experience
        for exp in result.get("experiences", []):
            exp["retrieval_paths"] = ["vector", "keyword"]
            exp["match_details"] = _compute_match_details(query, exp)
            exp["ranking_reason"] = _compute_ranking_reason(exp)

    return _j(result)


@mcp.tool()
async def experience_rerank(query: str, experiences_json: str) -> str:
    """Semantic reranking for experience search results -- multi-dimensional scoring.

    Re-ranks candidate experiences based on: tag overlap, problem match, solution match,
    and credibility (rating + applied_count). This is a lightweight MCP-side tool
    (no backend call). Use after experience_search_smart for final ordering.

    Args:
        query: The original user query
        experiences_json: JSON string of experience list (from search results)

    Returns:
        {success, ranked: [{id, title, scenario, tier, relevance_score, reason,
          vector_score, content_score, rating_avg, applied_count}],
         original_count, reranked_count, query}
    """
    try:
        exps = json.loads(experiences_json)
    except Exception:
        return _j({"success": False, "error": "Invalid experiences_json: not valid JSON"})

    if not exps:
        return _j({"success": True, "ranked": [], "original_count": 0, "reranked_count": 0,
                    "message": "No experiences to rerank"})

    ranked = []
    query_tokens = _tokenize_for_match(query)

    for exp in exps:
        score = 0.0
        reasons = []

        # Tag match (weight: up to 0.45)
        tags = exp.get("tags", [])
        tag_text = " ".join(tags).lower()
        tag_matches = [t for t in query_tokens if t in tag_text]
        if tag_matches:
            score += min(len(tag_matches) * 0.15, 0.45)
            reasons.append("tag-match:" + ",".join(tag_matches[:3]))

        # Problem match (weight: up to 0.3)
        problem = exp.get("problem", "").lower()
        prob_matches = [t for t in query_tokens if t in problem]
        if prob_matches:
            score += min(len(prob_matches) * 0.1, 0.3)
            reasons.append("problem-match")

        # Solution match (weight: up to 0.2)
        solution = exp.get("solution", "").lower()
        sol_matches = [t for t in query_tokens if t in solution]
        if sol_matches:
            score += min(len(sol_matches) * 0.08, 0.2)
            reasons.append("solution-match")

        # Credibility boost (weight: up to 0.25)
        rating = exp.get("rating_avg", 0) or 0
        applied = exp.get("applied_count", 0) or 0
        credibility = min(rating / 5.0 * 0.15, 0.15) + min(applied / 10.0 * 0.1, 0.1)
        score += credibility
        if credibility > 0.15:
            reasons.append("high-credibility(r={},a={})".format(rating, applied))

        ranked.append({
            "id": exp.get("id", ""),
            "title": exp.get("title", ""),
            "scenario": exp.get("scenario", ""),
            "tier": exp.get("tier", "P2"),
            "relevance_score": round(min(score, 1.0), 3),
            "reason": "; ".join(reasons) if reasons else "comprehensive",
            "vector_score": exp.get("vector_score", 0) or 0,
            "content_score": exp.get("content_score", 0) or 0,
            "rating_avg": rating,
            "applied_count": applied,
        })

    # Sort by relevance score descending
    ranked.sort(key=lambda x: (-x["relevance_score"], -x["vector_score"], -x["content_score"]))

    return _j({
        "success": True,
        "ranked": ranked,
        "original_count": len(exps),
        "reranked_count": len(ranked),
        "query": query,
        "hint": "Ranked by multi-dimensional relevance. Use experience_read to verify before acting on top results."
    })


# ============================================================
# EXPERIENCE ENHANCEMENT — E0/E1 Extraction / E3 Draft / E6 Sync / E8 Dashboard / E11 Decay
# ============================================================

@mcp.tool()
async def experience_extract(
    kb_id: str,
    doc_paths: list = None,
    dry_run: bool = True,
    mode: str = "heuristic",
) -> str:
    """E0/E1: Auto-extract experience candidates from KB documents.

    Two modes:
    - mode="heuristic" (default): heuristic rules extract candidate experiences. dry_run=True returns candidate list;
      dry_run=False writes to draft pool for review.
    - mode="prepare": returns an extraction task package (full document text + dedup context + extraction template)
      for the agent to refine with LLM (recommended for critical KBs).

    Typical scenario: scanning for experiences after new documents are ingested; batch learning from a KB.

    Args:
        kb_id: Target KB (UUID or path)
        doc_paths: Optional, scan only specified docs; empty scans all .md in the KB (excluding experience directory)
        dry_run: True=report only (default safe); False=write to draft pool
        mode: heuristic (rule-based extraction) | prepare (returns LLM task package)

    Returns:
        heuristic+dry_run: {success, total_candidates, candidates: [...], hint}
        heuristic+!dry_run: {success, drafts_created, draft_ids}
        prepare: {success, docs_to_extract, documents, existing_scenarios, extraction_template}
    """
    if (err := _require_kb(kb_id)): return err
    return _j(await _client().experience_extract(kb_id, doc_paths, dry_run, mode))


@mcp.tool()
async def experience_drafts_list(kb_id: str) -> str:
    """E3: List the experience draft pool (pending review candidates).

    Drafts are produced by experience_extract(dry_run=False). Agent reviews them, then calls
    experience_draft_approve to publish or experience_draft_reject to reject.

    Returns: {success, count, drafts: [{id, title, scenario, confidence, ...}]}
    """
    if (err := _require_kb(kb_id)): return err
    return _j(await _client().experience_drafts_list(kb_id))


@mcp.tool()
async def experience_draft_read(kb_id: str, draft_id: str) -> str:
    """E3: Read draft details (including extraction evidence, source document).

    Args:
        kb_id: KB ID or path
        draft_id: Draft ID (draft-xxx, from experience_drafts_list)

    Returns: {success, draft: {id, title, problem, solution, key_lessons, source_doc, ...}}
    """
    if (err := _require_kb(kb_id)): return err
    if (err := _require_param("draft_id", draft_id)): return err
    return _j(await _client().experience_draft_read(kb_id, draft_id))


@mcp.tool()
async def experience_draft_approve(
    kb_id: str, draft_id: str, edits: dict = None,
) -> str:
    """E3: Approve draft -> formal experience (write index + vector index).

    Optional edits parameter to override fields (passed after agent LLM refinement). After approval, draft is deleted from pool,
    experience is marked auto_extracted=true with extraction_method.

    Args:
        kb_id: KB ID or path
        draft_id: Draft ID
        edits: Optional field overrides, e.g. {"title":"...", "solution":"refined solution", "key_lessons":[...]}

    Returns: {success, approved, experience, exp_id}
    """
    if (err := _require_kb(kb_id)): return err
    if (err := _require_param("draft_id", draft_id)): return err
    return _j(await _client().experience_draft_approve(kb_id, draft_id, edits))


@mcp.tool()
async def experience_draft_reject(kb_id: str, draft_id: str, reason: str = "") -> str:
    """E3: Reject draft -> move to rejected/ (retain reject reason for traceability).

    Args:
        kb_id: KB ID or path
        draft_id: Draft ID
        reason: Rejection reason (optional)

    Returns: {success, rejected}
    """
    if (err := _require_kb(kb_id)): return err
    if (err := _require_param("draft_id", draft_id)): return err
    return _j(await _client().experience_draft_reject(kb_id, draft_id, reason))


@mcp.tool()
async def experience_check_stale(kb_id: str = "") -> str:
    """E6: Check consistency between experiences and their related documents.

    Unified entry — replaces the former experience_check_stale /
    experience_check_stale_global pair. Empty kb_id = global check across all KBs;
    a specific kb_id = single-KB check.

    Checks each experience's related_docs:
    - Document updated_at is newer than experience updated_at -> stale (experience needs re-extraction)
    - Document does not exist -> orphan (broken reference)

    Typical scenarios: after document updates, check which experiences are stale; periodic consistency audit.

    Returns (single-KB): {success, total, fresh, stale, orphan, stale_experiences, orphan_experiences}
    Returns (global):    {success, total_experiences, stale, orphan, stale_experiences, orphan_experiences}
    """
    client = _client()
    if not kb_id or not kb_id.strip():
        return _j(await client.experience_check_stale_global())
    if (err := _require_kb(kb_id)): return err
    return _j(await client.experience_check_stale(kb_id))


@mcp.tool()
async def experience_sync_kb(kb_id: str) -> str:
    """E6: Mark entire KB for sync (stale/orphan experiences marked needs_sync).

    After marking, the agent should read each related_doc, re-extract with experience_extract,
    then update_experience to refresh content. This is the "document update -> experience sync" trigger.

    Returns: {success, marked_for_sync, hint}
    """
    if (err := _require_kb(kb_id)): return err
    return _j(await _client().experience_sync_kb(kb_id))


@mcp.tool()
async def experience_dashboard(kb_id: str) -> str:
    """E8: Experience dashboard - KB experience overview aggregate statistics.

    Includes: total count, P0/P1/P2 tiering, category/severity distribution, draft count, stale/orphan count, needs-sync count, top experiences.

    Typical scenarios: assess KB experience coverage and quality; discover experiences needing supplementation or cleanup.

    Returns: {success, total_experiences, by_tier, summary, drafts_pending, stale, orphan, needs_sync}
    """
    if (err := _require_kb(kb_id)): return err
    return _j(await _client().experience_dashboard(kb_id))


@mcp.tool()
async def experience_apply_decay(kb_id: str) -> str:
    """E11: Apply experience decay rules (periodic credibility degradation).

    Rules:
    - stale_unverified: created > 30 days and 0 applications -> flagged (demoted in search)
    - disputed: >= 3 reviews and rating < 2.0 -> flagged (demoted to P2)
    - unvetted: 0 reviews and 0 applications -> flagged (max P1)

    Typical scenarios: periodic freshness maintenance; clean up long-unverified experiences.

    Returns: {success, decayed: {stale_unverified, disputed, unvetted}, total_flagged}
    """
    if (err := _require_kb(kb_id)): return err
    return _j(await _client().experience_apply_decay(kb_id))



# ============================================================
# MEDITATION (Experience Auto-Summarization)
# ============================================================

@mcp.tool()
async def experience_meditation_status(kb_id: str = "") -> str:
    """Get meditation status: scheduler, harness health, circuit breaker, per-KB configs.

    Args:
        kb_id: Optional KB filter; empty returns global status

    Returns: {success, scheduler, harnesses, circuit_breaker, kb_configs}
    """
    if kb_id:
        return _j(await _client().meditation_status(kb_id))
    return _j(await _client().meditation_status())


@mcp.tool()
async def experience_meditation_run(kb_id: str = "", trigger: str = "manual") -> str:
    """Manually trigger a meditation run. Optionally scoped to one KB.

    NON-BLOCKING: returns a task_id immediately; poll with
    experience_meditation_task_status(task_id) for the result.
    The meditation agent (omp/claude) may run for several minutes.

    Args:
        kb_id: Target KB (empty = all enabled KBs)
        trigger: "manual" | "scheduled" | "incremental"

    Returns: {success, status:'running', task_id, kb_id} right away.
    When done, poll experience_meditation_task_status → result holds
    {success, report/experiences/drafts}.
    """
    client = _client()
    meta = {"kb_id": kb_id, "trigger": trigger}

    async def _work():
        return await client.meditation_run(kb_id, trigger)

    task_id = task_registry.submit(_work(), "meditation_run", meta)
    return _running_payload(
        task_id, "meditation_run", {"kb_id": kb_id},
        message="meditation is running; call experience_meditation_task_status to get the result",
    )


@mcp.tool()
async def experience_meditation_task_status(task_id: str) -> str:
    """Check the status of a non-blocking meditation run.

    status is 'running', 'done', or 'error'. When done, result holds the
    meditation report (experiences_created, drafts_created, summary, ...).
    When error, error holds the message. Use this to poll tasks from
    experience_meditation_run.
    """
    rec = task_registry.get(task_id)
    if rec is None:
        return _j({"success": False, "error": f"unknown task_id: {task_id}"})
    view = task_registry.public_view(rec)
    view["success"] = True
    return _j(view)


@mcp.tool()
async def experience_meditation_config_get(kb_id: str) -> str:
    """Get meditation config for a KB.

    Args:
        kb_id: Target KB (UUID or path)

    Returns: {success, kb_id, kb_path, config: {...}, source}
    """
    if (err := _require_kb(kb_id)): return err
    return _j(await _client().meditation_config_get(kb_id))


@mcp.tool()
async def experience_meditation_config_update(kb_id: str, config: dict) -> str:
    """Update meditation config for a KB. Only pass fields to change.

    Args:
        kb_id: Target KB (UUID or path)
        config: Dict of config fields to update, e.g. {"enabled": true, "harness": "claude", "interval_hours": 12}

    Returns: {success, kb_id, kb_path, config}
    """
    if (err := _require_kb(kb_id)): return err
    if not config:
        return _j({"success": False, "error": "config parameter is required"})
    return _j(await _client().meditation_config_update(kb_id, config))


@mcp.tool()
async def experience_meditation_history(kb_id: str = "", limit: int = 20) -> str:
    """List recent meditation runs, optionally filtered by KB.

    Args:
        kb_id: Optional KB filter
        limit: Max results (default 20)

    Returns: {success, count, runs: [{id, kb_id, harness, trigger, status, ...}]}
    """
    return _j(await _client().meditation_history(kb_id, limit))

# ============================================================
# BACKEND STATUS
# ============================================================

@mcp.tool()
async def backend_status() -> str:
    """Get backend service health and MinerU OCR engine status."""
    return _j(await _client().backend_status())


@mcp.tool()
async def kb_project_status(scope: str = "runtime") -> str:
    """Full project service status.

    scope="runtime" (default): backend/web ports listening + HTTP health checks,
    Neo4j bolt/http ports, MinerU availability, per-service PIDs, and shared log
    file paths. Returns a one-line `summary` plus a per-service `services` dict.
    `ready` is True only when backend AND web are HTTP-healthy.

    scope="setup": Check whether the project is SET UP and ready to start services.
    Verifies .env exists, backend/web are initialized, and backend .venv + web
    node_modules are installed. Returns `ready_to_start` plus a list of `problems`
    and the exact `fix` command (`ragctl setup`)."""
    if scope == "setup":
        return _j(project_manager.preflight())
    data = await asyncio.to_thread(project_manager.project_status)
    return _j(data)


@mcp.tool()
async def kb_project_start(backend: bool = True, web: bool = True, neo4j: bool = False,
                           mode: str = "", wait: bool = False) -> str:
    """Silently start project services. HEADLESS on every OS and every mode —
    NO terminal/console window opens (dev behaves identically to prod).
    stdout+stderr are redirected to the shared log files that ragctl and the
    Tauri desktop console also read (backend/logs/desktop-stdout.log,
    web/logs/desktop-stdout.log). View via `ragctl logs <svc>` or Tauri.

    Args:
      backend: start the FastAPI backend (default True)
      web: start the Nuxt web server (default True)
      neo4j: start Neo4j via `docker compose up -d neo4j` (default False; needs Docker)
      mode: override APP_MODE "dev"|"prod" (default "" = current env)
      wait: if True, block until backend+web are HTTP-healthy or ~45s timeout
            (default False — returns immediately after launch; poll kb_project_status)

    Fails fast with a `preflight` block if the project isn't set up yet (missing
    .env / deps). Services already listening are skipped (idempotent).
    """
    data = await asyncio.to_thread(
        lambda: project_manager.start_project(
            backend=backend, web=web, neo4j=neo4j, mode=mode, wait=wait,
        ),
    )
    return _j(data)


@mcp.tool()
async def kb_project_update(check_only: bool = False, force: bool = False,
                            no_deps: bool = False, restart: bool = False,
                            show_version: bool = False) -> str:
    """Check GitHub for a newer version of the project and optionally pull it.
    Delegates to `ragctl update` (single source of truth for version compare +
    git pull + optional deps reinstall).

    Modes:
    - show_version=True: Show local project version (VERSION file + git SHA)
      compared with the latest GitHub release. Does NOT pull.
    - check_only=True: dry-run — report only, never pull (default False)
    - check_only=False: pull the update

    Safety:
      - Refuses to pull over a dirty worktree unless force=True
      - Prefer check_only=True first to preview

    Args:
      check_only: dry-run — report only, never pull (default False)
      force: pull even if versions look equal / worktree is dirty
      no_deps: after pull, skip `ragctl deps` reinstall
      restart: after pull, run `ragctl up --force` to reload services
      show_version: show local vs remote version without pulling (default False)
    """
    if show_version:
        data = await asyncio.to_thread(
            lambda: project_manager.project_version(local_only=False),
        )
        return _j(data)
    data = await asyncio.to_thread(
        lambda: project_manager.project_update(
            check_only=check_only, force=force, no_deps=no_deps, restart=restart,
        ),
    )
    return _j(data)


# ============================================================
# VECTOR SEARCH & TWO-STAGE PRECISION SEARCH
# ============================================================

@mcp.tool()
async def kb_search_vector(query: str, kb_id: str = "", top_k: int = 5,
                            score_threshold: float = 0.0,
                            balance_kbs: bool = False) -> str:
    """Vector semantic search for document chunks.

    Args:
        query: Query text
        kb_id: Limit to specific KB; empty means cross-KB
        top_k: Number of results to return
        score_threshold: Minimum cosine similarity threshold (0~1); <=0 uses backend default (0.35). Lower to recall more chunks
        balance_kbs: Whether to balance results across KBs in cross-KB search (default False). True prevents large KBs from dominating results

    Returns:
        {success, results: [{content, score, doc_path, chunk_index, kb_id}]}
    """
    client = _client()
    if kb_id and kb_id.strip() and not await _kb_exists(client, kb_id):
        return _j({"success": False, "error": f"knowledge base not found: {kb_id}"})
    result = await client.vector_search(query, kb_id, top_k, score_threshold, balance_kbs)
    # Normalize doc_path separators and deduplicate (backend may return backslash/forward-slash variants)
    if isinstance(result, dict) and result.get("success"):
        raw_results = result.get("results", [])
        seen = {}
        for r in raw_results:
            if isinstance(r, dict) and r.get("doc_path"):
                norm_path = r["doc_path"].replace("\\", "/")
                r["doc_path"] = norm_path
                key = (norm_path, r.get("chunk_index", 0))
                if key not in seen or r.get("score", 0) > seen[key].get("score", 0):
                    seen[key] = r
        result["results"] = list(seen.values())
        result["count"] = len(result["results"])
    return _j(result)


@mcp.tool()
async def kb_search_two_stage(
    query: str,
    kb_id: str = "",
    stage1_top_k: int = 20,
    stage2_top_k: int = 5,
    enable_graph_expansion: bool = True,
    score_threshold: float = 0.0,
    balance_kbs: bool = False,
) -> str:
    """Two-stage precision search: first broad search to locate candidate documents, then vector fine-search for chunks.

    Recommended as the preferred tool for agents - more precise than pure vector search, reduces hallucination risk.

    Args:
        query: User question
        kb_id: Limit to specific KB; empty means cross-KB
        stage1_top_k: Number of candidate documents in Stage 1
        stage2_top_k: Number of chunks per document in Stage 2
        enable_graph_expansion: Whether to enable graph neighbor expansion
        score_threshold: Vector similarity threshold (0~1); <=0 uses backend default (0.35)
        balance_kbs: Whether to balance results across KBs in cross-KB search (default False). True prevents large KBs from dominating

    Returns:
        {success, stage1: {candidates}, stage2: {results}, total_results}
        When cross-KB search results come from <2 distinct KBs (BM25 blind spot),
        an auto-upgrade supplementary vector search is appended as _cross_kb_fallback.
    """
    client = _client()
    if kb_id and kb_id.strip() and not await _kb_exists(client, kb_id):
        return _j({"success": False, "error": f"knowledge base not found: {kb_id}"})
    result = await client.two_stage_search(
        query, kb_id, stage1_top_k, stage2_top_k, enable_graph_expansion,
        score_threshold, balance_kbs
    )
    # Normalize paths and deduplicate stage2 results (keyword+graph sources may produce separator variants)
    if isinstance(result, dict) and result.get("success"):
        stage2 = result.get("stage2", {})
        if isinstance(stage2, dict):
            raw_results = stage2.get("results", [])
            seen = {}
            for r in raw_results:
                if isinstance(r, dict) and r.get("doc_path"):
                    norm_path = r["doc_path"].replace("\\", "/")
                    r["doc_path"] = norm_path
                    key = (norm_path, r.get("chunk_index", 0))
                    if key not in seen or r.get("score", 0) > seen[key].get("score", 0):
                        seen[key] = r
            deduped = list(seen.values())
            # FIX: cap total results at stage2_top_k so the parameter actually
            # controls result count (previously returned up to top_k*candidates).
            deduped = deduped[:stage2_top_k]
            stage2["results"] = deduped
            if "total_results" in stage2:
                stage2["total_results"] = len(deduped)
            if "total_results" in result:
                result["total_results"] = len(deduped)
            result["stage2"] = stage2
    # P2.1: Auto-upgrade for cross-KB BM25 blind spot.
    # When searching across all KBs with empty kb_id and the two-stage
    # results come from <2 distinct KBs, run a supplementary vector search
    # with balance_kbs=True to surface semantically relevant docs from
    # other KBs that BM25 missed.
    if not kb_id and result.get("success") and not balance_kbs:
        stage2 = result.get("stage2", {})
        results = stage2.get("results", []) if isinstance(stage2, dict) else []
        distinct_kbs = set(r.get("kb_id") for r in results if r.get("kb_id"))
        if len(distinct_kbs) < 2 and results:
            supplement = await _client().vector_search(
                query, kb_id="", top_k=max(stage2_top_k, 5),
                score_threshold=score_threshold, balance_kbs=True
            )
            if supplement.get("success") and supplement.get("count", 0) > 0:
                result["_cross_kb_fallback"] = {
                    "triggered": True,
                    "reason": f"BM25 stage1 returned results from only {len(distinct_kbs)} KB(s); supplementing with balanced vector search",
                    "supplement_count": supplement.get("count", 0),
                    "supplement": supplement.get("results", []),
                }
    return _j(result)


@mcp.tool()
async def kb_reindex(kb_id: str = "", force: bool = False) -> str:
    """Rebuild vector index and knowledge graph. Empty kb_id rebuilds all.

    force=True forces rebuild of all documents (including already indexed ones).

    NON-BLOCKING: returns a task_id immediately; poll with kb_task_status(task_id).
    For small KBs this finishes in seconds; for large KBs (50+ docs, force=True) it
    can take minutes (re-embedding all documents). The result includes a post-reindex
    verification that confirms the vector index is queryable.
    """
    client = _client()
    meta = {"kb_id": kb_id, "force": force}

    async def _work():
        result = await client.reindex(kb_id, force)
        # Post-reindex verification: if KB was specified and documents were processed,
        # run a quick search to confirm the index is actually usable
        processed = result.get("total_indexed") or result.get("total_docs", 0)
        if kb_id and result.get("success") and processed > 0:
            docs = await client.kb_get_documents(kb_id)
            doc_list = docs.get("documents", []) if isinstance(docs, dict) else []
            if doc_list and len(doc_list) > 0:
                first_doc = doc_list[0]
                test_query = first_doc.get("name", "").replace(".md", "").replace("-", " ")[:60]
                if test_query.strip():
                    verify = await client.vector_search(test_query, kb_id=kb_id, top_k=1)
                    if verify.get("success") and verify.get("count", 0) > 0:
                        result["_verify"] = "ok"
                    else:
                        result["_verify"] = "WARNING: vector search returned 0 results after reindex — index may be corrupted"
        return result

    task_id = task_registry.submit(_work(), "kb_reindex", meta)
    return _running_payload(task_id, "kb_reindex", {"kb_id": kb_id, "force": force},
                            message="reindex is running; call kb_task_status to get the result")


@mcp.tool()
async def kb_index_document(kb_id: str = "", doc_path: str = "", doc_id: str = "", doc_name: str = "", description: str = "", content: str = "") -> str:
    """Index a single document (vector + graph). Stores document content (or existing document) into the vector database and records vector_index in metadata.

    Two invocation modes:
    1. Provide doc_id (document UUID) -> auto-resolves kb_id and doc_path
    2. Provide kb_id + doc_path -> direct usage

    Used to manually trigger vector index construction for a document. If content is provided, it is used directly; otherwise auto-reads from storage.
    After indexing, records vector_index information (collection, chunks, etc.) in .knowledge-base.yml for the corresponding document.
    Also rebuilds BM25 keyword index so subsequent two-stage search can locate this document.

    **Atomic**: ONLY indexes (vector + graph + YAML metadata writeback).
    Does NOT create or modify the document file itself.

    Args:
        kb_id: Knowledge base ID or path (optional in doc_id mode)
        doc_path: Relative path of the document within the KB (optional in doc_id mode)
        doc_id: Document UUID (from .knowledge-base.yml); when provided, auto-resolves the above two
        doc_name: Document name
        description: Document description
        content: Document body content; auto-reads from file if empty

    Returns:
        {success, vector_index: {collection, chunk_id_prefix, total_chunks, graph_doc_id}, graph_stats: {entities, relations}}
    """
    return _j(await _client().index_document(kb_id, doc_path, doc_name, description, content, doc_id))


@mcp.tool()
async def kb_batch_index(
    kb_id: str,
    doc_paths: list,
    force: bool = False,
) -> str:
    """Batch index documents (vector + graph).

    Builds vector index and knowledge graph index for multiple documents in a KB at once.
    Updates vector_index metadata in .knowledge-base.yml after indexing.

    Args:
        kb_id: Knowledge base ID or path
        doc_paths: List of relative document paths (e.g. ["doc1.md", "doc2.md"])
        force: Whether to overwrite existing index

    Returns:
        {success, indexed: [...], skipped: [...], errors: [...], total_indexed}
    """
    if (err := _require_kb(kb_id)): return err
    return _j(await _client().batch_index_documents(kb_id, doc_paths, force))


@mcp.tool()
async def kb_search_stats(kb_id: str = "") -> str:
    """Vector index statistics. View each knowledge base's index status in the vector database.

    Args:
        kb_id: Optional, limit to specific KB; empty returns all

    Returns:
        {success, stats: {collections: [{collection, chunk_count}]}}
    """
    return _j(await _client().search_stats(kb_id))


@mcp.tool()
async def kb_cleanup_orphan_collections(dry_run: bool = True) -> str:
    """Detect and clean up orphan/duplicate vector collections (vector index residue from deleted/renamed KBs).

    Orphan collections waste space and slow down cross-KB search (observed: 27 collections vs 10 KBs).
    This tool: 1) Lists all collections in the vector store 2) Recursively identifies all KBs (top-level + sub-KBs) 3) Compares to find orphans/duplicates 4) Reports or cleans.

    ⚠️ Sub-KB safety protection: recursively reads .tree-fs.json to collect all isKnowledgeBase nodes (including sub-KBs),
    so sub-KB UUID collections are NOT misidentified as orphans. This fixes the early-version incident where polymer sub-KB vectors were accidentally deleted.

    Classification:
    - **orphan**: collection key does not match any KB (top-level or sub-KB) UUID/path/name (including test residue zzz_*/test*)
    - **duplicate**: KB has both kb_{UUID} and kb_{path} collections (historical index naming split)

    Args:
        dry_run: True=detect only (default, safe); False=execute cleanup (irreversible)

    Returns:
        dry_run=True:  {success, total_collections, top_kb_count, sub_kb_count, valid_collections, orphan_count, duplicate_count, reclaimable_chunks, orphans[], duplicates[], hint}
        dry_run=False: {success, cleaned_count, cleaned_ok, cleaned[]}
    """
    client = _client()
    # 1. All collections in vector store
    stats = await client.search_stats("")
    collections = (stats.get("stats", {}) or {}).get("collections", []) if isinstance(stats, dict) else []
    all_col_names = {c.get("collection", "") for c in collections}

    # 2. All current KBs (UUID + path + name) - recursive, includes sub-KBs to avoid accidental deletion
    kb_data = await client.kb_list()
    top_kbs = (kb_data.get("knowledgeBases", []) if isinstance(kb_data, dict) else [])
    uuid_to_kb = {}  # id -> {kbId, path, name, _sub?}
    for kb in top_kbs:
        if kb.get("kbId"):
            uuid_to_kb[kb["kbId"]] = kb
    top_kb_count = len(uuid_to_kb)

    # Recursively read .tree-fs.json, collect all isKnowledgeBase nodes (sub-KBs)
    # ⚠️ kb_list only returns top-level KBs; sub-KBs (independent isKnowledgeBase folders)
    #    use sub-KB UUID and must be included in the valid set, otherwise they are misidentified as orphans and wrongly deleted (root cause of 2026-07-13 PVA incident)
    tree = await client.fs_get_tree()
    sub_kb_count = 0
    def _collect_kb_nodes(nodes):
        nonlocal sub_kb_count
        if not isinstance(nodes, list):
            return
        for n in nodes:
            if not isinstance(n, dict):
                continue
            if n.get("isKnowledgeBase") or n.get("is_knowledge_base"):
                nid = n.get("id") or n.get("node_id")
                npath = n.get("path") or n.get("name")
                if nid and nid not in uuid_to_kb:
                    uuid_to_kb[nid] = {"kbId": nid, "path": npath, "name": npath, "_sub": True}
                    sub_kb_count += 1
            _collect_kb_nodes(n.get("children", []))
    tree_list = tree if isinstance(tree, list) else ([tree] if isinstance(tree, dict) else [])
    _collect_kb_nodes(tree_list)

    # path/name -> uuid mapping (includes sub-KBs), used for path-form collection judgment
    path_to_uuid = {}
    for uid, kb in uuid_to_kb.items():
        if kb.get("path"):
            path_to_uuid[kb["path"]] = uid
        if kb.get("name"):
            path_to_uuid[kb["name"]] = uid

    # 3. Classify (sub-KB UUIDs are now in uuid_to_kb, will not be misidentified as orphans)
    orphans = []
    duplicates = []
    for c in collections:
        name = c.get("collection", "")
        if not name.startswith("kb_"):
            continue
        key = name[3:]
        chunks = c.get("chunk_count", 0)
        if key in uuid_to_kb:
            continue  # Valid UUID collection (top-level KB or sub-KB)
        if key in path_to_uuid:
            uid = path_to_uuid[key]
            if f"kb_{uid}" in all_col_names:
                uid_chunks = next((cc.get("chunk_count", 0) for cc in collections if cc.get("collection") == f"kb_{uid}"), 0)
                duplicates.append({
                    "collection": name, "key": key, "chunk_count": chunks,
                    "is_duplicate": True,  # 删除时只删 path-named 版，绝不碰 UUID 真数据
                    "note": f"Duplicate: KB already has UUID collection kb_{uid}({uid_chunks} chunks)"
                })
            # else: path collection without UUID version, keep as valid
        else:
            kl = key.lower()
            note = "test residue" if (key.startswith("zzz_") or "test" in kl or "move_test" in kl) else "orphan: no matching KB"
            orphans.append({"collection": name, "key": key, "chunk_count": chunks, "note": note})

    total = len(collections)
    reclaimable = sum(o["chunk_count"] for o in orphans) + sum(d["chunk_count"] for d in duplicates)

    if dry_run:
        return _j({
            "success": True, "dry_run": True,
            "total_collections": total,
            "top_kb_count": top_kb_count,
            "sub_kb_count": sub_kb_count,
            "valid_collections": total - len(orphans) - len(duplicates),
            "orphan_count": len(orphans), "duplicate_count": len(duplicates),
            "reclaimable_chunks": reclaimable,
            "orphans": orphans, "duplicates": duplicates,
            "hint": "Use dry_run=False to execute cleanup (irreversible). For duplicate collections, confirm the UUID version covers its chunks before cleaning.",
        })

    # Actual cleanup
    # ⚠️ duplicate 清理只删 path-named 版（path_only=True）：库仍存在且持有 UUID
    # 真数据时，delete_kb_vectors(key) 会把 UUID 版一并删掉（2026-07-31 事故：
    # kb_Materials-Science/kb_Energy-Batteries 的 714/548 chunks 被误删）。
    cleaned = []
    for o in orphans + duplicates:
        key = o["key"]
        r = await client.delete_kb_vectors(key, path_only=bool(o.get("is_duplicate")))
        ok = bool(r.get("success")) if isinstance(r, dict) else False
        cleaned.append({"collection": o["collection"], "key": key, "note": o.get("note", ""), "deleted": ok})
    return _j({
        "success": True, "dry_run": False,
        "cleaned_count": len(cleaned),
        "cleaned_ok": sum(1 for c in cleaned if c["deleted"]),
        "reclaimed_chunks": reclaimable,
        "cleaned": cleaned,
    })


@mcp.tool()
async def kb_graph_search(keyword: str, node_type: str = "all", limit: int = 20) -> str:
    """Search nodes in the knowledge graph by keyword (name/path/label).

    Unified entry for graph node search — replaces the former
    kb_graph_search / kb_graph_search_kbs / kb_graph_search_tags trio.

    Args:
        keyword: Search term.
        node_type: "all" (default) runs document+kb+tag in parallel and merges;
                   "document", "kb", or "tag" runs a single node-type search.
        limit: Max results per node type.

    Returns:
        node_type="all": {success, keyword, documents, kbs, tags, counts}
        specific node_type: the raw backend response for that node type.
    """
    client = _client()
    if node_type == "document":
        return _j(await client.graph_search(keyword, limit))
    if node_type == "kb":
        return _j(await client.graph_search_kbs(keyword, limit))
    if node_type == "tag":
        return _j(await client.graph_search_tags(keyword, limit))
    # "all" — run all three and merge under typed keys
    docs, kbs, tags = await asyncio.gather(
        client.graph_search(keyword, limit),
        client.graph_search_kbs(keyword, limit),
        client.graph_search_tags(keyword, limit),
    )
    # Helper: extract list from backend response (backend uses type-specific keys: documents/kbs/tags)
    def _extract(resp, key):
        if isinstance(resp, list):
            return resp
        if isinstance(resp, dict):
            return resp.get(key, resp.get("results", []))
        return []

    docs_list = _extract(docs, "documents")
    kbs_list = _extract(kbs, "kbs")
    tags_list = _extract(tags, "tags")
    return _j({
        "success": True,
        "keyword": keyword,
        "documents": docs_list,
        "kbs": kbs_list,
        "tags": tags_list,
        "counts": {
            "documents": len(docs_list),
            "kbs": len(kbs_list),
            "tags": len(tags_list),
        },
    })


@mcp.tool()
async def kb_graph_stats() -> str:
    """Return knowledge graph statistics and Neo4j availability.

    Response includes node/edge counts, relationship distribution, and
    a `neo4j_available` boolean (health probe, never throws)."""
    stats = await _client().graph_stats()
    try:
        health = await _client().graph_health()
    except Exception:
        health = {"available": False}
    if isinstance(stats, dict):
        # graph_health() returns the full {"success":..., "health":{...}} envelope;
        # unwrap the inner health object to read the actual availability flag.
        inner = health.get("health", health) if isinstance(health, dict) else {}
        if not isinstance(inner, dict):
            inner = {}
        stats["neo4j_available"] = inner.get("available", False)
    return _j(stats)


@mcp.tool()
async def kb_graph_document(doc_path: str, limit: int = 50) -> str:
    """View a single document's knowledge graph: document info, tags, related documents, cross-KB connections.

    Finds all graph information for the document in Neo4j by its path.
    Returns: {document, tags, related_documents, cross_kb_links, ...}"""
    if (err := _require_param("doc_path", doc_path)): return err
    return _j(await _client().graph_document(doc_path, limit))


@mcp.tool()
async def kb_graph_document_related(doc_path: str, limit: int = 20) -> str:
    """Return documents related to a given document (based on same KB / shared tags / description similarity)."""
    if (err := _require_param("doc_path", doc_path)): return err
    return _j(await _client().graph_document_related(doc_path, limit))


@mcp.tool()
async def kb_graph_kb_overview(kb_id: str) -> str:
    """KB-level graph overview: document statistics, tag distribution, related KBs, top related documents.

    View the overall graph state of a knowledge base and discover its core documents and connections."""
    if (err := _require_kb(kb_id)): return err
    return _j(await _client().graph_kb_overview(kb_id))


@mcp.tool()
async def kb_graph_build(kb_id: str = "", force: bool = False) -> str:
    """Build the document relationship graph for one KB (kb_id given) or all KBs (kb_id empty).

    Unified entry — replaces the former kb_graph_build_kb / kb_graph_build_all pair.
    Empty kb_id builds graphs for every KB (cross-KB shared tags form cross-KB connections);
    a specific kb_id builds only that KB.

    NON-BLOCKING: returns a task_id immediately; poll with kb_task_status(task_id).
    For small KBs this finishes in seconds; for large KBs (50+ docs) it can take a minute+.

    Iterates documents' metadata (name, description, tags) and builds RELATED_TO
    relationships via shared tags / same KB / description similarity. Does NOT read
    document content.
    force=True: clear and rebuild; force=False: incremental (skip already-indexed documents).

    Returns (per-KB): {docs_processed, docs_skipped, total_relations, errors, ...}
    Returns (all):    {total_top_kbs, kbs: [{kb_id, docs_processed, ...}], ...}

    Note: total_relations counts relations CREATED this run. When force=false and all
    docs are already indexed, total_relations is 0 but the graph IS populated — verify
    with kb_graph_document(doc_path) or kb_graph_kb_overview(kb_id).
    """
    client = _client()
    if kb_id and kb_id.strip():
        if (err := _require_kb(kb_id)): return err
    meta = {"kb_id": kb_id, "force": force}

    async def _work():
        if not kb_id or not kb_id.strip():
            return await client.graph_build_all(force)
        return await client.graph_build_kb(kb_id, force)

    task_id = task_registry.submit(_work(), "kb_graph_build", meta)
    return _running_payload(task_id, "kb_graph_build", {"kb_id": kb_id},
                            message="graph build is running; call kb_task_status to get the result")


@mcp.tool()
async def kb_graph_cross_kb_documents(min_kbs: int = 2, limit: int = 50) -> str:
    """Discover cross-knowledge-base bridge documents - documents connected to >= min_kbs different KBs.

    These documents are the backbone connecting different knowledge bases.
    Returns: {documents: [{name, path, kb_id, tags, related_kb_count}], ...}"""
    return _j(await _client().graph_cross_kb_documents(min_kbs, limit))


@mcp.tool()
async def kb_graph_document_paths(doc_a: str, doc_b: str, max_depth: int = 4) -> str:
    """Find the shortest relationship path between two documents (via RELATED_TO relationship chains).

    Shows how documents are connected through shared tags/same KB and other relationship chains.
    Returns: {paths: [{doc_path, reasons, hops}], path_count}"""
    if (err := _require_param("doc_a", doc_a)): return err
    if (err := _require_param("doc_b", doc_b)): return err
    return _j(await _client().graph_document_paths(doc_a, doc_b, max_depth))


@mcp.tool()
async def kb_graph_central_documents(kb_id: str, top_n: int = 20) -> str:
    """Find the most central documents in a KB (by RELATED_TO degree centrality).

    These are the core documents of the KB, useful for understanding the main topic structure.
    Returns: {documents: [{name, path, degree, total_weight}], ...}"""
    if (err := _require_kb(kb_id)): return err
    return _j(await _client().graph_central_documents(kb_id, top_n))


@mcp.tool()
async def kb_graph_delete_document(doc_path: str) -> str:
    """Delete a single document's graph data (shared entities preserved, only removes this document's contribution)."""
    if (err := _require_param("doc_path", doc_path)): return err
    return _j(await _client().graph_delete_document(doc_path))


@mcp.tool()
async def kb_graph_delete_kb(kb_id: str) -> str:
    """Delete an entire KB's graph data (cross-KB shared entities preserved)."""
    if (err := _require_kb(kb_id)): return err
    return _j(await _client().graph_delete_kb(kb_id))


# ---------- entry ----------
def main():
    _startup_health_check_and_launch()
    if "--http" in sys.argv:
        mcp.run(transport="sse")
    else:
        mcp.run()



# ================================================================
# STARTUP HEALTH CHECK & AUTO-LAUNCH
# ================================================================

def _startup_health_check_and_launch():
    """Startup health check; silently auto-launch backend/web if down.

    Runs synchronously before the MCP server accepts connections. Probes
    backend + web; if either is unreachable, launches it HEADLESS (no console
    window, dev == prod) via project_manager, with stdout+stderr redirected to
    the shared log files (backend/logs/desktop-stdout.log,
    web/logs/desktop-stdout.log) — NOT discarded. Then waits up to ~45 s for
    HTTP readiness.
    """
    # Load .env BEFORE importing config so BACKEND_PORT etc. are visible.
    _load_dotenv()
    import config  # noqa: F401 — ensures URL constants are resolved from env

    mode = project_manager.app_mode()
    print(f"[kb-mcp] === Startup health check (mode={mode}) ===", file=sys.stderr)
    print(f"[kb-mcp]   Backend URL : {project_manager._backend_url()}", file=sys.stderr)
    print(f"[kb-mcp]   Web URL     : {project_manager._web_url()}", file=sys.stderr)

    # If the project hasn't been set up yet, warn loudly and skip auto-launch —
    # starting services on an un-set-up clone would either silently download
    # multi-GB deps or crash. Guide the user to `ragctl setup`.
    pf = project_manager.preflight()
    if not pf["ready_to_start"]:
        print("[kb-mcp] ⚠️  PROJECT NOT SET UP — services will not auto-launch.", file=sys.stderr)
        for p in pf["problems"]:
            print(f"[kb-mcp]   • {p}", file=sys.stderr)
        print(f"[kb-mcp] FIX: {pf['fix']}", file=sys.stderr)
        print(f"[kb-mcp]      → {pf['setup_command']}", file=sys.stderr)
        print("[kb-mcp] (MCP server will still start so you can run ragctl setup via Bash,", file=sys.stderr)
        print("[kb-mcp]  then restart Claude Code to reconnect.)", file=sys.stderr)
        return

    status = project_manager.project_status()
    svc = status["services"]

    if status["ready"]:
        print("[kb-mcp] All services healthy — no auto-launch needed.", file=sys.stderr)
        return

    launched = []
    if not svc["backend"]["http_ok"]:
        print(f"[kb-mcp]   Backend : {svc['backend']['detail']} → launching (silent, log={svc['backend']['log_path']})", file=sys.stderr)
        launched.append(("backend", project_manager.start_service("backend", mode)))
    else:
        print("[kb-mcp]   Backend : OK", file=sys.stderr)

    if not svc["web"]["http_ok"]:
        print(f"[kb-mcp]   Web     : {svc['web']['detail']} → launching (silent, log={svc['web']['log_path']})", file=sys.stderr)
        launched.append(("web", project_manager.start_service("web", mode)))
    else:
        print("[kb-mcp]   Web     : OK", file=sys.stderr)

    if not launched:
        return

    print(f"[kb-mcp] Launched {len(launched)} service(s) headless; waiting for readiness (timeout: 45s)...", file=sys.stderr)
    waited = project_manager._wait_ready(timeout=45)
    if waited.get("ready"):
        print(f"[kb-mcp] All services ready ({waited.get('elapsed_s')}s).", file=sys.stderr)
    else:
        print(f"[kb-mcp] WARNING: services not fully ready after {waited.get('timeout_s')}s — continuing anyway.", file=sys.stderr)
        print("[kb-mcp]   Check: ragctl logs backend | ragctl logs web  (or the Tauri desktop console)", file=sys.stderr)


def _load_dotenv() -> None:
    """Load `.env` from the monorepo root into ``os.environ`` if present.

    Uses ``setdefault`` so an explicitly-exported shell / .mcp.json env var
    ALWAYS wins over the file — this is the project-wide documented priority
    (shell/.mcp.json env > .env > config.yml, see kb-mcp/config.py:35).
    The previous unconditional overwrite silently clobbered intentionally-set
    env vars (e.g. BACKEND_PORT injected by .mcp.json / project_manager).
    Call this *before* any code that reads env vars (``import config``, etc.).
    """
    from pathlib import Path
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip("\"'")
            if key:
                os.environ.setdefault(key, val)

if __name__ == "__main__":
    main()
