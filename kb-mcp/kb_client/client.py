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
PARSE_TIMEOUT = int(os.environ.get("MCP_PARSE_TIMEOUT", "300"))


class KbClient:
    """Thin async wrapper around the knowledge-base REST API.

    Holds a persistent httpx.AsyncClient for connection pooling.
    Call aclose() when done, or use as an async context manager.
    """

    def __init__(self, web_url=DEFAULT_WEB_URL, backend_url=DEFAULT_BACKEND_URL, mineru_url="", timeout=HTTP_TIMEOUT):
        self.web_url = web_url.rstrip("/")
        self.backend_url = backend_url.rstrip("/")
        self.timeout = timeout
        self.mineru_url = mineru_url or ""
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
                ("mineru", f"{self.mineru_url}/health"),
                ("web", f"{self.web_url}/api/kb/catalog"),
            ]:
                try:
                    r = await c.get(url)
                    status[name] = r.status_code == 200
                except Exception as e:
                    status["errors"].append(f"{name}: {e}")
            status["all_ok"] = status["backend"] and status["mineru"] and status["web"]
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

    async def kb_doc_read(self, path, max_chars=20000, offset=0, limit=200):
        """Read the content of a document (paginated)."""
        return await self._get("/api/kb/document", path=path, max_chars=max_chars, offset=offset, limit=limit)

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
    # PROMPTS MANAGEMENT (CRUD)
    # ================================================================

    async def prompts_list(self, keyword="", category="", tag="", sort_by="updatedAt", sort_order="desc"):
        """List/search prompts with optional filters."""
        params = {"sortBy": sort_by, "sortOrder": sort_order}
        if keyword:
            params["keyword"] = keyword
        if category:
            params["category"] = category
        if tag:
            params["tag"] = tag
        return await self._get("/api/prompts", **params)

    async def prompts_create(self, name, description, content, category="default", tags=None):
        """Create a new prompt."""
        body = {"name": name, "description": description, "content": content, "category": category, "tags": tags or []}
        return await self._post_json("/api/prompts", body)

    async def prompts_get(self, prompt_id):
        """Get a single prompt by id."""
        return await self._get(f"/api/prompts/{prompt_id}")

    async def prompts_update(self, prompt_id, name="", description="", content="", category=""):
        """Update an existing prompt."""
        body = {}
        if name:
            body["name"] = name
        if description:
            body["description"] = description
        if content:
            body["content"] = content
        if category:
            body["category"] = category
        return await self._put_json(f"/api/prompts/{prompt_id}", body)

    async def prompts_delete(self, prompt_id):
        """Delete a prompt by id."""
        return await self._request("DELETE", f"/api/prompts/{prompt_id}")

    async def prompts_list_categories(self):
        """List all prompt categories."""
        return await self._get("/api/prompts/categories")

    async def prompts_list_tags(self):
        """List all prompt tags."""
        return await self._get("/api/prompts/tags")

    # ================================================================
    # PDF PARSING
    # ================================================================

    async def parse_pdf(self, file_path, use_ocr=True, parent_id="", description=""):
        """Parse a PDF into Markdown. If parent_id is given, saves to KB."""
        data = {"use_ocr": str(use_ocr).lower()}
        if parent_id:
            data["parent_id"] = parent_id
        if description:
            data["description"] = description
        return await self._post_file("/api/parse/file-vt", file_path, data, timeout=PARSE_TIMEOUT)

    async def parse_pdf_batch(self, file_paths, use_ocr=True):
        """Batch-parse multiple PDF files."""
        results = []
        for fp in file_paths:
            p = Path(fp)
            if not p.exists():
                results.append({"success": False, "error": f"file not found: {fp}"})
                continue
            try:
                result = await self._post_file("/api/parse/batch-file-vt", fp, {"use_ocr": str(use_ocr).lower()}, timeout=PARSE_TIMEOUT)
                results.append(result)
            except Exception as e:
                results.append({"success": False, "error": f"{type(e).__name__}: {e}"})
        successful = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        return {"total": len(results), "successful": successful, "results": results}

    async def parse_pdf_to_kb(self, file_path, kb_id, use_ocr=True, description=""):
        """Full pipeline: parse a PDF and save into a knowledge base."""
        data = {"use_ocr": str(use_ocr).lower(), "parent_id": kb_id}
        if description:
            data["description"] = description
        return await self._post_file("/api/parse/file-vt", file_path, data, timeout=PARSE_TIMEOUT)

    async def parse_pdf_to_kb_batch(self, file_paths, kb_id, use_ocr=True, descriptions=None):
        """Parse multiple PDFs and save each into the same knowledge base.

        Files are parsed sequentially; each successful one is saved into
        *kb_id* via the parse pipeline (parent_id = kb_id). Returns an
        aggregate {total, successful, results} so callers can see which
        files failed without losing the ones that succeeded.
        """
        results = []
        for i, fp in enumerate(file_paths):
            p = Path(fp)
            if not p.exists():
                results.append({"success": False, "file": fp, "error": "file not found"})
                continue
            desc = descriptions[i] if descriptions and i < len(descriptions) else ""
            try:
                r = await self._post_file(
                    "/api/parse/file-vt", fp,
                    {"use_ocr": str(use_ocr).lower(), "parent_id": kb_id, "description": desc},
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
    # BACKEND STATUS
    # ================================================================

    async def backend_status(self):
        """Get backend service info including DeepAgent and MinerU."""
        results = {}
        for name, endpoint in [
            ("backend_health", "/api/v1/health"),
            ("mineru", "/api/v1/mineru/status"),
            ("deepagent", "/api/deepagent/"),
        ]:
            try:
                results[name] = await self._request("GET", endpoint, base=self.backend_url, timeout=5)
            except Exception as e:
                results[name] = {"error": str(e)}
        return results
