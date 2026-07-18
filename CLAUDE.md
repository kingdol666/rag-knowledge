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
kb-mcp MCP Server              ← 77 tools: KB CRUD, file ops, parse, search, tags, vector, graph, experience
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
├── web/                    # [submodule] rag-knowledge-frondend — Nuxt 3 UI (only frontend)
├── kb-mcp/                 # [local] MCP server — provides ~40 MCP tools for KB operations
├── .claude/skills/         # OMC skills (knowledgebase dispatcher, ingest, search, manage, etc.)
├── .claude/agents/         # Archival agent definition (knowledge-admin.md)
├── docs/ARCHITECTURE.md    # Detailed architecture + MCP dev guide
└── README.md               # Project overview + roadmap
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
│   └── utils/
│       ├── paths.py          # PROJECT_ROOT, config path resolution
│       └── mineru_manager.py # MineruApiManager: subprocess lifecycle + async task API
├── tests/
│   ├── conftest.py            # Skips integration tests unless --run-integration
│   ├── test_unit.py           # Hermetic unit tests (no MinerU)
│   └── test_parse_async.py    # Integration (needs running MinerU)
└── pyproject.toml             # uv; 三平台支持 (required-environments: win32/linux/darwin; marker 条件源)
```

Key properties:
- **No DeepAgent** — old DeepAgent routes were removed.
- **MinerU port is ephemeral** — `MineruApiManager(port=None)` auto-picks a free port avoiding common dev ports. The resolved port is at `manager.port` / `manager.api_url`. **Do NOT hardcode 8764.**
- **Subprocess lifecycle** — MinerU runs as a hidden subprocess: Windows binds to a Job Object (`KILL_ON_JOB_CLOSE`); Linux uses `prctl(PR_SET_PDEATHSIG)` as the equivalent parent-death cleanup; macOS falls back to process-group + atexit. stdout→log file on all platforms (never a pipe, avoids [Errno 22]).
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
├── pages/                  # file-system.vue, knowledgebase-search.vue, prompts.vue, etc.
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
- **KB Catalog (agentic-first, lightweight):** `kb_catalog`, `kb_doc_catalog`, `fs_catalog_all`
- **Document CRUD:** `kb_doc_read`, `kb_doc_create`, `kb_doc_update_meta`, `kb_doc_update_content`, `kb_doc_delete`, `kb_doc_batch_delete`, `kb_doc_move`
- **File System (4):** `fs_get_tree`, `fs_get_children`, `fs_get_count`, `fs_upload_file`
- **Parse (non-blocking, 4):** `parse_doc`, `parse_doc_batch`, `parse_task_status`, `kb_doc_save_parsed`
- **Tags (4):** `kb_tags_list`, `kb_doc_update_tags`, `kb_doc_get_by_tag`, `kb_tags_cleanup`
- **Search (Agentic RAG, 4):** `kb_search` (metadata only), `kb_search_vector` (semantic), `kb_search_two_stage` (BM25→vector, primary), `kb_search_stats`
- **Vector/Index:** `kb_index_document`, `kb_batch_index`, `kb_reindex`
- **Knowledge Graph:** `kb_graph_search`, `kb_graph_neighbors`, `kb_graph_stats`
- **Experience (21 tools):** Full lifecycle — create/read/list/update/delete/apply/review/summary | Search: search/search_vector/search_global | Extract/Drafts: extract/drafts_list/draft_read/draft_approve/draft_reject | Health: check_stale/check_stale_global/sync_kb/dashboard/apply_decay

**Architecture principle:** writes go through HTTP API (backend/web proxy), reads go through direct file access (`.tree-fs.json` + `.knowledge-base.yml`).

## Enterprise-Grade Retrieval Architecture

### Agentic-First Retrieval Pipeline (6 stages)

```
User Query → [Step 0: Intent Recognition] → [Step 1: kb_catalog() Agentic KB scan]
  → [Step 2: kb_doc_catalog() Agentic doc scan]
  → [Step 3: Experience-first (if operational/fault query, strict P0/P1/P2)]
  → [Step 4: Vector confirmation (auxiliary, within confirmed candidates)]
  → [Step 5: Content verification (kb_doc_read mandatory)]
  → [Step 6: Synthesized answer with sources + certainty + blind-spots]
