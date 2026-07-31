<h1 align="center">
  <img src="../docs/images/logo.svg" alt="kb-mcp" width="80" />
  <br/>
  kb-mcp
</h1>

<p align="center">
  <strong>MCP Server · 74 Tools · KB Lifecycle · Search · Graph · Experience</strong><br/>
  <em>The MCP tool layer connecting Claude Code agents to the RAG Knowledge Platform</em>
</p>

<p align="center">
  <a href="#-quick-start"><img src="https://img.shields.io/badge/Quick%20Start-3%20steps-blue?style=for-the-badge" /></a>
  <a href="#-tools-74"><img src="https://img.shields.io/badge/MCP-74%20tools-blueviolet?style=for-the-badge" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" /></a>
  <a href="#-tech-stack"><img src="https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge" /></a>
  <a href="#-tech-stack"><img src="https://img.shields.io/badge/FastMCP-latest-9cf?style=for-the-badge" /></a>
</p>

---

<p align="center">
  <sub><a href="./README.md"><b>English</b></a> · <a href="./README-zh.md">中文</a></sub>
</p>

---

## 📌 Table of Contents

- [🌟 Overview](#-overview)
- [🏗️ Architecture](#️-architecture)
- [🚀 Quick Start](#-quick-start)
- [🔌 Tools (74)](#-tools-74)
- [📡 Client Library](#-client-library)
- [⚙️ Configuration](#️-configuration)
- [📁 Project Structure](#-project-structure)
- [🔧 Tech Stack](#-tech-stack)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)

## 🌟 Overview

`kb-mcp` is the MCP (Model Context Protocol) server that bridges Claude Code (or any MCP-compatible agent) to the RAG Knowledge Platform. It provides **74 tools** organized into 11 categories — enough to manage every aspect of a production knowledge base without leaving the agent conversation.

**Key principles:**

- **MCP-first** — All KB operations go through `mcp__kb-mcp__*` tools. No `curl`, no raw HTTP, no terminal commands for KB work.
- **Zero HTTP in server.py** — `server.py` contains pure MCP tool definitions. All HTTP logic is isolated in `kb_client/client.py`.
- **Non-blocking by default** — Parse tools return immediately with a `task_id`; background task registry handles the async work.
- **Direct file reads** — Where possible, tools read `.tree-fs.json` and `.knowledge-base.yml` directly (write operations still go through the web proxy / backend API).
- **Global registration** — With `RAG_PROJECT_ROOT` set, kb-mcp connects from any directory, any Claude Code session.

## 🏗️ Architecture

```
┌──────────────────────────────────────────┐
│          Claude Code / MCP Client         │
│          mcp__kb-mcp__* (stdio)          │
└──────────────────┬───────────────────────┘
                   │ MCP stdio (FastMCP)
┌──────────────────▼───────────────────────┐
│              kb-mcp/server.py             │
│         74 @mcp.tool() definitions       │
│         Zero HTTP code — delegates down   │
└──────┬──────────────────────┬────────────┘
       │ kb_client (HTTP)     │ direct file I/O
       ▼                      ▼
┌──────────────┐    ┌──────────────────────┐
│  Web Proxy   │    │ .tree-fs.json         │
│  :6789/:3000 │    │ .knowledge-base.yml   │
└──────┬───────┘    │ web/storage/...       │
       │            └──────────────────────┘
┌──────▼───────┐
│   Backend    │
│   :8765/8001 │
└──────────────┘
```

**Data flow by operation type:**

| Operation type | Path | Why |
|---------------|------|-----|
| **Write** (create, update, delete, parse, save) | `server.py` → `kb_client` → HTTP → Web proxy → Backend API | Writes need consistency across disk, `.tree-fs.json`, and `.knowledge-base.yml` |
| **Read** (catalog, search, list, stats) | `server.py` → direct file read of `.tree-fs.json` + `.knowledge-base.yml` | Reads are zero-backend-load; faster and avoids proxy dependency |
| **Service lifecycle** (start, status, preflight, version, update) | `server.py` → `project_manager.py` → subprocess + `ragctl` | Silent headless startup + version-aware update |

## 🚀 Quick Start

```bash
# 1. Install (3 lightweight deps: mcp + httpx + pyyaml)
uv sync

# 2. Run standalone (stdio mode — for MCP clients)
uv run python server.py

# 3. Run in SSE mode (for HTTP transport)
uv run python server.py --http
```

> **Normally you don't run kb-mcp manually.** Claude Code auto-launches it via `../.mcp.json` when you open the project. The first `uv run` auto-syncs deps if needed. For global usage, `claude plugin install rag-knowledge` registers it in `~/.claude.json` → `mcpServers`.

## 🔌 Tools (74)

All tools are accessible via `mcp__kb-mcp__*` from any MCP client. Organized by domain:

### Service Lifecycle (4) — silent, headless management

| Tool | Description |
|------|-------------|
| `kb_project_start()` | Silently start project services. HEADLESS on every OS and every mode — |
| `kb_project_status()` | Full project service status. |
| `kb_project_update()` | Check GitHub for a newer version of the project and optionally pull it. |
| `backend_status()` | Get backend service health and MinerU OCR engine status. |

### KB CRUD (5)

| Tool | Description |
|------|-------------|
| `kb_list()` | List all knowledge bases with id, name, description, and document count. |
| `kb_create()` | Create a new knowledge base. parent_id is an optional tree folder UUID for nesting (omit for root). Returns knowledgeBase with id (UUID) and path -- both work as kb_id in other tools. |
| `kb_update()` | Update a knowledge base's name and/or description. kb_id accepts path or UUID. |
| `kb_delete()` | Delete an entire knowledge base and all its contents (irreversible). kb_id accepts either the path string or the UUID returned by kb_create. |
| `kb_find_duplicates()` | Find duplicate / near-duplicate documents via content hash + vector similarity. |

### Document CRUD (9)

| Tool | Description |
|------|-------------|
| `kb_get_documents()` | List all documents inside a knowledge base. kb_id accepts path or UUID. |
| `kb_doc_create()` | Create a new Markdown document in a KB. Auto-dedup on name collision. |
| `kb_doc_read()` | Read the content of a document (Markdown body, paginated). |
| `kb_doc_update_meta()` | Update a document's metadata (name, description). |
| `kb_doc_update_content()` | Overwrite a document's content. |
| `kb_doc_delete()` | Delete a single document. |
| `kb_doc_batch_delete()` | Delete multiple documents at once. |
| `kb_doc_move()` | Move a document to a different knowledge base. |
| `kb_doc_save_parsed()` |  |

### Search (4)

| Tool | Description |
|------|-------------|
| `kb_search()` | Search KB metadata by keyword across ALL knowledge bases. Scans only document |
| `kb_search_vector()` | Vector semantic search for document chunks. |
| `kb_search_two_stage()` |  |
| `kb_search_stats()` | Vector index statistics. View each knowledge base's index status in the vector database. |

### File System (3)

| Tool | Description |
|------|-------------|
| `fs_get_tree()` | Get the full file system tree of knowledge bases and their contents. |
| `fs_get_children()` | Get immediate children (folders + files) of a folder. |
| `fs_upload_file()` | Upload a local file into the file system tree. file_path is an absolute local disk path. parent_id is a tree folder UUID (empty = root). |

### Knowledge Graph (11)

| Tool | Description |
|------|-------------|
| `kb_graph_build()` | Build the document relationship graph for one KB (kb_id given) or all KBs (kb_id empty). |
| `kb_graph_central_documents()` | Find the most central documents in a KB (by RELATED_TO degree centrality). |
| `kb_graph_cross_kb_documents()` | Discover cross-knowledge-base bridge documents - documents connected to >= min_kbs different KBs. |
| `kb_graph_delete_document()` | Delete a single document's graph data (shared entities preserved, only removes this document's contribution). |
| `kb_graph_delete_kb()` | Delete an entire KB's graph data (cross-KB shared entities preserved). |
| `kb_graph_document()` | View a single document's knowledge graph: document info, tags, related documents, cross-KB connections. |
| `kb_graph_document_paths()` | Find the shortest relationship path between two documents (via RELATED_TO relationship chains). |
| `kb_graph_document_related()` | Return documents related to a given document (based on same KB / shared tags / description similarity). |
| `kb_graph_kb_overview()` | KB-level graph overview: document statistics, tag distribution, related KBs, top related documents. |
| `kb_graph_search()` | Search nodes in the knowledge graph by keyword (name/path/label). |
| `kb_graph_stats()` | Return knowledge graph statistics and Neo4j availability. |

### Experience (20)

| Tool | Description |
|------|-------------|
| `experience_apply()` | Mark an experience as applied. Records the user, context, and effect. Each call increments applied_count. |
| `experience_apply_decay()` | E11: Apply experience decay rules (periodic credibility degradation). |
| `experience_check_stale()` | E6: Check consistency between experiences and their related documents. |
| `experience_create()` | Create an experience record. |
| `experience_dashboard()` | E8: Experience dashboard - KB experience overview aggregate statistics. |
| `experience_delete()` | Permanently delete an experience. Irreversible. |
| `experience_draft_approve()` | E3: Approve draft -> formal experience (write index + vector index). |
| `experience_draft_read()` | E3: Read draft details (including extraction evidence, source document). |
| `experience_draft_reject()` | E3: Reject draft -> move to rejected/ (retain reject reason for traceability). |
| `experience_drafts_list()` | E3: List the experience draft pool (pending review candidates). |
| `experience_extract()` |  |
| `experience_list()` | List experiences in a knowledge base, supports filtering by scenario/category/tag. Results sorted by rating descending. |
| `experience_read()` | Read full experience information (metadata + content body). |
| `experience_rerank()` | Semantic reranking for experience search results -- multi-dimensional scoring. |
| `experience_review()` | Review an experience with a rating (0-5) and comment. Automatically updates the experience's average rating and review count. |
| `experience_search_global()` | Cross-KB global experience search -- QDCVR pipeline (isomorphic with document search). |
| `experience_search_smart()` | Intelligent multi-path experience retrieval -- the RECOMMENDED entry point for experience search. |
| `experience_summary()` | Get experience statistics summary, including total count, distribution by category, distribution by severity, total applications, average rating, top 5 experiences. |
| `experience_sync_kb()` | E6: Mark entire KB for sync (stale/orphan experiences marked needs_sync). |
| `experience_update()` |  |

### Meditation (6) — auto-insight scheduler

| Tool | Description |
|------|-------------|
| `experience_meditation_config_get()` | Get meditation config for a KB. |
| `experience_meditation_config_update()` | Update meditation config for a KB. Only pass fields to change. |
| `experience_meditation_history()` | List recent meditation runs, optionally filtered by KB. |
| `experience_meditation_run()` | Manually trigger a meditation run. Optionally scoped to one KB. |
| `experience_meditation_status()` | Get meditation status: scheduler, harness health, circuit breaker, per-KB configs. |
| `experience_meditation_task_status()` | Check the status of a non-blocking meditation run. |

### Tags & Cleanup (4)

| Tool | Description |
|------|-------------|
| `kb_tags_list()` | List all registered tags in the system. |
| `kb_doc_update_tags()` | Update a document's tags. kb_id accepts UUID; doc_path accepts full path or bare filename. |
| `kb_doc_get_by_tag()` | Find documents by tag across all KBs (or one KB if kb_id given). |
| `kb_tags_cleanup()` | Detect and clean up orphan tags (tags referenced by 0 documents). |

### Parse (3) — non-blocking

| Tool | Description |
|------|-------------|
| `parse_doc()` | Parse a document (PDF / Image / Word / Excel) into Markdown. |
| `parse_doc_batch()` | Batch: parse multiple documents (PDF / Image / Word / Excel) into Markdown. |
| `parse_task_status()` | Check the status of a non-blocking parse task. |

### Vector Index (4)

| Tool | Description |
|------|-------------|
| `kb_index_document()` | Index a single document (vector + graph). Stores document content (or existing document) into the vector database and records vector_index in metadata. |
| `kb_batch_index()` | Batch index documents (vector + graph). |
| `kb_reindex()` | Rebuild vector index and knowledge graph. Empty kb_id rebuilds all. |
| `kb_task_status()` | Check the status of ANY non-blocking background task (kb_reindex, kb_graph_build). |

### Cleanup (1)

| Tool | Description |
|------|-------------|
| `kb_cleanup_orphan_collections()` | Detect and clean up orphan/duplicate vector collections (vector index residue from deleted/renamed KBs). |

## 📡 Client Library

The `kb_client/` package contains all HTTP logic, cleanly separated from the MCP tool definitions:

```python
from kb_client import KbClient

client = KbClient(
    web_url="http://localhost:6789",
    backend_url="http://localhost:8765",
)

# KB operations
kbs = client.list_kbs()
client.create_kb(name="Research Papers", description="...")

# Search
results = client.search_two_stage(query="transformer architecture")

# Parse
task_id = client.parse_doc(file_path="/path/to/paper.pdf", kb_id="kb-123")
status = client.get_parse_status(task_id)
```

The client handles all edge cases: proxy fallback, `trust_env=False` to avoid HTTPS_PROXY hijacking, path normalization, and API response parsing.

## ⚙️ Configuration

`kb-mcp/config.py` reads URLs from the **root `config.yml`** and environment variables. No hardcoded paths or ports.

| Variable | Source | Purpose |
|----------|--------|---------|
| `BACKEND_URL` | root config.yml or env | Backend API for write operations |
| `WEB_URL` | root config.yml or env | Web proxy for file-system read operations |
| `APP_MODE` | env (`dev` / `prod`) | Selects dev or prod section from config.yml |
| `TREE_STORAGE_PATH` | env | Path to KB file storage (for direct reads) |

The `.mcp.json` at the monorepo root auto-configures kb-mcp for Claude Code:

```json
{
  "mcpServers": {
    "kb-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "kb-mcp", "python", "server.py"]
    }
  }
}
```

> **Note:** `.mcp.json` does not support the `cwd` field. Use `--directory kb-mcp` (or `--directory kb-mcp` on all platforms) instead.

## 📁 Project Structure

```
kb-mcp/
├── server.py                # FastMCP server — 74 @mcp.tool() definitions (zero HTTP code)
├── project_manager.py       # Service lifecycle + version/update (delegates to ragctl)
├── task_registry.py         # In-process async background task manager for parse jobs
├── config.py                # Reads URLs from shared config.yml (zero hardcoded paths)
├── plugin_install.py        # Global registraton: ragctl → ~/.local/bin, MCP → ~/.claude.json → mcpServers
├── kb_client/
│   └── client.py            # All HTTP logic (server.py has zero HTTP — delegates here)
├── pyproject.toml           # 3 deps: mcp + httpx + pyyaml
├── uv.lock                  # Locked dependency versions
├── test_smoke.py            # Import smoke test (fast, no services needed)
└── tests/                   # Integration test scripts
```

## 🔧 Tech Stack

| Component | Technology |
|-----------|-----------|
| MCP Framework | FastMCP (Python) |
| HTTP Client | httpx (with `trust_env=False`) |
| Config Parsing | PyYAML |
| Async Tasks | In-process task registry (no Celery, no Redis) |
| Package Manager | uv (hatchling build) |
| Transport | stdio (primary) + SSE (optional) |

## 🤝 Contributing

1. Fork → feature branch → commit → push → PR
2. New tools: add `@mcp.tool()` in `server.py`, HTTP logic in `kb_client/client.py` — keep the separation clean
3. Test with `uv run python test_smoke.py` for import sanity; full integration tests need running services
4. If adding a new dependency, keep it lightweight — kb-mcp is meant to be fast to start

## 📄 License

MIT © [kingdol](https://github.com/kingdol666) · Part of the [RAG Knowledge Platform](https://github.com/kingdol666/rag-knowledge)

---

<div align="center">

<sub>Part of</sub>
<a href="https://github.com/kingdol666/rag-knowledge"><b>RAG Knowledge Platform</b></a>
<br>
⭐ <a href="https://github.com/kingdol666/rag-knowledge">Star us on GitHub</a> ⭐

</div>
