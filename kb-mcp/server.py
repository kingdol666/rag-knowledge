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
parse_task_status(task_id) / parse_tasks_list().

Run:
  python server.py            # stdio mode (for Agent harness)
  python server.py --http     # SSE mode
"""
from __future__ import annotations

import asyncio
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


# ────────────────────────────────────────────────────────────────
# Auto-index helper (fire-and-forget): vector index + graph +
# vector_index YAML metadata for any document change.
# All document/non-parse write tools call this via asyncio.create_task.
# ────────────────────────────────────────────────────────────────

async def _auto_index_kb(kb_id: str, force: bool = False) -> None:
    """Best-effort background indexing: batch vector index + graph build.

    Called fire-and-forget after any document mutation (create, update,
    upload, move).  If indexing fails the main tool result is unaffected.
    """
    import logging
    logger = logging.getLogger(__name__)
    try:
        await asyncio.sleep(1.5)  # brief wait for web layer persistence
        client = _client()
        docs_resp = await client.kb_get_documents(kb_id)
        if not isinstance(docs_resp, dict) or not docs_resp.get("success"):
            return
        all_docs = docs_resp.get("documents", [])
        doc_paths = [d["path"] for d in all_docs if "path" in d]
        if not doc_paths:
            return
        # Phase 1: vector index + vector_index YAML metadata
        await client.batch_index_documents(kb_id, doc_paths, force=force)
        # Phase 2: knowledge graph
        await client.graph_build_kb(kb_id, force=False)
    except Exception:
        logger.warning("Auto-index background task failed for KB %s", kb_id, exc_info=True)


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
    """Create a new knowledge base. parent_id is an optional tree folder UUID for nesting (omit for root). Returns knowledgeBase with id (UUID) and path -- both work as kb_id in other tools. Automatically initializes the experience management folder."""
    result = await _client().kb_create(name, description, parent_id)
    if isinstance(result, dict) and result.get("success") and result.get("knowledgeBase", {}).get("id"):
        try:
            await _client().experience_init(result["knowledgeBase"]["id"])
        except Exception:
            pass  # non-fatal: experience init failure shouldn't break KB creation
    return _j(result)


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
    """Search KB metadata by keyword across ALL knowledge bases. Scans only document
    name and description (NOT the full document body or path). Returns ranked hits
    with scores where name match > description match.

    USE CASE: quick metadata lookup when you already have a specific doc name in
    mind and want to find which KB it lives in. For semantic content retrieval,
    prefer kb_search_vector or kb_search_two_stage.

    This is NOT a full-text content search. It does NOT read document bodies."""
    return _j(await _client().kb_search(query, top_k))


@mcp.tool()
async def kb_get_documents(kb_id: str) -> str:
    """List all documents inside a knowledge base. kb_id accepts path or UUID."""
    return _j(await _client().kb_get_documents(kb_id))


# ============================================================
# LIGHTWEIGHT CATALOG (id + description only, agentic-first retrieval)
# 仅返回 id/description 等最小投影，避免 file_size/tags/vector_index 等元信息污染 context。
# Agent 应优先用这些方法读 description 判断相关性，确认后再 kb_doc_read/kb_search_vector 取详情。
# ============================================================

@mcp.tool()
async def kb_catalog() -> str:
    """轻量知识库目录 —— 仅返回 [{kb_id, name, description, doc_count}]。

    用途（agentic 优先检索的第一步）：Agent 阅读每个 KB 的 description，
    用模型判断力决定哪个 KB 与当前场景真正相关，再深入该 KB。
    不加载 path/file_size 等多余字段，保持 context 干净。
    """
    data = await _client().kb_list()
    if not isinstance(data, dict) or not data.get("success"):
        return _j(data)
    catalog = [{
        "kb_id": kb.get("kbId") or kb.get("path"),
        "name": kb.get("name") or kb.get("path"),
        "description": kb.get("description", ""),
        "doc_count": kb.get("documentCount", 0),
    } for kb in data.get("knowledgeBases", [])]
    return _j({"success": True, "count": len(catalog), "catalog": catalog})


@mcp.tool()
async def kb_doc_catalog(kb_id: str) -> str:
    """轻量文档目录 —— 返回某 KB 内全部文档的 [{doc_path, name, description}]（仅这三字段）。

    用途（agentic 优先检索的第二步）：进入候选 KB 后，Agent 阅读每篇文档的 description，
    判断哪篇真正契合当前场景，确认后再 kb_doc_read 读全文或 kb_search_vector 向量精排。
    不加载 file_size/tags/vector_index/metadata，避免污染 context。
    """
    data = await _client().kb_get_documents(kb_id)
    if not isinstance(data, dict) or not data.get("success"):
        return _j(data)
    catalog = [{
        "doc_path": d.get("path"),
        "name": d.get("name"),
        "description": d.get("description", ""),
    } for d in data.get("documents", [])]
    return _j({"success": True, "kb_id": kb_id, "count": len(catalog), "catalog": catalog})


@mcp.tool()
async def fs_catalog_all(include_files: bool = True) -> str:
    """全库轻量目录（扁平）—— 返回所有文件夹+文件的 [{id, path, name, description, type, is_kb, doc_count, parent_id}]。

    用途：一次性获取全库结构概览（仅 id+description），Agent 据此规划检索路径。
    与 fs_get_tree 的区别：扁平结构 + 仅必要字段（无 fileSize/metadata/dates/children 嵌套），
    大幅减少 context 占用。include_files=False 只列文件夹。
    """
    tree = await _client().fs_get_tree()
    if not isinstance(tree, list):
        return _j(tree)
    flat = []

    def _walk(nodes, parent_id=""):
        for n in nodes:
            ntype = n.get("type", "folder")
            if ntype == "file" and not include_files:
                continue
            flat.append({
                "id": n.get("id"),
                "path": n.get("path"),
                "name": n.get("name"),
                "description": n.get("description", ""),
                "type": ntype,
                "is_kb": bool(n.get("isKnowledgeBase")),
                "doc_count": n.get("documentCount", 0),
                "parent_id": parent_id,
            })
            for child in n.get("children", []):
                _walk([child], n.get("id"))

    _walk(tree)
    return _j({"success": True, "count": len(flat), "catalog": flat})


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
    """Create a new Markdown document. Auto-dedup on name collision.

    **Auto-indexing**: after creation the document is automatically vector
    indexed (ChromaDB) and graph indexed (Neo4j), and ``vector_index``
    metadata is written to ``.knowledge-base.yml``."""
    result = await _client().kb_doc_create(kb_id, name, content, description)
    asyncio.create_task(_auto_index_kb(kb_id))
    return _j(result)


@mcp.tool()
async def kb_doc_update_meta(kb_id: str, doc_path: str, name: str = "", description: str = "") -> str:
    """Update a document's metadata (name, description)."""
    return _j(await _client().kb_doc_update_meta(kb_id, doc_path, name, description))