```

### Multi-Strategy Enterprise Search (cross-KB blind spot mitigation)

When standard `kb_search_two_stage` cross-KB search returns candidates from <2 distinct KBs (BM25 stage1 semantic blind spot), auto-upgrade to enterprise multi-strategy:

```
Phase 1: Parallel 3-path recall
  ├── Path A: kb_catalog() → Agentic KB judgment
  ├── Path B: kb_search_two_stage() → BM25 + vector
  └── Path C: kb_search_vector(kb_id="") → pure vector cross-KB semantic

Phase 2: Cross-validation + dedup (A+B+C → merged)
Phase 3: Short-content filtering (<50 chars → downgrade P2)
Phase 4: Content rerank (kb_doc_read each candidate, score 0-8)
Phase 5: Fused presentation (P0→P1, P2 hidden, blind-spots declared)
```

### Experience Credibility Model

| Tier | Condition | Action |
|------|-----------|--------|
| **P0 Strong** | vector≥0.65 ∧ content≥6 ∧ rating≥4 ∧ review≥1 | Strong recommend, pin to top |
| **P1 Reference** | vector≥0.45 ∧ content≥4 | Recommend, annotate credibility |
| **P2 Weak** | vector≥0.35 ∧ content≥3 | Suppress by default (show only on explicit expand) |
| **Discard** | Content verification fails OR vector < 0.35 | Never present |

Credibility modifiers: disputed (≥3 reviews ∧ rating<2.0) → downgrade to max P2; unvetted (0 reviews ∧ 0 applied) → cap at max P1.

Credibility decay: stale unverified (>30d, 0 applied), disputed (rating <2.0 with ≥3 reviews), fully unvetted (0 reviews ∧ 0 applied → max P1).

### Short-Content False Positive Guard

Vector search may return extremely short chunks (e.g., just "## 问题") with inflated scores:
- Chunks < 50 chars → downgrade to P2 (suppressed)
- Document with >50% short-chunk results → downgrade entire document
- Exception: if another P0/P1 chunk from the same document exists, short chunks pass through

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

# MinerU is included via `uv sync` (mineru[core]); first parse auto-downloads models.
# (No manual install step — the old sandbox/mineru_module path was removed.)

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

## Quick Start (All Platforms)

```bash
# 1. First time: one-command setup
./ragctl setup       # Windows: ragctl setup

# 2. Start everything
./ragctl up          # Windows: ragctl up

# 3. Check status
./ragctl status      # Windows: ragctl status
```

**ragctl** is the unified CLI for all operations — start, stop, install, test, config, health checks, KB operations, and more. See `ragctl help` for all commands.

### Platform-specific launchers

```bash
# Windows (either works)
ragctl setup && ragctl up          # Recommended
start.bat                         # Legacy launcher (for reference)

# Linux / macOS (either works)
./ragctl setup && ./ragctl up      # Recommended
./start.sh                        # Legacy launcher (for reference)
```

### One-time setup (manual, if not using `ragctl setup`)

```bash
# 1. Submodules
git submodule update --init --recursive

# 2. Install deps
cd command && npm install && cd ..
cd backend && uv sync && cd ..
cd web && npm install && cd ..
cd kb-mcp && uv sync && cd ..

# 3. Create .env
cp .env.example .env   # or copy manually on Windows

