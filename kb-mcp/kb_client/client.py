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
INDEX_TIMEOUT = int(os.environ.get("MCP_INDEX_TIMEOUT", "600"))  # Large-document CPU embedding takes time; relax index calls to 600s
# Shared auth token — when set, attached as `Authorization: Bearer <token>` to all requests.
AUTH_TOKEN = os.environ.get("KB_AUTH_TOKEN", "")


class KbClient:
    """Thin async wrapper around the knowledge-base REST API.

    Holds a persistent httpx.AsyncClient for connection pooling.
    Call aclose() when done, or use as an async context manager.
    """

    # ---- parameter validation helpers ----

    @staticmethod
    def _require_kb_id(kb_id: str) -> dict | None:
        """Return error dict if kb_id is empty/blank; None otherwise.

        Prevents double-slash URLs (/api/.../{empty}//...) that cause HTTP 404.
        Call at the top of any method that places kb_id in the URL path.
        """
        if not kb_id or not kb_id.strip():
            return {"success": False, "error": "kb_id is required (cannot be empty)", "status": 400}
        return None

    @staticmethod
    def _require_exp_id(exp_id: str) -> dict | None:
        """Return error dict if exp_id is empty/blank; None otherwise."""
        if not exp_id or not exp_id.strip():
            return {"success": False, "error": "exp_id is required (cannot be empty)", "status": 400}
        return None

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
        """Check health of backend, MinerU, and web services.
        Uses the shared client for connection pooling and auth consistency."""
        client = await self._ensure_client()
        status = {"backend": False, "mineru": False, "web": False, "errors": []}
        for name, url in [
            ("backend", f"{self.backend_url}/api/v1/health"),
            ("web", f"{self.web_url}/api/kb/catalog"),
        ]:
            try:
                r = await client.get(url)
                status[name] = r.status_code == 200
            except Exception as e:
                status["errors"].append(f"{name}: {e}")
        # MinerU status — call the backend's /api/v1/mineru/status endpoint
        try:
            r = await client.get(f"{self.backend_url}/api/v1/mineru/status")
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
        are provided, doc_path is resolved relative to the KB.

        Path normalization: backslashes (Windows) are auto-converted to
        forward slashes so callers don't need to worry about platform differences."""
        if not any([doc_id, path, kb_id]):
            return {"success": False, "error": "At least one of doc_id, path, or kb_id+doc_path is required", "status": 400}
        # Normalize path separators: backslash → forward slash
        path = path.replace("\\", "/") if path else path
        doc_path = doc_path.replace("\\", "/") if doc_path else doc_path
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
    # BACKEND POST/GET (allows MCP tools to call backend search/graph APIs)
    # ================================================================

    async def _post_backend_json(self, endpoint, body, timeout=None):
        """POST JSON to backend (base=self.backend_url). timeout=None uses client default; index calls pass INDEX_TIMEOUT."""
        kwargs = {"json": body}
        if timeout:
            kwargs["timeout"] = timeout
        return await self._request("POST", endpoint, base=self.backend_url, **kwargs)

    async def _get_backend(self, endpoint, **params):
        """GET backend endpoint."""
        return await self._request("GET", endpoint, base=self.backend_url, params=params)

    # ================================================================
    # VECTOR & TWO-STAGE SEARCH
    # ================================================================

    async def vector_search(self, query, kb_id="", top_k=5, score_threshold=0.0, balance_kbs=False):
        """Vector semantic search. score_threshold<=0 uses backend default.
        balance_kbs=True balances across KBs to prevent large-KB dominance."""
        body = {"query": query, "top_k": top_k}
        if kb_id:
            body["kb_id"] = kb_id
        if score_threshold and score_threshold > 0:
            body["score_threshold"] = score_threshold
        if balance_kbs:
            body["balance_kbs"] = True
        return await self._post_backend_json("/api/v1/search/vector", body)

    async def batch_vector_search(self, query_doc_paths, kb_id="", top_k=5, score_threshold=0.3):
        """Batch vector similarity query: find similar documents for multiple source documents."""
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
        """Two-stage precision search. score_threshold<=0 uses backend default.
        balance_kbs=True balances across KBs to prevent large-KB dominance."""
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
        """Rebuild index."""
        body = {"force": force}
        if kb_id:
            body["kb_id"] = kb_id
        return await self._post_backend_json("/api/v1/search/reindex", body, timeout=INDEX_TIMEOUT)

    async def index_document(self, kb_id, doc_path, doc_name="", description="", content="", doc_id=""):
        """Index a single document: vector + graph. Stores vectors and records vector_index in metadata.

        Supports two modes:
        1. doc_id mode: provide doc_id, auto-resolves kb_id and doc_path
        2. Legacy mode: provide kb_id + doc_path
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
        """Batch document vector indexing."""
        body = {
            "kb_id": kb_id,
            "doc_paths": doc_paths,
            "force": force,
        }
        return await self._post_backend_json("/api/v1/search/batch-index", body, timeout=INDEX_TIMEOUT)

    async def search_stats(self, kb_id=""):
        """Vector index statistics."""
        return await self._get_backend("/api/v1/search/stats", kb_id=kb_id)

    async def delete_kb_vectors(self, kb_id: str, kb_path: str = ""):
        """Delete an entire KB's vector collection (backend DELETE /api/v1/search/kb/{kb_id}).

        Backend auto-cleans both kb_{uuid} and kb_{path} naming conventions,
        silently handling non-existent collections. Used for orphan collection cleanup.
        kb_path is optional; when passed, also cleans the path-named collection.
        """
        params = {"kb_path": kb_path} if kb_path else {}
        return await self._request(
            "DELETE", f"/api/v1/search/kb/{kb_id}",
            base=self.backend_url, params=params,
        )

    async def graph_search(self, keyword, limit=20):
        """Graph document search (by name/path)."""
        return await self._get_backend(
            "/api/v1/graph/search/documents", keyword=keyword, limit=limit
        )

    async def graph_search_kbs(self, keyword, limit=20):
        """Graph KB search."""
        return await self._get_backend(
            "/api/v1/graph/search/kbs", keyword=keyword, limit=limit
        )

    async def graph_search_tags(self, keyword, limit=20):
        """Graph tag search."""
        return await self._get_backend(
            "/api/v1/graph/search/tags", keyword=keyword, limit=limit
        )

    async def graph_neighbors(self, node_id, node_type="document", depth=1):
        """Graph neighbor subgraph (document/KB/tag)."""
        return await self._get_backend(
            "/api/v1/graph/neighbors", node_id=node_id, node_type=node_type, depth=depth
        )

    async def graph_stats(self):
        """Graph statistics."""
        return await self._get_backend("/api/v1/graph/stats")

    # ──────────────────────────────────────────────────────────────
    # GRAPH v3 (document/KB/tag centric, no NER)
    # ──────────────────────────────────────────────────────────────

    async def graph_health(self) -> dict:
        """Graph health probe (Neo4j availability)."""
        return await self._get_backend("/api/v1/graph/health")

    async def graph_document(self, doc_path: str, limit: int = 50) -> dict:
        """Single document graph view: doc info + tags + related docs + cross-KB connections."""
        if not doc_path or not doc_path.strip():
            return {"success": False, "error": "doc_path is required (cannot be empty)", "status": 400}
        return await self._get_backend("/api/v1/graph/document",
                                       doc_path=doc_path, limit=limit)

    async def graph_document_related(self, doc_path: str, limit: int = 20) -> dict:
        """Document's related document list (quality-filtered)."""
        if not doc_path or not doc_path.strip():
            return {"success": False, "error": "doc_path is required (cannot be empty)", "status": 400}
        return await self._get_backend("/api/v1/graph/document/related",
                                       doc_path=doc_path, limit=limit)

    async def graph_document_enhanced(self, doc_path: str, limit: int = 20) -> dict:
        """Enhanced document relation query: grouped by connection type (vector_similar/shared_tag/agent_judged)."""
        if not doc_path or not doc_path.strip():
            return {"success": False, "error": "doc_path is required (cannot be empty)", "status": 400}
        return await self._get_backend("/api/v1/graph/document/enhanced",
                                       doc_path=doc_path, limit=limit)

    async def graph_documents_by_tag(self, tag_name: str, limit: int = 50) -> dict:
        """Find documents by tag."""
        if not tag_name or not tag_name.strip():
            return {"success": False, "error": "tag_name is required (cannot be empty)", "status": 400}
        return await self._get_backend("/api/v1/graph/documents-by-tag",
                                       tag_name=tag_name, limit=limit)

    async def graph_kb_overview(self, kb_id: str) -> dict:
        """KB graph overview: doc stats + tag distribution + related KBs + top docs."""
        if (err := self._require_kb_id(kb_id)): return err
        return await self._get_backend("/api/v1/graph/kb-overview", kb_id=kb_id)

    async def graph_build_kb(self, kb_id: str, force: bool = False) -> dict:
        """Build document relationship graph for an entire KB (based on metadata)."""
        if (err := self._require_kb_id(kb_id)): return err
        return await self._post_backend_json(
            "/api/v1/graph/build-kb",
            {"kb_id": kb_id, "force": force}, timeout=INDEX_TIMEOUT,
        )

    async def graph_build_all(self, force: bool = False) -> dict:
        """Build document relationship graph for all KBs."""
        return await self._post_backend_json(
            "/api/v1/graph/build-all",
            {"force": force}, timeout=INDEX_TIMEOUT,
        )

    async def graph_cross_kb_documents(self, min_kbs: int = 2, limit: int = 50) -> dict:
        """Cross-KB bridge documents."""
        return await self._get_backend(
            "/api/v1/graph/cross-kb-documents", min_kbs=min_kbs, limit=limit,
        )

    async def graph_document_paths(self, doc_a: str, doc_b: str,
                                    max_depth: int = 4) -> dict:
        """Shortest path between two documents."""
        if not doc_a or not doc_a.strip():
            return {"success": False, "error": "doc_a is required (cannot be empty)", "status": 400}
        if not doc_b or not doc_b.strip():
            return {"success": False, "error": "doc_b is required (cannot be empty)", "status": 400}
        return await self._get_backend(
            "/api/v1/graph/document-paths",
            doc_a=doc_a, doc_b=doc_b, max_depth=max_depth,
        )

    async def graph_central_documents(self, kb_id: str, top_n: int = 20) -> dict:
        """Most connected documents within a KB."""
        if (err := self._require_kb_id(kb_id)): return err
        return await self._get_backend(
            "/api/v1/graph/central-documents", kb_id=kb_id, top_n=top_n,
        )

    async def graph_delete_document(self, doc_path: str) -> dict:
        """Delete graph data for a single document."""
        if not doc_path or not doc_path.strip():
            return {"success": False, "error": "doc_path is required (cannot be empty)", "status": 400}
        return await self._request(
            "DELETE", "/api/v1/graph/document",
            base=self.backend_url, params={"doc_path": doc_path},
        )

    async def graph_delete_kb(self, kb_id: str) -> dict:
        """Delete all graph data for an entire KB."""
        if (err := self._require_kb_id(kb_id)): return err
        return await self._request(
            "DELETE", f"/api/v1/graph/kb/{kb_id}", base=self.backend_url,
        )

    # ================================================================
    # EXPERIENCE MANAGEMENT
    # ================================================================

    async def experience_init(self, kb_id: str) -> dict:
        """Initialize the experience folder."""
        if (err := self._require_kb_id(kb_id)): return err
        return await self._get_backend(f"/api/v1/experience/{kb_id}/init")

    async def experience_create(self, kb_id: str, title: str,
        scenario: str = "", category: str = "tip", problem: str = "",
        solution: str = "", result: str = "success",
        key_lessons: list = None, tags: list = None,
        severity: str = "normal", related_docs: list = None,
        prerequisites: list = None, metrics: dict = None) -> dict:
        """Create a new experience record."""
        if (err := self._require_kb_id(kb_id)): return err
        body = {
            "title": title, "scenario": scenario, "category": category,
            "problem": problem, "solution": solution, "result": result,
            "key_lessons": key_lessons or [], "tags": tags or [],
            "severity": severity, "related_docs": related_docs or [],
            "prerequisites": prerequisites or [], "metrics": metrics or {},
        }
        return await self._post_backend_json(f"/api/v1/experience/{kb_id}", body)

    async def experience_reindex(self, kb_id: str, exp_id: str = None) -> dict:
        """Reindex experience into vector store. exp_id=None reindexes all experiences in the KB."""
        if (err := self._require_kb_id(kb_id)): return err
        body = {}
        if exp_id:
            body["exp_id"] = exp_id
        return await self._post_backend_json(f"/api/v1/experience/{kb_id}/reindex", body)

    async def experience_read(self, kb_id: str, exp_id: str) -> dict:
        """Read experience metadata and content."""
        if (err := self._require_kb_id(kb_id)): return err
        if (err := self._require_exp_id(exp_id)): return err
        return await self._get_backend(f"/api/v1/experience/{kb_id}/{exp_id}")

    async def experience_list(self, kb_id: str, scenario: str = "",
        category: str = "", tag: str = "") -> dict:
        """List experiences, optionally filtered by scenario/category/tag."""
        if (err := self._require_kb_id(kb_id)): return err
        params = {}
        if scenario: params["scenario"] = scenario
        if category: params["category"] = category
        if tag: params["tag"] = tag
        return await self._get_backend(f"/api/v1/experience/{kb_id}", **params)

    async def experience_update(self, kb_id: str, exp_id: str, **kwargs) -> dict:
        """Update experience. Pass only the fields to update."""
        if (err := self._require_kb_id(kb_id)): return err
        if (err := self._require_exp_id(exp_id)): return err
        body = {k: v for k, v in kwargs.items() if v is not None and v != ""}
        return await self._request("PUT", f"/api/v1/experience/{kb_id}/{exp_id}",
                                   base=self.backend_url, json=body)

    async def experience_delete(self, kb_id: str, exp_id: str) -> dict:
        """Permanently delete an experience."""
        if (err := self._require_kb_id(kb_id)): return err
        if (err := self._require_exp_id(exp_id)): return err
        return await self._request("DELETE", f"/api/v1/experience/{kb_id}/{exp_id}",
                                   base=self.backend_url)

    async def experience_apply(self, kb_id: str, exp_id: str,
        user: str = "", context: str = "", result: str = "", notes: str = "") -> dict:
        """Mark an experience as applied."""
        if (err := self._require_kb_id(kb_id)): return err
        if (err := self._require_exp_id(exp_id)): return err
        body = {"user": user, "context": context, "result": result, "notes": notes}
        return await self._post_backend_json(
            f"/api/v1/experience/{kb_id}/{exp_id}/apply", body)

    async def experience_review(self, kb_id: str, exp_id: str,
        reviewer: str = "", rating: float = 5.0, comment: str = "") -> dict:
        """Review an experience (rating)."""
        if (err := self._require_kb_id(kb_id)): return err
        if (err := self._require_exp_id(exp_id)): return err
        body = {"reviewer": reviewer, "rating": rating, "comment": comment}
        return await self._post_backend_json(
            f"/api/v1/experience/{kb_id}/{exp_id}/review", body)

    async def experience_summary(self, kb_id: str) -> dict:
        """Get experience statistics summary."""
        if (err := self._require_kb_id(kb_id)): return err
        return await self._get_backend(f"/api/v1/experience/{kb_id}/summary")

    async def experience_search(self, kb_id: str, query: str, top_k: int = 10) -> dict:
        """Metadata search for experiences.
        NOTE: When kb_id is empty, the MCP tool layer (server.py) should
        automatically fall back to experience_search_global before calling this method.
        """
        if (err := self._require_kb_id(kb_id)): return err
        body = {"query": query, "top_k": top_k}
        return await self._post_backend_json(f"/api/v1/experience/{kb_id}/search", body)

    async def experience_search_vector(self, kb_id: str, query: str, top_k: int = 5) -> dict:
        """Vector semantic search for experiences.
        NOTE: When kb_id is empty, the MCP tool layer (server.py) should
        automatically fall back to experience_search_global before calling this method.
        """
        if (err := self._require_kb_id(kb_id)): return err
        body = {"query": query, "top_k": top_k}
        return await self._post_backend_json(f"/api/v1/experience/{kb_id}/vector-search", body)

    async def experience_search_global(self, query: str, top_k: int = 10,
                                        score_threshold: float = None,
                                        verify_content: bool = True) -> dict:
        """Cross-KB global experience search — QDCVR pipeline (vector + content verification)."""
        body: dict = {"query": query, "top_k": top_k, "verify_content": verify_content}
        if score_threshold is not None:
            body["score_threshold"] = score_threshold
        return await self._post_backend_json("/api/v1/experience/global-search", body)

    async def experience_search_smart(self, query: str, top_k: int = 10,
                                       score_threshold: float = None,
                                       verify_content: bool = True) -> dict:
        """Smart experience search: delegates to experience_search_global.
        The MCP tool layer adds query understanding, adaptive thresholds,
        multi-round retrieval, and transparency metadata."""
        return await self.experience_search_global(
            query, top_k, score_threshold=score_threshold, verify_content=verify_content)

    # ── E0/E1: Experience extraction (heuristic + task bundle) ──

    async def experience_extract(self, kb_id: str, doc_paths: list = None,
                                  dry_run: bool = True, mode: str = "heuristic") -> dict:
        """E0/E1: Experience extraction. mode=prepare returns task bundle; heuristic for heuristic extraction.
        dry_run=True returns candidates only; False writes to draft pool."""
        if (err := self._require_kb_id(kb_id)): return err
        body = {"dry_run": dry_run, "mode": mode}
        if doc_paths is not None:
            body["doc_paths"] = doc_paths
        return await self._post_backend_json(f"/api/v1/experience/{kb_id}/extract", body)

    # ── E3: Draft pool ──

    async def experience_drafts_list(self, kb_id: str) -> dict:
        """List draft pool."""
        if (err := self._require_kb_id(kb_id)): return err
        return await self._get_backend(f"/api/v1/experience/{kb_id}/drafts")

    async def experience_draft_read(self, kb_id: str, draft_id: str) -> dict:
        """Read draft details."""
        if (err := self._require_kb_id(kb_id)): return err
        return await self._get_backend(f"/api/v1/experience/{kb_id}/drafts/{draft_id}")

    async def experience_draft_approve(self, kb_id: str, draft_id: str, edits: dict = None) -> dict:
        """Approve draft -> formal experience. edits can override fields."""
        if (err := self._require_kb_id(kb_id)): return err
        body = {"edits": edits} if edits else {}
        return await self._post_backend_json(
            f"/api/v1/experience/{kb_id}/drafts/{draft_id}/approve", body)

    async def experience_draft_reject(self, kb_id: str, draft_id: str, reason: str = "") -> dict:
        """Reject a draft."""
        if (err := self._require_kb_id(kb_id)): return err
        return await self._post_backend_json(
            f"/api/v1/experience/{kb_id}/drafts/{draft_id}/reject", {"reason": reason})

    # ── E6: Sync / stale ──

    async def experience_check_stale(self, kb_id: str) -> dict:
        """Check KB experience-document consistency."""
        if (err := self._require_kb_id(kb_id)): return err
        return await self._get_backend(f"/api/v1/experience/{kb_id}/stale")

    async def experience_check_stale_global(self) -> dict:
        """Global stale check."""
        return await self._post_backend_json("/api/v1/experience/stale-global", {})

    async def experience_sync_kb(self, kb_id: str) -> dict:
        """Mark entire KB for sync."""
        if (err := self._require_kb_id(kb_id)): return err
        return await self._post_backend_json(f"/api/v1/experience/{kb_id}/sync", {})

    # ── E8/E11: Dashboard / decay ──

    async def experience_dashboard(self, kb_id: str) -> dict:
        """Experience dashboard."""
        if (err := self._require_kb_id(kb_id)): return err
        return await self._get_backend(f"/api/v1/experience/{kb_id}/dashboard")

    async def experience_apply_decay(self, kb_id: str) -> dict:
        """Apply decay rules."""
        if (err := self._require_kb_id(kb_id)): return err
        return await self._post_backend_json(f"/api/v1/experience/{kb_id}/decay", {})
