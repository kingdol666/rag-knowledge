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

`kb-mcp` is the MCP (Model Context Protocol) server that bridges Claude Code (or any MCP-compatible agent) to the RAG Knowledge Platform. It provides **74 tools** organized into 13 categories — enough to manage every aspect of a production knowledge base without leaving the agent conversation.

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
│         ~74 @mcp.tool() definitions       │
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
| **Service lifecycle** (start, stop, status) | `server.py` → `project_manager.py` → subprocess management | Direct process control for silent headless startup |

## 🚀 Quick Start

```bash
# 1. Install (3 lightweight deps: mcp + httpx + pyyaml)
uv sync

# 2. Run standalone (stdio mode — for MCP clients)
uv run python server.py

# 3. Run in SSE mode (for HTTP transport)
uv run python server.py --http
```

> **Normally you don't run kb-mcp manually.** Claude Code auto-launches it via `../.mcp.json` when you open the project. The first `uv run` auto-syncs deps if needed. For global usage, `claude plugin install rag-knowledge` registers it in `~/.claude/.mcp.json`.

## 🔌 Tools (74)

All tools are accessible via `mcp__kb-mcp__*` from any MCP client. Organized by domain:

### Service Lifecycle (4) — silent, headless management

| Tool | Description |
|------|-------------|
| `kb_project_start(backend, web, neo4j, mode, wait)` | Silently launch services (headless, logged to files, idempotent). `wait=true` blocks until HTTP-healthy. |
| `kb_project_status()` | Are services running? Ports + HTTP health + PIDs + MinerU + log paths + `ready` boolean. |
| `kb_project_preflight()` | Is the project set up? `.env`/submodules/deps check + exact `fix` command. |
| `backend_status()` | Quick backend health check. |

### KB CRUD (6)

| Tool | Description |
|------|-------------|
| `kb_list()` | List all knowledge bases with metadata. |
| `kb_create(name, description, parent_id)` | Create a new KB (optionally as a sub-KB). |
| `kb_update(kb_id, name, description)` | Update KB metadata. |
| `kb_delete(kb_id)` | Delete a KB and all its documents. |
| `kb_catalog()` | Agentic-first KB scan — names, descriptions, doc counts, tag vocabulary. |
| `kb_doc_catalog(kb_id)` | Per-KB document scan — metadata overview for each document. |

### Document CRUD (9)

| Tool | Description |
|------|-------------|
| `kb_doc_create(kb_id, name, content, description)` | Create a new document with content + metadata. |
| `kb_doc_read(kb_id, doc_path)` | Read full document content (for content verification step). |
| `kb_doc_update_meta(kb_id, doc_path, name, description)` | Update document metadata. |
| `kb_doc_update_content(kb_id, doc_path, content)` | Replace document content. |
| `kb_doc_delete(kb_id, doc_path)` | Delete a single document. |
| `kb_doc_batch_delete(kb_id, doc_paths)` | Delete multiple documents at once. |
| `kb_doc_move(doc_path, target_kb_id)` | Move a document to a different KB. |
| `kb_doc_save_parsed(kb_id, doc_path, ...)` | Save parsed content (post-OCR) — different from `kb_doc_create`. |
| `kb_get_documents(kb_id)` | List all documents in a KB with full metadata. |

### Search (4)

| Tool | Description |
|------|-------------|
| `kb_search(query, kb_ids)` | Metadata-only keyword search across KBs. |
| `kb_search_vector(query, kb_id)` | Semantic vector search (BGE-M3 1024-dim). |
| `kb_search_two_stage(query, balance_kbs)` | **Primary search tool.** BM25 recall → vector rerank with cross-KB balancing. |
| `kb_search_stats()` | Search index statistics (document count, chunk count, collection sizes). |

### File System (4)

