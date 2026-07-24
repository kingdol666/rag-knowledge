<div align="center">

<img src="./docs/images/logo.svg" alt="RAG Knowledge Platform" width="128" height="128" />

# RAG Knowledge Platform

### Enterprise-Grade Document Intelligence & Agentic Knowledge Base

**One pipeline from raw PDF to verified, agent-queryable knowledge — with content-verified retrieval that refuses to be fooled by vector similarity.**

<p>
<em>QDCVR Semantic Search &middot; Neo4j Knowledge Graph &middot; Experience Lifecycle (E0–E12)<br>
76 MCP Tools &middot; 14 Agent Skills &middot; MinerU OCR &middot; Cross-Platform</em>
</p>

<p>
<a href="#-quick-start"><img src="https://img.shields.io/badge/Quick_Start-3_commands-4338ca?style=for-the-badge&logo=rocket" /></a>
&nbsp;
<img src="https://img.shields.io/badge/Platform-Win_%7C_Linux_%7C_macOS-334155?style=for-the-badge&logo=linux" />
&nbsp;
<img src="https://img.shields.io/badge/MCP_Tools-76-8b5cf6?style=for-the-badge&logo=code" />
&nbsp;
<img src="https://img.shields.io/badge/Skills-14-f97316?style=for-the-badge&logo=openai" />
</p>

<p>
<a href="https://github.com/kingdol666/rag-knowledge/stargazers"><img src="https://img.shields.io/github/stars/kingdol666/rag-knowledge?style=flat-square&color=facc15" /></a>
&nbsp;
<a href="https://github.com/kingdol666/rag-knowledge/releases"><img src="https://img.shields.io/github/v/release/kingdol666/rag-knowledge?style=flat-square&color=8b5cf6&label=release" /></a>
&nbsp;
<img src="https://img.shields.io/badge/Python-3.12-3776ab?style=flat-square&logo=python&logoColor=white" />
&nbsp;
<img src="https://img.shields.io/badge/License-MIT-22c55e?style=flat-square" />
&nbsp;
<img src="https://img.shields.io/badge/status-production_ready-0ea5e9?style=flat-square" />
</p>

<p>
<sub><b>English</b></sub> &nbsp;&middot;&nbsp; <sub><a href="./README-zh.md">中文</a></sub>
</p>

---

<img src="./docs/images/rag-architecture.png" alt="RAG Knowledge Platform — 5-layer architecture" width="900" />

</div>

<br>

## ✨ Why This Exists

> **The core problem with modern RAG:** high vector similarity ≠ content relevance. A query about *"PET biaxial stretching"* cheerfully returns *"PP film"* literature at cosine 0.90 — both live in the "polymer film" semantic space, so the embedder is fooled. The LLM then hallucinates a confident, wrong answer.

This platform solves that at the **retrieval layer**, not the generation layer. Its flagship method — **QDCVR (Query-Driven, Content-Verified Retrieval)** — reads candidate documents and scores them on an independent **0–8 content rubric**, applying the uncompromising rule:

> ### 🎯 *“Vectors are fast. Content is accurate.”*
> Even at vector similarity **0.95**, if the content score is **≤ 4**, the document is **discarded**.

<div align="center">

| | Traditional KB Tools | **RAG Knowledge Platform** |
|:---:|:---|:---|
| 🔍 | Single search strategy (vector *or* keyword) | **Multi-strategy**: BM25 + vector + tag-semantic + graph expansion |
| 🧠 | Trust vector similarity blindly | **Content-verified retrieval** — independent 0–8 adjudication |
| 🤖 | Bolt-on AI, hard to integrate with agents | **Agent-native**: 76 MCP tools, 14 skills — any MCP client works |
| 💡 | No structured knowledge reuse | **Experience library**: E0–E12 lifecycle with P0/P1/P2 credibility |
| 🔧 | Complex multi-tool setup, scattered configs | **One command** `ragctl setup`, single `config.yml` source of truth |
| 🪟 | Terminal windows everywhere | **Silent headless** — zero terminals in dev *and* prod |

