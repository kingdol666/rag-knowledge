<h1 align="center">
  <img src="./docs/images/logo.svg" alt="RAG Knowledge Platform" width="96" />
  <br/>
  RAG Knowledge Platform
</h1>

<p align="center">
  <strong>Enterprise-Grade Document Intelligence & Agentic Knowledge Base</strong><br/>
  <em>PDF Parsing · QDCVR Semantic Search · Neo4j Knowledge Graph · Experience Library · MCP-Native (76 tools) · 14 Claude Code Skills · Silent Headless Startup</em>
</p>

<p align="center">
  <a href="#-quick-start"><img src="https://img.shields.io/badge/Quick%20Start-3%20steps-blue?style=for-the-badge&logo=rocket" /></a>
  <a href="https://github.com/kingdol666/rag-knowledge/stargazers"><img src="https://img.shields.io/github/stars/kingdol666/rag-knowledge?style=for-the-badge&color=yellow" /></a>
  <a href="#-features"><img src="https://img.shields.io/badge/Features-8%20pillars-9cf?style=for-the-badge" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" /></a>
  <a href="https://github.com/kingdol666/rag-knowledge/releases"><img src="https://img.shields.io/github/v/release/kingdol666/rag-knowledge?style=for-the-badge&color=blueviolet" /></a>
  <a href="#-platforms"><img src="https://img.shields.io/badge/Platform-Win%20%7C%20Linux%20%7C%20macOS-lightgrey?style=for-the-badge" /></a>
  <a href="#-mcp-tools"><img src="https://img.shields.io/badge/MCP-76%20tools-blueviolet?style=for-the-badge&logo=code" /></a>
  <a href="#-skills"><img src="https://img.shields.io/badge/Skills-14-orange?style=for-the-badge&logo=openai" /></a>
  <a href="#-plugin"><img src="https://img.shields.io/badge/Install-Plugin-brightgreen?style=for-the-badge&logo=claude" /></a>
</p>

<p align="center">
  <sub><a href="./README.md"><b>English</b></a> · <a href="./README-zh.md">中文</a></sub>
</p>

---

<br>

<div align="center">
  <img src="./docs/images/rag-architecture.png" alt="RAG Knowledge Platform — 5-layer architecture" width="960" />
</div>

<br>

---

## 📌 Table of Contents

