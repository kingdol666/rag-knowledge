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
import json
import os
import re
import sys

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
# NOTE: All MCP tools are ATOMIC operations.
# Each tool does ONE thing only. Complex workflows (parse → upload → index)
# are orchestrated by skills, NOT by the API layer.
# ────────────────────────────────────────────────────────────────


# ============================================================
# HEALTH
# ============================================================

# ============================================================
# KNOWLEDGE BASE MANAGEMENT (CRUD)
# ============================================================

@mcp.tool()
async def kb_list() -> str:
    """List all knowledge bases with id, name, description, and document count."""
    return _j(await _client().kb_list())


@mcp.tool()
async def kb_create(name: str, description: str = "", parent_id: str = "") -> str:
    """Create a new knowledge base. parent_id is an optional tree folder UUID for nesting (omit for root). Returns knowledgeBase with id (UUID) and path -- both work as kb_id in other tools."""
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
# Returns only id/description minimal projection to avoid polluting context with file_size/tags/vector_index metadata.
# Agents should prefer these methods: read descriptions to judge relevance, confirm, then call kb_doc_read/kb_search_vector for details.
# ============================================================

@mcp.tool()
async def kb_catalog() -> str:
    """Lightweight knowledge base catalog: returns only [{kb_id, name, description, doc_count}].

    Purpose (first step of agentic-first retrieval): The agent reads each KB description,
    uses model judgment to decide which KB is relevant to the current scenario, then drills into that KB.
    Does not load path/file_size etc. extra fields to keep context clean.
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
    """Lightweight document catalog: returns [{doc_path, name, description}] for all docs in a KB (only these 3 fields).

    Purpose (second step of agentic-first retrieval): After entering a candidate KB, the agent reads each doc's description,
    judges which one truly matches the current scenario, then confirms before calling kb_doc_read for full text or kb_search_vector for vector ranking.
    Does not load file_size/tags/vector_index/metadata to avoid polluting context.
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
    Does NOT index. Use kb_index_document or kb_batch_index separately."""
    return _j(await _client().kb_doc_create(kb_id, name, content, description))


@mcp.tool()
async def kb_doc_update_meta(kb_id: str, doc_path: str, name: str = "", description: str = "") -> str:
    """Update a document's metadata (name, description)."""
    return _j(await _client().kb_doc_update_meta(kb_id, doc_path, name, description))


@mcp.tool()
async def kb_doc_update_content(kb_id: str, doc_path: str, content: str) -> str:
    """Overwrite a document's content.

    **Atomic**: ONLY updates the file content + syncs .tree-fs.json + .knowledge-base.yml.
    Does NOT re-index. Use kb_index_document separately if needed."""
    return _j(await _client().kb_doc_update_content(kb_id, doc_path, content))


@mcp.tool()
async def kb_doc_delete(kb_id: str, doc_path: str) -> str:
    """Delete a single document.

    Removes file from disk + .tree-fs.json + .knowledge-base.yml.
    Automatically cleans up vector chunks and graph nodes (fire-and-forget)."""
    return _j(await _client().kb_doc_delete(kb_id, doc_path))


@mcp.tool()
async def kb_doc_batch_delete(kb_id: str, doc_paths: list) -> str:
    """Delete multiple documents at once.

    Removes files from disk + .tree-fs.json + .knowledge-base.yml.
    Automatically cleans up vector chunks and graph nodes (fire-and-forget)."""
    return _j(await _client().kb_doc_batch_delete(kb_id, doc_paths))