</div>

---

## 🌟 Eight Pillars

<div align="center">
<img src="./docs/images/rag-pipeline.png" alt="QDCVR Agentic-First Enterprise Retrieval Pipeline" width="900" />
</div>

| | Pillar | What you get |
|:---:|:---|:---|
| 📄 | **Document parsing** | PDF / Word / Excel / PPT / images → Markdown via **MinerU OCR** engine |
| 🧠 | **QDCVR retrieval** | Query-driven, content-verified retrieval — independent 0–8 content scoring |
| 🔍 | **Multi-strategy search** | BM25 + vector two-stage recall · cross-KB enterprise search · `balance_kbs` diversity guard |
| 📊 | **Knowledge graph** | Neo4j-powered · 14 graph tools · entity/relation graphs · cross-KB document bridges |
| 💡 | **Experience library** | E0–E12 lifecycle · structured problem→solution→lessons · P0/P1/P2 credibility · decay |
| 🔌 | **76 MCP tools** | KB CRUD · search · graph · experience · parsing · tags · vector/index · lifecycle — all MCP-native |
| 🎯 | **14 agent skills** | Natural-language commands · bilingual triggers (中/EN) · auto-dispatch to Archival agent |
| 🤫 | **Silent headless** | Every launcher runs with **zero terminal windows** · dev and prod behave identically |

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
<summary><b>🔧 Windows users — use the same commands natively</b></summary>

```powershell
.\ragctl.bat setup
.\ragctl.bat up

# Or once ragctl is registered globally:
ragctl setup
ragctl up
```
</details>

> [!TIP]
> **No Claude Code? No problem.** The Web UI is fully functional standalone. Use any MCP client to access 76 tools, or just browse/search at `http://localhost:6789`.

### ✅ Verify Everything Works

```bash
ragctl status                                   # dual-mode: dev + prod side-by-side
curl http://localhost:8765/api/v1/health        # → {"status":"healthy"}
```

---

## 💻 Four Ways to Install

All four end with the **same working platform**. Methods **A / B / C** are **agent-driven** — install once, then a single conversation initializes the whole thing. Method **D** is the **manual CLI** path.

<table>
<tr>
<th width="25%">A. Claude Code Plugin<br><sub><code>recommended</code></sub></th>
<th width="25%">B. OMP Global Install</th>
<th width="25%">C. Skills Copy + Wizard</th>
<th width="25%">D. Git Clone (Manual CLI)</th>
</tr>
<tr>
<td valign="top">

You use **Claude Code** and want everything (skills + 76 MCP tools + commands) registered globally.

```bash
# Run inside a Claude Code session:
/plugin marketplace add kingdol666/rag-knowledge
/plugin install rag-knowledge@rag-knowledge
/reload-plugins
```

💬 Then **start any conversation** and ask the agent to initialize:

> `/knowledgebase-init` · or just say **"set up the knowledge base"** / **"初始化知识库"**

</td>
<td valign="top">

You use **Oh My Pi (OMP)** as your coding agent.

```bash
git clone https://github.com/kingdol666/rag-knowledge.git
cd rag-knowledge
node scripts/install_omp.cjs
```

💬 **Restart the OMP session** (or run `/mcp reload`), then start a conversation and ask the agent to initialize:

> **"初始化知识库"** · **"set up the knowledge base"** → `/knowledgebase-init`

</td>
<td valign="top">

You want the skills + guided wizard, without a plugin.

```bash
git clone https://github.com/kingdol666/rag-knowledge.git ~/rag-knowledge
mkdir -p ~/.claude/skills
cp -r ~/rag-knowledge/.claude/skills/knowledgebase* ~/.claude/skills/
```

💬 **Restart Claude Code**, then start a conversation and ask the agent to initialize:

> `/knowledgebase-init` · or just say **"初始化知识库"**