@mcp.tool()
async def kb_doc_update_content(kb_id: str, doc_path: str, content: str) -> str:
    """Overwrite a document's content.

    **Auto-indexing**: after the content update, the document is automatically
    re-vector-indexed and its graph index rebuilt, and ``vector_index``
    metadata is refreshed in ``.knowledge-base.yml``."""
    result = await _client().kb_doc_update_content(kb_id, doc_path, content)
    asyncio.create_task(_auto_index_kb(kb_id, force=True))
    return _j(result)


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
    """Move a document to a different knowledge base.

    **Auto-indexing**: after the move, both the source and target KBs have
    their vector index, graph index, and ``vector_index`` YAML metadata
    automatically rebuilt."""
    result = await _client().kb_doc_move(doc_path, target_kb_id)
    # Index both KBs — derive source kb_id from the doc_path
    # (doc_path looks like "SourceKB/doc.md")
    source_path = doc_path.split("/")[0].split("\\")[0] if "/" in doc_path or "\\" in doc_path else ""
    if source_path and source_path != target_kb_id:
        asyncio.create_task(_auto_index_kb(source_path, force=True))
    asyncio.create_task(_auto_index_kb(target_kb_id, force=True))
    return _j(result)


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
    """Upload a local file into the file system tree. file_path is an absolute local disk path. parent_id is a tree folder UUID (empty = root).

    **Auto-indexing**: if the parent folder is a knowledge base, the uploaded
    file is automatically vector indexed and graph indexed, and
    ``vector_index`` metadata written to ``.knowledge-base.yml``."""
    result = await _client().fs_upload_file(file_path, parent_id, description)
    # If parent_id looks like a KB path (not a UUID), use it directly
    if parent_id:
        asyncio.create_task(_auto_index_kb(parent_id, force=True))
    return _j(result)


# ============================================================
# PREVIEW
# ============================================================

@mcp.tool()
async def preview_file(node_id: str = "", path: str = "") -> str:
    """Preview or download a file by node id (preferred) or relative path (e.g. "test/readme.md"). Either node_id or path must be provided."""
    return _j(await _client().preview_file(node_id, path))


# ============================================================
# DOCUMENT PARSING  (NON-BLOCKING)
# The MinerU OCR engine runs alongside the backend — no manual
# startup needed. Each parse call returns a task_id immediately;
# poll parse_task_status(task_id) for the result.
# Supported formats: .pdf .png .jpg .jpeg .docx .xlsx
# ============================================================

@mcp.tool()
async def parse_doc(file_path: str, kb_id: str, use_ocr: bool = True, description: str = "", tags: list = None) -> str:
    """Parse a document (PDF / Image / Word / Excel) into Markdown and save into a knowledge base.

    NON-BLOCKING: parse the file, then save the Markdown into the given
    knowledge base. You may provide a ``description`` to help identify the
    parsed document in the KB (searchable / visible in the UI).
    Returns immediately with a task_id once parsing has started;
    poll the result with parse_task_status(task_id).

    **Auto-indexing**: after successful parse + save, the task automatically
    triggers vector index (ChromaDB) and knowledge graph (Neo4j) for the
    document, so ``kb_search_vector`` and ``kb_graph_*`` work immediately
    once the task completes.

    Supported formats: .pdf .png .jpg .jpeg .docx .xlsx

    Returns {success, status:'running', task_id, ...} right away."""
    if not _exists(file_path):
        return _j({"success": False, "error": f"file not found: {file_path}"})
    client = _client()
    meta = {"file_path": file_path, "kb_id": kb_id, "use_ocr": use_ocr, "description": description, "tags": tags}

    async def _work():
        result = await client.parse_doc(file_path, kb_id, use_ocr, description, tags)
        if isinstance(result, dict) and result.get("success"):
            payload = {
                "success": True,
                "source_filename": result.get("source_filename"),
                "markdown_path": result.get("markdown_path"),
                "image_count": result.get("image_count"),
                "markdown_chars": len(result.get("markdown", "") or ""),
                "saved_to_kb": kb_id,
            }

            # ─────────────────────────────────────────────────────
            # Phase 2: auto vector index + vector_index YAML metadata
            # ─────────────────────────────────────────────────────
            await asyncio.sleep(2)  # brief wait for web layer persistence
            try:
                docs_resp = await client.kb_get_documents(kb_id)
                if isinstance(docs_resp, dict) and docs_resp.get("success"):
                    all_docs = docs_resp.get("documents", [])
                    doc_paths = [d["path"] for d in all_docs if "path" in d]
                    if doc_paths:
                        # Batch-vector-index all docs (writes vector_index to YAML)
                        index_resp = await client.batch_index_documents(
                            kb_id, doc_paths, force=False
                        )
                        payload["auto_indexed"] = (
                            index_resp.get("total_indexed", 0)
                            if isinstance(index_resp, dict) else 0
                        )

                        # Build knowledge graph for the KB
                        graph_resp = await client.graph_build_kb(kb_id, force=False)
                        if isinstance(graph_resp, dict) and graph_resp.get("result"):
                            payload["auto_graph_docs"] = (
                                graph_resp["result"].get("docs_processed", 0)
                            )

                    payload["auto_pipeline"] = "auto-vector-index+graph"
            except Exception as e:
                payload["auto_index_warning"] = str(e)

            return payload
        return result

    task_id = task_registry.submit(_work(), "parse_doc", meta)
    return _running_payload(task_id, "parse_doc", {"file_path": file_path, "kb_id": kb_id, "description": description if description else None})


