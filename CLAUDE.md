# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# RAG Knowledge Platform

Monorepo for a document intelligence platform: PDF parsing (MinerU OCR), tree-based knowledge base management, keyword search, and an MCP tool layer for Agentic KB operations.

**Tech stack:** Python 3.12 + FastAPI · TypeScript + Nuxt 3 + Ant Design Vue · MCP (Python FastMCP) · Git submodules

## Architecture

Three services + one MCP layer, all configured from a single `config.yml`:

```
Browser (6789 / 3000)
    │  fetch()
    ▼
Nuxt 3 Server (proxy layer)   ← file tree, parse triggers, KB search UI
    │  server-to-server
    ▼
FastAPI Backend (8765 / 8001)  ← parse scheduling, MinerU subprocess management
    │  subprocess (Job Object)
    ▼
MinerU OCR Engine (ephemeral port)  ← PDF → Markdown conversion
```

```
Claude Code / Agent
    │  MCP stdio (kb-mcp)
    ▼
kb-mcp MCP Server              ← ~40 tools: KB CRUD, file ops, parse, search, tags
    │  HTTP → web proxy / backend     +  direct file reads
    ▼
Nuxt / Backend                 ← writes: parse + save pipeline
                                    reads: .tree-fs.json, .knowledge-base.yml
```

## Repository Structure

```
rag-knowledge/
├── config.yml              # Single source of truth for ports (shared across all modules)
├── start.bat / start.sh    # One-click launch scripts
├── backend/                # [submodule] rag-knowledge-backend — FastAPI + MinerU
├── web/                    # [submodule] rag-knowledge-frondend — Nuxt 3 UI (active frontend)
├── frontend/               # [submodule] rag-knowledge-frontend — legacy Vue 3/Vite (inactive)
├── kb-mcp/                 # [local] MCP server — provides ~40 MCP tools for KB operations
├── .claude/skills/         # OMC skills (knowledge-store dispatcher, ingest, search, manage, etc.)
├── .claude/agents/         # Archival agent definition (knowledge-admin.md)
├── .codex/                 # Parallel agent/skill definitions for Codex
├── docs/ARCHITECTURE.md    # Detailed architecture + MCP dev guide
└── KB_MCP_DEVELOPMENT.md   # API test report + MCP feasibility analysis
```

### Backend (FastAPI Python)

```
backend/
├── main.py                    # Entry point: port probe (anti-zombie) → uvicorn
├── app/
│   ├── main.py                # FastAPI app factory + lifespan (starts MinerU)
│   ├── config.py              # Singleton; reads backend/config.yml + shared config.yml
│   ├── api/routes/
│   │   ├── health.py          # GET /api/v1/health
│   │   ├── parse.py           # POST /api/v1/parse/file/vt (async), batch (SSE + JSON)
│   │   └── mineru.py          # GET /api/v1/mineru/status, POST /api/v1/mineru/restart
│   ├── models/schemas.py      # Pydantic response models
│   ├── services/mineru_service.py  # MineruParseService wrapper
│   └── utils/paths.py         # PROJECT_ROOT, config path resolution
├── sandbox/mineru_module/
│   └── manager.py             # MineruApiManager: subprocess lifecycle + async task API
├── tests/
│   ├── conftest.py            # Skips integration tests unless --run-integration
│   ├── test_unit.py           # Hermetic unit tests (no MinerU)
│   └── test_parse_async.py    # Integration (needs running MinerU)
└── pyproject.toml             # uv; Windows-only (required-environments: win32)
```

Key properties:
- **No DeepAgent** — old DeepAgent routes were removed.
- **MinerU port is ephemeral** — `MineruApiManager(port=None)` auto-picks a free port avoiding common dev ports. The resolved port is at `manager.port` / `manager.api_url`. **Do NOT hardcode 8764.**
- **Subprocess lifecycle** — MinerU runs as a hidden subprocess bound to a Windows Job Object (`KILL_ON_JOB_CLOSE`); stdout→log file (never a pipe, avoids [Errno 22]).
- **Anti-zombie startup** — `main.py:_port_in_use()` does a bare `socket.bind` before uvicorn; refuses to start if port is occupied.

### Web (Nuxt 3 TypeScript)

