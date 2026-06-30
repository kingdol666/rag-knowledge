# -*- coding: utf-8 -*-
"""
kb-mcp MCP Server
=================
Thin MCP tool layer over kb_client.KbClient.

This server defines MCP tools. Each tool is a one-liner that
delegates to the matching KbClient method. All HTTP logic lives in
kb_client/client.py ??this file contains zero HTTP code.

Long-running parse jobs (parse_pdf / parse_pdf_batch / parse_pdf_to_kb)
are NON-BLOCKING: they hand the slow work to an in-process background
task (task_registry) and return a task_id immediately. Poll results with
parse_task_status(task_id) / parse_tasks_list().

Run:
  python server.py            # stdio mode (for Agent harness)
  python server.py --http     # SSE mode
"""
from __future__ import annotations

import os
import sys
import json

from mcp.server.fastmcp import FastMCP

from kb_client import KbClient

import task_registry

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


def _exists(file_path: str) -> bool:
    from pathlib import Path
    return bool(file_path) and Path(file_path).exists()


def _running_payload(task_id: str, kind: str, detail: dict | None = None) -> str:
    """Immediate 'parse is running' reply returned for non-blocking parse tools."""
    payload = {
        "success": True,
        "status": "running",
        "message": "parsing task is running; call parse_task_status to get the result",
        "task_id": task_id,
        "kind": kind,
    }
    if detail:
        payload.update(detail)
    return _j(payload)


# ============================================================
# HEALTH
# ============================================================

@mcp.tool()
async def health_check() -> str:
    """Check health of backend and web frontend."""
    return _j(await _client().health_check())


# ============================================================
# KNOWLEDGE BASE MANAGEMENT (CRUD)
# ============================================================

@mcp.tool()
async def kb_list() -> str:
    """List all knowledge bases with id, name, description, and document count."""
    return _j(await _client().kb_list())


@mcp.tool()
async def kb_create(name: str, description: str = "", parent_id: str = "") -> str:
    """Create a new knowledge base. parent_id is an optional tree folder UUID for nesting (omit for root). Returns knowledgeBase with id (UUID) and path ??both work as kb_id in other tools."""
    return _j(await _client().kb_create(name, description, parent_id))


@mcp.tool()
async def kb_update(kb_id: str, name: str = "", description: str = "") -> str:
    """Update a knowledge base's name and/or description. kb_id accepts path or UUID."""
    return _j(await _client().kb_update(kb_id, name, description))


@mcp.tool()
async def kb_delete(kb_id: str) -> str:
    """Delete an entire knowledge base and all its contents (irreversible). kb_id accepts either the path string or the UUID returned by kb_create."""
    return _j(await _client().kb_delete(kb_id))


@mcp.tool()
async def kb_search(query: str, top_k: int = 10) -> str:
    """Search across ALL knowledge bases by keyword (full-text search). Returns ranked hits with scores and source fields."""
    return _j(await _client().kb_search(query, top_k))


@mcp.tool()
async def kb_get_documents(kb_id: str) -> str:
    """List all documents inside a knowledge base. kb_id accepts path or UUID."""
    return _j(await _client().kb_get_documents(kb_id))


# ============================================================
# DOCUMENT MANAGEMENT (CRUD)
# ============================================================

@mcp.tool()
async def kb_doc_read(kb_id: str = "", doc_path: str = "", path: str = "", max_chars: int = 20000, offset: int = 0, limit: int = 200) -> str:
    """Read the content of a document (Markdown body, paginated).

    Accepts either kb_id+doc_path (bare filename or relative, e.g.
    kb_id="uuid" doc_path="readme.md") or path (full relative path,
    e.g. "test/readme.md"). max_chars limits response size."""
    return _j(await _client().kb_doc_read(kb_id, doc_path, path, max_chars, offset, limit))


@mcp.tool()
async def kb_doc_create(kb_id: str, name: str, content: str, description: str = "") -> str:
    """Create a new Markdown document. Auto-dedup on name collision."""
    return _j(await _client().kb_doc_create(kb_id, name, content, description))


@mcp.tool()
async def kb_doc_update_meta(kb_id: str, doc_path: str, name: str = "", description: str = "") -> str:
    """Update a document's metadata (name, description)."""
    return _j(await _client().kb_doc_update_meta(kb_id, doc_path, name, description))


@mcp.tool()
async def kb_doc_update_content(kb_id: str, doc_path: str, content: str) -> str:
    """Overwrite a document's content."""
    return _j(await _client().kb_doc_update_content(kb_id, doc_path, content))


@mcp.tool()
async def kb_doc_delete(kb_id: str, doc_path: str) -> str:
    """Delete a single document."""
    return _j(await _client().kb_doc_delete(kb_id, doc_path))


@mcp.tool()
async def kb_doc_batch_delete(kb_id: str, doc_paths: list) -> str:
    """Delete multiple documents at once."""
    return _j(await _client().kb_doc_batch_delete(kb_id, doc_paths))