@mcp.tool()
async def parse_doc_batch(file_paths: list, kb_id: str, use_ocr: bool = True, descriptions: list = None, tags: list = None) -> str:
    """Batch: parse multiple documents (PDF / Image / Word / Excel) and save each into the same knowledge base.

    NON-BLOCKING: all files parse (sequentially) in ONE background task,
    so you get back a single task_id instead of one per file. You may
    provide ``descriptions`` (one per file, in order) to label each
    parsed document in the KB. Poll with parse_task_status(task_id).
    When done the result is {total, successful, saved_to_kb, results:[...]}
    where each entry in results carries the per-file outcome.

    Supported formats: .pdf .png .jpg .jpeg .docx .xlsx"""
    missing = [fp for fp in file_paths if not _exists(fp)]
    if missing:
        return _j({"success": False, "error": "file(s) not found", "missing": missing})
    client = _client()
    meta = {"file_paths": list(file_paths), "kb_id": kb_id, "use_ocr": use_ocr, "descriptions": descriptions, "tags": tags}

    async def _batch_work():
        """Parse batch → auto-describe → auto-vector-index → auto-graph-build → quality-check pipeline."""
        import time
        from pathlib import Path
        # Phase 1: parse all files
        parse_result = await client.parse_doc_batch(file_paths, kb_id, use_ocr, descriptions, tags)
        successful = parse_result.get("successful", 0)
        if successful == 0:
            return parse_result

        # Wait a brief moment for web layer to persist files
        await asyncio.sleep(2)

        quality = {"description_issues": [], "vector_missing": [], "warnings": [],
                   "descriptions_auto_generated": []}

        # Phase 2: get all documents in the KB to discover their paths
        try:
            docs_resp = await client.kb_get_documents(kb_id)
            if isinstance(docs_resp, dict) and docs_resp.get("success"):
                all_docs = docs_resp.get("documents", [])
                doc_paths = [d["path"] for d in all_docs if "path" in d]
                if doc_paths:
                    # ─────────────────────────────────────────────────────
                    # Phase 2a: Auto-generate A4 descriptions from content
                    # Read the first 2000 chars of each doc, extract the
                    # real title and abstract, write an A4-format description
                    # that an Agent can use to judge relevance at a glance.
                    # ─────────────────────────────────────────────────────
                    import re
                    for doc in all_docs:
                        try:
                            doc_name = doc.get("name", "")
                            current_desc = (doc.get("description") or "").strip()
                            # Read doc content (bare filename as doc_path)
                            content_resp = await client.kb_doc_read(
                                kb_id=kb_id, doc_path=doc_name, max_chars=2000
                            )
                            content = ""
                            if isinstance(content_resp, dict):
                                content = content_resp.get("markdown") or content_resp.get("content") or ""

                            if content and len(content) > 100:
                                # Extract real title (first # line)
                                title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
                                real_title = title_match.group(1).strip() if title_match else ""

                                # Extract abstract
                                abstract = ""
                                abs_match = re.search(
                                    r'##\s*(?:ABSTRACT|Abstract|摘要)\s*\n(.*?)(?:\n##|\Z)',
                                    content, re.DOTALL
                                )
                                if abs_match:
                                    abstract = abs_match.group(1).strip()[:500]

                                # Build A4-format description
                                # Format: [Title] — [key methods/approach] — [problem/solution] — [key metrics] — [year/source]
                                parts = []
                                if real_title:
                                    parts.append(real_title)
                                else:
                                    parts.append(doc_name.replace('.md','').replace('-',' '))

                                # Extract key methods and metrics from abstract
                                if abstract:
                                    # Take first 2 sentences as method + result summary
                                    sentences = re.split(r'(?<=[.!?])\s+', abstract)
                                    method_part = sentences[0][:200] if sentences else ""
                                    parts.append(method_part)
                                    if len(sentences) > 1:
                                        result_part = sentences[1][:200]
                                        parts.append(result_part)

                                # Find year (YYYY) in filename or content
                                year_match = re.search(r'(19|20)\d{2}', doc_name + content[:500])
                                year_str = year_match.group(0) if year_match else ""

                                # Build final description (120-250 chars, A4 format)
                                a4_desc = " — ".join(p.strip() for p in parts if p.strip())[:350]
                                if a4_desc and len(a4_desc) > 60:
                                    # Only apply if significantly better than current
                                    if not current_desc or len(current_desc) < 30 or \
                                       current_desc.startswith("Parsed from") or \
                                       current_desc == doc_name.replace('.md',''):
                                        desc_to_set = a4_desc
                                    else:
                                        # Keep current if it already has good content; flag for review
                                        desc_to_set = None
                                        quality["description_issues"].append({
                                            "path": doc.get("path"),
                                            "name": doc_name,
                                            "current_desc": current_desc[:80],
                                            "auto_suggestion": a4_desc[:200],
                                        })

                                    if desc_to_set:
                                        try:
                                            await client.kb_doc_update_meta(
                                                kb_id=kb_id, doc_path=doc_name,
                                                description=desc_to_set
                                            )
                                            quality["descriptions_auto_generated"].append({
                                                "name": doc_name,
                                                "old": current_desc[:60],
                                                "new": desc_to_set[:120],
                                            })
                                        except Exception as e:
                                            quality["warnings"].append(
                                                f"description更新失败: {doc_name}: {e}"
                                            )
                        except Exception:
                            pass  # non-fatal per-doc

                    # Phase 2b: batch vector index all docs → ChromaDB
                    index_resp = await client.batch_index_documents(kb_id, doc_paths, force=False)
                    indexed_count = index_resp.get("total_indexed", 0) if isinstance(index_resp, dict) else 0
                    parse_result["auto_indexed"] = indexed_count

                    # Phase 2c: build knowledge graph → Neo4j
                    graph_resp = await client.graph_build_kb(kb_id, force=False)
                    graph_docs = 0
                    if isinstance(graph_resp, dict) and graph_resp.get("result"):
                        graph_docs = graph_resp["result"].get("docs_processed", 0)
                    parse_result["auto_graph_docs"] = graph_docs

                    # ─────────────────────────────────────────────────────
                    # Phase 3: Quality Check (lightweight organize audit)
                    # ─────────────────────────────────────────────────────

                    # 3a — O11-lite: remaining description issues check
                    for doc in all_docs:
                        desc = (doc.get("description") or "").strip()
                        if not desc or desc.startswith("Parsed from"):
                            # Only flag if our auto-generate didn't catch it
                            already_fixed = any(
                                gen["name"] == doc.get("name")
                                for gen in quality.get("descriptions_auto_generated", [])
                            )
                            if not already_fixed:
                                quality["description_issues"].append({
                                    "path": doc.get("path"),
                                    "name": doc.get("name"),
                                    "current_desc": desc[:80],
                                    "suggestion": "自动生成description失败，需人工处理"
                                })

                    # 3b — O12-lite: vector index coverage
                    try:
                        for doc in all_docs:
                            vi = doc.get("vector_index") or doc.get("vectorIndex") or {}
                            if not vi or not vi.get("total_chunks", 0):
                                quality["vector_missing"].append({
                                    "path": doc.get("path"),
                                    "name": doc.get("name"),
                                })
                    except Exception:
                        pass

                    # 3c — O13-lite: count consistency
                    quality["total_docs_in_kb"] = len(all_docs)
                    quality["total_successful_parsed"] = successful
                    if len(all_docs) != successful:
                        quality["warnings"].append(
                            f"文档计数不一致: parse成功{successful}, KB目录显示{len(all_docs)}"
                        )

        except Exception as e:
            parse_result["auto_index_warning"] = str(e)

        parse_result["auto_pipeline"] = "auto-describe+vector+graph+quality-check"
        parse_result["quality_check"] = quality

        # Phase 4: flag recommendation
        if quality.get("descriptions_auto_generated"):
            parse_result["descriptions_auto_generated"] = len(quality["descriptions_auto_generated"])
        if quality["description_issues"] or quality["vector_missing"]:
            parse_result["organize_recommended"] = True
            remaining_desc = len(quality["description_issues"])
            parse_result["organize_tip"] = (
                f"自动修复了{len(quality.get('descriptions_auto_generated',[]))}个description, "
                f"还有{remaining_desc}个待处理, "
                f"向量索引缺失({len(quality['vector_missing'])}个). "
            )
        else:
            parse_result["organize_recommended"] = False

        return parse_result

    task_id = task_registry.submit(
        _batch_work(),
        "parse_doc_batch",
        meta,
    )
    return _running_payload(
        task_id, "parse_doc_batch", {"file_count": len(file_paths), "kb_id": kb_id, "descriptions": descriptions}
    )


