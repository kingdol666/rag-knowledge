# -*- coding: utf-8 -*-
"""KbClient - async HTTP client for the RAG Knowledge Platform API.

Every method maps 1:1 to a web API endpoint. Returns plain dicts.
This module has ZERO MCP dependencies - it is a pure HTTP client
that can be reused by the MCP server, test scripts, or any tool.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, List

import httpx

DEFAULT_WEB_URL = ""  # set by caller via config.WEB_URL
DEFAULT_BACKEND_URL = ""  # set by caller via config.BACKEND_URL
HTTP_TIMEOUT = int(os.environ.get("MCP_HTTP_TIMEOUT", "30"))
PARSE_TIMEOUT = int(os.environ.get("MCP_PARSE_TIMEOUT", "5000"))
INDEX_TIMEOUT = int(os.environ.get("MCP_INDEX_TIMEOUT", "600"))  # 大文档 CPU embedding 耗时长，索引类调用单独放宽到 600s
# Shared auth token — when set, attached as `Authorization: Bearer <token>` to all requests.
AUTH_TOKEN = os.environ.get("KB_AUTH_TOKEN", "")


class KbClient:
    """Thin async wrapper around the knowledge-base REST API.

    Holds a persistent httpx.AsyncClient for connection pooling.
    Call aclose() when done, or use as an async context manager.
    """

    def __init__(self, web_url=DEFAULT_WEB_URL, backend_url=DEFAULT_BACKEND_URL, timeout=HTTP_TIMEOUT):
        self.web_url = web_url.rstrip("/")
        self.backend_url = backend_url.rstrip("/")
        self.timeout = timeout
        self._client = None

    # ---- lifecycle ----

    async def _ensure_client(self):
        if self._client is None or self._client.is_closed:
            headers = {}
            if AUTH_TOKEN:
                headers["Authorization"] = f"Bearer {AUTH_TOKEN}"
            self._client = httpx.AsyncClient(
                timeout=self.timeout, trust_env=False, headers=headers
            )
        return self._client

    async def aclose(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self.aclose()

    # ---- low-level HTTP ----

    async def _request(self, method, endpoint, base=None, **kwargs):
        """Send an HTTP request and return parsed JSON (or error dict)."""
        client = await self._ensure_client()
        url = f"{base or self.web_url}{endpoint}"
        try:
            resp = await client.request(method, url, **kwargs)
            if resp.status_code >= 400:
                return {"success": False, "error": resp.text[:500], "status": resp.status_code}
            ct = resp.headers.get("content-type", "")
            if "json" in ct:
                return resp.json()
            return {"success": True, "content_type": ct, "content_length": len(resp.content)}
        except Exception as e:
            return {"success": False, "error": f"{type(e).__name__}: {e}"}

    async def _get(self, endpoint, **params):
        return await self._request("GET", endpoint, params=params)

    async def _post_json(self, endpoint, body):
        return await self._request("POST", endpoint, json=body)

    async def _put_json(self, endpoint, body):
        return await self._request("PUT", endpoint, json=body)

    async def _patch_json(self, endpoint, body):
        return await self._request("PATCH", endpoint, json=body)

    async def _delete_json(self, endpoint, body):
        return await self._request("DELETE", endpoint, json=body)

    async def _post_file(self, endpoint, file_path, data=None, timeout=None):
        """Upload a file via multipart form-data."""
        fp = Path(file_path)
        if not fp.exists():
            return {"success": False, "error": f"file not found: {file_path}"}
        client = await self._ensure_client()
        try:
            with open(fp, "rb") as f:
                resp = await client.post(
                    f"{self.web_url}{endpoint}",
                    files={"file": (fp.name, f)},
                    data=data or {},
                    timeout=timeout or PARSE_TIMEOUT,
                )
            if resp.status_code >= 400:
                return {"success": False, "error": resp.text[:500], "status": resp.status_code}
            return resp.json()
        except Exception as e:
            return {"success": False, "error": f"{type(e).__name__}: {e}"}

    # ================================================================
    # HEALTH
    # ================================================================

    async def health_check(self):
        """Check health of backend, MinerU, and web services."""
        async with httpx.AsyncClient(timeout=5, trust_env=False) as c:
            status = {"backend": False, "mineru": False, "web": False, "errors": []}
            for name, url in [
                ("backend", f"{self.backend_url}/api/v1/health"),
                ("web", f"{self.web_url}/api/kb/catalog"),
            ]:
                try:
                    r = await c.get(url)
                    status[name] = r.status_code == 200
                except Exception as e:
                    status["errors"].append(f"{name}: {e}")
            # MinerU status — call the backend's /api/v1/mineru/status endpoint
            try:
                r = await c.get(f"{self.backend_url}/api/v1/mineru/status")
                if r.status_code == 200:
                    data = r.json()
                    status["mineru"] = bool(data.get("running", False))
                else:
                    status["errors"].append(f"mineru: HTTP {r.status_code}")
            except Exception as e:
                status["errors"].append(f"mineru: {e}")
            status["all_ok"] = status["backend"] and status["web"]
            return status

    # ================================================================
    # KNOWLEDGE BASE MANAGEMENT (CRUD)
    # ================================================================

    async def kb_list(self):
        """List all knowledge bases."""
        return await self._get("/api/kb/catalog")

    async def kb_create(self, name, description="", parent_id=""):
        """Create a new knowledge base."""
        body = {"name": name, "description": description}
        if parent_id:
            body["parentId"] = parent_id
        return await self._post_json("/api/kb/create", body)

    async def kb_update(self, kb_id, name="", description=""):
        """Update a knowledge base's name and/or description."""
        body = {"kbId": kb_id}
        if name:
            body["name"] = name
        if description:
            body["description"] = description
        return await self._put_json("/api/kb/update", body)

    async def kb_delete(self, kb_id):
        """Delete an entire knowledge base and all its contents."""
        return await self._delete_json("/api/kb/delete", {"kbId": kb_id})

    async def kb_search(self, query, top_k=10):
        """Search across all knowledge bases by keyword."""
        return await self._get("/api/kb/search", query=query, top_k=top_k)

    async def kb_get_documents(self, kb_id):
        """List all documents inside a knowledge base."""
        return await self._get("/api/kb/documents", kb_id=kb_id)

    # ================================================================
    # DOCUMENT MANAGEMENT (CRUD)
    # ================================================================

    async def kb_doc_read(self, kb_id="", doc_path="", path="", max_chars=20000, offset=0, limit=200, doc_id=""):
        """Read the content of a document (paginated).

        Accepts doc_id, kb_id+doc_path, or path alone. When doc_id is provided,
        it is resolved to a path via the web API. When kb_id and doc_path
        are provided, doc_path is resolved relative to the KB."""
        params = {"max_chars": max_chars, "offset": offset, "limit": limit}
        if doc_id:
            params["doc_id"] = doc_id
        elif path:
            params["path"] = path
        else:
            params["kb_id"] = kb_id
            params["doc_path"] = doc_path
        return await self._get("/api/kb/document", **params)


    async def kb_doc_create(self, kb_id, name, content, description=""):
        """Create a new Markdown document. Auto-dedup on name collision."""
        body = {"kbId": kb_id, "name": name, "content": content, "description": description}
        return await self._post_json("/api/kb/documents/create", body)

    async def kb_doc_update_meta(self, kb_id, doc_path, name="", description=""):
        """Update a document's metadata (name, description)."""
        body = {"kbId": kb_id, "docPath": doc_path}
        if name:
            body["name"] = name
        if description:
            body["description"] = description
        return await self._patch_json("/api/kb/documents/update", body)

    async def kb_doc_update_content(self, kb_id, doc_path, content):
        """Overwrite a document's content."""
        body = {"kbId": kb_id, "docPath": doc_path, "content": content}
        return await self._put_json("/api/kb/documents/content", body)

    async def kb_doc_delete(self, kb_id, doc_path):
        """Delete a single document."""
        return await self._delete_json("/api/kb/documents/delete", {"kbId": kb_id, "docPath": doc_path})

    async def kb_doc_batch_delete(self, kb_id, doc_paths):
        """Delete multiple documents at once."""
        return await self._post_json("/api/kb/documents/batch-delete", {"kbId": kb_id, "docPaths": doc_paths})

    async def kb_doc_move(self, doc_path, target_kb_id):
        """Move a document to a different knowledge base."""
        return await self._post_json("/api/kb/documents/move", {"docPath": doc_path, "targetKbId": target_kb_id})

    # ================================================================
    # FILE SYSTEM OPERATIONS
    # ================================================================

    async def fs_get_tree(self):
        """Get the full file system tree."""
        return await self._get("/api/filesystem")

    async def fs_get_children(self, parent_id=""):
        """Get immediate children of a folder."""
        return await self._get("/api/filesystem", action="children", parentId=parent_id)

    async def fs_get_node(self, node_id):
        """Get a single node by its id."""
        return await self._get("/api/filesystem", action="node", id=node_id)

    async def fs_get_count(self):
        """Get total folder, file, and combined counts."""
        return await self._get("/api/filesystem", action="count")

    async def fs_create_folder(self, name, parent_id="", description="", is_knowledge_base=False):
        """Create a new folder (optionally as a knowledge base)."""
        body = {"type": "folder", "name": name, "description": description, "isKnowledgeBase": is_knowledge_base}
        if parent_id:
            body["parentId"] = parent_id
        return await self._post_json("/api/filesystem/nodes", body)

    async def fs_create_file(self, name, parent_id="", description=""):
        """Create a new file node (metadata only)."""
        body = {"type": "file", "name": name, "description": description}
        if parent_id:
            body["parentId"] = parent_id
        return await self._post_json("/api/filesystem/nodes", body)

    async def fs_update_node(self, node_id, name="", description=""):
        """Update a node's name and/or description."""
        body = {}
        if name:
            body["name"] = name
        if description:
            body["description"] = description
        return await self._patch_json(f"/api/filesystem/nodes/{node_id}", body)

    async def fs_delete_node(self, node_id):
        """Delete a node (recursively for folders)."""
        return await self._request("DELETE", f"/api/filesystem/nodes/{node_id}")

    async def fs_upload_file(self, file_path, parent_id="", description=""):
        """Upload a local file into the file system tree."""
        data = {"description": description}
        if parent_id:
            data["parentId"] = parent_id
        return await self._post_file("/api/filesystem/upload", file_path, data)

    async def save_parsed_files(self, parent_id, results):
        """Save parsed markdown files (with images) into the file system tree.

        Calls the Nuxt /api/parse/save-parsed-files endpoint which:
        - Writes the FULL markdown content to disk (not truncated)
        - Copies all parsed images to the KB's images/ folder
        - Writes .tree-fs.json + .knowledge-base.yml with file UUID + image metadata
        - Does NOT index (call kb_index_document separately)

        Args:
            parent_id: Target KB/folder UUID
            results: List of parse result dicts, each with:
                - markdown: full parsed markdown content (string)
                - markdown_path: path to .md file on disk (fallback if markdown is empty)
                - images_dir: path to parsed images directory
                - source_filename: original filename (e.g. "paper.pdf")
                - filename: alternative filename
                - description: document description (optional)
                - success: must be True
                - parse_method: parse method used (optional)

        Returns:
            {success, savedCount, files: [{id, name, path, ...}]}
        """
        body = {
            "parentId": parent_id,
            "results": results,
        }
        return await self._post_json("/api/parse/save-parsed-files", body)

    # ================================================================
    # PREVIEW
    # ================================================================

    async def preview_file(self, node_id="", path=""):
        """Preview or download a file by node id or relative path."""
        if node_id:
            return await self._get("/api/preview/file", id=node_id)
        if path:
            return await self._get("/api/preview/file", path=path)
        return {"success": False, "error": "Either node_id or path is required"}

    # ================================================================
    # DOCUMENT PARSING  (PDF / Word / Image — all via MinerU)
    # ================================================================

    async def parse_doc(self, file_path, use_ocr=True):
        """Parse a document (PDF/Image/Word/Excel) and return the markdown result.

        **Atomic**: ONLY parses. Does NOT save to KB, does NOT index.
        Supported: .pdf .png .jpg .jpeg .docx .xlsx."""
        data = {"use_ocr": str(use_ocr).lower()}
        return await self._post_file("/api/parse/file-vt", file_path, data, timeout=PARSE_TIMEOUT)

    async def parse_doc_batch(self, file_paths, use_ocr=True):
        """Batch: parse multiple documents (PDF/Image/Word/Excel).

        **Atomic**: ONLY parses. Does NOT save to KB, does NOT index.
        Files are parsed sequentially. Returns an aggregate
        {total, successful, results} so callers can see which files failed.
        Supported: .pdf .png .jpg .jpeg .docx .xlsx."""

        results = []
        for i, fp in enumerate(file_paths):
            p = Path(fp)
            if not p.exists():
                results.append({"success": False, "file": fp, "error": "file not found"})
                continue
            try:
                payload = {"use_ocr": str(use_ocr).lower()}
                r = await self._post_file(
                    "/api/parse/file-vt", fp,
                    payload,
                    timeout=PARSE_TIMEOUT,
                )
                if isinstance(r, dict):
                    r = {**r, "file": fp}
                results.append(r)
            except Exception as e:
                results.append({"success": False, "file": fp, "error": f"{type(e).__name__}: {e}"})
        successful = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        return {"total": len(results), "successful": successful, "results": results}

    # ================================================================
    # TAGS MANAGEMENT
    # ================================================================

    async def kb_tags_list(self):
        """List all registered tags."""
        return await self._get("/api/kb/tags")

    async def kb_tag_create(self, tag):
        """Register a new tag (dedup)."""
        return await self._post_json("/api/kb/tags", {"tag": tag})

    async def kb_doc_update_tags(self, kb_id, doc_path, tags):
        """Update a document's tags (string[])."""
        return await self._patch_json("/api/kb/documents/tags", {
            "kbId": kb_id, "docPath": doc_path, "tags": tags
        })

    async def kb_doc_get_by_tag(self, tag, kb_id=""):
        """Find documents by tag across all KBs (or one KB if kb_id given)."""
        params = {"tag": tag}
        if kb_id:
            params["kb_id"] = kb_id
        return await self._get("/api/kb/documents/by-tag", **params)

    # ================================================================
    # BACKEND STATUS
    # ================================================================

    async def backend_status(self):
        """Get backend service health and MinerU OCR engine status."""
        results = {}
        for name, endpoint in [
            ("backend_health", "/api/v1/health"),
            ("mineru_status", "/api/v1/mineru/status"),
        ]:
            try:
                results[name] = await self._request("GET", endpoint, base=self.backend_url, timeout=5)
            except Exception as e:
                results[name] = {"error": str(e)}
        return results

    # ================================================================
    # BACKEND POST/GET (新增：让 MCP 工具能调用后端 search/graph API)
    # ================================================================

    async def _post_backend_json(self, endpoint, body, timeout=None):
        """POST JSON 到后端（base=self.backend_url）。timeout=None 用客户端默认；索引类调用传 INDEX_TIMEOUT。"""
        kwargs = {"json": body}
        if timeout:
            kwargs["timeout"] = timeout
        return await self._request("POST", endpoint, base=self.backend_url, **kwargs)

    async def _get_backend(self, endpoint, **params):
        """GET 后端接口。"""
        return await self._request("GET", endpoint, base=self.backend_url, params=params)

    # ================================================================
    # 向量检索与两阶段检索（新增）
    # ================================================================

    async def vector_search(self, query, kb_id="", top_k=5, score_threshold=0.0, balance_kbs=False):
        """向量语义搜索。score_threshold<=0 表示用后端默认阈值。
        balance_kbs=True 时跨库均衡，防大KB主导结果。"""
        body = {"query": query, "top_k": top_k}
        if kb_id:
            body["kb_id"] = kb_id
        if score_threshold and score_threshold > 0:
            body["score_threshold"] = score_threshold
        if balance_kbs:
            body["balance_kbs"] = True
        return await self._post_backend_json("/api/v1/search/vector", body)

    async def batch_vector_search(self, query_doc_paths, kb_id="", top_k=5, score_threshold=0.3):
        """批量向量相似度查询：对多个源文档查询相似文档。"""
        body = {
            "query_doc_paths": query_doc_paths,
            "top_k": top_k,
            "score_threshold": score_threshold,
        }
        if kb_id:
            body["kb_id"] = kb_id
        return await self._post_backend_json("/api/v1/search/batch-vector", body)

    async def two_stage_search(self, query, kb_id="", stage1_top_k=20,
                                stage2_top_k=5, enable_graph_expansion=True,
                                score_threshold=0.0, balance_kbs=False):
        """两阶段精准检索。score_threshold<=0 表示用后端默认阈值。
        balance_kbs=True 时跨库均衡，防大KB主导结果。"""
        body = {
            "query": query,
            "stage1_top_k": stage1_top_k,
            "stage2_top_k": stage2_top_k,
            "enable_graph_expansion": enable_graph_expansion,
        }
        if kb_id:
            body["kb_id"] = kb_id
        if score_threshold and score_threshold > 0:
            body["score_threshold"] = score_threshold
        if balance_kbs:
            body["balance_kbs"] = True
        return await self._post_backend_json("/api/v1/search/two-stage", body)

    async def reindex(self, kb_id="", force=False):
        """重建索引。"""
        body = {"force": force}
        if kb_id:
            body["kb_id"] = kb_id
        return await self._post_backend_json("/api/v1/search/reindex", body, timeout=INDEX_TIMEOUT)

    async def index_document(self, kb_id, doc_path, doc_name="", description="", content="", doc_id=""):
        """单文档索引：向量 + 图谱。存入向量库并记录 vector_index 到元信息。

        支持两种模式：
        1. doc_id 模式：提供 doc_id，自动解析 kb_id 和 doc_path
        2. 传统模式：提供 kb_id + doc_path
        """
        body = {
            "kb_id": kb_id,
            "doc_path": doc_path,
            "doc_name": doc_name,
            "description": description,
            "content": content,
        }
        if doc_id:
            body["doc_id"] = doc_id
        return await self._post_backend_json("/api/v1/search/index-document", body, timeout=INDEX_TIMEOUT)

    async def batch_index_documents(self, kb_id, doc_paths, force=False):
        """批量文档向量索引。"""
        body = {
            "kb_id": kb_id,
            "doc_paths": doc_paths,
            "force": force,
        }
        return await self._post_backend_json("/api/v1/search/batch-index", body, timeout=INDEX_TIMEOUT)

    async def search_stats(self, kb_id=""):
        """向量索引统计。"""
        return await self._get_backend("/api/v1/search/stats", kb_id=kb_id)

    async def graph_search(self, keyword, limit=20):
        """图谱文档搜索（按名称/路径）。"""
        return await self._get_backend(
            "/api/v1/graph/search/documents", keyword=keyword, limit=limit
        )

    async def graph_search_kbs(self, keyword, limit=20):
        """图谱 KB 搜索。"""
        return await self._get_backend(
            "/api/v1/graph/search/kbs", keyword=keyword, limit=limit
        )

    async def graph_search_tags(self, keyword, limit=20):
        """图谱标签搜索。"""
        return await self._get_backend(
            "/api/v1/graph/search/tags", keyword=keyword, limit=limit
        )

    async def graph_neighbors(self, node_id, node_type="document", depth=1):
        """图谱邻居子图（文档/KB/标签）。"""
        return await self._get_backend(
            "/api/v1/graph/neighbors", node_id=node_id, node_type=node_type, depth=depth
        )

    async def graph_stats(self):
        """图谱统计。"""
        return await self._get_backend("/api/v1/graph/stats")

    # ──────────────────────────────────────────────────────────────
    # GRAPH v3（文档/KB/标签为中心，无 NER）
    # ──────────────────────────────────────────────────────────────

    async def graph_health(self) -> dict:
        """图谱健康探测（Neo4j 是否可用）。"""
        return await self._get_backend("/api/v1/graph/health")

    async def graph_document(self, doc_path: str, limit: int = 50) -> dict:
        """单文档图谱视图：文档信息 + 标签 + 关联文档 + 跨 KB 连接。"""
        return await self._get_backend("/api/v1/graph/document",
                                       doc_path=doc_path, limit=limit)

    async def graph_document_related(self, doc_path: str, limit: int = 20) -> dict:
        """文档的关联文档列表。"""
        return await self._get_backend("/api/v1/graph/document/related",
                                       doc_path=doc_path, limit=limit)

    async def graph_documents_by_tag(self, tag_name: str, limit: int = 50) -> dict:
        """按标签查找文档。"""
        return await self._get_backend("/api/v1/graph/documents-by-tag",
                                       tag_name=tag_name, limit=limit)

    async def graph_kb_overview(self, kb_id: str) -> dict:
        """KB 图谱概览：文档统计 + 标签分布 + 关联 KB + Top 文档。"""
        return await self._get_backend("/api/v1/graph/kb-overview", kb_id=kb_id)

    async def graph_build_kb(self, kb_id: str, force: bool = False) -> dict:
        """为整个 KB 构建文档关系图谱（基于 metadata）。"""
        return await self._post_backend_json(
            "/api/v1/graph/build-kb",
            {"kb_id": kb_id, "force": force}, timeout=INDEX_TIMEOUT,
        )

    async def graph_build_all(self, force: bool = False) -> dict:
        """为所有 KB 构建文档关系图谱。"""
        return await self._post_backend_json(
            "/api/v1/graph/build-all",
            {"force": force}, timeout=INDEX_TIMEOUT,
        )

    async def graph_cross_kb_documents(self, min_kbs: int = 2, limit: int = 50) -> dict:
        """跨 KB 桥梁文档。"""
        return await self._get_backend(
            "/api/v1/graph/cross-kb-documents", min_kbs=min_kbs, limit=limit,
        )

    async def graph_document_paths(self, doc_a: str, doc_b: str,
                                    max_depth: int = 4) -> dict:
        """两文档间最短路径。"""
        return await self._get_backend(
            "/api/v1/graph/document-paths",
            doc_a=doc_a, doc_b=doc_b, max_depth=max_depth,
        )

    async def graph_central_documents(self, kb_id: str, top_n: int = 20) -> dict:
        """KB 内关联度最高的文档。"""
        return await self._get_backend(
            "/api/v1/graph/central-documents", kb_id=kb_id, top_n=top_n,
        )

    async def graph_delete_document(self, doc_path: str) -> dict:
        """删除单文档图谱数据。"""
        return await self._request(
            "DELETE", "/api/v1/graph/document",
            base=self.backend_url, params={"doc_path": doc_path},
        )

    async def graph_delete_kb(self, kb_id: str) -> dict:
        """删除整个 KB 的图谱数据。"""
        return await self._request(
            "DELETE", f"/api/v1/graph/kb/{kb_id}", base=self.backend_url,
        )

    # ================================================================
    # EXPERIENCE MANAGEMENT (经验管理)
    # ================================================================

    async def experience_init(self, kb_id: str) -> dict:
        """初始化经验文件夹。"""
        return await self._get_backend(f"/api/v1/experience/{kb_id}/init")

    async def experience_create(self, kb_id: str, title: str,
        scenario: str = "", category: str = "tip", problem: str = "",
        solution: str = "", result: str = "success",
        key_lessons: list = None, tags: list = None,
        severity: str = "normal", related_docs: list = None,
        prerequisites: list = None, metrics: dict = None) -> dict:
        """创建新经验记录。"""
        body = {
            "title": title, "scenario": scenario, "category": category,
            "problem": problem, "solution": solution, "result": result,
            "key_lessons": key_lessons or [], "tags": tags or [],
            "severity": severity, "related_docs": related_docs or [],
            "prerequisites": prerequisites or [], "metrics": metrics or {},
        }
        return await self._post_backend_json(f"/api/v1/experience/{kb_id}", body)

    async def experience_read(self, kb_id: str, exp_id: str) -> dict:
        """读取经验元数据和正文。"""
        return await self._get_backend(f"/api/v1/experience/{kb_id}/{exp_id}")

    async def experience_list(self, kb_id: str, scenario: str = "",
        category: str = "", tag: str = "") -> dict:
        """列出经验，支持按场景/类别/标签过滤。"""
        params = {}
        if scenario: params["scenario"] = scenario
        if category: params["category"] = category
        if tag: params["tag"] = tag
        return await self._get_backend(f"/api/v1/experience/{kb_id}", **params)

    async def experience_update(self, kb_id: str, exp_id: str, **kwargs) -> dict:
        """更新经验。传需要更新的字段。"""
        body = {k: v for k, v in kwargs.items() if v is not None and v != ""}
        return await self._request("PUT", f"/api/v1/experience/{kb_id}/{exp_id}",
                                   base=self.backend_url, json=body)

    async def experience_delete(self, kb_id: str, exp_id: str) -> dict:
        """永久删除经验。"""
        return await self._request("DELETE", f"/api/v1/experience/{kb_id}/{exp_id}",
                                   base=self.backend_url)

    async def experience_apply(self, kb_id: str, exp_id: str,
        user: str = "", context: str = "", result: str = "", notes: str = "") -> dict:
        """标记经验被应用。"""
        body = {"user": user, "context": context, "result": result, "notes": notes}
        return await self._post_backend_json(
            f"/api/v1/experience/{kb_id}/{exp_id}/apply", body)

    async def experience_review(self, kb_id: str, exp_id: str,
        reviewer: str = "", rating: float = 5.0, comment: str = "") -> dict:
        """评审经验（评分）。"""
        body = {"reviewer": reviewer, "rating": rating, "comment": comment}
        return await self._post_backend_json(
            f"/api/v1/experience/{kb_id}/{exp_id}/review", body)

    async def experience_summary(self, kb_id: str) -> dict:
        """获取经验统计摘要。"""
        return await self._get_backend(f"/api/v1/experience/{kb_id}/summary")

    async def experience_search(self, kb_id: str, query: str, top_k: int = 10) -> dict:
        """元信息搜索经验。"""
        body = {"query": query, "top_k": top_k}
        return await self._post_backend_json(f"/api/v1/experience/{kb_id}/search", body)

    async def experience_search_vector(self, kb_id: str, query: str, top_k: int = 5) -> dict:
        """向量语义搜索经验。"""
        body = {"query": query, "top_k": top_k}
        return await self._post_backend_json(f"/api/v1/experience/{kb_id}/vector-search", body)

    async def experience_search_global(self, query: str, top_k: int = 10) -> dict:
        """跨 KB 全局搜索经验。"""
        body = {"query": query, "top_k": top_k}
        return await self._post_backend_json("/api/v1/experience/global-search", body)