```
web/
├── start.mjs               # Reads config.yml → launches Nuxt CLI with resolved port
├── utils/paths.mjs         # Config.yml reader (manual YAML parser, no npm dependency)
├── nuxt.config.ts          # Nuxt config; runtimeConfig from config.yml
├── server/
│   ├── api/                # Nuxt server routes (proxy to backend)
│   │   ├── filesystem/     # File tree CRUD
│   │   ├── parse/          # PDF parse proxy + KB registration
│   │   ├── kb/             # KB search, catalog, document CRUD, tags
│   │   └── preview/        # File preview endpoints
│   ├── services/           # Core business logic (runs on Nuxt server, not browser)
│   │   ├── tree-file-system-service.ts   # .tree-fs.json + disk operations
│   │   ├── knowledge-base-yaml-service.ts # .knowledge-base.yml management
│   │   ├── kb-search-service.ts          # Cross-KB keyword search
│   │   ├── pdf-parse-service.ts          # Backend proxy + markdown backfill
│   │   └── tag-management-service.ts     # Tag registry
│   └── utils/
│       ├── runtime-paths.ts  # Tree-storage path resolution
│       └── tree-service.ts   # Singleton helpers
├── composables/            # Vue composables (useTreeFileSystem, usePDFParser, etc.)
├── pages/                  # file-system.vue, knowledge-search.vue, prompts.vue, etc.
├── types/                  # TypeScript interfaces
└── storage/tree-file-system/  # On-disk KB storage (dev; configurable path)
```

Key properties:
- **Server-to-server proxy** — Nuxt server routes forward to backend (no CORS issues). Browser never directly hits FastAPI.
- **Parse data flow:** `browser POST /api/parse/file-vt` → Nuxt calls backend `/api/v1/parse/file/vt` → backend returns `markdown_path` → Nuxt reads the `markdown_path` file, backfills content, writes into KB via `TreeFileSystemService.uploadFile()` (updates `.tree-fs.json` + `.knowledge-base.yml` + disk).
- **KB search is file-read only** — `kb-search-service.ts` reads `.tree-fs.json` + `.knowledge-base.yml` directly; zero backend load.

### kb-mcp (MCP Server Python)

```
kb-mcp/
├── server.py               # ~40 MCP tools via FastMCP; parse tools are NON-BLOCKING
├── client.py               # Copy of KbClient for quick tests
├── kb_client/
│   └── client.py           # All HTTP logic (server.py has zero HTTP code)
├── config.py               # Reads URLs from shared config.yml; zero hardcoded paths
├── task_registry.py        # In-process async background task manager for parse jobs
├── pyproject.toml          # MCP + httpx deps
└── .mcp.json (at root)     # Connects kb-mcp to Claude Code via stdio
```

MCP Tools by category:
- **Health:** `health_check`, `backend_status`
- **KB CRUD:** `kb_list`, `kb_create`, `kb_update`, `kb_delete`
- **Document CRUD:** `kb_doc_read`, `kb_doc_create`, `kb_doc_update_meta`, `kb_doc_update_content`, `kb_doc_delete`, `kb_doc_batch_delete`, `kb_doc_move`
- **File System:** `fs_get_tree`, `fs_get_children`, `fs_get_node`, `fs_get_count`, `fs_create_folder`, `fs_create_file`, `fs_update_node`, `fs_delete_node`, `fs_upload_file`
- **Parse (non-blocking):** `parse_pdf`, `parse_pdf_batch`, `parse_pdf_to_kb`, `parse_pdf_to_kb_batch` — return `task_id` immediately; poll via `parse_task_status`, `parse_tasks_list`
- **Tags:** `kb_tags_list`, `kb_tag_create`, `kb_doc_update_tags`, `kb_doc_get_by_tag`
- **Preview:** `preview_file`
- **Search:** `kb_search`

**Architecture principle:** writes go through HTTP API (backend/web proxy), reads go through direct file access (`.tree-fs.json` + `.knowledge-base.yml`).

## Key Commands

### Backend

```bash
cd backend

# Install
uv sync

# Run (dev mode — reload on, port from config.yml)
APP_MODE=dev uv run python main.py

# Run (prod mode — reload off)
APP_MODE=prod uv run python main.py

# Override port
BACKEND_PORT=9000 APP_MODE=dev uv run python main.py

# Tests (fast — skips integration)
uv run pytest

# Tests (with MinerU)
uv run pytest --run-integration

# Run a single test
uv run pytest tests/test_unit.py -x -k "test_name"

# Install MinerU (isolated venv, first time only)
cd sandbox/mineru_module
uv venv --python 3.12
uv pip install mineru[all]
cd ../..

# Health check
curl http://localhost:8765/api/v1/health
```