</td>
<td valign="top">

You want full manual control over every step.

```bash
git clone https://github.com/kingdol666/rag-knowledge.git
cd rag-knowledge
./ragctl setup && ./ragctl up
```

Open **http://localhost:6789** — ready.

(Or, from the project dir, run `/knowledgebase-init` for guided setup instead of doing it by hand.)

</td>
</tr>
</table>

### 🧙 Then initialize — one conversation, full setup

> For methods **A / B / C**, installing isn't the end — your agent then **deploys the entire platform for you.** Start a conversation in Claude Code / OMP and trigger the init wizard with any of these (they all auto-match):

| Trigger phrase | Language |
|---|---|
| `/knowledgebase-init` | exact command |
| `初始化知识库` · `部署知识库` · `知识库启动` · `配置知识库` | 中文 |
| `init KB` · `set up the knowledge base` · `bootstrap` · `deploy KB` | English |

The **knowledgebase-init** wizard runs live on your **main agent** (real-time, interactive — no delegation) and walks through a verified 12-phase flow:

| Phase | What it does | Skips when… |
|:---:|--------------|-------------|
| **0** | Detects GPU (NVIDIA CUDA / AMD ROCm / Apple MPS / CPU) → picks the correct PyTorch wheel | — |
| **1** | `ragctl check` → audits the environment and classifies what's missing | **everything present → fast path** |
| **2** | Locates the project (plugin cache / OMP env / git root / CWD / ask + clone) | already inside the project |
| **3–4** | Installs **only** missing deps (uv · Node · Python 3.12 · backend · web · mcp) + GPU-matched torch | already installed |
| **5** | Downloads **only** missing models (BGE-M3 ~2.2 GB · MinerU VLM) | already cached |
| **6** | Writes **only** missing config (`config.yml` + `.env`) — asks before every decision | already configured |
| **7** | Registers `ragctl` globally → `~/.local/bin` | already registered |
| **8** | **Optional** global MCP registration into `~/.claude.json` → `mcpServers` | you decline |
| **9–10** | Starts Neo4j (if Docker) + backend + web — silent, zero terminals | already healthy |
| **11** | Full-chain validation: HTTP health + MCP round-trip (`kb_catalog`) + torch↔GPU match | — |

Every phase is **incremental** — no re-installs, no re-downloads, no repeated questions. If your environment is already complete, Phase 1 detects it and **skips straight to validation**.

> [!IMPORTANT]
> The wizard **never decides for you** on paths, ports, passwords, or optional features (MCP/Neo4j). It asks, then acts. On any failure it stops immediately and offers 3 recovery options.

<details>
<summary><b>💬 Right after init — start working with your KB in the same conversation</b></summary>

The wizard hands you a healthy system and the commands to use it. Keep talking in the **same session** — the 76 MCP tools and 14 skills are live, so plain language works immediately:

```text
"list all knowledge bases"                              → knowledgebase-list (L1→L3)
"ingest every PDF in ./papers into a 'research' KB"     → knowledgebase-ingest (A0→A9 quality gates)
"search: what are the PET biaxial stretching parameters?"
                                                        → QDCVR → content-verified answer + sources
"organize all KBs — fix tags, descriptions, move misplaced docs"
                                                        → knowledgebase-organize (O0→O13)
"记录这个排查经验"                                        → knowledgebase-experience-summarize
```

If services ever stop, the **Archival agent silently restarts them** via `kb_project_start` — no terminals, no manual steps.
</details>

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

---

## ✅ Prerequisites

Only these need to be installed **before** you begin — `ragctl setup` handles everything else.

| Tool | Version | Required? | Notes |
|------|---------|:---------:|-------|
| **Git** | any | ✅ Required | Cloning the repository |
| **Node.js** | ≥ 18 (22 recommended) | ✅ Required | `ragctl` CLI + Nuxt frontend |
| **uv** | ≥ 0.7 | ⚡ Auto-installed | Python package manager — installed by `ragctl setup` if missing |
| **Python** | 3.12 | ⚡ via uv | uv manages the env; no manual Python install needed |
| **Docker** | any | 📋 Optional | Only for Neo4j graph. Parsing, search, and experience work without it |
| **Rust** | stable | 📋 Optional | Only to build the Tauri desktop app |