- [🚀 Quick Start](#-quick-start)
- [✅ Prerequisites](#-prerequisites)
- [💡 Why This Project](#-why-this-project)
- [🌟 Features](#-features)
- [📦 Install](#-install)
- [🖥️ Usage](#️-usage)
- [📋 CLI Reference](#-cli-reference)
- [🔌 MCP Tools (76)](#-mcp-tools)
- [🎯 Skills (14)](#-skills)
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

> [!TIP]
> **Two paths, same result.** Pick whichever fits you — both end with a fully running knowledge base.

### Path A — Claude Code plugin · *recommended*

```bash
# 1. Install the plugin (one time, 30 seconds)
claude plugin marketplace add kingdol666/rag-knowledge
claude plugin install rag-knowledge

# 2. Just say:
"初始化知识库"
# —or—
"set up the knowledge base"

# 3. Watch the 11-phase wizard run — it clones, installs, configures, and starts everything.
```

<details>
<summary><b>🧙 What happens behind the scenes</b></summary>

The `knowledgebase-init` skill runs:

| Phase | What it does |
|-------|-------------|
| 0 | Detects your OS (Windows / Linux / macOS) |
| 1 | Checks prerequisites (uv, node, git, docker) |
| 2–3 | Clones or updates the repo |
| 4 | Runs `ragctl setup` — installs ALL dependencies + BGE-M3 model |
| 5 | Asks 12 interactive config questions (mode, ports, storage, auth…) |
| 6 | Writes `.env` with your choices |
| 7 | Registers `ragctl` globally + `kb-mcp` as a global MCP server |
| 8–9 | Starts Neo4j + all services (silently, no terminals) |
| 10 | Runs full-chain validation (backend health, MCP tools, KB list, search) |
| 11 | Prints a complete installation report |

All guided, all silent. 14 skills + 76 MCP tools ready globally.
</details>

### Path B — git clone · *classic*

```bash
# 1. Clone
git clone https://github.com/kingdol666/rag-knowledge.git
cd rag-knowledge

# 2. One-click setup
ragctl setup          # → uv + deps + model + .env (5–30 min first time)

# 3. Start
ragctl up             # → http://localhost:6789 (silent, no terminal windows)
```

### ✅ Verify everything

```bash
ragctl status          # shows dev + prod side-by-side
ragctl logs backend    # peek at recent backend activity
curl http://localhost:8765/api/v1/health   # → {"status":"healthy"}
```

> [!NOTE]
> **Opening Claude Code inside the project** auto-loads all 14 skills + `kb-mcp` MCP server (via `.mcp.json` at the project root). No manual MCP config needed.

---

## ✅ Prerequisites

Only two tools are required upfront — `ragctl setup` installs everything else for you.

| Tool | Version | Required? | Notes |
|------|---------|-----------|-------|
| **Git** | any | ✅ Required | Cloning |
| **Node.js** | ≥ 18 (22 recommended) | ✅ Required | `ragctl` CLI + Nuxt frontend |
| **uv** | ≥ 0.7 | ⚡ Auto-installed | Python package manager — `ragctl setup` installs if missing |
| **Python** | 3.12 | ⚡ via uv | uv manages the Python env; no manual Python install needed |
| **Docker** | any | 📋 Optional | Only for Neo4j graph. Parsing/search/experience work without it |
| **Rust** | stable | 📋 Optional | Only to build the Tauri desktop app |

- **Disk:** ~5 GB total
- **Network:** First run downloads BGE-M3 (~2.2 GB) from HuggingFace. Default mirror is `hf-mirror.com` (fast inside China); set `HF_ENDPOINT=https://huggingface.co` outside China.

<details>
<summary><b>📦 What gets installed where</b></summary>

| Component | Location | Size |
|-----------|----------|------|
| uv (Python pkg mgr) | `~/.local/bin/uv` | ~15 MB |
| Backend venv | `backend/.venv/` | ~2 GB (torch + transformers + mineru) |
| kb-mcp venv | `kb-mcp/.venv/` | ~50 MB (mcp + httpx + pyyaml) |
| Web deps | `web/node_modules/` | ~500 MB |
| CLI deps | `command/node_modules/` | ~5 MB (js-yaml) |
| BGE-M3 model | `~/.cache/huggingface/` | ~2.2 GB |
| Neo4j (optional) | Docker volume | ~600 MB |

All paths configurable. Nothing touches system-wide Python or Node.
</details>

---

## 💡 Why This Project

> What makes RAG Knowledge Platform different?

| Traditional KB tools | RAG Knowledge Platform |
|---|---|
| Separate search, storage, and AI layers | **Unified**: document parsing → indexing → search → graph → experience — one pipeline |
| Manual setup with complex CLI | **One command**: `ragctl setup` installs everything; or say "初始化知识库" |
| Hard to integrate with agents | **Native**: 76 MCP tools + 14 Claude Code skills, any MCP client works |
| Separate dev/prod configurations | **Single config**: `config.yml` is the source of truth; `--appmode` switches at runtime |
| Terminal windows clutter | **Silent headless**: all launchers start services with zero terminal windows |
| No structured knowledge reuse | **Experience library**: E0–E12 lifecycle with P0/P1/P2 credibility tiers |
| Single KB search | **Multi-strategy**: BM25 + vector + tag semantic + graph expansion + cross-KB enterprise |

---

## 🌟 Features

<p align="center">
  <img src="./docs/images/rag-pipeline.png" alt="QDCVR Agentic-First Enterprise Retrieval Pipeline — 6-stage architecture" width="960" />
</p>

| Pillar | What you get |
|--------|-------------|
| 📄 **Document parsing** | PDF / Word / Excel / PPT / images → Markdown via MinerU OCR engine |
| 🧠 **QDCVR retrieval** | Query-Driven, Content-Verified Retrieval — independent 0–8 content scoring. *Vectors are fast. Content is accurate.* |
| 🔍 **Multi-strategy search** | BM25 + vector two-stage recall · cross-KB enterprise search · tag semantic + graph expansion · balance_kbs |
| 📊 **Knowledge graph** | Neo4j-powered · 14 graph tools · entity/relation graphs · cross-KB document bridges · centrality discovery · path queries |
| 💡 **Experience library** | E0–E12 full lifecycle · structured problem→solution→lessons · P0/P1/P2 credibility tiers · stale detection · decay cycles · draft-approve workflow |
| 🔌 **76 MCP tools** | KB CRUD · search · graph · experience · parsing · tags · vector/index · service lifecycle · all MCP-native · non-blocking parse |
| 🎯 **14 Claude Code skills** | Natural-language commands · bilingual triggers (中/EN) · auto-dispatch to Archival agent · self-contained for global plugin · init + update + 12 Archival |
| 🤫 **Silent headless** | Every launcher (`ragctl`, `start.bat/.sh`, Tauri) runs with **zero terminal windows** · dev and prod behave identically · all logs unified across surfaces |

---

## 📦 Install

### Primary: Claude Code plugin

```bash
claude plugin marketplace add kingdol666/rag-knowledge
claude plugin install rag-knowledge
```

Then say: **"初始化知识库"** / **"set up the knowledge base"**

The skill auto-registers `ragctl` globally (`ragctl install` → `~/.local/bin`) and `kb-mcp` globally (`~/.claude/.mcp.json` with `RAG_PROJECT_ROOT`). After setup the platform works **from any directory, any Claude Code session** — 14 skills + 76 MCP tools + `ragctl` CLI.

<details>
<summary><b>Alternative: git clone + manual</b></summary>

```bash
git clone https://github.com/kingdol666/rag-knowledge.git
cd rag-knowledge

# One-click (recommended)
ragctl setup

# Or step-by-step
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

### 1. Claude Code · *natural language*

After `claude plugin install`, just describe what you want:

```
"ingest every PDF in ./papers into a new 'ML-research' KB"
  → knowledgebase-ingest (A0→A9 quality gates)

"search: what are the PET biaxial stretching parameters?"
  → QDCVR → content-verified answer with sources + confidence

"记录这个排查经验"
  → knowledgebase-experience-summarize → structured lesson

"organize all KBs — fix tags, descriptions, move misplaced docs"
  → knowledgebase-organize (O0→O13)
```

If services aren't running, the **Archival agent silently starts them** via `kb_project_start` — no terminals, no manual steps.

### 2. CLI · `ragctl`

```bash
ragctl up                     # start all (silent, dev mode)
ragctl up --appmode prod      # prod ports (8001/3000)
ragctl up --force             # force restart
ragctl status                 # dual-mode: dev + prod side-by-side
ragctl logs web --tail        # live-follow web logs
ragctl restart backend -f     # force-restart one service
ragctl down --appmode prod    # stop prod only (shared Neo4j kept)
```

#### Flags (`--` parameters)

| Flag | Alias | Purpose |
|------|-------|---------|
| `--appmode dev\|prod` | `--mode`, `-m` | Select port group |
| `--port-backend N` | `--backend-port` | Override backend port |
| `--port-web N` | `--web-port` | Override web port |
| `--no-neo4j` / `--no-backend` / `--no-web` | — | Skip a service |
| `--only SERVICE` | — | Operate on one service |
| `--force` | `-f` | Force stop-then-start |
| `--tail` | — | Live-follow logs |

### 3. MCP client · *any agent*

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
| `ragctl version` | Show local VERSION + git SHA vs GitHub remote |
| `ragctl update` | Check GitHub and pull latest (+ optional deps) |
| `ragctl update --check` | Dry-run version compare only |
| `ragctl install` | Register `ragctl` globally → `~/.local/bin` |
| `ragctl desktop` · `ui` | Launch Tauri desktop console |
| `ragctl help` | All commands + flags |

---

## 🔌 MCP Tools (76)

All accessible via `mcp__kb-mcp__*` from Claude Code or any MCP client.

| Category | Count | Key tools |
|----------|-------|-----------|
| **Service life cycle** | 6 | `kb_project_start`, `kb_project_status`, `kb_project_preflight`, `kb_project_version`, `kb_project_update`, `backend_status` |
| **KB CRUD** | 7 | `kb_list`, `kb_create`, `kb_update`, `kb_delete`, `kb_catalog`, `kb_doc_catalog`, `kb_get_documents` |
| **Document CRUD** | 7 | `kb_doc_read`, `kb_doc_create`, `kb_doc_update_meta`, `kb_doc_update_content`, `kb_doc_delete`, `kb_doc_batch_delete`, `kb_doc_move` |
| **File System** | 4 | `fs_get_tree`, `fs_get_children`, `fs_get_count`, `fs_upload_file` |
| **Parse** | 4 | `parse_doc`, `parse_doc_batch`, `parse_task_status`, `kb_doc_save_parsed` |
| **Tags** | 4 | `kb_tags_list`, `kb_doc_update_tags`, `kb_doc_get_by_tag`, `kb_tags_cleanup` |
| **Search** | 4 | `kb_search`, `kb_search_vector`, `kb_search_two_stage`, `kb_search_stats` |
| **Vector/Index** | 4 | `kb_index_document`, `kb_batch_index`, `kb_reindex`, `kb_cleanup_orphan_collections` |
| **Knowledge Graph** | 14 | `kb_graph_search` · `kb_graph_kb_overview` · `kb_graph_build` · `kb_graph_cross_kb_documents` · … |
| **Experience** | 22 | `experience_create` · `experience_search_global` · `experience_search_smart` · `experience_dashboard` · `experience_extract` · … |

---

## 🎯 Skills (14)

| Skill | Flow | Purpose |
|-------|------|---------|
| **knowledgebase** | Router | Dispatch user intent to the correct sub-skill |
| **knowledgebase-init** | Phase 0→11 | Guided fresh-install wizard (main agent) |
| **knowledgebase-update** | Phase 0→5 | Version check + safe GitHub pull (main agent) |
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

> [!NOTE]
> All skills are **self-contained** — no external CLAUDE.md dependencies. 12 skills delegate to the Archival agent; `init` runs on the main agent.

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
┌─────────────────────────────────────┐
│  $TREE_STORAGE_PATH/                │
│  ├── .tree-fs.json                  │
│  │── {KB}/.knowledge-base.yml       │
│  │── {KB}/doc.md                    │
│  │                                  │
│  + ChromaDB (BGE-M3, 1024-dim)     │
│  + Neo4j (bolt://127.0.0.1:7687)   │
└─────────────────────────────────────┘
```

> **Principle:** writes → HTTP API (backend/web proxy). reads → direct file access (`.tree-fs.json` + `.knowledge-base.yml`).

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
| `TREE_STORAGE_PATH` | `./storage/tree-file-system` | KB data storage path |
| `NEO4J_PASSWORD` | (from docker-compose) | Graph DB auth |

Switch modes at runtime without editing `.env`:

```bash
ragctl up --appmode prod       # backend → 8001, web → 3000
ragctl status                  # shows both dev + prod
ragctl down --appmode prod     # stops only prod (Neo4j preserved)
```

---

## 🤫 Silent Operation

All launchers start services with **zero terminal windows** in both dev and prod. Output flows to **three synchronized surfaces** — all reading the same log files:

| Surface | Command |
|---------|---------|
| 📄 On-disk files | `backend/logs/desktop-stdout.log` · `web/logs/desktop-stdout.log` · `backend/logs/mineru-api.log` |
| 🖥️ Tauri desktop console | Real-time log stream (tails the exact same files) |
| ⌨️ `ragctl logs` | CLI viewer + live tail |

```bash
ragctl logs backend            # last 80 lines
ragctl logs web --tail         # live follow (Ctrl+C to exit)
ragctl logs mineru --lines 200 # 200 lines of OCR output
```

> [!TIP]
> It doesn't matter which launcher you use to start services — `ragctl`, Tauri, and MCP's `kb_project_start` all write to the same files. Any of them can monitor what any of them started.

---

## 🛠️ Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| MCP not connecting | `uv` not on PATH (fresh terminal) | `ragctl setup` installs uv; reopen terminal |
| Backend won't start | deps not installed | `ragctl setup` (or `cd backend && uv sync`) |
| Web won't start | `node_modules` missing | `ragctl setup` (or `cd web && npm install`) |
| `backend/` or `web/` is empty | repo not fully cloned | `ragctl setup` |
| Graph queries fail (search works) | Neo4j not running | `ragctl start neo4j` (requires Docker) |
| BGE model download slow/fails | network to HuggingFace | set `HF_ENDPOINT=https://huggingface.co` |
| Port already in use | previous service still running | `ragctl down` then `ragctl up` |

---

## ❓ FAQ

<details>
<summary><b>Does it really open zero terminal windows?</b></summary>

Yes. Verified: `windowsHide` + detached binary spawn (no `cmd.exe` wrapper) on Windows; `start_new_session` on POSIX.
</details>

<details>
<summary><b>Dev or prod — what's the difference?</b></summary>

Ports and config. Dev: backend `8765` / web `6789`. Prod: backend `8001` / web `3000`. Switch with `--appmode prod`. Both fully silent. `ragctl status` shows both modes side-by-side.
</details>

<details>
<summary><b>Where is my data?</b></summary>

All local — `$TREE_STORAGE_PATH` (KB files) + Neo4j (graph) + ChromaDB (vectors). No cloud, no telemetry.
</details>

<details>
<summary><b>Do I need Docker?</b></summary>

Only for the Neo4j knowledge graph. Parsing, search, and experience all work without it.
</details>

<details>
<summary><b>Can I use this without Claude Code?</b></summary>

Yes. The Web UI at `http://localhost:6789` is fully functional, and any MCP client can call the 76 tools.
</details>

---

## 📁 Project Structure

```
rag-knowledge/
├── backend/              ← FastAPI + MinerU OCR engine
├── web/                  ← Nuxt 3 + Ant Design Vue
├── kb-mcp/               ← MCP server — 76 tools
├── command/              ← ragctl CLI (Node.js, js-yaml)
├── src-tauri/            ← Tauri v2 desktop application (Rust)
├── .claude/              ← Claude Code skills (13) + Archival agent
├── .claude-plugin/       ← Plugin + marketplace manifests
├── .mcp.json             ← kb-mcp MCP auto-connect
├── config.yml            ← Central configuration (single source of truth)
├── docker-compose.yml    ← Neo4j container
├── ragctl / ragctl.bat   ← CLI entry (Linux·macOS / Windows)
├── start.bat / start.sh  ← Silent launchers (delegate to ragctl up)
└── README.md
```

---

## 🔧 Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.12 · FastAPI · MinerU OCR · ChromaDB |
| Frontend | TypeScript · Nuxt 3 · Ant Design Vue · "Nocturne Atelier" theme |
| MCP Server | Python · FastMCP · httpx |
| CLI | Node.js · js-yaml |
| Desktop | Rust · Tauri v2 · reqwest · tokio |
| Graph | Neo4j 5.20 (Docker) |
| Embedding | BGE-M3 (1024-dim) · sentence-transformers |
| Search | BM25 + Vector two-stage · QDCVR pipeline |

---

## 🤝 Contributing

1. Fork → feature branch → commit → push → PR
2. `ragctl check` should pass before submitting
3. Cross-platform: test on Win + Linux (or macOS) if touching startup/scripts
4. See [CLAUDE.md](CLAUDE.md) for architecture details and development conventions

---

## 📄 License

MIT © [kingdol](https://github.com/kingdol666)