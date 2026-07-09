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
# NOTE: All MCP tools are ATOMIC operations.
# Each tool does ONE thing only. Complex workflows (parse → upload → index)
# are orchestrated by skills, NOT by the API layer.
# ────────────────────────────────────────────────────────────────


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
    """Delete a single document."""
    return _j(await _client().kb_doc_delete(kb_id, doc_path))


@mcp.tool()
async def kb_doc_batch_delete(kb_id: str, doc_paths: list) -> str:
    """Delete multiple documents at once."""
    return _j(await _client().kb_doc_batch_delete(kb_id, doc_paths))


@mcp.tool()
async def kb_doc_move(doc_path: str, target_kb_id: str) -> str:
    """Move a document to a different knowledge base.

    **Atomic**: ONLY moves the file + syncs .tree-fs.json + .knowledge-base.yml
    (both source and target). Does NOT re-index or clean up old vectors/graph.
    Use kb_index_document on the new path, and DELETE /api/v1/search/document
    + DELETE /api/v1/graph/document on the old path separately if needed."""
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
    """Upload a local file into the file system tree. file_path is an absolute local disk path. parent_id is a tree folder UUID (empty = root).

    **Atomic**: ONLY uploads the file + writes .tree-fs.json + .knowledge-base.yml (with file ID).
    Does NOT index. Use kb_index_document separately if needed."""
    return _j(await _client().fs_upload_file(file_path, parent_id, description))


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
                            score_threshold: float = 0.0,
                            balance_kbs: bool = False) -> str:
    """向量语义搜索文档片段。

    Args:
        query: 查询文本
        kb_id: 限定知识库；空则跨库
        top_k: 返回结果数
        score_threshold: 最低余弦相似度阈值（0~1）；<=0 用后端默认(0.35)。降低可召回更多片段
        balance_kbs: 跨库搜索时是否均衡结果（默认 False）。设为 True 可防大KB主导结果

    Returns:
        {success, results: [{content, score, doc_path, chunk_index, kb_id}]}
    """
    return _j(await _client().vector_search(query, kb_id, top_k, score_threshold, balance_kbs))


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
    balance_kbs: bool = False,
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
        balance_kbs: 跨库搜索时是否均衡结果（默认 False）。设为 True 可防大KB主导结果

    Returns:
        {success, stage1: {candidates}, stage2: {results}, total_results}
    """
    return _j(await _client().two_stage_search(
        query, kb_id, stage1_top_k, stage2_top_k, enable_graph_expansion,
        score_threshold, balance_kbs
    ))


@mcp.tool()
async def kb_reindex(kb_id: str = "", force: bool = False) -> str:
    """重建向量索引和知识图谱。kb_id 为空则重建全部。

    force=True 时强制重建所有文档（包括已索引的）。
    """
    return _j(await _client().reindex(kb_id, force))


@mcp.tool()
async def kb_index_document(kb_id: str = "", doc_path: str = "", doc_id: str = "", doc_name: str = "", description: str = "", content: str = "") -> str:
    """单文档向量+图谱索引。将文档内容（或已有文档）存入向量数据库并记录 vector_index 到元信息。

    支持两种调用方式：
    1. 提供 doc_id（文档 UUID）→ 自动解析 kb_id 和 doc_path
    2. 提供 kb_id + doc_path → 直接使用

    用于手动触发文档的向量索引构建。如果提供 content 则直接使用，否则从存储自动读取。
    索引完成后会在 .knowledge-base.yml 的对应文档记录 vector_index 信息（含 collection、chunks 等）。
    同时会重建 BM25 关键词索引使后续两阶段检索能定位到该文档。

    **Atomic**: ONLY indexes (vector + graph + YAML metadata writeback).
    Does NOT create or modify the document file itself.

    Args:
        kb_id: 知识库 ID 或路径（doc_id 模式下可省略）
        doc_path: 文档在 KB 中的相对路径（doc_id 模式下可省略）
        doc_id: 文档 UUID（来自 .knowledge-base.yml），提供时自动解析上述两项
        doc_name: 文档名称
        description: 文档描述
        content: 文档正文内容；为空则从文件自动读取

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