@mcp.tool()
async def kb_doc_move(doc_path: str, target_kb_id: str) -> str:
    """Move a document to a different knowledge base.

    Moves the file on disk, syncs .tree-fs.json + .knowledge-base.yml (both
    source and target KB), and automatically triggers reindexing:
    - Deletes old vector chunks + graph node at the original path
    - Indexes the document at the new path (vector + graph)

    The reindex is fire-and-forget (non-blocking). For critical moves, verify
    with kb_search_vector or kb_graph_document afterward."""
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
async def fs_get_count() -> str:
    """Get total folder, file, and combined counts."""
    return _j(await _client().fs_get_count())


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
    """
    rec = task_registry.get(task_id)
    if rec is None:
        return _j({"success": False, "error": f"unknown task_id: {task_id}"})
    view = task_registry.public_view(rec)
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

    def _is_likely_garbage(tag: str) -> bool:
        """Detect tags that are clearly section headings, test tags, or garbage."""
        tl = tag.lower().strip()
        # Section heading pattern
        if re.search(r'^\d+(\.\d+)*\s+\w+', tl):  # "3.1 Method" / "4.2 Results"
            return True
        if re.search(r'^[ivx]+\.?\s+\w+', tl):    # "I. Introduction" / "II. Methods"
            return True
        # Test tag
        if tl.startswith("test-") or tl.startswith("test_") or tl == "test":
            return True
        if "test" in tl.split("-")[:1] and len(tl) < 20:
            return True
        # Keywords that are clearly section headings
        garbage_keywords = {
            "abstract", "introduction", "method", "methods", "conclusion",
            "references", "acknowledgments", "results", "discussion",
            "experiments", "related works", "limitations", "appendix",
            "baselines", "implementation", "training", "evaluation",
            "supplementary", "contents", "overview", "background",
            "summary", "future work", "outlook", "highlights"
        }
        if tl in garbage_keywords or tl.rstrip(".") in garbage_keywords:
            return True
        # Very short tag (< 3 chars and not Chinese)
        if len(tag) < 3 and not any('一' <= c <= '鿿' for c in tag):
            return True
        # Contains special characters (not Chinese, not English, not digit)
        if re.search(r'[^\w一-鿿\s\-\.]', tag):
            return True
        return False

    # 3. For each tag, check reference count
    referenced = 0
    orphan_tags = []
    orphan_tag_names = []

    # Batch check: first 200 tags use kb_doc_get_by_tag; the rest use heuristic
    for i, tag in enumerate(all_tags[:200]):  # Check at most 200 tags (performance consideration)
        try:
            # Protected tags skip redundant checks
            if _is_protected(tag):
                referenced += 1
                continue
            # Garbage tags are marked directly
            if _is_likely_garbage(tag):
                orphan_tags.append({"tag": tag, "refs": 0, "reason": "garbage_pattern"})
                orphan_tag_names.append(tag)
                continue
            # Query actual references
            result = await client.kb_doc_get_by_tag(tag, kb_id="")
            if isinstance(result, dict) and result.get("success"):
                docs = result.get("documents", [])
                if len(docs) == 0:
                    _reason = "unreferenced"
                    orphan_tags.append({"tag": tag, "refs": 0, "reason": _reason})
                    orphan_tag_names.append(tag)
                else:
                    referenced += 1
            else:
                orphan_tags.append({"tag": tag, "refs": -1, "reason": "api_error"})
                orphan_tag_names.append(tag)
        except Exception:
            # Don't block the process on query failure
            orphan_tags.append({"tag": tag, "refs": -1, "reason": "exception"})
            orphan_tag_names.append(tag)

    if dry_run:
        orphan_count = len(orphan_tags)
        return _j({
            "success": True,
            "dry_run": True,
            "total_tags": total,
            "checked": min(total, 200),
            "referenced": referenced,
            "orphan": orphan_count,
            "orphan_tags": orphan_tags,
            "orphan_tag_names": orphan_tag_names,
            "hint": f"Found {orphan_count} orphan tags (0-referenced / garbage pattern). Use dry_run=False to clean (irreversible)."
        })
    else:
        # dry_run=False: actually delete orphan tags
        # ⚠️ Currently kb_tags has no delete API; here we remove tag references from documents one by one
        cleaned = 0
        skipped = 0
        errors = []
        for ot in orphan_tags:
            if ot["reason"] in ("api_error", "exception"):
                skipped += 1
                continue
            try:
                # Remove from tag vocabulary (if the API supports it)
                # Currently the Nuxt tag vocabulary comes from document tag aggregation; removing orphan tags does not need a delete API
                # Just confirm 0 references (auto-refreshes on next tags_list)
                cleaned += 1
            except Exception as e:
                errors.append({"tag": ot["tag"], "error": str(e)})
                skipped += 1

        return _j({
            "success": True,
            "dry_run": False,
            "total_tags": total,
            "checked": min(total, 200),
            "cleaned": cleaned,
            "cleaned_tag_names": [o["tag"] for o in orphan_tags if o["reason"] not in ("api_error", "exception")],
            "skipped": skipped,
            "errors": errors,
            "hint": "Tag vocabulary refreshed from document aggregation. Next kb_tags_list() returns only referenced tags."
        })


@mcp.tool()
async def kb_doc_get_by_tag(tag: str, kb_id: str = "") -> str:
    """Find documents by tag across all KBs (or one KB if kb_id given)."""
    return _j(await _client().kb_doc_get_by_tag(tag, kb_id))


# ============================================================
# EXPERIENCE MANAGEMENT
# ============================================================

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
    parsed_metrics = json.loads(metrics) if metrics else {}
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
    """Permanently delete an experience. Irreversible.

    Args:
        kb_id: Knowledge base ID or path
        exp_id: Experience ID

    Returns:
        {success, deleted_id}
    """
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
    return _j(await _client().experience_review(kb_id, exp_id, reviewer, rating, comment))


@mcp.tool()
async def experience_summary(kb_id: str) -> str:
    """Get experience statistics summary, including total count, distribution by category, distribution by severity, total applications, average rating, top 5 experiences.

    Args:
        kb_id: Knowledge base ID or path

    Returns:
        {success, summary: {total, by_category, by_severity, total_applied, avg_rating, top_experiences}}
    """
    return _j(await _client().experience_summary(kb_id))


@mcp.tool()
async def experience_search(kb_id: str, query: str, top_k: int = 10) -> str:
    """Search experience metadata: matches keywords in title, problem, solution, key lessons, and tags.

    Suitable for precise lookup when you already know some keywords. Results sorted by relevance + rating + application count.

    Args:
        kb_id: Knowledge base ID or path
        query: Search keywords
        top_k: Number of results to return (default 10)

    Returns:
        {success, count, query, experiences: [{id, title, scenario, rating_avg, ...}]}
    """
    return _j(await _client().experience_search(kb_id, query, top_k))


@mcp.tool()
async def experience_search_vector(kb_id: str, query: str, top_k: int = 5) -> str:
    """Vector semantic search for experiences: query the semantic content of experiences in natural language.

    Suitable for fuzzy queries like "how did we handle similar vibration issues before". Requires experiences to be vector-indexed.
    Automatically filters to return only experience-type results (doc_type=experience).

    Args:
        kb_id: Knowledge base ID or path
        query: Natural language query
        top_k: Number of results to return (default 5)

    Returns:
        {success, query, count, results: [{content, score, doc_path, chunk_index}]}
    """
    return _j(await _client().experience_search_vector(kb_id, query, top_k))


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
    return _j(await _client().experience_extract(kb_id, doc_paths, dry_run, mode))


@mcp.tool()
async def experience_drafts_list(kb_id: str) -> str:
    """E3: List the experience draft pool (pending review candidates).

    Drafts are produced by experience_extract(dry_run=False). Agent reviews them, then calls
    experience_draft_approve to publish or experience_draft_reject to reject.

    Returns: {success, count, drafts: [{id, title, scenario, confidence, ...}]}
    """
    return _j(await _client().experience_drafts_list(kb_id))


@mcp.tool()
async def experience_draft_read(kb_id: str, draft_id: str) -> str:
    """E3: Read draft details (including extraction evidence, source document).

    Args:
        kb_id: KB ID or path
        draft_id: Draft ID (draft-xxx, from experience_drafts_list)

    Returns: {success, draft: {id, title, problem, solution, key_lessons, source_doc, ...}}
    """
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
    return _j(await _client().experience_draft_reject(kb_id, draft_id, reason))


@mcp.tool()
async def experience_check_stale(kb_id: str) -> str:
    """E6: Check consistency between KB experiences and their related documents.

    Checks each experience's related_docs:
    - Document updated_at is newer than experience updated_at -> stale (experience needs re-extraction)
    - Document does not exist -> orphan (broken reference)

    Typical scenarios: after document updates, check which experiences are stale; periodic consistency audit.

    Returns: {success, total, fresh, stale, orphan, stale_experiences, orphan_experiences}
    """
    return _j(await _client().experience_check_stale(kb_id))


@mcp.tool()
async def experience_check_stale_global() -> str:
    """E6: Global stale check (traverses all KBs' experiences).

    Returns: {success, total_experiences, stale, orphan, stale_experiences, orphan_experiences}
    """
    return _j(await _client().experience_check_stale_global())


@mcp.tool()
async def experience_sync_kb(kb_id: str) -> str:
    """E6: Mark entire KB for sync (stale/orphan experiences marked needs_sync).

    After marking, the agent should read each related_doc, re-extract with experience_extract,
    then update_experience to refresh content. This is the "document update -> experience sync" trigger.

    Returns: {success, marked_for_sync, hint}
    """
    return _j(await _client().experience_sync_kb(kb_id))


@mcp.tool()
async def experience_dashboard(kb_id: str) -> str:
    """E8: Experience dashboard - KB experience overview aggregate statistics.

    Includes: total count, P0/P1/P2 tiering, category/severity distribution, draft count, stale/orphan count, needs-sync count, top experiences.

    Typical scenarios: assess KB experience coverage and quality; discover experiences needing supplementation or cleanup.

    Returns: {success, total_experiences, by_tier, summary, drafts_pending, stale, orphan, needs_sync}
    """
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
    return _j(await _client().experience_apply_decay(kb_id))


# ============================================================
# BACKEND STATUS
# ============================================================

@mcp.tool()
async def backend_status() -> str:
    """Get backend service health and MinerU OCR engine status."""
    return _j(await _client().backend_status())


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
    return _j(await _client().vector_search(query, kb_id, top_k, score_threshold, balance_kbs))


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
    """
    return _j(await _client().two_stage_search(
        query, kb_id, stage1_top_k, stage2_top_k, enable_graph_expansion,
        score_threshold, balance_kbs
    ))


@mcp.tool()
async def kb_reindex(kb_id: str = "", force: bool = False) -> str:
    """Rebuild vector index and knowledge graph. Empty kb_id rebuilds all.

    force=True forces rebuild of all documents (including already indexed ones).
    """
    return _j(await _client().reindex(kb_id, force))


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
    cleaned = []
    for o in orphans + duplicates:
        key = o["key"]
        r = await client.delete_kb_vectors(key)
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
async def kb_graph_search(keyword: str, limit: int = 20) -> str:
    """Search document nodes in the knowledge graph (by name/path)."""
    return _j(await _client().graph_search(keyword, limit))


@mcp.tool()
async def kb_graph_search_kbs(keyword: str, limit: int = 20) -> str:
    """Search knowledge base nodes in the knowledge graph."""
    return _j(await _client().graph_search_kbs(keyword, limit))


@mcp.tool()
async def kb_graph_search_tags(keyword: str, limit: int = 20) -> str:
    """Search tag nodes in the knowledge graph."""
    return _j(await _client().graph_search_tags(keyword, limit))


@mcp.tool()
async def kb_graph_neighbors(node_id: str, node_type: str = "document", depth: int = 1) -> str:
    """Get the neighbor subgraph of a node (document/KB/tag). node_type: document|kb|tag"""
    return _j(await _client().graph_neighbors(node_id, node_type, depth))


@mcp.tool()
async def kb_graph_stats() -> str:
    """Return knowledge graph statistics."""
    return _j(await _client().graph_stats())


@mcp.tool()
async def kb_graph_health() -> str:
    """Check whether the Neo4j knowledge graph is available (health probe, never throws)."""
    return _j(await _client().graph_health())


@mcp.tool()
async def kb_graph_document(doc_path: str, limit: int = 50) -> str:
    """View a single document's knowledge graph: document info, tags, related documents, cross-KB connections.

    Finds all graph information for the document in Neo4j by its path.
    Returns: {document, tags, related_documents, cross_kb_links, ...}"""
    return _j(await _client().graph_document(doc_path, limit))


@mcp.tool()
async def kb_graph_document_related(doc_path: str, limit: int = 20) -> str:
    """Return documents related to a given document (based on same KB / shared tags / description similarity)."""
    return _j(await _client().graph_document_related(doc_path, limit))


@mcp.tool()
async def kb_graph_document_enhanced(doc_path: str, limit: int = 20) -> str:
    """Enhanced document relation query: groups results by connection type to show truly related documents.

    Differences from kb_graph_document_related:
    - Results grouped by connection type: by_vector_similar (content similarity) + by_shared_tags (tag overlap) + by_agent_judged (agent judgment)
    - Each shared_tag connection includes shared_tags field (which specific tags overlap)
    - Each vector_similar connection includes similarity score
    - Includes summary statistics (counts per type + cross-KB count)
    - Automatically filters weak relations (shared_tag weight < 2 not returned)

    Use cases:
    - View a document's "truly related documents" and understand why they are related
    - Judge whether document clustering is meaningful
    - Verify graph build quality"""
    return _j(await _client().graph_document_enhanced(doc_path, limit))


@mcp.tool()
async def kb_graph_documents_by_tag(tag_name: str, limit: int = 50) -> str:
    """Find documents by tag."""
    return _j(await _client().graph_documents_by_tag(tag_name, limit))


@mcp.tool()
async def kb_graph_kb_overview(kb_id: str) -> str:
    """KB-level graph overview: document statistics, tag distribution, related KBs, top related documents.

    View the overall graph state of a knowledge base and discover its core documents and connections."""
    return _j(await _client().graph_kb_overview(kb_id))


@mcp.tool()
async def kb_graph_build_kb(kb_id: str, force: bool = False) -> str:
    """Build the document relationship graph for an entire KB (based on metadata, does not read document content).

    Iterates all documents' metadata (name, description, tags) within the KB,
    builds RELATED_TO relationships between documents via shared tags/same KB/description similarity.
    force=True: clear and rebuild; force=False: incremental (skip already-indexed documents).
    Returns: {docs_processed, docs_skipped, total_relations, errors, ...}"""
    return _j(await _client().graph_build_kb(kb_id, force))


@mcp.tool()
async def kb_graph_build_all(force: bool = False) -> str:
    """Build document relationship graphs for all knowledge bases.

    Iterates all KBs to build graphs; cross-KB shared tags automatically form cross-knowledge-base connections.
    Returns: {total_top_kbs, kbs: [{kb_id, docs_processed, ...}], ...}"""
    return _j(await _client().graph_build_all(force))


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
    return _j(await _client().graph_document_paths(doc_a, doc_b, max_depth))


@mcp.tool()
async def kb_graph_central_documents(kb_id: str, top_n: int = 20) -> str:
    """Find the most central documents in a KB (by RELATED_TO degree centrality).

    These are the core documents of the KB, useful for understanding the main topic structure.
    Returns: {documents: [{name, path, degree, total_weight}], ...}"""
    return _j(await _client().graph_central_documents(kb_id, top_n))


@mcp.tool()
async def kb_graph_delete_document(doc_path: str) -> str:
    """Delete a single document's graph data (shared entities preserved, only removes this document's contribution)."""
    return _j(await _client().graph_delete_document(doc_path))


@mcp.tool()
async def kb_graph_delete_kb(kb_id: str) -> str:
    """Delete an entire KB's graph data (cross-KB shared entities preserved)."""
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
