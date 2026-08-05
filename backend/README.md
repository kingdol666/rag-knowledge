<h1 align="center">
  <img src="../docs/images/logo.svg" alt="RAG Knowledge Backend" width="80" />
  <br/>
  RAG Knowledge Backend
</h1>

<p align="center">
  <strong>FastAPI Backend · MinerU OCR Engine · Vector Search · Knowledge Graph</strong><br/>
  <em>The document intelligence engine powering the RAG Knowledge Platform</em>
</p>

<p align="center">
  <a href="#-quick-start"><img src="https://img.shields.io/badge/Quick%20Start-3%20steps-blue?style=for-the-badge" /></a>
  <a href="#-api-reference"><img src="https://img.shields.io/badge/API-112%20endpoints-009688?style=for-the-badge" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" /></a>
  <a href="#-cross-platform"><img src="https://img.shields.io/badge/platform-Win%20%7C%20Linux%20%7C%20macOS-lightgrey?style=for-the-badge" /></a>
  <a href="#-tech-stack"><img src="https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge" /></a>
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
- [📡 API Reference](#-api-reference)
- [⚙️ Configuration](#️-configuration)
- [🧪 Testing](#-testing)
- [📁 Project Structure](#-project-structure)
- [🌍 Cross-Platform](#-cross-platform)
- [🔧 Tech Stack](#-tech-stack)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)

## 🌟 Overview

The backend is the computational core of the RAG Knowledge Platform. It provides:

- **📄 PDF Parsing** — MinerU OCR engine converts PDF/Word/Excel/PPT/images → Markdown. Async submission, batch SSE streaming, offline model auto-download.
- **🔍 Vector Search** — ChromaDB-powered semantic search with BGE-M3 embeddings (1024-dim). Two-stage BM25 + vector retrieval.
- **🕸️ Knowledge Graph** — Neo4j-powered entity extraction, cross-document relationship mining, centrality analysis. NER via transformers pipeline.
- **💡 Experience Engine** — Structured lesson extraction (heuristic + LLM-refined), credibility scoring, decay cycles, draft approval pipeline.
- **⚙️ Configuration API** — Runtime config read/write with schema validation and hot-reload.

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────┐
│                   main.py                         │
│          Port probe → uvicorn launch              │
└──────────────────┬───────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────┐
│            app/main.py                            │
│     FastAPI app factory + lifespan mgr            │
│                                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │ /health  │ │ /parse   │ │ /mineru  │          │
│  │  GET     │ │  POST    │ │  GET/POST│          │
│  └──────────┘ └────┬─────┘ └────┬─────┘          │
│                    │             │                │
│  ┌──────────┐ ┌────▼─────┐ ┌───▼──────┐          │
│  │ /config  │ │ /search  │ │ /graph   │          │
│  │  GET/POST│ │  POST    │ │  POST    │          │
│  └──────────┘ └──────────┘ └──────────┘          │
│                                                   │
│  ┌──────────┐ ┌──────────────────┐                │
│  │/experience│ │MineruApiManager  │                │
│  │  POST    │ │(subprocess mgmt) │                │
│  └──────────┘ └────────┬─────────┘                │
└─────────────────────────┼─────────────────────────┘
                          │ subprocess (Job Object)
┌─────────────────────────▼─────────────────────────┐
│              MinerU OCR Engine                     │
│          Ephemeral port · stdout → file            │
│          Hidden window · Kill-on-close             │
└───────────────────────────────────────────────────┘
```

**Key design decisions:**

| Decision | Rationale |
|----------|-----------|
| MinerU as a subprocess | Isolated lifecycle; crash doesn't take down the API |
| Ephemeral port (`port=None`) | No port conflicts; auto-avoids common dev ports |
| stdout → file (never a pipe) | Eliminates `[Errno 22]` pipe-closure crashes |
| Job Object (Win) / `prctl` (Linux) | Guaranteed cleanup when parent dies |
| `trust_env=False` on all httpx | Prevents `HTTPS_PROXY` from hijacking localhost |

## 🚀 Quick Start

```bash
# 1. Install dependencies
uv sync

# 2. Run (dev mode — hot reload)
APP_MODE=dev uv run python main.py
# → http://localhost:8765

# 3. Verify
curl http://localhost:8765/api/v1/health
```

```bash
# Production mode (no reload)
APP_MODE=prod uv run python main.py
# → http://localhost:8001

# Custom port
BACKEND_PORT=9000 APP_MODE=dev uv run python main.py
```

> **Prerequisites:** Python 3.12, `uv`. The first parse auto-downloads MinerU models (~2 GB). Use `HF_ENDPOINT=https://hf-mirror.com` (default) for faster downloads in China.

## 📡 API Reference

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/health` | Backend health + MinerU status + version info |

### Parse

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/parse/file/vt` | Async parse a single file (async) |
| `POST` | `/api/v1/parse/file/vt/legacy` | Legacy parse endpoint |
| `POST` | `/api/v1/batch/parse/file/vt/stream` | Batch parse with SSE streaming progress |
| `POST` | `/api/v1/batch/parse/file/vt` | Batch parse with JSON response |

### MinerU

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/mineru/status` | MinerU engine status |
| `POST` | `/api/v1/mineru/restart` | Force-restart the MinerU subprocess |

### Search

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/search/debug-paths` | Debug path resolution (dev-mode only) |
| `POST` | `/api/v1/search/vector` | Semantic vector search (BGE-M3) |
| `POST` | `/api/v1/search/batch-vector` | Batch vector search |
| `POST` | `/api/v1/search/two-stage` | Two-stage: BM25 → vector rerank |
| `POST` | `/api/v1/search/index-document` | Index single document |
| `POST` | `/api/v1/search/batch-index` | Batch index documents |
| `POST` | `/api/v1/search/reindex` | Rebuild vector index |
| `GET` | `/api/v1/search/stats` | Search index statistics |
| `DELETE` | `/api/v1/search/kb/{kb_id}` | Delete KB search data |
| `DELETE` | `/api/v1/search/document` | Delete document from index |

### Graph

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/graph/health` | Graph database health |
| `GET` | `/api/v1/graph/stats` | Graph statistics |
| `GET` | `/api/v1/graph/search/documents` | Search graph by keyword |
| `GET` | `/api/v1/graph/search/kbs` | Search KBs in graph |
| `GET` | `/api/v1/graph/search/tags` | Search tags in graph |
| `GET` | `/api/v1/graph/document` | Document-centric graph |
| `GET` | `/api/v1/graph/document/related` | Related documents |
| `GET` | `/api/v1/graph/document/enhanced` | Enhanced document graph |
| `GET` | `/api/v1/graph/documents-by-tag` | Documents by tag |
| `GET` | `/api/v1/graph/kb-overview` | KB-level graph overview |
| `GET` | `/api/v1/graph/neighbors` | Neighborhood exploration |
| `GET` | `/api/v1/graph/cross-kb-documents` | Cross-KB bridge documents |
| `GET` | `/api/v1/graph/document-paths` | Path between two documents |
| `GET` | `/api/v1/graph/central-documents` | Centrality-ranked documents |
| `POST` | `/api/v1/graph/build-kb` | Build graph for a KB |
| `POST` | `/api/v1/graph/build-all` | Build graphs for all KBs |
| `POST` | `/api/v1/graph/agent-relation` | Agent-driven relation |
| `POST` | `/api/v1/graph/agent-relations/batch` | Batch agent relations |
| `DELETE` | `/api/v1/graph/document` | Delete document from graph |
| `DELETE` | `/api/v1/graph/kb/{kb_id}` | Delete KB from graph |

### Experience (23)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/experience/global-search` | Global Search Experiences |
| `POST` | `/api/v1/experience/stale-global` | Check Stale Global |
| `POST` | `/api/v1/experience/{kb_id}` | Create Experience |
| `GET` | `/api/v1/experience/{kb_id}` | List Experiences |
| `GET` | `/api/v1/experience/{kb_id}/dashboard` | Dashboard |
| `POST` | `/api/v1/experience/{kb_id}/decay` | Apply Decay |
| `GET` | `/api/v1/experience/{kb_id}/drafts` | List Drafts |
| `GET` | `/api/v1/experience/{kb_id}/drafts/{draft_id}` | Read Draft |
| `POST` | `/api/v1/experience/{kb_id}/drafts/{draft_id}/approve` | Approve Draft |
| `POST` | `/api/v1/experience/{kb_id}/drafts/{draft_id}/reject` | Reject Draft |
| `POST` | `/api/v1/experience/{kb_id}/extract` | Extract Experiences |
| `POST` | `/api/v1/experience/{kb_id}/init` | Init Experience |
| `POST` | `/api/v1/experience/{kb_id}/reindex` | Reindex Experiences |
| `POST` | `/api/v1/experience/{kb_id}/search` | Search Experiences |
| `GET` | `/api/v1/experience/{kb_id}/stale` | Check Stale |
| `GET` | `/api/v1/experience/{kb_id}/summary` | Experience Summary |
| `POST` | `/api/v1/experience/{kb_id}/sync` | Sync Kb |
| `POST` | `/api/v1/experience/{kb_id}/vector-search` | Vector Search Experiences |
| `GET` | `/api/v1/experience/{kb_id}/{exp_id}` | Read Experience |
| `PUT` | `/api/v1/experience/{kb_id}/{exp_id}` | Update Experience |
| `DELETE` | `/api/v1/experience/{kb_id}/{exp_id}` | Delete Experience |
| `POST` | `/api/v1/experience/{kb_id}/{exp_id}/apply` | Apply Experience |
| `POST` | `/api/v1/experience/{kb_id}/{exp_id}/review` | Review Experience |

### Meditation (10)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/meditation/config` | Meditation Config |
| `PUT` | `/api/v1/meditation/config` | Meditation Config Update |
| `POST` | `/api/v1/meditation/feedback` | Meditation Feedback |
| `GET` | `/api/v1/meditation/harness-status` | Harness Status |
| `GET` | `/api/v1/meditation/history` | Meditation History |
| `GET` | `/api/v1/meditation/history/{run_id}` | Meditation Run Detail |
| `GET` | `/api/v1/meditation/models` | Meditation Models |
| `POST` | `/api/v1/meditation/run` | Meditation Run |
| `GET` | `/api/v1/meditation/signals` | Meditation Signals |
| `GET` | `/api/v1/meditation/status` | Meditation Status |

### SOUL (35)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/soul/ask` | Soul Ask |
| `POST` | `/api/v1/soul/bootstrap` | Soul Bootstrap |
| `POST` | `/api/v1/soul/distill` | Distill Persona |
| `POST` | `/api/v1/soul/distill-files` | Distill Files |
| `POST` | `/api/v1/soul/init` | Soul Init |
| `POST` | `/api/v1/soul/learn-all` | Learn All Global |
| `GET` | `/api/v1/soul/list` | Soul List |
| `POST` | `/api/v1/soul/qdcvr-ask` | Soul Qdcvr Ask |
| `POST` | `/api/v1/soul/router` | Router Route |
| `GET` | `/api/v1/soul/router/status` | Router Status |
| `GET` | `/api/v1/soul/settings` | Soul Settings |
| `GET` | `/api/v1/soul/tasks` | List Tasks |
| `GET` | `/api/v1/soul/tasks/{task_id}` | Task Status |
| `POST` | `/api/v1/soul/tasks/{task_id}/pause` | Pause Task |
| `POST` | `/api/v1/soul/tasks/{task_id}/resume` | Resume Task |
| `GET` | `/api/v1/soul/training/history` | Training History |
| `GET` | `/api/v1/soul/training/runs/{run_id}` | Training Run Detail |
| `DELETE` | `/api/v1/soul/{soul_kb_id}` | Soul Delete |
| `POST` | `/api/v1/soul/{soul_kb_id}/calibrate` | Calibrate |
| `POST` | `/api/v1/soul/{soul_kb_id}/checkpoint` | Checkpoint |
| `POST` | `/api/v1/soul/{soul_kb_id}/cognition-drafts` | Gen Cognition Drafts |
| `PUT` | `/api/v1/soul/{soul_kb_id}/config` | Soul Config Update |
| `POST` | `/api/v1/soul/{soul_kb_id}/eval` | Eval Answer |
| `POST` | `/api/v1/soul/{soul_kb_id}/evaluate` | Evaluate |
| `POST` | `/api/v1/soul/{soul_kb_id}/export` | Export Training |
| `GET` | `/api/v1/soul/{soul_kb_id}/folder` | Soul Folder |
| `POST` | `/api/v1/soul/{soul_kb_id}/learn` | Learn |
| `POST` | `/api/v1/soul/{soul_kb_id}/learn-all` | Learn All |
| `GET` | `/api/v1/soul/{soul_kb_id}/persona-docs` | Persona Docs |
| `POST` | `/api/v1/soul/{soul_kb_id}/reflect` | Reflect |
| `POST` | `/api/v1/soul/{soul_kb_id}/review-drafts` | Review Drafts |
| `GET` | `/api/v1/soul/{soul_kb_id}/reward-history` | Reward History |
| `POST` | `/api/v1/soul/{soul_kb_id}/rollback` | Rollback |
| `GET` | `/api/v1/soul/{soul_kb_id}/status` | Status |
| `POST` | `/api/v1/soul/{soul_kb_id}/train-rl` | Train Rl |

### System (2)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/system/clean` | Clean Caches |
| `GET` | `/api/v1/system/clean/mineru-entries` | List Mineru Entries |

### Configuration

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/config` | Read current runtime config |
| `PUT` | `/api/v1/config` | Update configuration |
| `GET` | `/api/v1/config/schema` | Config JSON Schema |
| `POST` | `/api/v1/config/reload` | Hot-reload configuration |

## ⚙️ Configuration

`backend/config.yml` — backend-specific settings:

```yaml
mineru:
  enabled: true             # Enable MinerU OCR engine
  host: "127.0.0.1"        # MinerU bind address
  model_source: "modelscope"  # or "huggingface"
```

Ports and mode are read from the **root `config.yml`** (single source of truth). Override with env vars:

| Variable | Default (dev / prod) | Purpose |
|----------|----------------------|---------|
| `APP_MODE` | `dev` | Selects dev or prod section from root config.yml |
| `BACKEND_PORT` | `8765` / `8001` | Override the backend listen port |
| `HF_ENDPOINT` | `https://hf-mirror.com` | HuggingFace model download mirror |
| `NEO4J_PASSWORD` | (from docker-compose) | Neo4j authentication |

## 🧪 Testing

```bash
# Fast unit tests (skips MinerU — no engine needed)
uv run pytest
# → ~50 hermetic tests, <10 seconds

# With MinerU integration
uv run pytest --run-integration
# → full parse pipeline, needs running MinerU

# Single test
uv run pytest tests/test_unit.py -x -k "test_health_check"

# Coverage
uv run pytest --cov=app --cov-report=html
```

**Test structure:**
- `test_unit.py` — Hermetic: health, config, schemas, path resolution.
- `test_parse_async.py` — Integration: full parse flow with live MinerU.
- `conftest.py` — Skips integration tests by default (add `--run-integration` to include).

## 📁 Project Structure

```
backend/
├── main.py                    # Entry point: port probe → uvicorn
├── app/
│   ├── main.py                # FastAPI app factory + lifespan (starts MinerU)
│   ├── config.py              # Singleton config reader (root + backend configs)
│   ├── api/routes/
│   │   ├── __init__.py        # Router registration
│   │   ├── health.py          # GET /api/v1/health
│   │   ├── parse.py           # POST /api/v1/parse/* (async + batch SSE)
│   │   ├── mineru.py          # GET/POST /api/v1/mineru/*
│   │   ├── search.py          # POST /api/v1/search/* (keyword + vector + two-stage)
│   │   ├── graph.py           # POST /api/v1/graph/* (build + search)
│   │   ├── experience.py      # POST /api/v1/experience/* (extract + dashboard)
│   │   ├── config.py          # GET/POST /api/v1/config
│   │   └── config_schema.py   # JSON Schema for config validation
│   ├── models/
│   │   └── schemas.py         # Pydantic request/response models
│   ├── services/
│   │   └── mineru_service.py  # MineruParseService wrapper
│   └── utils/
│       ├── paths.py           # PROJECT_ROOT, config path resolution
│       └── mineru_manager.py  # MineruApiManager: subprocess lifecycle + task polling
├── tests/
│   ├── conftest.py            # Pytest fixtures + integration skip logic
│   ├── test_unit.py           # Hermetic unit tests
│   └── test_parse_async.py    # Integration tests (needs running MinerU)
├── pyproject.toml             # uv project config + PyTorch CUDA sources
└── config.yml                 # Backend-specific config (MinerU settings)
```

## 🌍 Cross-Platform

First-class support for all three platforms with platform-specific subprocess lifecycle:

| Platform | MinerU cleanup | stdout handling | GPU support |
|----------|---------------|-----------------|-------------|
| **Windows** | Job Object (`KILL_ON_JOB_CLOSE`) | File (no pipe) | CUDA (cu130) |
| **Linux** | `prctl(PR_SET_PDEATHSIG)` | File (no pipe) | CUDA (cu130 x86_64) |
| **macOS** | Process group + atexit | File (no pipe) | MPS / CPU fallback |

`pyproject.toml` uses **marker-based conditional sources**: Windows + Linux x86_64 pull CUDA wheels from PyTorch's cu130 index; macOS and Linux aarch64 gracefully fall back to PyPI (CPU/MPS). `required-environments` allows all three, so `uv sync` works everywhere.

## 🔧 Tech Stack

| Component | Technology |
|-----------|-----------|
| Framework | Python 3.12 · FastAPI · Uvicorn |
| PDF Parsing | MinerU OCR (≥3.4.2) |
| Vector DB | ChromaDB |
| Embeddings | BGE-M3 (1024-dim) · sentence-transformers |
| Keyword Search | jieba · BM25 |
| Knowledge Graph | Neo4j (≥6.2.0) · transformers NER |
| Validation | Pydantic · JSON Schema |
| Package Manager | uv (hatchling build) |
| ML Runtime | PyTorch 2.12.1 + CUDA 13.0 / MPS / CPU |

## 🤝 Contributing

1. Fork → feature branch → commit → push → PR
2. Run `uv run pytest` before submitting — all unit tests must pass
3. If you touch MinerU lifecycle code, test with `--run-integration`
4. Cross-platform: test on your platform; CI covers the other two

## 📄 License

MIT © [kingdol](https://github.com/kingdol666) · Part of the [RAG Knowledge Platform](https://github.com/kingdol666/rag-knowledge)

---

<div align="center">

<sub>Part of</sub>
<a href="https://github.com/kingdol666/rag-knowledge"><b>RAG Knowledge Platform</b></a>
<br>
⭐ <a href="https://github.com/kingdol666/rag-knowledge">Star us on GitHub</a> ⭐

</div>
