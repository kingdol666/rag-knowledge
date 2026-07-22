<div align="center">
  <img src="./docs/images/logo.svg" alt="RAG Knowledge Platform" width="120" />

  <h1>RAG Knowledge Platform</h1>

  <p><strong>Enterprise-Grade Document Intelligence & Agentic Knowledge Base</strong></p>

  <p>
    <em>PDF Parsing &middot; QDCVR Semantic Search &middot; Neo4j Knowledge Graph &middot; Experience Library<br>
    76 MCP Tools &middot; 14 Claude Code Skills &middot; Silent Headless Startup &middot; Cross-Platform</em>
  </p>

  <p>
    <a href="#-quick-start"><img src="https://img.shields.io/badge/Quick_Start-3_steps-4338ca?style=for-the-badge&logo=rocket" /></a>
    &nbsp;
    <a href="https://github.com/kingdol666/rag-knowledge/stargazers"><img src="https://img.shields.io/github/stars/kingdol666/rag-knowledge?style=for-the-badge&color=facc15" /></a>
    &nbsp;
    <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-22c55e?style=for-the-badge" /></a>
    &nbsp;
    <a href="https://github.com/kingdol666/rag-knowledge/releases"><img src="https://img.shields.io/github/v/release/kingdol666/rag-knowledge?style=for-the-badge&color=8b5cf6&label=release" /></a>
  </p>

  <p>
    <a href="#-features"><img src="https://img.shields.io/badge/Features-8_pillars-0ea5e9?style=for-the-badge" /></a>
    &nbsp;
    <a href="#-platforms"><img src="https://img.shields.io/badge/Platform-Win_%7C_Linux_%7C_macOS-6b7280?style=for-the-badge" /></a>
    &nbsp;
    <a href="#-mcp-tools--76"><img src="https://img.shields.io/badge/MCP-76_tools-8b5cf6?style=for-the-badge&logo=code" /></a>
    &nbsp;
    <a href="#-skills--14"><img src="https://img.shields.io/badge/Skills-14-f97316?style=for-the-badge&logo=openai" /></a>
  </p>

  <p>
    <sub>
      <a href="./README.md"><b>English</b></a>
      &nbsp;&middot;&nbsp;
      <a href="./README-zh.md">中文</a>
    </sub>
  </p>
</div>

<br>

<div align="center">
  <img src="./docs/images/rag-architecture.png" alt="RAG Knowledge Platform — 5-layer architecture" width="880" />
</div>

<br>

---

## 📌 Table of Contents

