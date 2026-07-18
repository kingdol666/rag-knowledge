<h1 align="center">
  <img src="./docs/images/logo.svg" alt="RAG Knowledge Platform" width="96" />
  <br/>
  RAG Knowledge Platform
</h1>

<p align="center">
  <strong>Enterprise-Grade Document Intelligence & Agentic Knowledge Base</strong><br/>
  <em>PDF Parsing · QDCVR Semantic Search · Neo4j Knowledge Graph · Experience Library · MCP-Native (77 tools) · 13 Claude Code Skills · Silent Headless Startup</em>
</p>

<p align="center">
  <a href="#-quick-start"><img src="https://img.shields.io/badge/Quick%20Start-3%20steps-blue?style=for-the-badge" /></a>
  <a href="#-features"><img src="https://img.shields.io/badge/Features-8%20pillars-9cf?style=for-the-badge" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" /></a>
  <a href="#-platforms"><img src="https://img.shields.io/badge/Platform-Win%20%7C%20Linux%20%7C%20macOS-lightgrey?style=for-the-badge" /></a>
  <a href="#-mcp-tools"><img src="https://img.shields.io/badge/MCP-77%20tools-blueviolet?style=for-the-badge" /></a>
  <a href="#-skills"><img src="https://img.shields.io/badge/Skills-13-orange?style=for-the-badge" /></a>
  <a href="#-plugin"><img src="https://img.shields.io/badge/Install-Plugin-brightgreen?style=for-the-badge" /></a>
</p>

<p align="center">
  <sub><a href="./README.md"><b>English</b></a> · <a href="./README-zh.md">中文</a></sub>
</p>

---

<br>

<div align="center">
  <img src="./docs/images/rag-architecture.png" alt="RAG Knowledge Platform — 5-layer architecture: Claude Code → MCP → Nuxt proxy → FastAPI → MinerU OCR + Storage" width="960" />
</div>

<br>

---

## 📌 Table of Contents

