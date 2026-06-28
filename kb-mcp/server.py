# -*- coding: utf-8 -*-
"""
kb-mcp MCP Server
=================
Thin MCP tool layer over kb_client.KbClient.

This server defines 35 MCP tools. Each tool is a one-liner that
delegates to the matching KbClient method. All HTTP logic lives in
kb_client/client.py — this file contains zero HTTP code.

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

mcp = FastMCP("kb-mcp")

# Singleton client (shared across all tool calls for connection pooling)
_kb: KbClient | None = None


def _client() -> KbClient:
    global _kb
    if _kb is None:
        import config
        _kb = KbClient(
            web_url=config.WEB_URL,
            backend_url=config.BACKEND_URL,
            mineru_url=config.MINERU_URL,
        )
    return _kb


def _j(data) -> str:
    """Serialize to compact JSON string."""
    return json.dumps(data, ensure_ascii=False)


# ============================================================
# HEALTH
# ============================================================

@mcp.tool()
async def health_check() -> str:
    """Check health of backend, MinerU OCR engine, and web frontend."""
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
    """Create a new knowledge base."""
    return _j(await _client().kb_create(name, description, parent_id))


@mcp.tool()
async def kb_update(kb_id: str, name: str = "", description: str = "") -> str:
    """Update a knowledge base's name and/or description."""
    return _j(await _client().kb_update(kb_id, name, description))


@mcp.tool()
async def kb_delete(kb_id: str) -> str:
    """Delete an entire knowledge base and all its contents (irreversible)."""
    return _j(await _client().kb_delete(kb_id))


@mcp.tool()
async def kb_search(query: str, top_k: int = 10) -> str:
    """Search across ALL knowledge bases by keyword. Returns ranked hits."""
    return _j(await _client().kb_search(query, top_k))


@mcp.tool()
async def kb_get_documents(kb_id: str) -> str:
    """List all documents inside a knowledge base."""
    return _j(await _client().kb_get_documents(kb_id))


# ============================================================
# DOCUMENT MANAGEMENT (CRUD)
# ============================================================

@mcp.tool()
async def kb_doc_read(path: str, max_chars: int = 20000, offset: int = 0, limit: int = 200) -> str:
    """Read the content of a document (Markdown body, paginated)."""
    return _j(await _client().kb_doc_read(path, max_chars, offset, limit))


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
async def fs_get_tree() -> str:
    """Get the full file system tree."""
    return _j(await _client().fs_get_tree())


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
    """Upload a local file into the file system tree."""
    return _j(await _client().fs_upload_file(file_path, parent_id, description))


# ============================================================
# PREVIEW
# ============================================================

@mcp.tool()
async def preview_file(node_id: str = "", path: str = "") -> str:
    """Preview or download a file by node id or relative path."""
    return _j(await _client().preview_file(node_id, path))


# ============================================================
# PROMPTS MANAGEMENT (CRUD)
# ============================================================

@mcp.tool()
async def prompts_list(keyword: str = "", category: str = "", tag: str = "", sort_by: str = "updatedAt", sort_order: str = "desc") -> str:
    """List/search prompts with optional filters."""
    return _j(await _client().prompts_list(keyword, category, tag, sort_by, sort_order))


@mcp.tool()
async def prompts_create(name: str, description: str, content: str, category: str = "default", tags: list = None) -> str:
    """Create a new prompt."""
    return _j(await _client().prompts_create(name, description, content, category, tags))


@mcp.tool()
async def prompts_get(prompt_id: str) -> str:
    """Get a single prompt by id."""
    return _j(await _client().prompts_get(prompt_id))


@mcp.tool()
async def prompts_update(prompt_id: str, name: str = "", description: str = "", content: str = "", category: str = "") -> str:
    """Update an existing prompt."""
    return _j(await _client().prompts_update(prompt_id, name, description, content, category))


@mcp.tool()
async def prompts_delete(prompt_id: str) -> str:
    """Delete a prompt by id."""
    return _j(await _client().prompts_delete(prompt_id))


@mcp.tool()
async def prompts_list_categories() -> str:
    """List all prompt categories."""
    return _j(await _client().prompts_list_categories())


@mcp.tool()
async def prompts_list_tags() -> str:
    """List all prompt tags."""
    return _j(await _client().prompts_list_tags())


# ============================================================
# PDF PARSING
# ============================================================

@mcp.tool()
async def parse_pdf(file_path: str, use_ocr: bool = True, parent_id: str = "") -> str:
    """Parse a PDF into Markdown. If parent_id is given, auto-saves to KB."""
    result = await _client().parse_pdf(file_path, use_ocr, parent_id)
    if isinstance(result, dict) and result.get("success"):
        return _j({
            "success": True,
            "source_filename": result.get("source_filename"),
            "markdown_path": result.get("markdown_path"),
            "page_count": result.get("page_count"),
            "image_count": result.get("image_count"),
            "markdown_chars": len(result.get("markdown", "") or ""),
        })
    return _j(result)


@mcp.tool()
async def parse_pdf_batch(file_paths: list, use_ocr: bool = True) -> str:
    """Batch-parse multiple PDF files."""
    return _j(await _client().parse_pdf_batch(file_paths, use_ocr))


@mcp.tool()
async def parse_pdf_to_kb(file_path: str, kb_id: str, use_ocr: bool = True) -> str:
    """Full pipeline: parse a PDF and save into a knowledge base."""
    result = await _client().parse_pdf_to_kb(file_path, kb_id, use_ocr)
    if isinstance(result, dict) and result.get("success"):
        return _j({
            "success": True,
            "source_filename": result.get("source_filename"),
            "markdown_path": result.get("markdown_path"),
            "page_count": result.get("page_count"),
            "image_count": result.get("image_count"),
            "markdown_chars": len(result.get("markdown", "") or ""),
            "saved_to_kb": kb_id,
        })
    return _j(result)


# ============================================================
# BACKEND STATUS
# ============================================================

@mcp.tool()
async def backend_status() -> str:
    """Get backend service info including DeepAgent and MinerU engine status."""
    return _j(await _client().backend_status())


# ---------- entry ----------
def main():
    if "--http" in sys.argv:
        mcp.run(transport="sse")
    else:
        mcp.run()


if __name__ == "__main__":
    main()