| Tool | Description |
|------|-------------|
| `fs_get_tree()` | Full file tree with metadata (folders, files, sizes, dates). |
| `fs_get_children(node_path)` | Children of a specific folder node. |
| `fs_get_count()` | Total file and folder count. |
| `fs_upload_file(path, content)` | Upload + register a file in the file system. |

### Knowledge Graph (14)

| Sub-category | Tools |
|-------------|-------|
| **Health & Stats** | `kb_graph_health()`, `kb_graph_stats()` |
| **Search** | `kb_graph_search(keyword, node_type)` — `node_type`: all (default) / document / kb / tag |
| **Exploration** | `kb_graph_neighbors(node_id)`, `kb_graph_kb_overview(kb_id)`, `kb_graph_cross_kb_documents()` |
| **Document-centric** | `kb_graph_document(doc_path)`, `kb_graph_document_related(doc_path)`, `kb_graph_document_paths(doc_path)`, `kb_graph_documents_by_tag(tag)` |
| **Centrality** | `kb_graph_central_documents(kb_id)` |
| **Build & Cleanup** | `kb_graph_build(kb_id)` (empty = all KBs), `kb_graph_delete_document(doc_path)`, `kb_graph_delete_kb(kb_id)` |

### Experience (22)

| Sub-category | Tools |
|-------------|-------|
| **CRUD** | `experience_create()`, `experience_read(id)`, `experience_list()`, `experience_update()`, `experience_delete()` |
| **Actions** | `experience_apply(id)`, `experience_review(id, rating, comment)`, `experience_summary(kb_id)` |
| **Search** | `experience_search(query)`, `experience_search_vector(query)`, `experience_search_global(query)`, `experience_search_smart(query)` (推荐入口), `experience_rerank(query, exps)` |
| **Extract & Drafts** | `experience_extract(mode, kb_id)`, `experience_drafts_list()`, `experience_draft_read(id)`, `experience_draft_approve(id)`, `experience_draft_reject(id)` |
| **Health** | `experience_check_stale(kb_id)` (空 = 全库), `experience_sync_kb(kb_id)`, `experience_dashboard()`, `experience_apply_decay()` |

### Tags & Cleanup (4)

| Tool | Description |
|------|-------------|
| `kb_tags_list(kb_id)` | List all tags with document counts. |
| `kb_doc_update_tags(doc_path, tags)` | Set tags on a document. |
| `kb_doc_get_by_tag(tag)` | Find documents by tag. |
| `kb_tags_cleanup(dry_run)` | Remove orphan tags (0 document references). |

### Parse (3) — non-blocking

| Tool | Description |
|------|-------------|
| `parse_doc(file_path, kb_id)` | Submit a file for async parsing. Returns `task_id` immediately. |
| `parse_doc_batch(file_paths, kb_id)` | Submit multiple files for parsing. |
| `parse_task_status(task_id)` | Poll the status of a parse task (pending → running → done/failed). |

### Vector Index (3)

| Tool | Description |
|------|-------------|
| `kb_index_document(doc_path, kb_id)` | Index a single document into the vector store. |
| `kb_batch_index(kb_id)` | Index all unindexed documents in a KB. |
| `kb_reindex(kb_id, force)` | Rebuild vector index for a KB. Use `force=true` to overwrite existing. |

### Cleanup (1)

| Tool | Description |
|------|-------------|
| `kb_cleanup_orphan_collections(dry_run)` | Detect and remove orphan ChromaDB collections. |

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
├── server.py                # FastMCP server — ~74 @mcp.tool() definitions (zero HTTP code)
├── project_manager.py       # Service lifecycle: start/stop/status (subprocess management)
├── task_registry.py         # In-process async background task manager for parse jobs
├── config.py                # Reads URLs from shared config.yml (zero hardcoded paths)
├── plugin_install.py        # Global registraton: ragctl → ~/.local/bin, MCP → ~/.claude/.mcp.json
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

MIT · Part of the [RAG Knowledge Platform](https://github.com/kingdol666/rag-knowledge)
