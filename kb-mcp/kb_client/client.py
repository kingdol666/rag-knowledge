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
            self._client = httpx.AsyncClient(timeout=self.timeout)
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
        async with httpx.AsyncClient(timeout=5) as c:
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

    async def kb_doc_read(self, kb_id="", doc_path="", path="", max_chars=20000, offset=0, limit=200):
        """Read the content of a document (paginated).

        Accepts kb_id+doc_path or path alone. When kb_id and doc_path
        are provided, doc_path is resolved relative to the KB."""
        params = {"max_chars": max_chars, "offset": offset, "limit": limit}
        if path:
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

    async def parse_doc(self, file_path, kb_id, use_ocr=True, description="", tags=None):
        """Parse a document (PDF/Image/Word/Excel) and save into a knowledge base.
        tags: optional list[str] written to .knowledge-base.yml.
        Supported: .pdf .png .jpg .jpeg .docx .xlsx."""
        data = {"use_ocr": str(use_ocr).lower(), "parent_id": kb_id}
        if description:
            data["description"] = description
        if tags:
            data["tags"] = ",".join(tags)
        return await self._post_file("/api/parse/file-vt", file_path, data, timeout=PARSE_TIMEOUT)

    async def parse_doc_batch(self, file_paths, kb_id, use_ocr=True, descriptions=None, tags=None):
        """Batch: parse multiple documents (PDF/Image/Word/Excel) and save into the same KB.

        Files are parsed sequentially; each successful one is saved into
        *kb_id* via the parse pipeline (parent_id = kb_id). Returns an
        aggregate {total, successful, results} so callers can see which
        files failed without losing the ones that succeeded.
        tags: optional list[str] applied to every file (written to .knowledge-base.yml).
        Supported: .pdf .png .jpg .jpeg .docx .xlsx."""

        results = []
        for i, fp in enumerate(file_paths):
            p = Path(fp)
            if not p.exists():
                results.append({"success": False, "file": fp, "error": "file not found"})
                continue
            desc = descriptions[i] if descriptions and i < len(descriptions) else ""
            try:
                payload = {"use_ocr": str(use_ocr).lower(), "parent_id": kb_id, "description": desc}
                if tags:
                    payload["tags"] = ",".join(tags)
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
        return {"total": len(results), "successful": successful, "saved_to_kb": kb_id, "results": results}

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
            ("backend_health", "/api/v1/health")
        ]:
            try:
                results[name] = await self._request("GET", endpoint, base=self.backend_url, timeout=5)
            except Exception as e:
                results[name] = {"error": str(e)}
        return results

    # ================================================================
    # BACKEND POST/GET (新增：让 MCP 工具能调用后端 search/graph API)
    # ================================================================

    async def _post_backend_json(self, endpoint, body):
        """POST JSON 到后端（base=self.backend_url）。"""
        return await self._request("POST", endpoint, base=self.backend_url, json=body)

    async def _get_backend(self, endpoint, **params):
        """GET 后端接口。"""
        return await self._request("GET", endpoint, base=self.backend_url, params=params)

    # ================================================================
    # 向量检索与两阶段检索（新增）
    # ================================================================

    async def vector_search(self, query, kb_id="", top_k=5):
        """向量语义搜索。"""
        body = {"query": query, "top_k": top_k}
        if kb_id:
            body["kb_id"] = kb_id
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
                                stage2_top_k=5, enable_graph_expansion=True):
        """两阶段精准检索。"""
        body = {
            "query": query,
            "stage1_top_k": stage1_top_k,
            "stage2_top_k": stage2_top_k,
            "enable_graph_expansion": enable_graph_expansion,
        }
        if kb_id:
            body["kb_id"] = kb_id
        return await self._post_backend_json("/api/v1/search/two-stage", body)

    async def reindex(self, kb_id="", force=False):
        """重建索引。"""
        body = {"force": force}
        if kb_id:
            body["kb_id"] = kb_id
        return await self._post_backend_json("/api/v1/search/reindex", body)

    async def index_document(self, kb_id, doc_path, doc_name="", description="", content=""):
        """单文档索引：向量 + 图谱。存入向量库并记录 vector_index 到元信息。"""
        body = {
            "kb_id": kb_id,
            "doc_path": doc_path,
            "doc_name": doc_name,
            "description": description,
            "content": content,
        }
        return await self._post_backend_json("/api/v1/search/index-document", body)

    async def batch_index_documents(self, kb_id, doc_paths, force=False):
        """批量文档向量索引。"""
        body = {
            "kb_id": kb_id,
            "doc_paths": doc_paths,
            "force": force,
        }
        return await self._post_backend_json("/api/v1/search/batch-index", body)

    async def search_stats(self, kb_id=""):
        """向量索引统计。"""
        return await self._get_backend("/api/v1/search/stats", kb_id=kb_id)

    async def graph_search(self, keyword, limit=20):
        """图谱实体搜索。"""
        return await self._get_backend(
            "/api/v1/graph/search", keyword=keyword, limit=limit
        )

    async def graph_neighbors(self, entity_name, depth=1):
        """图谱邻居子图。"""
        return await self._get_backend(
            "/api/v1/graph/neighbors", entity_name=entity_name, depth=depth
        )

    async def graph_stats(self):
        """图谱统计。"""
        return await self._get_backend("/api/v1/graph/stats")