@mcp.tool()
async def kb_doc_move(doc_path: str, target_kb_id: str) -> str:
    """Move a document to a different knowledge base."""
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
    level children, etc.). 0 means unlimited."""
    tree = await _client().fs_get_tree()

    def _filter(nodes, depth=1):
        out = []
        for n in nodes:
            node_type = n.get("type", "")
            # When include_files is False, skip ALL file nodes at every level
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

    return _j(_filter(tree))


@mcp.tool()
async def fs_get_children(parent_id: str = "") -> str:
    """Get immediate children (folders + files) of a folder."""
    return _j(await _client().fs_get_children(parent_id))


@mcp.tool()
async def fs_get_node(node_id: str) -> str:
    """Get a single node by its id."""
    return _j(await _client().fs_get_node(node_id))


@mcp.tool()
async def fs_get_count() -> str:
    """Get total folder, file, and combined counts."""
    return _j(await _client().fs_get_count())


@mcp.tool()
async def fs_create_folder(name: str, parent_id: str = "", description: str = "", is_knowledge_base: bool = False) -> str:
    """Create a new folder (optionally as a knowledge base)."""
    return _j(await _client().fs_create_folder(name, parent_id, description, is_knowledge_base))


@mcp.tool()
async def fs_create_file(name: str, parent_id: str = "", description: str = "") -> str:
    """Create a new file node (metadata only)."""
    return _j(await _client().fs_create_file(name, parent_id, description))


@mcp.tool()
async def fs_update_node(node_id: str, name: str = "", description: str = "") -> str:
    """Update a node's name and/or description."""
    return _j(await _client().fs_update_node(node_id, name, description))


@mcp.tool()
async def fs_delete_node(node_id: str) -> str:
    """Delete a node (recursively for folders)."""
    return _j(await _client().fs_delete_node(node_id))


@mcp.tool()
async def fs_upload_file(file_path: str, parent_id: str = "", description: str = "") -> str:
    """Upload a local file into the file system tree. file_path is an absolute local disk path. parent_id is a tree folder UUID (empty = root)."""
    return _j(await _client().fs_upload_file(file_path, parent_id, description))


# ============================================================
# PREVIEW
# ============================================================

@mcp.tool()
async def preview_file(node_id: str = "", path: str = "") -> str:
    """Preview or download a file by node id (preferred) or relative path (e.g. "test/readme.md"). Either node_id or path must be provided."""
    return _j(await _client().preview_file(node_id, path))


# ============================================================
# PDF PARSING  (NON-BLOCKING)
# The parse HTTP calls can take minutes (MinerU OCR). To avoid blocking
# the MCP tool response ??and freezing the agent ??each parse tool hands
# the work to an asyncio background task (task_registry) and returns a
# task_id immediately. Results are retrieved via parse_task_status().
# ============================================================

@mcp.tool()
async def parse_pdf(file_path: str, use_ocr: bool = True, parent_id: str = "", description: str = "", tags: list = None) -> str:
    """Parse a PDF into Markdown. If parent_id is given, auto-saves to KB.

    NON-BLOCKING: returns immediately with a task_id once parsing has
    started. The actual parse (minutes for OCR) runs in the background. You
    can also provide a ``description`` that will be saved into the KB along
    with the parsed document (and will be searchable / visible in the UI).
    Poll the result with parse_task_status(task_id).

    Returns {success, status:'running', task_id, ...} right away."""
    if not _exists(file_path):
        return _j({"success": False, "error": f"file not found: {file_path}"})
    client = _client()
    meta = {"file_path": file_path, "use_ocr": use_ocr, "parent_id": parent_id, "description": description}

    async def _work():
        result = await client.parse_pdf(file_path, use_ocr, parent_id, description)
        if isinstance(result, dict) and result.get("success"):
            return {
                "success": True,
                "source_filename": result.get("source_filename"),
                "markdown_path": result.get("markdown_path"),
                "image_count": result.get("image_count"),
                "markdown_chars": len(result.get("markdown", "") or ""),
            }
        return result

    task_id = task_registry.submit(_work(), "parse_pdf", meta)
    return _running_payload(task_id, "parse_pdf", {"file_path": file_path, "description": description if description else None})


@mcp.tool()
async def parse_pdf_batch(file_paths: list, use_ocr: bool = True, descriptions: list = None, tags: list = None) -> str:
    """Batch-parse multiple PDF files.

    NON-BLOCKING: returns immediately with a task_id; files parse
    sequentially in the background. If you provide ``descriptions``, each
    will be forwarded to the parse endpoint (one per file, in order).
    Poll with parse_task_status(task_id).
    When done the result is {total, successful, results:[...]}."""
    client = _client()
    meta = {"file_paths": list(file_paths), "use_ocr": use_ocr, "descriptions": descriptions, "tags": tags}
    task_id = task_registry.submit(
        client.parse_pdf_batch(file_paths, use_ocr, descriptions, tags), "parse_pdf_batch", meta
    )
    return _running_payload(task_id, "parse_pdf_batch", {"file_count": len(file_paths)})