| | Section | | Section |
|:---:|---|:---:|---|
| 🚀 | [Quick Start](#-quick-start) | 🔌 | [MCP Tools (76)](#-mcp-tools--76) |
| ✅ | [Prerequisites](#-prerequisites) | 🎯 | [Skills (14)](#-skills--14) |
| 💡 | [Why This Project](#-why-this-project) | 🏗️ | [Architecture](#-architecture) |
| 🌟 | [Features](#-features) | ⚙️ | [Configuration](#-configuration) |
| 🖥️ | [Usage](#-usage) | 🛠️ | [Troubleshooting](#-troubleshooting) |

---

## 🚀 Quick Start

> **Three commands from zero to a fully working platform.**

```bash
# 1 — Clone
git clone https://github.com/kingdol666/rag-knowledge.git
cd rag-knowledge

# 2 — One-click setup (installs ALL deps + models)
./ragctl setup

# 3 — Start everything (silent, zero terminal windows)
./ragctl up
```

That's it. Open **http://localhost:6789** and you're ready.

<details>
<summary><b>📋 What happens during <code>ragctl setup</code>?</b></summary>

| Step | Action | Duration |
|------|--------|----------|
| 1 | Install `uv` (Python package manager) if missing | ~5 sec |
| 2 | Ensure Python 3.12 (managed by uv) | ~10 sec |
| 3 | Verify project integrity (`backend/` + `web/`) | instant |
| 4 | Create `.env` from `.env.example` | instant |
| 5 | Install backend deps (FastAPI + torch + transformers + MinerU) | 5–15 min |
| 6 | Install kb-mcp deps (MCP server) | ~30 sec |
| 7 | Install web deps (Nuxt 3 + Ant Design Vue) | ~1 min |
| 8 | Pre-download BGE-M3 embedding model (~2.2 GB) | 2–10 min |
| 9 | Pre-download MinerU VLM model (OCR engine) | 3–10 min |
| 10 | Register `ragctl` globally → `~/.local/bin` | instant |
| 11 | Final environment check | ~2 sec |

</details>

<details>
<summary><b>🔧 Windows users — use PowerShell</b></summary>

```powershell
# Same commands, Windows-native:
.\ragctl.bat setup
.\ragctl.bat up

# Or if you registered ragctl globally:
ragctl setup
ragctl up
```

</details>

> [!TIP]
> **No Claude Code? No problem.** The Web UI is fully functional standalone. Use any MCP client to access 76 tools, or just browse/search at `http://localhost:6789`.

---

### Four Installation Methods

> Each method produces a fully working platform — pick the one that fits your workflow.

<table>
<tr>
<th width="25%">A. Claude Code Plugin<br><sub><code>recommended</code></sub></th>
<th width="25%">B. OMP Global Install<br><sub><code>Oh My Pi</code></sub></th>
<th width="25%">C. Skills Copy + Wizard</th>
<th width="25%">D. Git Clone (Local)</th>
</tr>
<tr>
<td valign="top">

You use **Claude Code** and want everything global

```bash
claude plugin marketplace add kingdol666/rag-knowledge
claude plugin install rag-knowledge
```

Then say: `"初始化知识库"`

</td>
<td valign="top">

You use **Oh My Pi** as your coding agent

```bash
git clone https://github.com/kingdol666/rag-knowledge.git
cd rag-knowledge
node scripts/install_omp.cjs
```

</td>
<td valign="top">

You don't want a plugin but still want guided setup

```bash
git clone https://github.com/kingdol666/rag-knowledge.git ~/rag-knowledge
mkdir -p ~/.claude/skills
cp -r ~/rag-knowledge/.claude/skills/knowledgebase* ~/.claude/skills/
```

</td>
<td valign="top">

You want full manual control, all in one directory

```bash
git clone https://github.com/kingdol666/rag-knowledge.git
cd rag-knowledge
./ragctl setup && ./ragctl up
```

</td>
</tr>
<tr>
<td colspan="4" align="center">

<details>
<summary><b>📖 Detailed comparison of all four methods</b></summary>
<br>

| Aspect | A. Plugin | B. OMP | C. Skills Copy | D. Local Clone |
|--------|-----------|--------|---------------|----------------|
| **Skills available** | Global (any dir) | Global (any dir) | Global (any dir) | Project dir only |
| **MCP tools** | Global (plugin) | Global (OMP) | Optional global | Project dir only |
| **`ragctl` CLI** | Global | Global | Global | Project root |
| **Setup effort** | Minimal | One command | Manual copy | `ragctl setup` |
| **Best for** | Claude Code users | OMP users | No-plugin users | Full control |

</details>

</td>
</tr>
</table>

### ✅ Verify Everything Works

```bash
ragctl status                 # dual-mode: dev + prod side-by-side
curl http://localhost:8765/api/v1/health   # → {"status":"healthy"}
```

---

## ✅ Prerequisites

Only these tools need to be installed **before** you begin — `ragctl setup` handles everything else automatically.

<table>
<tr>
<th>Tool</th><th>Version</th><th>Required?</th><th>Notes</th>
</tr>
<tr>
<td><b>Git</b></td><td>any</td><td>✅ Required</td><td>Cloning the repository</td>
</tr>
<tr>
<td><b>Node.js</b></td><td>≥ 18 (22 recommended)</td><td>✅ Required</td><td><code>ragctl</code> CLI + Nuxt frontend</td>
</tr>
<tr>
<td><b>uv</b></td><td>≥ 0.7</td><td>⚡ Auto-installed</td><td>Python package manager — <code>ragctl setup</code> installs if missing</td>
</tr>
<tr>
<td><b>Python</b></td><td>3.12</td><td>⚡ via uv</td><td>uv manages the env; no manual Python install needed</td>
</tr>
<tr>
<td><b>Docker</b></td><td>any</td><td>📋 Optional</td><td>Only for Neo4j graph. Parsing, search, and experience work without it</td>
</tr>
<tr>
<td><b>Rust</b></td><td>stable</td><td>📋 Optional</td><td>Only to build the Tauri desktop app</td>
</tr>
</table>

> **Resource requirements:** ~5 GB disk · First run downloads BGE-M3 (~2.2 GB). Default source: **ModelScope** (fast inside China). Set `embedding.model_source: huggingface` in `config.yml` for overseas.

---

## 💡 Why This Project

<table>
<tr>
<td width="50%" valign="top">

### Traditional KB Tools

- Separate search, storage, and AI layers
- Manual setup with complex CLI
- Hard to integrate with agents
- Separate dev/prod configurations
- Terminal windows clutter
- No structured knowledge reuse
- Single KB search strategy

</td>
<td width="50%" valign="top">

### RAG Knowledge Platform

- ✅ **Unified**: parse → index → search → graph → experience — one pipeline
- ✅ **One command or one phrase**: `ragctl setup` or `"初始化知识库"`
- ✅ **Native agent integration**: 76 MCP tools + 14 skills, any MCP client works
- ✅ **Single config**: `config.yml` is the source of truth; `--appmode` switches at runtime
- ✅ **Silent headless**: zero terminal windows in both dev and prod
- ✅ **Experience library**: E0–E12 lifecycle with P0/P1/P2 credibility tiers
- ✅ **Multi-strategy search**: BM25 + vector + tag semantic + graph expansion

</td>
</tr>
</table>

---

## 🌟 Features

<div align="center">
  <img src="./docs/images/rag-pipeline.png" alt="QDCVR Agentic-First Enterprise Retrieval Pipeline" width="880" />
</div>

<table>
<tr>
<th width="5%">Icon</th><th width="20%">Pillar</th><th>What you get</th>
</tr>
<tr>
<td align="center">📄</td>
<td><b>Document parsing</b></td>
<td>PDF / Word / Excel / PPT / images → Markdown via <b>MinerU OCR</b> engine</td>
</tr>
<tr>
<td align="center">🧠</td>
<td><b>QDCVR retrieval</b></td>
<td>Query-Driven, Content-Verified Retrieval — independent 0–8 content scoring. <em>Vectors are fast. Content is accurate.</em></td>
</tr>
<tr>
<td align="center">🔍</td>
<td><b>Multi-strategy search</b></td>
<td>BM25 + vector two-stage recall · cross-KB enterprise search · tag semantic + graph expansion · <code>balance_kbs</code></td>
</tr>
<tr>
<td align="center">📊</td>
<td><b>Knowledge graph</b></td>
<td>Neo4j-powered · 14 graph tools · entity/relation graphs · cross-KB document bridges · centrality discovery</td>
</tr>
<tr>
<td align="center">💡</td>
<td><b>Experience library</b></td>
<td>E0–E12 lifecycle · structured problem→solution→lessons · P0/P1/P2 credibility tiers · stale detection · draft-approve</td>
</tr>
<tr>
<td align="center">🔌</td>
<td><b>76 MCP tools</b></td>
<td>KB CRUD · search · graph · experience · parsing · tags · vector/index · service lifecycle · all MCP-native</td>
</tr>
<tr>
<td align="center">🎯</td>
<td><b>14 Claude Code skills</b></td>
<td>Natural-language commands · bilingual triggers (中/EN) · auto-dispatch to Archival agent</td>
</tr>
<tr>
<td align="center">🤫</td>
<td><b>Silent headless</b></td>
<td>Every launcher runs with <b>zero terminal windows</b> · dev and prod behave identically · logs unified</td>
</tr>
</table>

---

## 🖥️ Usage

Four interfaces, one backend. Pick whichever fits your workflow.

### 1. Claude Code — *natural language*

After installation, just describe what you want in plain English or Chinese:

```text
"ingest every PDF in ./papers into a new 'ML-research' KB"
  → knowledgebase-ingest (A0→A9 quality gates)

"search: what are the PET biaxial stretching parameters?"
  → QDCVR → content-verified answer with sources + confidence

"记录这个排查经验"
  → knowledgebase-experience-summarize → structured lesson

"organize all KBs — fix tags, descriptions, move misplaced docs"
  → knowledgebase-organize (O0→O13)
```

> If services aren't running, the **Archival agent silently starts them** via `kb_project_start` — no terminals, no manual steps.

### 2. CLI — `ragctl`

```bash
ragctl up                     # start all (silent, dev mode)
ragctl up --appmode prod      # prod ports (8001/3000)
ragctl up --force             # force restart
ragctl status                 # dual-mode: dev + prod side-by-side
ragctl logs web --tail        # live-follow web logs
ragctl restart backend -f     # force-restart one service
ragctl backup                 # cross-platform backup (KB + ChromaDB + Neo4j)
ragctl down --appmode prod    # stop prod only (shared Neo4j kept)
```

<details>
<summary><b>📋 Full CLI reference</b></summary>

| Command | Description |
|---------|-------------|
| `ragctl setup` · `init` | One-click full deployment |
| `ragctl check` | Full environment audit with fix hints |
| `ragctl up` / `down` | Start / stop all services (silent, no terminals) |
| `ragctl start` / `stop` / `restart` [svc] | Per-service lifecycle (`backend`\|`web`\|`neo4j`\|`all`) |
| `ragctl status [--appmode X]` | Dual-mode status: ports + HTTP health + PIDs + MinerU |
| `ragctl logs [svc] [--tail] [--lines N]` | View / live-tail logs |
| `ragctl deps` | Install all dependencies (real-time progress) |
| `ragctl model` | Pre-download BGE-M3 embedding model. `--source modelscope\|hf-mirror\|huggingface` |
| `ragctl backup` / `restore` | Cross-platform backup & restore (KB docs + ChromaDB + Neo4j) |
| `ragctl version` | Show local VERSION + git SHA vs GitHub remote |
| `ragctl update` | Check GitHub and pull latest |
| `ragctl install` | Register `ragctl` globally → `~/.local/bin` |
| `ragctl desktop` · `ui` | Launch Tauri desktop console |
| `ragctl clean` | Clean MinerU artifacts + caches (`--model` needs double confirm) |

**Flags:**

| Flag | Alias | Purpose |
|------|-------|---------|
| `--appmode dev\|prod` | `--mode`, `-m` | Select port group |
| `--port-backend N` | `--backend-port` | Override backend port |
| `--port-web N` | `--web-port` | Override web port |
| `--no-neo4j` / `--no-backend` / `--no-web` | — | Skip a service |
| `--force` | `-f` | Force stop-then-start |
| `--tail` | — | Live-follow logs |

</details>

### 3. MCP client — *any agent*

```python
kb_project_start(backend=True, web=True, wait=True)   # silent start
kb_search_two_stage(query="reinforcement learning", balance_kbs=True)
experience_search_global(query="ConnectError troubleshooting")
kb_graph_cross_kb_documents(min_kbs=2)
```

### 4. Web UI

Open **http://localhost:6789** — browse KBs, search documents, explore the graph, chat with Claude via the Agent SDK.

---

## 🔌 MCP Tools — 76

All accessible via `mcp__kb-mcp__*` from Claude Code or any MCP client.

| Category | Count | Key tools |
|----------|-------|-----------|
| **Service lifecycle** | 6 | `kb_project_start`, `kb_project_status`, `kb_project_preflight`, `kb_project_version`, `kb_project_update`, `backend_status` |
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

## 🎯 Skills — 14

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

> All skills are **self-contained** — no external CLAUDE.md dependencies. 12 delegate to the Archival agent; `init` and `update` run on the main agent.

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

### API Rate Limiting

The backend includes a built-in sliding-window rate limiter (configurable in `config.yml`):

```yaml
server:
  rate_limit:
    enabled: true
    window_sec: 60
    max_requests: 120      # general endpoints
    heavy_max: 20          # parse/mineru endpoints
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

> It doesn't matter which launcher you use to start services — `ragctl`, Tauri, and MCP's `kb_project_start` all write to the same files.

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
| Skills not showing in `/skills` | Not in project dir (Method C) | `cd rag-knowledge` and restart Claude Code |
| `ragctl` not found globally | `ragctl install` skipped | run `ragctl install` from project root |

<details>
<summary><b>❓ FAQ</b></summary>

<details>
<summary><b>Does it really open zero terminal windows?</b></summary>

Yes. Verified: `windowsHide` + detached binary spawn (no `cmd.exe` wrapper) on Windows; `start_new_session` on POSIX.
</details>

<details>
<summary><b>Dev or prod — what's the difference?</b></summary>

Ports and config. Dev: backend `8765` / web `6789`. Prod: backend `8001` / web `3000`. Switch with `--appmode prod`. Both fully silent.
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

</details>

---

## 📁 Project Structure

```
rag-knowledge/
├── backend/              ← FastAPI + MinerU OCR engine
├── web/                  ← Nuxt 3 + Ant Design Vue (incl. Claude Chat with Agent SDK)
├── kb-mcp/               ← MCP server — 76 tools
├── command/              ← ragctl CLI (Node.js, js-yaml)
├── src-tauri/            ← Tauri v2 desktop application (Rust)
├── .claude/              ← Claude Code skills (14) + Archival agent
├── .omp/                 ← OMP-native agent, commands, MCP config
├── .claude-plugin/       ← Plugin + marketplace manifests
├── scripts/              ← GPU detection, skill validation, OMP installer
├── .mcp.json             ← kb-mcp MCP auto-connect (Claude Code local project)
├── config.yml            ← Central configuration (single source of truth)
├── docker-compose.yml    ← Neo4j container
├── .env.example          ← Environment variable template
├── VERSION               ← Semantic version
├── ragctl / ragctl.bat   ← CLI entry (Linux·macOS / Windows)
├── start.bat / start.sh  ← Silent launchers (delegate to ragctl up)
└── README.md
```

---

## 🔧 Tech Stack

<table>
<tr>
<td width="50%" valign="top">

| Component | Technology |
|-----------|-----------|
| **Backend** | Python 3.12 · FastAPI · MinerU OCR · ChromaDB |
| **Frontend** | TypeScript · Nuxt 3 · Ant Design Vue |
| **Claude Chat** | Vue 3 · Claude Agent SDK · SQLite |
| **MCP Server** | Python · FastMCP · httpx |

</td>
<td width="50%" valign="top">

| Component | Technology |
|-----------|-----------|
| **CLI** | Node.js · js-yaml |
| **Desktop** | Rust · Tauri v2 |
| **Graph** | Neo4j 5.20 (Docker) |
| **Embedding** | BGE-M3 (1024-dim) · sentence-transformers |

</td>
</tr>
</table>

---

## 📄 License

MIT © [kingdol](https://github.com/kingdol666)

---

<div align="center">
  <sub>Built with</sub>
  <a href="https://fastapi.tiangolo.com/">FastAPI</a>
  <sub>·</sub>
  <a href="https://nuxt.com/">Nuxt 3</a>
  <sub>·</sub>
  <a href="https://neo4j.com/">Neo4j</a>
  <sub>·</sub>
  <a href="https://www.chromadb.com/">ChromaDB</a>
  <sub>·</sub>
  <a href="https://modelcontextprotocol.io/">MCP</a>
  <sub>·</sub>
  <a href="https://mineru.net/">MinerU</a>
  <br><br>
  <sub>⭐ If this project helps you, please consider giving it a star!</sub>
</div>
