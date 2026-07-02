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


# ============================================================
# 向量检索与两阶段精准检索（新增）
# ============================================================

@mcp.tool()
async def kb_search_vector(query: str, kb_id: str = "", top_k: int = 5) -> str:
    """向量语义搜索文档片段。

    Args:
        query: 查询文本
        kb_id: 限定知识库；空则跨库
        top_k: 返回结果数

    Returns:
        {success, results: [{content, score, doc_path, chunk_index, kb_id}]}
    """
    return _j(await _client().vector_search(query, kb_id, top_k))


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
) -> str:
    """两阶段精准检索：先广搜索定位候选文档，再向量精筛片段。

    推荐 Agent 首选此工具，比纯向量检索更精准，避免幻觉。

    Args:
        query: 用户问题
        kb_id: 限定知识库；空则跨库
        stage1_top_k: Stage 1 候选文档数
        stage2_top_k: Stage 2 每文档返回片段数
        enable_graph_expansion: 是否启用图谱邻居扩展

    Returns:
        {success, stage1: {candidates}, stage2: {results}, total_results}
    """
    return _j(await _client().two_stage_search(
        query, kb_id, stage1_top_k, stage2_top_k, enable_graph_expansion
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
    """搜索知识图谱中的实体。"""
    return _j(await _client().graph_search(keyword, limit))


@mcp.tool()
async def kb_graph_neighbors(entity_name: str, depth: int = 1) -> str:
    """获取实体的邻居子图，用于探索实体间关系。"""
    return _j(await _client().graph_neighbors(entity_name, depth))


@mcp.tool()
async def kb_graph_stats() -> str:
    """返回知识图谱统计信息。"""
    return _j(await _client().graph_stats())


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