@mcp.tool()
async def parse_task_status(task_id: str) -> str:
    """Check the status of a non-blocking parse task.

    status is 'running', 'done', or 'error'. When done, result holds the
    parse summary (markdown_path, image_count, ...). When error, error
    holds the message. Use this to poll tasks from parse_doc* tools.
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
# EXPERIENCE MANAGEMENT --- 经验管理（10个MCP工具）
# ============================================================

@mcp.tool()
async def experience_create(kb_id: str, title: str, scenario: str = "",
    category: str = "tip", problem: str = "", solution: str = "",
    result: str = "success", key_lessons: list = None, tags: list = None,
    severity: str = "normal", related_docs: list = None,
    prerequisites: list = None, metrics: str = "") -> str:
    """创建一条经验记录。

    经验是实践总结的可复用知识，相比文档多了评分、应用记录、场景绑定等维度。
    一条经验包含：问题描述、解决方案、关键教训（可执行条目列表）、结果（成功/失败）、
    严重程度（紧急/重要/普通/提示）、场景标识、关联文档等。

    Args:
        kb_id: 知识库 ID 或路径
        title: 经验标题
        scenario: 场景标识（如 "coal-mill-fault-prediction"），用于按场景检索
        category: 类别（best_practice=最佳实践, troubleshooting=故障排查,
                  lesson_learned=经验教训, optimization=优化, tip=小技巧,
                  workflow=工作流, decision=决策记录）
        problem: 要解决的问题描述
        solution: 解决方案或操作步骤
        result: 结果（success=成功, partial=部分成功, failed=失败, inconclusive=不确定）
        key_lessons: 关键教训列表，每条应该是可独立执行的操作条目
        tags: 标签列表
        severity: 严重程度（critical=紧急, important=重要, normal=普通, tip=提示）
        related_docs: 关联的文档路径列表（如 ["Thermal-Power/doc1.md"]）
        prerequisites: 前置条件列表
        metrics: JSON 字符串，自定义量化指标（如 '{"effectiveness": 95, "difficulty": 60}'）

    Returns:
        {success, experience: {id, title, path, scenario, ...}}
    """
    parsed_metrics = json.loads(metrics) if metrics else {}
    return _j(await _client().experience_create(
        kb_id, title, scenario, category, problem, solution, result,
        key_lessons or [], tags or [], severity, related_docs or [],
        prerequisites or [], parsed_metrics
    ))


@mcp.tool()
async def experience_read(kb_id: str, exp_id: str) -> str:
    """读取一条经验的完整信息（元数据 + 正文内容）。

    Args:
        kb_id: 知识库 ID 或路径
        exp_id: 经验 ID（如创建时返回的 "exp-xxxxxxxxxxxx"）

    Returns:
        {success, experience: {id, title, ...}, content: "markdown 正文"}
    """
    return _j(await _client().experience_read(kb_id, exp_id))


@mcp.tool()
async def experience_list(kb_id: str, scenario: str = "",
    category: str = "", tag: str = "") -> str:
    """列出知识库中的经验，支持按场景/类别/标签过滤。结果按评分从高到低排序。

    Args:
        kb_id: 知识库 ID 或路径
        scenario: 可选，按场景标识过滤
        category: 可选，按类别过滤（best_practice/troubleshooting/lesson_learned/...）
        tag: 可选，按标签过滤

    Returns:
        {success, count, experiences: [{id, title, scenario, rating_avg, ...}]}
    """
    return _j(await _client().experience_list(kb_id, scenario, category, tag))


@mcp.tool()
async def experience_update(kb_id: str, exp_id: str, title: str = "",
    scenario: str = "", category: str = "", problem: str = "",
    solution: str = "", result: str = "", key_lessons: list = None,
    tags: list = None, severity: str = "", status: str = "",
    related_docs: list = None, prerequisites: list = None,
    metrics: str = "") -> str:
    """更新一条经验记录。只传需要更新的字段，不传的字段保持不变。

    Args:
        kb_id: 知识库 ID 或路径
        exp_id: 经验 ID
        title: 新标题
        scenario: 新场景标识
        category: 新类别
        problem: 新问题描述
        solution: 新解决方案
        result: 新结果
        key_lessons: 新关键教训列表
        tags: 新标签列表
        severity: 新严重程度
        status: 新状态（draft=草稿, published=已发布, archived=已归档）
        related_docs: 新关联文档列表
        prerequisites: 新前置条件列表
        metrics: JSON 字符串，新量化指标

    Returns:
        {success, experience: {id, title, ...}}
    """
    kwargs = {}
    for k, v in [("title", title), ("scenario", scenario), ("category", category),
                 ("problem", problem), ("solution", solution), ("result", result),
                 ("severity", severity), ("status", status)]:
        if v: kwargs[k] = v
    if key_lessons: kwargs["key_lessons"] = key_lessons
    if tags: kwargs["tags"] = tags
    if related_docs: kwargs["related_docs"] = related_docs
    if prerequisites: kwargs["prerequisites"] = prerequisites
    if metrics: kwargs["metrics"] = json.loads(metrics)
    return _j(await _client().experience_update(kb_id, exp_id, **kwargs))


@mcp.tool()
async def experience_delete(kb_id: str, exp_id: str) -> str:
    """永久删除一条经验。不可恢复。

    Args:
        kb_id: 知识库 ID 或路径
        exp_id: 经验 ID

    Returns:
        {success, deleted_id}
    """
    return _j(await _client().experience_delete(kb_id, exp_id))


@mcp.tool()
async def experience_apply(kb_id: str, exp_id: str, user: str = "",
    context: str = "", result: str = "", notes: str = "") -> str:
    """标记一条经验已被应用。记录使用者、场景和效果。每次调用增加 applied_count。

    Args:
        kb_id: 知识库 ID 或路径
        exp_id: 经验 ID
        user: 使用者标识（如工号、用户名）
        context: 应用场景描述（如 "#3机组CNN-LSTM偏差度0.8"）
        result: 应用效果（success=成功, partial=部分有效, failed=无效）
        notes: 备注

    Returns:
        {success, experience: {..., applied_count, ...}, apply_record: {user, context, result, notes}}
    """
    return _j(await _client().experience_apply(kb_id, exp_id, user, context, result, notes))


@mcp.tool()
async def experience_review(kb_id: str, exp_id: str, reviewer: str = "",
    rating: float = 5.0, comment: str = "") -> str:
    """评审一条经验，给出评分（0-5分）和评论。自动更新该经验的平均评分和评审次数。

    Args:
        kb_id: 知识库 ID 或路径
        exp_id: 经验 ID
        reviewer: 评审人
        rating: 评分 0-5（0=无用, 5=非常有用）
        comment: 评审意见

    Returns:
        {success, experience: {..., rating_avg, review_count, ...}, review_record}
    """
    return _j(await _client().experience_review(kb_id, exp_id, reviewer, rating, comment))


@mcp.tool()
async def experience_find_by_scenario(kb_id: str, scenario: str) -> str:
    """按场景标识查找经验。这是经验检索的核心入口——Agent 应优先使用场景来定位经验。

    Args:
        kb_id: 知识库 ID 或路径
        scenario: 场景标识（如 "coal-mill-fault-prediction"）

    Returns:
        {success, count, experiences: [{id, title, scenario, rating_avg, applied_count}]}
    """
    return _j(await _client().experience_list(kb_id, scenario=scenario))


@mcp.tool()
async def experience_summary(kb_id: str) -> str:
    """获取经验的统计摘要，包括总数、按类别分布、按严重程度分布、总应用次数、平均评分、Top5经验。

    Args:
        kb_id: 知识库 ID 或路径

    Returns:
        {success, summary: {total, by_category, by_severity, total_applied, avg_rating, top_experiences}}
    """
    return _j(await _client().experience_summary(kb_id))


@mcp.tool()
async def experience_search(kb_id: str, query: str, top_k: int = 10) -> str:
    """元信息搜索经验：在经验的标题、问题、方案、关键教训、标签中匹配关键词。

    适用于已知部分关键词的精确查找。结果按相关度+评分+应用次数综合排序。

    Args:
        kb_id: 知识库 ID 或路径
        query: 搜索关键词
        top_k: 返回数量（默认10）

    Returns:
        {success, count, query, experiences: [{id, title, scenario, rating_avg, ...}]}
    """
    return _j(await _client().experience_search(kb_id, query, top_k))


@mcp.tool()
async def experience_search_vector(kb_id: str, query: str, top_k: int = 5) -> str:
    """向量语义搜索经验：用自然语言查询经验的语义内容。

    适用于模糊查询，如"以前遇到类似振动问题怎么处理的"。需要经验已建立向量索引。
    自动过滤只返回经验类型的结果（doc_type=experience）。

    Args:
        kb_id: 知识库 ID 或路径
        query: 自然语言查询
        top_k: 返回数量（默认5）

    Returns:
        {success, query, count, results: [{content, score, doc_path, chunk_index}]}
    """
    return _j(await _client().experience_search_vector(kb_id, query, top_k))


@mcp.tool()
async def experience_search_global(query: str, top_k: int = 10) -> str:
    """跨 KB 全局搜索经验：遍历所有知识库的经验，返回最相关的结果。

    适用于"全厂所有关于故障排查的经验有哪些？"这类全库查询。

    Args:
        query: 搜索关键词
        top_k: 返回数量（默认10）

    Returns:
        {success, query, count, experiences: [{id, title, kb_path, rating_avg, ...}]}
    """
    return _j(await _client().experience_search_global(query, top_k))


# ============================================================
# BACKEND STATUS
# ============================================================

@mcp.tool()
async def backend_status() -> str:
    """Get backend service health and MinerU OCR engine status."""
    return _j(await _client().backend_status())


# ============================================================
# 向量检索与两阶段精准检索（新增）
# ============================================================

@mcp.tool()
async def kb_search_vector(query: str, kb_id: str = "", top_k: int = 5,
                            score_threshold: float = 0.0) -> str:
    """向量语义搜索文档片段。

    Args:
        query: 查询文本
        kb_id: 限定知识库；空则跨库
        top_k: 返回结果数
        score_threshold: 最低余弦相似度阈值（0~1）；<=0 用后端默认(0.35)。降低可召回更多片段

    Returns:
        {success, results: [{content, score, doc_path, chunk_index, kb_id}]}
    """
    return _j(await _client().vector_search(query, kb_id, top_k, score_threshold))


@mcp.tool()
async def kb_search_batch_vector(
    query_doc_paths: list,
    kb_id: str = "",
    top_k: int = 5,
    score_threshold: float = 0.3,
) -> str:
    """批量向量相似度查询：对多个源文档找出最相似的其他文档。

    典型场景：
    - 跨文档相似度分析："哪些文档与文档A和文档B内容相似？"
    - 相关文档发现：批量查询一组文档的关联内容
    - 去重检测：发现近重复文档

    Args:
        query_doc_paths: 源文档路径列表（相对路径，如 ["legal/contract.md", "tech/python.md"]）
        kb_id: 可选限定知识库（路径或UUID）
        top_k: 每个源文档返回的最相似文档数
        score_threshold: 最低余弦相似度阈值 (0~1)，越高越严格

    Returns:
        {success, results: {doc_path: [{content, score, matched_doc_path, chunk_index, kb_id}]}, count}
    """
    return _j(await _client().batch_vector_search(
        query_doc_paths, kb_id, top_k, score_threshold
    ))


@mcp.tool()
async def kb_search_two_stage(
    query: str,
    kb_id: str = "",
    stage1_top_k: int = 20,
    stage2_top_k: int = 5,
    enable_graph_expansion: bool = True,
    score_threshold: float = 0.0,
) -> str:
    """两阶段精准检索：先广搜索定位候选文档，再向量精筛片段。

    推荐 Agent 首选此工具，比纯向量检索更精准，避免幻觉。

    Args:
        query: 用户问题
        kb_id: 限定知识库；空则跨库
        stage1_top_k: Stage 1 候选文档数
        stage2_top_k: Stage 2 每文档返回片段数
        enable_graph_expansion: 是否启用图谱邻居扩展
        score_threshold: 向量相似度阈值（0~1）；<=0 用后端默认(0.35)

    Returns:
        {success, stage1: {candidates}, stage2: {results}, total_results}
    """
    return _j(await _client().two_stage_search(
        query, kb_id, stage1_top_k, stage2_top_k, enable_graph_expansion,
        score_threshold
    ))


@mcp.tool()
async def kb_reindex(kb_id: str = "", force: bool = False) -> str:
    """重建向量索引和知识图谱。kb_id 为空则重建全部。

    force=True 时强制重建所有文档（包括已索引的）。
    """
    return _j(await _client().reindex(kb_id, force))


@mcp.tool()
async def kb_index_document(kb_id: str, doc_path: str, doc_name: str = "", description: str = "", content: str = "") -> str:
    """单文档向量+图谱索引。将文档内容（或已有文档）存入向量数据库并记录 vector_index 到元信息。

    用于手动触发文档的向量索引构建。如果提供 content 则直接使用，否则从存储自动读取。
    索引完成后会在 .knowledge-base.yml 的对应文档记录 vector_index 信息（含 collection、chunks 等）。
    同时会重建 BM25 关键词索引使后续两阶段检索能定位到该文档。

    Args:
        kb_id: 知识库 ID 或路径
        doc_path: 文档在 KB 中的相对路径
        doc_name: 文档名称
        description: 文档描述
        content: 文档正文内容；为空则从文件自动读取

    Returns:
        {success, vector_index: {collection, chunk_id_prefix, total_chunks, graph_doc_id}, graph_stats: {entities, relations}}
    """
    return _j(await _client().index_document(kb_id, doc_path, doc_name, description, content))


@mcp.tool()
async def kb_batch_index(
    kb_id: str,
    doc_paths: list,
    force: bool = False,
) -> str:
    """批量文档向量+图谱索引。

    一次性对知识库中的多个文档建立向量索引和知识图谱索引。
    索引后会更新 .knowledge-base.yml 中的 vector_index 元信息。

    Args:
        kb_id: 知识库 ID 或路径
        doc_paths: 文档相对路径列表（如 ["doc1.md", "doc2.md"]）
        force: 是否覆盖已有索引

    Returns:
        {success, indexed: [...], skipped: [...], errors: [...], total_indexed}
    """
    return _j(await _client().batch_index_documents(kb_id, doc_paths, force))


@mcp.tool()
async def kb_search_stats(kb_id: str = "") -> str:
    """向量索引统计信息。查看各知识库在向量数据库中的索引情况。

    Args:
        kb_id: 可选，限定知识库；空则返回全部

    Returns:
        {success, stats: {collections: [{collection, chunk_count}]}}
    """
    return _j(await _client().search_stats(kb_id))


@mcp.tool()
async def kb_graph_search(keyword: str, limit: int = 20) -> str:
    """搜索知识图谱中的文档节点（按名称/路径）。"""
    return _j(await _client().graph_search(keyword, limit))


@mcp.tool()
async def kb_graph_search_kbs(keyword: str, limit: int = 20) -> str:
    """搜索知识图谱中的知识库节点。"""
    return _j(await _client().graph_search_kbs(keyword, limit))


@mcp.tool()
async def kb_graph_search_tags(keyword: str, limit: int = 20) -> str:
    """搜索知识图谱中的标签节点。"""
    return _j(await _client().graph_search_tags(keyword, limit))


@mcp.tool()
async def kb_graph_neighbors(node_id: str, node_type: str = "document", depth: int = 1) -> str:
    """获取节点（文档/KB/标签）的邻居子图。node_type: document|kb|tag"""
    return _j(await _client().graph_neighbors(node_id, node_type, depth))


@mcp.tool()
async def kb_graph_stats() -> str:
    """返回知识图谱统计信息。"""
    return _j(await _client().graph_stats())


@mcp.tool()
async def kb_graph_health() -> str:
    """检查 Neo4j 知识图谱是否可用（健康探测，永不抛错）。"""
    return _j(await _client().graph_health())


@mcp.tool()
async def kb_graph_document(doc_path: str, limit: int = 50) -> str:
    """查看单文档的知识图谱视图：文档信息、标签、关联文档、跨 KB 连接。

    根据文档路径找到该文档在 Neo4j 中的全部图谱信息。
    返回：{document, tags, related_documents, cross_kb_links, ...}"""
    return _j(await _client().graph_document(doc_path, limit))


@mcp.tool()
async def kb_graph_document_related(doc_path: str, limit: int = 20) -> str:
    """返回与某文档关联的其他文档（基于同KB/共享标签/描述相似度）。"""
    return _j(await _client().graph_document_related(doc_path, limit))


@mcp.tool()
async def kb_graph_documents_by_tag(tag_name: str, limit: int = 50) -> str:
    """按标签查找文档。"""
    return _j(await _client().graph_documents_by_tag(tag_name, limit))


@mcp.tool()
async def kb_graph_kb_overview(kb_id: str) -> str:
    """KB 级图谱概览：文档统计、标签分布、关联 KB、Top 关联文档。

    查看某个知识库的图谱整体情况，发现该 KB 的核心文档和关联。"""
    return _j(await _client().graph_kb_overview(kb_id))


@mcp.tool()
async def kb_graph_build_kb(kb_id: str, force: bool = False) -> str:
    """为整个知识库构建文档关系图谱（基于 metadata，不读文档内容）。

    遍历 KB 内所有文档的 metadata（name, description, tags），
    通过共享标签/同KB/描述相似度建立文档间 RELATED_TO 关系。
    force=True：先清空再重建；force=False：增量（跳过已索引文档）。
    返回：{docs_processed, docs_skipped, total_relations, errors, ...}"""
    return _j(await _client().graph_build_kb(kb_id, force))


@mcp.tool()
async def kb_graph_build_all(force: bool = False) -> str:
    """为所有知识库构建文档关系图谱。

    遍历全部 KB 构建图谱，跨 KB 共享标签自动形成跨知识库关联。
    返回：{total_top_kbs, kbs: [{kb_id, docs_processed, ...}], ...}"""
    return _j(await _client().graph_build_all(force))


@mcp.tool()
async def kb_graph_cross_kb_documents(min_kbs: int = 2, limit: int = 50) -> str:
    """发现跨知识库的桥梁文档——关联到 >= min_kbs 个不同 KB 的文档。

    这些文档是连接不同知识库的骨干。
    返回：{documents: [{name, path, kb_id, tags, related_kb_count}], ...}"""
    return _j(await _client().graph_cross_kb_documents(min_kbs, limit))


@mcp.tool()
async def kb_graph_document_paths(doc_a: str, doc_b: str, max_depth: int = 4) -> str:
    """查找两个文档之间的最短关系路径（经 RELATED_TO 关系链）。

    展示文档如何通过共享标签/同KB等关联链相连。
    返回：{paths: [{doc_path, reasons, hops}], path_count}"""
    return _j(await _client().graph_document_paths(doc_a, doc_b, max_depth))


@mcp.tool()
async def kb_graph_central_documents(kb_id: str, top_n: int = 20) -> str:
    """找出 KB 内关联度最高的文档（按 RELATED_TO 度中心性）。

    这些是 KB 的核心文档，用于理解知识库的主要话题结构。
    返回：{documents: [{name, path, degree, total_weight}], ...}"""
    return _j(await _client().graph_central_documents(kb_id, top_n))


@mcp.tool()
async def kb_graph_delete_document(doc_path: str) -> str:
    """删除单文档的图谱数据（共享实体保留，仅移除该文档的贡献）。"""
    return _j(await _client().graph_delete_document(doc_path))


@mcp.tool()
async def kb_graph_delete_kb(kb_id: str) -> str:
    """删除整个 KB 的图谱数据（跨 KB 共享实体保留）。"""
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
    """Perform startup health check; auto-launch backend/frontend if needed.

    This runs synchronously before the MCP server starts accepting
    connections.  If the backend or frontend is unreachable, we spawn
    them as detached child processes and wait up to 30 s for them to
    become ready.
    """
    import subprocess
    import httpx
    from pathlib import Path

    # ---- load .env from project root if present ----
    # MUST happen *before* 'import config' so that BACKEND_PORT etc.
    # from .env are visible to config.py's module-level URL builders.
    _load_dotenv()

    import config

    # ---- resolve directories ----
    # Within the monorepo, backend/ and web/ are git submodules.
    # This script lives at kb-mcp/server.py, so:
    #   kb-mcp/../..    = rag-knowledge/      (project root)
    #   .../backend/    = FastAPI submodule
    #   .../web/        = Nuxt 3 submodule (the active frontend)
    kb_mcp_dir = Path(__file__).resolve().parent          # kb-mcp/
    project_root = kb_mcp_dir.parent                      # rag-knowledge/
    backend_dir = project_root / "backend"
    frontend_dir = project_root / "web"

    backend_url = config.BACKEND_URL
    web_url = config.WEB_URL
    app_mode = os.environ.get("APP_MODE", "prod")

    print(f"[kb-mcp] === Startup health check (mode={app_mode}) ===", file=sys.stderr)
    print(f"[kb-mcp]   Backend URL : {backend_url}", file=sys.stderr)
    print(f"[kb-mcp]   Frontend URL: {web_url}", file=sys.stderr)

    needs_backend = False
    needs_frontend = False

    async def _probe():
        nonlocal needs_backend, needs_frontend
        async with httpx.AsyncClient(timeout=5) as client:
            try:
                r = await client.get(f"{backend_url}/api/v1/health")
                if r.status_code == 200:
                    print("[kb-mcp]   Backend : OK", file=sys.stderr)
                else:
                    needs_backend = True
                    print(f"[kb-mcp]   Backend : returned status {r.status_code}", file=sys.stderr)
            except Exception as e:
                needs_backend = True
                print(f"[kb-mcp]   Backend : unreachable ({e})", file=sys.stderr)

            try:
                r = await client.get(f"{web_url}/api/kb/catalog")
                if r.status_code == 200:
                    print("[kb-mcp]   Frontend: OK", file=sys.stderr)
                else:
                    needs_frontend = True
                    print(f"[kb-mcp]   Frontend: returned status {r.status_code}", file=sys.stderr)
            except Exception as e:
                needs_frontend = True
                print(f"[kb-mcp]   Frontend: unreachable ({e})", file=sys.stderr)

    asyncio.run(_probe())

    if not needs_backend and not needs_frontend:
        print("[kb-mcp] Both services healthy, no auto-launch needed.", file=sys.stderr)
        return

    if needs_backend:
        if not backend_dir.exists():
            print(f"[kb-mcp] ERROR: Backend directory not found: {backend_dir}", file=sys.stderr)
        else:
            backend_port = _port_from_url(backend_url, "8001")
            flags_info = " (visible console)" if app_mode == "dev" else " (background)"
            print(f"[kb-mcp] Starting backend{flags_info} (uv run python main.py, port={backend_port})...", file=sys.stderr)
            subprocess.Popen(
                ["uv", "run", "python", "main.py"],
                cwd=str(backend_dir),
                env={**os.environ, "APP_MODE": app_mode},
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                **_subprocess_flags(app_mode),
            )

    if needs_frontend:
        if not frontend_dir.exists():
            print(f"[kb-mcp] ERROR: Frontend directory not found: {frontend_dir}", file=sys.stderr)
        else:
            npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
            flags_info = " (visible console)" if app_mode == "dev" else " (background)"
            print(f"[kb-mcp] Starting frontend{flags_info} ({npm_cmd} run start)...", file=sys.stderr)
            subprocess.Popen(
                [npm_cmd, "run", "start"],
                cwd=str(frontend_dir),
                env={**os.environ, "APP_MODE": app_mode},
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                **_subprocess_flags(app_mode),
            )

    print("[kb-mcp] Waiting for services to become ready (timeout: 30s)...", file=sys.stderr)
    _wait_for_services(needs_backend, needs_frontend, backend_url, web_url)


def _wait_for_services(needs_backend, needs_frontend, backend_url, web_url, max_wait=30):
    """Poll backend/frontend health endpoints until ready or timeout."""
    import time
    import httpx

    async def _poll():
        elapsed = 0
        backend_ok = not needs_backend
        frontend_ok = not needs_frontend
        async with httpx.AsyncClient(timeout=3) as client:
            while elapsed < max_wait:
                if needs_backend and not backend_ok:
                    try:
                        r = await client.get(f"{backend_url}/api/v1/health")
                        if r.status_code == 200:
                            backend_ok = True
                    except Exception:
                        pass

                if needs_frontend and not frontend_ok:
                    try:
                        r = await client.get(f"{web_url}/api/kb/catalog")
                        if r.status_code == 200:
                            frontend_ok = True
                    except Exception:
                        pass

                if backend_ok and frontend_ok:
                    print(f"[kb-mcp] All services ready ({elapsed}s).", file=sys.stderr)
                    return

                await asyncio.sleep(2)
                elapsed += 2

        if needs_backend and not backend_ok:
            print(f"[kb-mcp] WARNING: Backend not ready after {max_wait}s, continuing anyway.", file=sys.stderr)
        if needs_frontend and not frontend_ok:
            print(f"[kb-mcp] WARNING: Frontend not ready after {max_wait}s, continuing anyway.", file=sys.stderr)

    asyncio.run(_poll())


def _port_from_url(url: str, default: str = "8001") -> str:
    """Extract the port number from a URL string."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if parsed.port:
            return str(parsed.port)
    except Exception:
        pass
    return default


def _subprocess_flags(app_mode: str = "prod"):
    """Platform-appropriate subprocess flags for detached child processes.

    In ``prod`` mode: hide console window (DETACHED_PROCESS | CREATE_NO_WINDOW).
    In ``dev``  mode: show a visible console window so the developer can see
    logs, Ctrl+C to stop, etc. (only CREATE_NEW_CONSOLE on Windows).
    """
    if sys.platform == "win32":
        if app_mode == "dev":
            # CREATE_NEW_CONSOLE (0x10) — child gets its own terminal window
            return {"creationflags": 0x00000010}
        else:
            # DETACHED_PROCESS (0x08) | CREATE_NO_WINDOW (0x08000000)
            return {"creationflags": 0x00000008 | 0x08000000}
    if app_mode == "dev":
        return {}
    return {"start_new_session": True}


def _load_dotenv() -> None:
    """Load `.env` from the monorepo root into ``os.environ`` if present.

    Unconditionally overrides existing values — ``.env`` is the single
    source of truth for project configuration.  Call this *before* any
    code that reads env vars (``import config``, etc.).
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
                os.environ[key] = val

if __name__ == "__main__":
    main()