# 4. Start
ragctl up
```

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
5. **Cross-platform** — `pyproject.toml` uses marker-based conditional sources; Win/Linux x86_64 pull cu130 (CUDA) from the PyTorch index, macOS and aarch64 fall back to PyPI (CPU/MPS). `required-environments` allows `win32`/`linux`/`darwin`, so `uv sync` works on all three. Linux uses `prctl(PR_SET_PDEATHSIG)` as the Job Object equivalent for MinerU subprocess cleanup; macOS falls back to process-group + atexit.
6. **Submodule management** — `backend` and `web` are git submodules (the legacy `frontend/` submodule was removed; `.gitmodules` lists only backend + web). After cloning or switching branches, run `git submodule update --init --recursive`. The `kb-mcp` directory is NOT a submodule.
7. **Hierarchical KB search returns empty content** — 父KB（如高分子双向拉伸文献库）的 `kb_search_two_stage` 返回子KB容器条目，content 为空。子KB本身无向量chunk。**Workaround**：用 `kb_graph_kb_overview(kb_id)` 获取子KB UUID列表，在相关子KB内分别检索（见 knowledgebase-search Skill Step 1b）。
8. **Vector index metadata may be missing after initial index** — 部分KB的文档 `vector_index` 字段可能在索引后未写入 YAML 元数据（向量实际存在于 ChromaDB）。用 `kb_reindex(kb_id, force=true)` 修复。
9. **Experience heuristic extraction produces low-quality candidates** — `experience_extract(mode="heuristic")` 的 key_lessons 可能返回章节标题。**推荐**：用 `mode="prepare"` → LLM 精炼。详见 knowledgebase-experience Skill E2a 质量门控。
10. **Graph sub-KB nodes show UUID only** — `kb_graph_kb_overview` 返回的 sub_kbs 列表中 name 字段为 UUID 而非可读名称。
11. **Tag registry accumulates orphan tags** — `kb_tags_list()` 返回的标签列表包含 0 文档引用的历史标签（如测试标签、章节标题）。使用 `kb_tags_cleanup(dry_run=true)` 检测，`dry_run=false` 清理。不影响搜索功能——文档级标签自动过滤。
12. **`kb_graph_build_kb` 返回的 `total_relations` 可能为 0** — 这是 stats 统计 bug，实际图谱数据已写入 Neo4j。**不要**因为返回 0 就认为构建失败。用 `kb_graph_document(doc_path)` 或 `kb_graph_kb_overview(kb_id)` 抽检验证。
13. **Experience credibility thresholds differ between CLAUDE.md and SKILL.md** — CLAUDE.md 的 P0/P1/P2 阈值已同步对齐到 SKILL.md（以 skill 为准，含 content 验证维度）。如需调整请同时改两处。
14. **⭐ kb-mcp MCP 启动检查（强制规则）** — 在执行任何 KB 操作之前，必须先验证 kb-mcp MCP 服务器是否已连接：
    - 调用 `mcp__kb-mcp__backend_status` 检测 MCP 连通性
    - **如果 MCP 工具可用** → 正常执行，所有操作必须通过 MCP 工具（遵循 MCP 优先原则）
    - **如果 MCP 工具不可用**（返回 "No such tool available"）：
      1. 使用 `Bash` 检查核心服务状态：`curl -s http://localhost:8765/api/v1/health`（后端）、`netstat -ano | findstr "8765"`（端口）
      2. 检查 `.mcp.json` 配置是否正确的 `uv run --directory kb-mcp python server.py`
      3. 尝试手动启动 kb-mcp：`cd kb-mcp && start "kb-mcp" uv run python server.py`（Windows）或 `cd kb-mcp && uv run python server.py &`（Linux/macOS）
      4. 如果后端健康但 MCP 仍不可用 → 通知用户 "kb-mcp MCP 未连接，请重启 Claude Code 或检查 .mcp.json"
      5. **仅在 MCP 确认不可用且用户明确允许后**，才可用 HTTP API 作为兜底（如 `curl` 调用 localhost:6789），且必须向用户声明 "MCP 不可用，已用 HTTP API 兜底"
    - Archival Agent 启动时将此检查作为 **Pre-Flight** 步骤，在所有 Step 0 场景诊断之前执行

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

## ⚡ 知识库技能触发契约（强制规则）

**任何对话中，用户输入一旦命中以下 KB 关键词，必须无条件执行以下流程，不得绕过、不得用主观经验替代、不得省略步骤。**

### 第一条：触发不可绕过

用户请求包含下表关键词（中/英/组合）时，**禁止自行处理**，必须调用对应的 knowledgebase 技能：