### Web

```bash
cd web

# Install
npm install

# Dev mode (port 6789)
APP_MODE=dev npm run dev

# Prod mode (port 3000)
APP_MODE=prod npm run start

# Build + preview
npm run build
npm run preview
```

### kb-mcp

```bash
cd kb-mcp

# Install (requires backend's .venv for its sync)
uv sync

# Run standalone (stdio mode — for Agent harness)
uv run python server.py

# Run SSE mode (for HTTP transport)
uv run python server.py --http
```

The MCP server is normally launched by Claude Code via `.mcp.json` at the monorepo root — no manual start needed.

### One-click Launch

```bash
./start.sh       # Linux/macOS
start.bat        # Windows
```
(Launches backend + web in separate terminals.)

## Storage Model

```
web/storage/tree-file-system/
├── .tree-fs.json                    # Global index: all folders + files with metadata
├── {knowledge-base-name}/
│   ├── .knowledge-base.yml          # Per-KB document index (name, description, path, tags, metadata)
│   ├── doc1.md                      # Parsed/uploaded markdown documents
│   └── images/                      # Images extracted from parsed PDFs
```

- `.tree-fs.json` — authoritative tree structure; folder/file CRUD always updates it first.
- `.knowledge-base.yml` — search index for each KB; `kb_search` reads it directly.

## Configuration

`config.yml` (at root) is the single source of truth for ports:

```yaml
server:
  dev:
    backend_port: 8765
    frontend_port: 6789
    backend_url: "http://localhost:8765"
  prod:
    backend_port: 8001
    frontend_port: 3000
    backend_url: "http://localhost:8001"
```

**Priority:** `BACKEND_PORT` env var > config.yml > code default.
**Mode selection:** `APP_MODE=dev|prod` env var selects the section.
**MinerU** has its own section in `backend/config.yml` (enabled, host, model_source, etc.).

## Known Pitfalls

1. **MinerU port changed to auto-pick** — `Manager` now uses `port=None` to pick a free ephemeral port. Don't hardcode 8764 in new code. Check `manager.port` or `manager.api_url`.
2. **Stdout pipe → file** — MinerU stdout goes to `backend/logs/mineru-api.log`, never a pipe. The old [Errno 22] pipe-closure crash is solved by this + Job Object lifecycle.
3. **HTTPS_PROXY hijacks localhost** — httpx calls use `trust_env=False` to avoid localhost calls being proxied to 7890. If adding new httpx calls, use the same flag.
4. **kb-mcp API inconsistencies** — `kb_client` has known quirks: batch_delete requires full paths while delete/read accept bare names; `file_size` in `.knowledge-base.yml` can be stale after index updates; `name` field doesn't always sync with `path`.
5. **Windows-only** — `pyproject.toml` has `required-environments = ["sys.platform == 'win32']`; `uv sync` fails on other platforms. The sandbox manager has cross-platform fallbacks but Windows is primary.
6. **Submodule management** — `backend`, `web`, `frontend` are git submodules. After cloning or switching branches, run `git submodule update --init --recursive`. The `kb-mcp` directory is NOT a submodule.

## Development Conventions

- All ports/URLs come from `config.yml` — never hardcoded.
- Paths resolved from `pathlib.Path(__file__)` or `import.meta.url` — never hardcoded.
- Python: type annotations required on all function parameters and returns.
- Python: use `logging.getLogger(__name__)`, never `print()` (except in entry-point scripts).
- Python: `httpx` calls use `trust_env=False` to avoid proxy hijacking localhost.
- TypeScript: server code uses `defineEventHandler` (Nuxt 3 / h3 pattern).
- The kb-mcp `server.py` contains zero HTTP code — all HTTP lives in `kb_client/client.py`.
- Parse tools in kb-mcp are NON-BLOCKING via `task_registry` — never `await` a parse directly in an MCP tool handler.
- Backend return values for parsed PDFs are **paths** (not content). The Nuxt proxy layer reads the path and backfills content.