- [🚀 Quick Start](#-quick-start)
- [✅ Prerequisites](#-prerequisites)
- [🌟 Features](#-features)
- [📦 Install](#-install) — Plugin · git clone · Tauri
- [🖥️ Usage](#️-usage) — 4 interfaces
- [📋 CLI Reference](#-cli-reference)
- [🔌 MCP Tools (77)](#-mcp-tools)
- [🎯 Skills (13)](#-skills)
- [🏗️ Architecture](#️-architecture)
- [⚙️ Configuration](#️-configuration)
- [🤫 Silent Operation](#-silent-operation)
- [🛠️ Troubleshooting](#️-troubleshooting)
- [❓ FAQ](#-faq)
- [📁 Project Structure](#-project-structure)
- [🔧 Tech Stack](#-tech-stack)
- [🤝 Contributing](#-contributing)

---

## 🚀 Quick Start

> **Two paths, same result. Pick whichever fits you.**

### Path A — Claude Code plugin (freshest)

```bash
# Install the plugin (one time)
claude plugin marketplace add kingdol666/rag-knowledge
claude plugin install rag-knowledge

# Then just say:
"初始化知识库"
# or: "set up the knowledge base"
```

The `knowledgebase-init` skill runs an **11-phase interactive wizard**: detects your platform, checks prerequisites, clones the repo, runs `ragctl setup` (installs everything), guides you through 12 config decisions, registers `ragctl` globally, and starts all services — **all guided, all silent**.

### Path B — git clone (classic)

```bash
git clone --recursive https://github.com/kingdol666/rag-knowledge.git
cd rag-knowledge

ragctl setup       # one-click: uv + deps + model + .env (5–30 min first time)
ragctl up          # silent start → http://localhost:6789
```

### ✅ Verify

```bash
ragctl status          # shows dev + prod side-by-side
ragctl logs backend    # view backend logs
```

> **Opening Claude Code inside the project** auto-loads all 13 skills + `kb-mcp` MCP server (the `.mcp.json` at project root handles it). No manual MCP config needed.

---

## ✅ Prerequisites

Only two tools are required upfront — `ragctl setup` installs everything else.

| Tool | Version | Required? | Notes |
|------|---------|-----------|-------|
| **Git** | any | ✅ Required | cloning + submodules |
| **Node.js** | ≥ 22 | ✅ Required | `ragctl` CLI + Nuxt frontend |
| **uv** | ≥ 0.7 | ⚡ Auto-installed | Python package manager — `ragctl setup` installs if missing |
| **Python** | 3.12 | ⚡ via uv | uv manages the Python env; no manual Python install needed |
| **Docker** | any | 📋 Optional | only for Neo4j graph. Parsing/search/experience work without it |
| **Rust** | stable | 📋 Optional | only to build the Tauri desktop app |

**Disk:** ~5 GB · **Network:** first run downloads BGE-M3 model (~2.2 GB) from HuggingFace. Default mirror is `hf-mirror.com` (fast inside China); set `HF_ENDPOINT=https://huggingface.co` outside China.

<details>
<summary><b>📦 What gets installed where</b></summary>

| Component | Location | Size |
|-----------|----------|------|
| uv | `~/.local/bin/uv` | ~15 MB |
| Backend venv | `backend/.venv/` | ~2 GB |
| kb-mcp venv | `kb-mcp/.venv/` | ~50 MB |
| Web deps | `web/node_modules/` | ~500 MB |
| CLI deps | `command/node_modules/` | ~5 MB |
| BGE-M3 model | `~/.cache/huggingface/` | ~2.2 GB |
| Neo4j (optional) | Docker volume | ~600 MB |

All paths configurable. Nothing touches system-wide Python or Node.
</details>

---

## 🌟 Features

<p align="center">
  <img src="./docs/images/rag-pipeline.png" alt="QDCVR Agentic-First Enterprise Retrieval Pipeline" width="960" />
</p>

| Pillar | What you get |
|--------|-------------|
| 📄 **Document parsing** | PDF / Word / Excel / PPT / images → Markdown via MinerU OCR engine |
| 🧠 **QDCVR retrieval** | Query-Driven, Content-Verified Retrieval — independent 0–8 content scoring. *Vectors are fast. Content is accurate.* |
| 🔍 **Multi-strategy search** | BM25 + vector two-stage recall · cross-KB enterprise search · tag semantic + graph expansion |
| 📊 **Knowledge graph** | Neo4j-powered entity/relation graph · cross-KB document bridges · centrality discovery · path queries |
| 💡 **Experience library** | E0–E12 full lifecycle · structured problem→solution→lessons · P0/P1/P2 credibility tiers · stale detection · decay cycles |
| 🔌 **77 MCP tools** | KB CRUD · search · graph · experience · parsing · service lifecycle · all MCP-native |
| 🎯 **13 Claude Code skills** | natural-language commands · bilingual triggers · auto-dispatch to Archival agent · self-contained for global plugin |
| 🤫 **Silent headless** | every launcher (`ragctl`, `start.bat/.sh`, Tauri) runs with **zero terminal windows** — dev and prod behave identically |

<a id="-platforms"></a>

---

## 📦 Install

### Primary: Claude Code plugin

```bash
claude plugin marketplace add kingdol666/rag-knowledge
claude plugin install rag-knowledge
```

Then say: **"初始化知识库"** / **"set up the knowledge base"**

The skill auto-registers `ragctl` globally (`ragctl install` → `~/.local/bin`) and `kb-mcp` globally (`~/.claude/.mcp.json` with `RAG_PROJECT_ROOT`). After setup the platform works **from any directory, any Claude Code session** — 13 skills + 77 MCP tools + `ragctl` CLI.

<details>
<summary><b>Alternative: git clone + manual</b></summary>

```bash
git clone --recursive https://github.com/kingdol666/rag-knowledge.git
cd rag-knowledge

# One-click (recommended)
ragctl setup

# Or step-by-step
git submodule update --init --recursive
cd backend && uv sync && cd ..
cd kb-mcp  && uv sync && cd ..
cd web && npm install && cd ..
cp .env.example .env
ragctl model   # pre-download BGE-M3 (optional — auto-downloads on first index)
ragctl up
```
</details>

<details>
<summary><b>Tauri desktop console</b></summary>

```bash
# Build once
cd src-tauri && cargo tauri build

# Launch either way:
ragctl desktop          # launches the built binary
cargo tauri dev         # dev mode with hot-reload
```

The desktop console provides visual start/stop, dependency install, real-time logs, and a config editor — all sharing the same log files as `ragctl`.
</details>

---

## 🖥️ Usage

Four interfaces, one backend. Pick whichever fits your workflow.

### 1. Claude Code (natural language)

After `claude plugin install`, just describe what you want:

```
"ingest every PDF in ./papers into a new 'ML-research' KB"
  → knowledgebase-ingest (A0→A9 quality gates)

"search: what are the PET biaxial stretching process parameters?"
  → QDCVR → content-verified answer with sources + confidence

"记录这个排查经验" / "save this troubleshooting as an experience"
  → knowledgebase-experience-summarize → structured lesson
```

If services aren't running, the **Archival agent silently starts them** via `kb_project_start` — no terminals, no manual steps.

### 2. CLI (`ragctl`)

```bash
ragctl up                     # start all (silent, dev mode)
ragctl up --appmode prod      # prod ports (8001/3000)
ragctl up --force             # force restart
ragctl status                 # dual-mode: dev + prod side-by-side
ragctl logs web --tail        # live-follow web logs
ragctl restart backend -f     # force-restart one service
ragctl down --appmode prod    # stop prod only (shared Neo4j kept)
```

#### Flags (`--` secondary params)

| Flag | Alias | Purpose |
|------|-------|---------|
| `--appmode dev\|prod` | `--mode`, `-m` | Select port group |
| `--port-backend N` | `--backend-port` | Override backend port |
| `--port-web N` | `--web-port` | Override web port |
| `--no-neo4j` / `--no-backend` / `--no-web` | — | Skip a service |
| `--only SERVICE` | — | Operate on one service |
| `--force` | `-f` | Force stop-then-start |
| `--tail` | — | Live-follow logs |

### 3. MCP client (any agent)

```python
kb_project_start(backend=True, web=True, wait=True)   # silent start
kb_search_two_stage(query="reinforcement learning", balance_kbs=True)
experience_search_global(query="ConnectError troubleshooting")
kb_graph_cross_kb_documents(min_kbs=2)
```

### 4. Web UI

Open `http://localhost:6789` — browse KBs, search documents, explore the graph, chat with Claude via the Agent SDK.

---

## 📋 CLI Reference

| Command | Description |
|---------|-------------|
| `ragctl setup` · `init` | One-click full deployment |
| `ragctl check` | Full environment audit with fix hints |
| `ragctl up` / `down` | Start / stop all services (silent, no terminals) |
| `ragctl up --appmode prod` | Start on prod ports (8001 / 3000) |
| `ragctl up --force` / `--no-neo4j` | Force restart / skip Neo4j |
| `ragctl start` / `stop` / `restart` [svc] | Per-service lifecycle (`backend`\|`web`\|`neo4j`\|`all`) |
| `ragctl restart [svc] -f` | Force-restart one service |
| `ragctl status [--appmode X]` | Dual-mode status: ports + HTTP health + PIDs + MinerU |
| `ragctl logs [svc] [--tail] [--lines N]` | View / live-tail logs |
| `ragctl deps` | Install all dependencies (real-time progress) |
| `ragctl model` | Pre-download BGE-M3 embedding model (~2.2 GB) |
| `ragctl install` | Register `ragctl` globally → `~/.local/bin` |
| `ragctl desktop` · `ui` | Launch Tauri desktop console |
| `ragctl help` | All commands + flags |

<a id="-mcp-tools"></a>

## 🔌 MCP Tools (77)

All accessible via `mcp__kb-mcp__*` from Claude Code or any MCP client.

| Category | Count | Key tools |
|----------|-------|-----------|
| **Service life cycle** | 4 | `kb_project_start`, `kb_project_status`, `kb_project_preflight`, `backend_status` |
| **KB CRUD** | 7 | `kb_list`, `kb_create`, `kb_update`, `kb_delete`, `kb_catalog`, `kb_doc_catalog`, `kb_get_documents` |
| **Document CRUD** | 7 | `kb_doc_read`, `kb_doc_create`, `kb_doc_update_meta`, `kb_doc_update_content`, `kb_doc_delete`, `kb_doc_batch_delete`, `kb_doc_move` |
| **File System** | 4 | `fs_get_tree`, `fs_get_children`, `fs_get_count`, `fs_upload_file` |
| **Parse** | 4 | `parse_doc`, `parse_doc_batch`, `parse_task_status`, `kb_doc_save_parsed` |
| **Tags** | 4 | `kb_tags_list`, `kb_doc_update_tags`, `kb_doc_get_by_tag`, `kb_tags_cleanup` |
| **Search** | 4 | `kb_search`, `kb_search_vector`, `kb_search_two_stage`, `kb_search_stats` |
| **Vector/Index** | 4 | `kb_index_document`, `kb_batch_index`, `kb_reindex`, `kb_cleanup_orphan_collections` |
| **Knowledge Graph** | 18 | `kb_graph_search`, `kb_graph_kb_overview`, `kb_graph_build_kb`, `kb_graph_cross_kb_documents`, … |
| **Experience** | 21 | `experience_create`, `experience_search_global`, `experience_dashboard`, `experience_extract`, … |

<a id="-skills"></a>

## 🎯 Skills (13)

| Skill | Flow | Purpose |
|-------|------|---------|
| **knowledgebase** | Router | Dispatch user intent to the correct sub-skill |
| **knowledgebase-init** | Phase 0→11 | Guided fresh-install wizard (main agent, no Archival) |
| **knowledgebase-ingest** | A0→A9 | Document ingestion with quality gates |
| **knowledgebase-search** | Step 0–6 | QDCVR retrieval with content verification |
| **knowledgebase-search-enterprise** | Phase 0–5 | Multi-strategy cross-KB search |
| **knowledgebase-manage** | M1→M6 | Document and KB administration |
| **knowledgebase-organize** | O0→O13 | Full collection restructuring |
| **knowledgebase-verify** | V1→V9 | Integrity and quality validation |
| **knowledgebase-list** | L1→L3 | Read-only browsing |
| **knowledgebase-graph** | — | Neo4j graph build, query, analysis |
| **knowledgebase-experience** | E0→E12 | Experience lifecycle management |
| **knowledgebase-experience-summarize** | S1→S5 | Distill and persist structured experiences |
| **knowledgebase-batch** | B1→B7 | High-volume batch operations |

> All skills are **self-contained** — reference files live in `knowledgebase/references/` and work with global plugin installs. 12 skills delegate to the Archival agent; `init` runs on the main agent.

---

## 🏗️ Architecture

```
Browser / Claude Code / MCP Client
        │
        ▼
┌──────────────────┐
│  Nuxt 3 Web UI   │  port 6789 (dev) / 3000 (prod)
│  (proxy layer)   │
└────────┬─────────┘
         │  server-to-server
         ▼
┌──────────────────┐
│  FastAPI Backend  │  port 8765 (dev) / 8001 (prod)
│  + MinerU OCR     │  ephemeral port
└────────┬─────────┘
         │  file read
         ▼
┌──────────────────┐
│  Tree FS + YAML   │  .tree-fs.json + .knowledge-base.yml
│  + ChromaDB       │  vector embeddings (BGE-M3, 1024-dim)
│  + Neo4j          │  knowledge graph (bolt://127.0.0.1:7687)
└──────────────────┘
```

**Principle:** writes → HTTP API (backend/web proxy). reads → direct file access (`.tree-fs.json` + `.knowledge-base.yml`).

---

## ⚙️ Configuration

**`config.yml`** (repo root) is the **single source of truth for ports**. **`.env`** overrides and is created by `ragctl setup`.

| Variable | Default (dev / prod) | Purpose |
|----------|----------------------|---------|
| `APP_MODE` | `dev` | Selects config.yml section |
| `BACKEND_PORT` | `8765` / `8001` | FastAPI port |
| `WEB_PORT` | `6789` / `3000` | Nuxt web port |
| `BACKEND_URL` | derived | Full backend URL |
| `HF_ENDPOINT` | `https://hf-mirror.com` | Model download mirror |
| `TREE_STORAGE_PATH` | `web/storage/tree-file-system` | KB data on disk |
| `NEO4J_PASSWORD` | (from docker-compose) | Graph DB auth |

Switch modes without editing `.env`:

```bash
ragctl up --appmode prod
ragctl status               # shows both dev + prod
ragctl down --appmode prod  # stops only prod (Neo4j stays)
```

---

## 🤫 Silent Operation

All launchers start services with **zero terminal windows** in both dev and prod:

| Surface | Command |
|---------|---------|
| CLI viewer | `ragctl logs backend` / `ragctl logs web` / `ragctl logs mineru` |
| Live tail | `ragctl logs backend --tail` (Ctrl+C to exit) |
| Lines | `ragctl logs backend --lines 200` / `-n 200` |
| Tauri desktop | Real-time log stream (same files) |

```bash
ragctl logs backend       # last 80 lines
ragctl logs web --tail    # live follow
ragctl logs mineru -n 200 # 200 lines of OCR output
```

---

## 🛠️ Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| MCP not connecting | `uv` not on PATH (fresh terminal) | `ragctl setup` installs uv; reopen terminal |
| Backend won't start | deps not installed | `ragctl setup` (or `cd backend && uv sync`) |
| Web won't start | `node_modules` missing | `ragctl setup` (or `cd web && npm install`) |
| `backend/` or `web/` is empty | submodules not initialized | `git submodule update --init --recursive` |
| Graph queries fail | Neo4j not running | `ragctl start neo4j` (requires Docker) |
| BGE model download slow | network to HuggingFace | set `HF_ENDPOINT=https://huggingface.co` |
| Port already in use | previous service still running | `ragctl down` then `ragctl up` |

---

## ❓ FAQ

**Does it really open no terminal windows?** Yes. Verified: `windowsHide` + detached binary spawn (no `cmd.exe` wrapper) on Windows; `start_new_session` on POSIX.

**Dev or prod?** Dev: `8765` / `6789`. Prod: `8001` / `3000`. Switch with `--appmode prod`. Both fully silent.

**Where is my data?** All local — `web/storage/tree-file-system/` (KB files) + Neo4j (graph) + ChromaDB (vectors). No cloud, no telemetry.

**Do I need Docker?** Only for Neo4j. Parsing, search, and experience all work without it.

**Can I use this without Claude Code?** Yes. The Web UI at `http://localhost:6789` is fully functional, and any MCP client can call the 77 tools.

---

## 📁 Project Structure

```
rag-knowledge/
├── backend/              ← [submodule] FastAPI + MinerU OCR
├── web/                  ← [submodule] Nuxt 3 + Ant Design Vue
├── kb-mcp/               ← MCP server — 77 tools
├── command/              ← ragctl CLI (Node.js)
├── src-tauri/            ← Tauri desktop app (Rust)
├── .claude/              ← Skills (13) + Archival agent
├── .claude-plugin/       ← Plugin marketplace manifests
├── .mcp.json             ← kb-mcp auto-connect
├── config.yml            ← Central configuration
├── docker-compose.yml    ← Neo4j container
├── ragctl / ragctl.bat   ← CLI entry (Linux·macOS / Windows)
├── start.bat / start.sh  ← Silent launchers
└── README.md
```

---

## 🔧 Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.12 · FastAPI · MinerU OCR · ChromaDB |
| Frontend | TypeScript · Nuxt 3 · Ant Design Vue |
| MCP Server | Python · FastMCP · httpx |
| CLI | Node.js · js-yaml |
| Desktop | Rust · Tauri v2 |
| Graph | Neo4j (Docker) |
| Embedding | BGE-M3 (1024-dim) · sentence-transformers |
| Search | BM25 + Vector two-stage · QDCVR pipeline |

---

## 🤝 Contributing

1. Fork → feature branch → commit → push → PR
2. `ragctl check` should pass before submitting
3. Cross-platform: test on Win + Linux (or macOS) if touching startup/scripts

---

## 📄 License

MIT © [kingdol](https://github.com/kingdol666)