| 关键词信号（命中任意即触发） | 必须调用的技能 |
|---|---|
| 知识库, KB, 知识库管理, 文档管理, 入库, 上传文档, 解析PDF, 导入, 存储, 保存到 kb, 放文档, 添加文档, 整理知识库, 清洗知识库, 盘点, 大扫除, store, upload, parse, ingest, save to KB, add doc, put document | `Skill("knowledgebase")` |
| 搜索知识库, 检索, 查询, 帮我查, 问一下, 知识库问答, 搜, 哪里, 办法, 怎么解决, search, find, query, ask, retrieve, what is, how to, explain, RAG | `Skill("knowledgebase")` |
| 查看, 展示, 浏览, 有什么, 列出来, 清单, 内容, list, show, overview, tree, browse, display | `Skill("knowledgebase")` |
| 移动, 改名, 重命名, 删除文档, 删除KB, 合并, 更新内容, move, rename, delete, merge, update content | `Skill("knowledgebase")` |
| 批量, 所有文档, 全部, 全量, 统一, batch, bulk, mass, all documents, every KB | `Skill("knowledgebase")` |
| 校验, 核对, 完整性, 检查, 一致性, 检测, verify, validate, integrity, health check, quality audit | `Skill("knowledgebase")` |
| 经验, 经验库, 经验教训, 故障经验, 运维经验, 实践, 案例, 怎么处理, experience, lesson, best practice, previous experience | `Skill("knowledgebase")` |
| 图谱, 知识图谱, 实体关系, graph, knowledge graph, neo4j, entity, build graph | `Skill("knowledgebase")` |

**例外条款**：仅当用户请求明确不涉及KB操作（如问代码实现、聊架构设计）时，可以不走此流程。有疑问时**默认路由到知识库指令**。

### 第二条：路由后必须委托 Archival 子 Agent

`Skill("knowledgebase")` 触发后，调度器的职责是：
1. 读取用户输入 → 匹配上表 → 确定场景标签
2. **立即委托 Archival 子 Agent**：`Agent(subagent_type="archival", ...)`
3. Archival 接到委托后，执行其 `Step 0 场景诊断协议` 自主确认场景
4. 路由到子 Skill（如 `knowledgebase-ingest`）严格按步骤执行

**严禁**：调度器在 skill 内自行执行操作，必须委托 Archival。

### 第三条：Archival 执行不可省略步骤

每个子 Skill 定义了完整的步骤流程（如 Ingest 的 A0→A9）。Archival **必须严格按流程执行，不得跳过任何质量门控**：

| 门控 | 规则 |
|---|---|
| A0 去重 | 向量≥0.85指纹判重，必做 |
| A2-Q 解析质量 | 乱码/空正文/二进制残留 → 拒绝入库 |
| A3b 标签质量 | 黑名单过滤 + 归一化 + 正文回查，必做 |
| A3c 描述质量 | 四要素 + 内容回查，必做 |
| A5 存储选择 | 解析文档必须用 `kb_doc_save_parsed`，禁止用 `kb_doc_create` |
| A6-V 索引验证 | 索引后必验证 collection 正确 + chunks ≥ 1 |
| A7 八项终检 | C1-C8 全部 ✅ 才算完成 |

### 第四条：违规自纠机制

如果在同一对话中发现之前违反了上述规则（如未触发skill直接操作、或用错工具）：
- **立即停止当前操作**
- 调用正确 skill 或子Agent重新执行
- 修正已产生的错误（如误用 `kb_doc_create` → 清理后改用 `kb_doc_save_parsed`）
- 向用户说明纠正了什么

### 第五条：⭐ MCP 优先原则（2026-07-13 新增，全库强制执行）

**当 MCP 工具已连接可用时，所有知识库操作必须通过 MCP 工具执行`（mcp__kb-mcp__*）`，不得绕过。**

| ❌ 禁止 | ✅ 必须 |
|---------|---------|
| 写 `curl` 终端命令操作 KB | 用 `mcp__kb-mcp__kb_*` 工具 |
| 写 `python -c` 调用 HTTP API | 用 `mcp__kb-mcp__parse_doc` 工具 |
| 用 `wget`/`httpx` 直调后端 | 用 `mcp__kb-mcp__kb_doc_*` 工具 |
| Bash/PowerShell 中硬编码 API URL | MCP 保证了原子操作和审计追踪 |

**例外条款**：仅在 MCP 明确不可用（MCP 连接失败且用户确认后），才可用终端命令或 HTTP API 作为兜底。兜底后必须向用户声明 "MCP 不可用，已用 HTTP API 兜底"。