@mcp.tool()
async def parse_pdf_to_kb(file_path: str, kb_id: str, use_ocr: bool = True, description: str = "", tags: list = None) -> str:
    """Full pipeline: parse a PDF and save into a knowledge base.

    NON-BLOCKING: parse the PDF, then save the Markdown into the given
    knowledge base. You may provide a ``description`` to help identify the
    parsed document in the KB (searchable / visible in the UI).
    Returns immediately with a task_id once the pipeline has started;
    poll the result with parse_task_status(task_id).

    Returns {success, status:'running', task_id, ...} right away."""
    if not _exists(file_path):
        return _j({"success": False, "error": f"file not found: {file_path}"})
    client = _client()
    meta = {"file_path": file_path, "kb_id": kb_id, "use_ocr": use_ocr, "description": description, "tags": tags}

    async def _work():
        result = await client.parse_pdf_to_kb(file_path, kb_id, use_ocr, description, tags)
        if isinstance(result, dict) and result.get("success"):
            return {
                "success": True,
                "source_filename": result.get("source_filename"),
                "markdown_path": result.get("markdown_path"),
                "image_count": result.get("image_count"),
                "markdown_chars": len(result.get("markdown", "") or ""),
                "saved_to_kb": kb_id,
            }
        return result

    task_id = task_registry.submit(_work(), "parse_pdf_to_kb", meta)
    return _running_payload(task_id, "parse_pdf_to_kb", {"file_path": file_path, "kb_id": kb_id, "description": description if description else None})


@mcp.tool()
async def parse_pdf_to_kb_batch(file_paths: list, kb_id: str, use_ocr: bool = True, descriptions: list = None, tags: list = None) -> str:
    """Batch: parse many PDFs and save each into the same knowledge base.

    NON-BLOCKING: all files parse (sequentially) in ONE background task,
    so you get back a single task_id instead of one per file. You may
    provide ``descriptions`` (one per file, in order) to label each
    parsed document in the KB. Poll with parse_task_status(task_id).
    When done the result is {total, successful, saved_to_kb, results:[...]}
    where each entry in results carries the per-file outcome."""
    missing = [fp for fp in file_paths if not _exists(fp)]
    if missing:
        return _j({"success": False, "error": "file(s) not found", "missing": missing})
    client = _client()
    meta = {"file_paths": list(file_paths), "kb_id": kb_id, "use_ocr": use_ocr, "descriptions": descriptions, "tags": tags}
    task_id = task_registry.submit(
        client.parse_pdf_to_kb_batch(file_paths, kb_id, use_ocr, descriptions, tags),
        "parse_pdf_to_kb_batch",
        meta,
    )
    return _running_payload(
        task_id, "parse_pdf_to_kb_batch", {"file_count": len(file_paths), "kb_id": kb_id, "descriptions": descriptions}
    )


@mcp.tool()
async def parse_task_status(task_id: str) -> str:
    """Check the status of a non-blocking parse task.

    status is 'running', 'done', or 'error'. When done, result holds the
    parse summary (markdown_path, image_count, ...). When error, error
    holds the message. Use this to poll tasks from parse_pdf* tools.
    """
    rec = task_registry.get(task_id)
    if rec is None:
        return _j({"success": False, "error": f"unknown task_id: {task_id}"})
    view = task_registry.public_view(rec)
    view["success"] = True
    return _j(view)


@mcp.tool()
async def parse_tasks_list(status: str = "") -> str:
    """List background parse tasks, optionally filtered by status.

    status filters by 'running', 'done', or 'error'; omit for all.
    Handy to recall task ids submitted earlier this session.
    """
    return _j({"success": True, "tasks": task_registry.list_views(status)})


# ============================================================
# TAGS MANAGEMENT
# ============================================================

@mcp.tool()
async def kb_tags_list() -> str:
    """List all registered tags in the system."""
    return _j(await _client().kb_tags_list())


@mcp.tool()
async def kb_tag_create(tag: str) -> str:
    """Register a new tag (deduped, max 50 chars)."""
    return _j(await _client().kb_tag_create(tag))


@mcp.tool()
async def kb_doc_update_tags(kb_id: str, doc_path: str, tags: list) -> str:
    """Update a document's tags. kb_id accepts UUID; doc_path accepts full path or bare filename."""
    return _j(await _client().kb_doc_update_tags(kb_id, doc_path, tags))


@mcp.tool()
async def kb_doc_get_by_tag(tag: str, kb_id: str = "") -> str:
    """Find documents by tag across all KBs (or one KB if kb_id given)."""
    return _j(await _client().kb_doc_get_by_tag(tag, kb_id))


# ============================================================
# BACKEND STATUS
# ============================================================

@mcp.tool()
async def backend_status() -> str:
    """Get backend service health and MinerU OCR engine status."""
    return _j(await _client().backend_status())


# ---------- entry ----------
def main():
    if "--http" in sys.argv:
        mcp.run(transport="sse")
    else:
        mcp.run()


if __name__ == "__main__":
    main()