> **Resource requirements:** ~5 GB disk · First run downloads BGE-M3 (~2.2 GB). Default source: **ModelScope** (fast inside China). Set `embedding.model_source: huggingface` in `config.yml` for overseas.

---

## 🖥️ Usage — Four Interfaces, One Backend

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

**Flags:** `--appmode dev\|prod` (`--mode`, `-m`), `--port-backend N`, `--port-web N`, `--no-neo4j` / `--no-backend` / `--no-web`, `--force` (`-f`), `--tail`

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
|----------|:-----:|-----------|
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

## 🧠 The QDCVR Retrieval Method

The flagship contribution. A seven-stage pipeline that makes retrieval trustworthy:

```
Query → Step 0: Intent + Rewrite → Step 1: Smart KB Selection
      → Step 2: Two-Stage Recall (BM25 → vector, balance_kbs)
      → Step 2.5: Dedup + Hard Threshold
      → Step 3: CONTENT VERIFICATION (0–8 scoring) ⭐
      → Step 5: Confidence Tiering (P0 / P1 / P2)
      → Step 6: Answer + Blind-Spot Declaration
```

**The content verification rubric** scores each candidate on three dimensions:

| Dimension | Score | Criterion |
|-----------|:-----:|-----------|
| Topic relevance | 0–3 | 3 = directly about the query subject |
| Scenario match | 0–3 | 3 = directly solves the query's problem |
| Answer evidence | 0–2 | 2 = cite-able data / steps / conclusions |

> **The decision rule:** `score ≥ 6 → accept (P0)` · `= 5 → supplement (P1)` · `≤ 4 → discard` — **independent of vector similarity.**

<details>
<summary><b>📖 Experience credibility model (P0/P1/P2)</b></summary>

Structured operational knowledge (problem→solution→lessons) is managed through a 13-stage lifecycle (**E0–E12**) with credibility tiers and temporal decay:

| Tier | Condition | Presentation |
|------|-----------|-------------|
| **P0 Strong** | vector≥0.65 ∧ content≥6 ∧ rating≥4 ∧ reviews≥1 | Directly cite as answer |
| **P1 Confirmed** | vector≥0.45 ∧ content≥4 | Cite with annotation |
| **P2 Supplement** | vector≥0.35 ∧ content≥3 | Hidden by default, expand on request |
| **Discard** | content verification fails OR vector < 0.35 | Never presented |

**Decay rules:** stale-unverified (>30d, 0 applied) → demoted; disputed (rating<2, ≥3 reviews) → hard cap P2; unvetted (0 reviews ∧ 0 applied) → cap P1.

</details>

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

### Five-Layer Data Model

| Layer | Content | Format |
|-------|---------|--------|
| L1 Raw | Original documents | PDF / DOCX / XLSX / PNG |
| L2 Parsed | Markdown + images | `.md` |
| L3 Vector | Chunked embeddings | ChromaDB collections |
| L4 Graph | Entity / relation nodes | Neo4j |
| L5 Experience | Structured lessons | YAML + Markdown |

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

Built-in sliding-window rate limiter (configurable in `config.yml`):

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
├── docs/                 ← Architecture, paper framework, test plans
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
|-----------|------------|
| **Backend** | Python 3.12 · FastAPI · MinerU OCR · ChromaDB |
| **Frontend** | TypeScript · Nuxt 3 · Ant Design Vue |
| **Claude Chat** | Vue 3 · Claude Agent SDK · SQLite |
| **MCP Server** | Python · FastMCP · httpx |

</td>
<td width="50%" valign="top">

| Component | Technology |
|-----------|------------|
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
