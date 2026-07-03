# RAG Knowledge Platform

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.139%2B-009688)](https://fastapi.tiangolo.com)
[![Nuxt](https://img.shields.io/badge/Nuxt-3.x-00DC82)](https://nuxt.com)
[![Neo4j](https://img.shields.io/badge/Neo4j-5.20-008CC1)](https://neo4j.com)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-1.5%2B-1E1E1E)](https://www.trychroma.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> A local-first, Agent-native knowledge base platform. Parse PDFs into structured Markdown, index them with keyword + vector + knowledge graph, and let both humans and AI agents query them through a unified MCP interface.

---

## TL;DR

```bash
git clone --recursive https://github.com/kingdol666/rag-knowledge.git
cd rag-knowledge
cp .env.example .env
cp config.yml.example config.yml

# Windows
start.bat dev

# macOS / Linux
./start.sh dev
```

Then open [http://localhost:6789](http://localhost:6789).

---

## Table of Contents

- [What is this?](#what-is-this)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Directory Structure](#directory-structure)
- [Quick Start](#quick-start)
- [Operation Workflow](#operation-workflow)
- [Configuration](#configuration)
- [Design Philosophy](#design-philosophy)
- [Troubleshooting](#troubleshooting)
- [Known Gaps &amp; Roadmap](#known-gaps--roadmap)
- [License](#license)

---

## What is this?

RAG Knowledge Platform turns your local documents into a searchable, traceable, and agent-accessible knowledge base.

It is built around three ideas:

1. **Local-first**: All files, indexes, and metadata stay on your machine.
2. **Multi-signal retrieval**: Combine keyword search (BM25), semantic search (BGE-M3 + ChromaDB), and knowledge graph traversal (Neo4j) to reduce hallucination.
3. **Agent-native**: Expose all capabilities as MCP tools so Claude Code, Cursor, or any MCP-compatible agent can manage and query the knowledge base directly.

---

## Key Features

| Feature                       | Description                                                             |
| ----------------------------- | ----------------------------------------------------------------------- |
| **PDF Parsing**               | MinerU OCR/VLM extracts text, tables, and images into Markdown.         |
| **Knowledge Base Management** | UUID-based KBs, tree filesystem, tags, descriptions.                    |
| **Keyword Search**            | jieba + BM25 full-text search across all KBs.                           |
| **Vector Search**             | BGE-M3 embeddings + ChromaDB for semantic retrieval.                    |
| **Knowledge Graph**           | Neo4j stores entities and relations extracted from documents.           |
| **Two-Stage Search**          | BM25 + graph expansion for recall, vector search for precision.         |
| **MCP Server**                | ~35 tools for agents: ingest, search, manage, graph query, reindex.     |
| **Claude Code Skills**        | 8 skills for autonomous KB governance: ingest, organize, verify, batch. |
| **Web Console**               | Nuxt 3 UI for browsing, uploading, parsing, and searching.              |

---

## Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  Agent / Claude Code                                        │
│  .claude/skills/*  →  Archival dispatcher  →  MCP tools     │
└──────────────────────────┬──────────────────────────────────┘
                           │ stdio / MCP
┌──────────────────────────▼──────────────────────────────────┐
│  kb-mcp/server.py                                           │
│  ~35 MCP tools (search, parse, manage, graph, reindex)      │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP
┌──────────────────────────▼──────────────────────────────────┐
│  Web Layer (Nuxt 3)                                         │
│  web/pages/*  +  web/server/api/*  (proxy to backend)       │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP
┌──────────────────────────▼──────────────────────────────────┐
│  Backend Layer (FastAPI + uv)                               │
│  parse  ·  search  ·  vector  ·  graph  ·  health           │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│  Storage                                                    │
│  Filesystem  +  .tree-fs.json  +  .knowledge-base.yml       │
│  ChromaDB (vectors)  +  Neo4j (graph)  +  models_cache      │
└─────────────────────────────────────────────────────────────┘
```

### Retrieval Flow

```text
User Query
    │
    ├──► Keyword Search (BM25)
    │
    ├──► Graph Neighbor Expansion (Neo4j)
    │
    └──► Candidate Document Set
              │
              ▼
    Vector Re-ranking (BGE-M3 + ChromaDB)
              │
              ▼
    Final Results with Source Documents
```

---

## Directory Structure

```text
rag-knowledge/
├── backend/               # FastAPI backend (git submodule)
│   ├── app/
│   │   ├── api/routes/    # health, parse, search, graph
│   │   ├── services/      # mineru, vector, graph, keyword, embedding
│   │   └── main.py        # FastAPI entry
│   ├── config.yml         # MinerU configuration
│   └── pyproject.toml     # Python dependencies (uv)
├── web/                   # Nuxt 3 web frontend (git submodule)
│   ├── pages/             # Vue pages
│   ├── server/api/        # Nuxt server routes (backend proxy)
│   └── start.mjs          # config.yml-aware launcher
├── kb-mcp/                # MCP server (stdio)
│   ├── server.py          # MCP tool definitions
│   └── kb_client/         # HTTP client to backend
├── .claude/skills/        # Claude Code skills
│   ├── KNOWLEDGE-SYSTEM.md
│   ├── knowledge-store/
│   ├── knowledge-ingest/
│   ├── knowledge-search/
│   ├── knowledge-organize/
│   ├── knowledge-verify/
│   └── ...
├── scripts/               # Startup helpers
│   ├── start-backend.sh|bat
│   ├── start-web.sh|bat
│   └── test-*.py          # E2E / integration tests
├── storage/               # Runtime file storage
├── config.yml             # Shared platform config
├── .env                   # Shared environment variables
├── docker-compose.yml     # Neo4j container
├── start.sh               # One-command launcher (Linux/macOS)
└── start.bat              # One-command launcher (Windows)
```

---

## Quick Start

### Prerequisites

| Component                        | Version                    | Required For                  |
| -------------------------------- | -------------------------- | ----------------------------- |
| Python                           | 3.11 or 3.12               | Backend                       |
| [uv](https://docs.astral.sh/uv/) | latest                     | Backend dependency management |
| Node.js                          | >= 18 (LTS 22 recommended) | Web frontend                  |
| npm                              | bundled with Node.js       | Web frontend                  |
| Git                              | with submodule support     | Cloning                       |
| Docker / Docker Compose          | optional                   | Neo4j knowledge graph         |

### 1. Clone

```bash
git clone --recursive https://github.com/kingdol666/rag-knowledge.git
cd rag-knowledge
```

If you already cloned without `--recursive`:

```bash
git submodule update --init --recursive
```

### 2. Configure

```bash
# Environment variables
cp .env.example .env

# Shared platform config
cp config.yml.example config.yml
```

Edit `.env` if you need custom ports:

```env
APP_MODE=dev
BACKEND_PORT=8765
WEB_PORT=6789
```

Edit `config.yml` to enable/disable features:

```yaml
vector:
  enabled: true

graph:
  enabled: true
  password: "${NEO4J_PASSWORD}"
```

If you enable the graph, set the Neo4j password in `.env`:

```env
NEO4J_PASSWORD=changeme
```

### 3. Start Neo4j (optional, for knowledge graph)

```bash
docker compose up -d neo4j
```

Neo4j Browser: [http://localhost:7474](http://localhost:7474)
Bolt URI: `bolt://127.0.0.1:7687`

### 4. Start the Platform

**Windows:**

```bat
start.bat dev
```

**Linux / macOS:**

```bash
./start.sh dev
```

This launches two terminals:

- Backend: [http://localhost:8765](http://localhost:8765)
- Web: [http://localhost:6789](http://localhost:6789)

### 5. Verify

Open the web UI: [http://localhost:6789](http://localhost:6789)

Backend health: [http://localhost:8765/api/v1/health](http://localhost:8765/api/v1/health)

Backend docs: [http://localhost:8765/docs](http://localhost:8765/docs)

---

## Operation Workflow

### 1. Create a Knowledge Base

**Web UI:**

1. Go to **File System**.
2. Right-click in the tree and select **New Knowledge Base**.
3. Enter a name and description.

**MCP / Agent:**

```python
kb_create(name="Energy Reports", description="Thermal power plant technical reports.")
```

### 2. Upload and Parse a PDF

**Web UI:**

1. Select a KB folder.
2. Click **Upload File** or drag a PDF.
3. Right-click the uploaded file and select **Parse Document**.
4. Wait for the parsing task to complete.

**MCP / Agent:**

```python
parse_pdf_to_kb(
    file_path="/absolute/path/to/document.pdf",
    kb_id="<kb-uuid>",
    use_ocr=True,
    description="A report about turbine diagnostics.",
    tags=["turbine", "diagnostics"]
)
```

### 3. Build Vector & Graph Indexes

> Currently, parsing does **not** automatically build vector/graph indexes. This step is required to enable semantic and graph search.

**Via MCP:**

```python
kb_reindex(kb_id="<kb-uuid>", force=True)
```

**Via backend API:**

```bash
curl -X POST http://localhost:8765/api/v1/search/reindex \
  -H "Content-Type: application/json" \
  -d '{"kb_id": "<kb-uuid>", "force": true}'
```

### 4. Search

**Keyword search:**

```bash
curl "http://localhost:8765/api/v1/search/?query=turbine%20failure&top_k=10"
```

**Vector search:**

```bash
curl -X POST http://localhost:8765/api/v1/search/vector \
  -H "Content-Type: application/json" \
  -d '{"query": "what causes turbine vibration", "top_k": 5}'
```

**Two-stage search (recommended):**

```bash
curl -X POST http://localhost:8765/api/v1/search/two-stage \
  -H "Content-Type: application/json" \
  -d '{"query": "turbine vibration analysis", "top_k": 5}'
```

**Graph search:**

```bash
curl "http://localhost:8765/api/v1/graph/search?keyword=turbine&limit=20"
```

### 5. Query from an Agent

With the MCP server configured, an agent can ask natural-language questions:

```text
User: Search the knowledge base for documents about turbine vibration.
Agent: kb_search_two_stage(query="turbine vibration", top_k=5)
```

---

## Configuration

Configuration follows this priority:

```text
Environment variables > config.yml > internal defaults
```

Key files:

| File                 | Purpose                                             |
| -------------------- | --------------------------------------------------- |
| `.env`               | Ports, storage path, Neo4j password, timeouts       |
| `config.yml`         | Server ports, vector/graph settings, search weights |
| `backend/config.yml` | MinerU-specific settings                            |
| `.mcp.json`          | MCP server launch config for Claude Code            |

### Important Settings

```yaml
# config.yml
server:
  dev:
    backend_port: 8765
    frontend_port: 6789
    backend_url: "http://localhost:8765"

vector:
  enabled: true
  chunk_size: 500
  chunk_overlap: 50
  top_k: 5

embedding:
  model_name: "BAAI/bge-m3"
  device: "cpu"

graph:
  enabled: true
  uri: "bolt://127.0.0.1:7687"
  username: "neo4j"
  password: "${NEO4J_PASSWORD}"

search:
  two_stage:
    enabled: true
    stage1_keyword_weight: 0.5
    stage1_graph_weight: 0.5
    min_candidates: 3
```

---

## Design Philosophy

### 1. Local-First, File-Centric Storage

Documents are stored as plain Markdown files. Metadata lives in YAML. Indexes are derived, not primary. This makes the corpus portable, version-controllable, and repairable by hand if needed.

### 2. UUID Identity, Path as Location

Every knowledge base has a UUID v4 identity. Renaming or moving a KB changes its path, not its ID. This keeps external references stable.

### 3. Retrieval as a Pipeline, Not a Single Algorithm

No single retrieval method is perfect. The platform combines:

- **Keyword** for exact terminology.
- **Vector** for semantic similarity.
- **Graph** for relational context.
- **Two-stage** for complex queries.

Each signal is optional and degrades gracefully.

### 4. Agent-Native by Default

All operations are exposed as MCP tools. The web UI is one client; Claude Code (via skills) is another. The system is designed to be driven by agents as much as by humans.

### 5. Explicit Verification

Skills and batch operations emphasize "survey first, execute second, verify third." Health scorecards quantify collection quality over time.

---

## Troubleshooting

### Submodule missing

```bash
git submodule update --init --recursive
```

### Port already in use

The backend refuses to start if its port is occupied. Find and stop the process, or change `BACKEND_PORT`.

**Windows:**

```powershell
Get-NetTCPConnection -LocalPort 8765 -State Listen |
  ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```

**Linux / macOS:**

```bash
lsof -ti:8765 | xargs kill -9
```

### Embedding model downloads slowly

The first vector search triggers a download of `BAAI/bge-m3`. On first use this may take several minutes depending on network speed. A local cache is stored in `models_cache/`.

### Neo4j connection fails

If graph is enabled but Neo4j is not running, graph features return empty results without crashing the backend. Start Neo4j:

```bash
docker compose up -d neo4j
```

### Web shows "Backend unavailable"

Check that:

1. Backend is running on the port expected by `config.yml`.
2. `BACKEND_URL` in `.env` matches the backend port.
3. No firewall blocks localhost communication.

---

## Known Gaps & Roadmap

The following improvements are planned or in progress. See [DEVELOPMENT-PLAN.md](DEVELOPMENT-PLAN.md) for the full roadmap.

| Gap                                  | Status          | Impact                                                                                        |
| ------------------------------------ | --------------- | --------------------------------------------------------------------------------------------- |
| Auto-index after parse               | Not implemented | Vector/graph indexes must be built manually after upload via `kb_reindex`                     |
| Vector/graph UI in web frontend      | Not implemented | Web search page only calls keyword search; server routes exist but page UI not wired          |
| Skill layer uses vector/graph search | Implemented     | `knowledge-search` skill calls `kb_search_vector` / `kb_search_two_stage` with adaptive depth |
| Graph visualization page             | Not implemented | No `/graph` page; graph endpoints exist but no UI                                             |
| Source tracing UI                    | Partial         | Results show doc path but not chunk/score/fragment                                            |
| Tests for vector/graph               | Missing         | No automated coverage for new retrieval features                                              |
| Dual frontend modules                | Legacy          | `frontend/` submodule is outdated; `web/` is the active frontend                              |
| Semantic chunking                    | Not implemented | Fixed 500-char chunks break semantic boundaries                                               |

---

## License

MIT
