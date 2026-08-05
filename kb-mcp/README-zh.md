<h1 align="center">
  <img src="../docs/images/logo.svg" alt="kb-mcp" width="80" />
  <br/>
  kb-mcp
</h1>

<p align="center">
  <strong>MCP 服务器 · 94 个工具 · KB 全生命周期 · 搜索 · 图谱 · 经验 · SOUL 人格</strong><br/>
  <em>连接 Claude Code 代理与 RAG Knowledge Platform 的 MCP 工具层</em>
</p>

<p align="center">
  <a href="#-快速开始"><img src="https://img.shields.io/badge/%E5%BF%AB%E9%80%9F%E5%BC%80%E5%A7%8B-3%20%E6%AD%A5-blue?style=for-the-badge" /></a>
  <a href="#-工具94"><img src="https://img.shields.io/badge/MCP-94%20%E5%B7%A5%E5%85%B7-blueviolet?style=for-the-badge" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" /></a>
  <a href="#-技术栈"><img src="https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge" /></a>
  <a href="#-技术栈"><img src="https://img.shields.io/badge/FastMCP-latest-9cf?style=for-the-badge" /></a>
</p>

---

<p align="center">
  <sub><a href="./README.md">English</a> · <a href="./README-zh.md"><b>中文</b></a></sub>
</p>

---

## 📌 目录

- [🌟 概述](#-概述)
- [🏗️ 架构](#️-架构)
- [🚀 快速开始](#-快速开始)
- [🔌 工具（94）](#-工具94)
- [📡 客户端库](#-客户端库)
- [⚙️ 配置](#️-配置)
- [📁 项目结构](#-项目结构)
- [🔧 技术栈](#-技术栈)
- [🤝 贡献](#-贡献)
- [📄 许可证](#-许可证)

## 🌟 概述

`kb-mcp` 是 MCP（Model Context Protocol）服务器，将 Claude Code（或任何 MCP 兼容代理）桥接到 RAG Knowledge Platform。提供 **94 个工具**，按 12 个类别组织 — 足以在不离开代理对话的情况下管理生产知识库的方方面面。

**核心原则：**

- **MCP 优先** — 所有 KB 操作通过 `mcp__kb-mcp__*` 工具执行。禁止 `curl`、禁止原始 HTTP、禁止终端命令操作 KB。
- **server.py 零 HTTP 代码** — `server.py` 只包含纯 MCP 工具定义。所有 HTTP 逻辑隔离在 `kb_client/client.py` 中。
- **默认非阻塞** — 解析工具立即返回 `task_id`；后台任务注册表处理异步工作。
- **直接文件读取** — 尽可能直接读取 `.tree-fs.json` 和 `.knowledge-base.yml`（写操作仍走 web 代理/后端 API）。
- **全局注册** — 设置 `RAG_PROJECT_ROOT` 后，kb-mcp 可从任何目录、任何 Claude Code 会话连接。

## 🏗️ 架构

```
┌──────────────────────────────────────────┐
│          Claude Code / MCP 客户端         │
│          mcp__kb-mcp__* (stdio)          │
└──────────────────┬───────────────────────┘
                   │ MCP stdio (FastMCP)
┌──────────────────▼───────────────────────┐
│              kb-mcp/server.py             │
│         94 @mcp.tool() 定义              │
│         零 HTTP 代码 — 向下委托            │
└──────┬──────────────────────┬────────────┘
       │ kb_client (HTTP)     │ 直接文件 I/O
       ▼                      ▼
┌──────────────┐    ┌──────────────────────┐
│  Web 代理     │    │ .tree-fs.json         │
│  :6789/:3000 │    │ .knowledge-base.yml   │
└──────┬───────┘    │ web/storage/...       │
       │            └──────────────────────┘
┌──────▼───────┐
│   后端        │
│   :8765/8001 │
└──────────────┘
```

**按操作类型的数据流：**

| 操作类型 | 路径 | 原因 |
|---------|------|------|
| **写**（创建、更新、删除、解析、保存） | `server.py` → `kb_client` → HTTP → Web 代理 → 后端 API | 写入需要磁盘、`.tree-fs.json` 和 `.knowledge-base.yml` 三者一致 |
| **读**（目录、搜索、列表、统计） | `server.py` → 直接读文件 `.tree-fs.json` + `.knowledge-base.yml` | 读取零后端负载；更快且避免代理依赖 |
| **服务生命周期**（启动、状态、预检、版本、更新） | `server.py` → `project_manager.py` → 子进程 + `ragctl` | 静默无头启动 + 版本感知更新 |

## 🚀 快速开始

```bash
# 1. 安装（3 个轻量依赖：mcp + httpx + pyyaml）
uv sync

# 2. 独立运行（stdio 模式 — 供 MCP 客户端使用）
uv run python server.py

# 3. SSE 模式运行（供 HTTP 传输使用）
uv run python server.py --http
```

> **通常无需手动运行 kb-mcp。** Claude Code 在打开项目时通过 `../.mcp.json` 自动启动。首次 `uv run` 自动同步依赖。全局使用时，`claude plugin install rag-knowledge` 将其注册到 `~/.claude.json` → `mcpServers`。

## 🔌 工具（94）

所有工具均可通过 `mcp__kb-mcp__*` 从任何 MCP 客户端访问。按领域组织：

### 服务生命周期（4）

| 工具 | 说明 |
|------|------|
| `backend_status()` | Get backend service health and MinerU OCR engine status. |
| `kb_project_start()` | Silently start project services. HEADLESS on every OS and every mode — |
| `kb_project_status()` | Full project service status. |
| `kb_project_update()` | Check GitHub for a newer version of the project and optionally pull it. |

### 知识库 CRUD（4）

| 工具 | 说明 |
|------|------|
| `kb_create()` | Create a new knowledge base. parent_id is an optional tree folder UUID for nesting (omit for root). Returns knowledgeBase with id (UUID) and path -- both work as kb_id in other tools. |
| `kb_delete()` | Delete an entire knowledge base and all its contents (irreversible). kb_id accepts either the path string or the UUID returned by kb_create. |
| `kb_list()` | List all knowledge bases with id, name, description, and document count. |
| `kb_update()` | Update a knowledge base's name and/or description. kb_id accepts path or UUID. |

### 文档 CRUD 与列表（11）

| 工具 | 说明 |
|------|------|
| `kb_doc_batch_delete()` | Delete multiple documents at once. |
| `kb_doc_create()` | Create a new Markdown document in a KB. Auto-dedup on name collision. |
| `kb_doc_delete()` | Delete a single document. |
| `kb_doc_get_by_tag()` | Find documents by tag across all KBs (or one KB if kb_id given). |
| `kb_doc_move()` | Move a document to a different knowledge base. |
| `kb_doc_read()` | Read the content of a document (Markdown body, paginated). |
| `kb_doc_save_parsed()` | Save parsed markdown (FULL content + images) into a knowledge base. |
| `kb_doc_update_content()` | Overwrite a document's content. |
| `kb_doc_update_meta()` | Update a document's metadata (name, description). |
| `kb_doc_update_tags()` | Update a document's tags. kb_id accepts UUID; doc_path accepts full path or bare filename. |
| `kb_get_documents()` | List all documents inside a knowledge base. kb_id accepts path or UUID. |

### 搜索（4）

| 工具 | 说明 |
|------|------|
| `kb_search()` | Search KB metadata by keyword across ALL knowledge bases. Scans only document |
| `kb_search_stats()` | Vector index statistics. View each knowledge base's index status in the vector database. |
| `kb_search_two_stage()` | Two-stage precision search: first broad search to locate candidate documents, then vector fine-search for chunks. |
| `kb_search_vector()` | Vector semantic search for document chunks. |

### 向量索引（6）

| 工具 | 说明 |
|------|------|
| `kb_batch_index()` | Batch index documents (vector + graph). |
| `kb_cleanup_orphan_collections()` | Detect and clean up orphan/duplicate vector collections (vector index residue from deleted/renamed KBs). |
| `kb_find_duplicates()` | Find duplicate / near-duplicate documents via content hash + vector similarity. |
| `kb_index_document()` | Index a single document (vector + graph). Stores document content (or existing document) into the vector database and records vector_index in metadata. |
| `kb_reindex()` | Rebuild vector index and knowledge graph. Empty kb_id rebuilds all. |
| `kb_task_status()` | Check the status of ANY non-blocking background task (kb_reindex, kb_graph_build). |

### 文件系统（3）

| 工具 | 说明 |
|------|------|
| `fs_get_children()` | Get immediate children (folders + files) of a folder. |
| `fs_get_tree()` | Get the full file system tree of knowledge bases and their contents. |
| `fs_upload_file()` | Upload a local file into the file system tree. file_path is an absolute local disk path. parent_id is a tree folder UUID (empty = root). |

### 知识图谱（11）

| 工具 | 说明 |
|------|------|
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

### 经验（20）

| 工具 | 说明 |
|------|------|
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
| `experience_extract()` | E0/E1: Auto-extract experience candidates from KB documents. |
| `experience_list()` | List experiences in a knowledge base, supports filtering by scenario/category/tag. Results sorted by rating descending. |
| `experience_read()` | Read full experience information (metadata + content body). |
| `experience_rerank()` | Semantic reranking for experience search results -- multi-dimensional scoring. |
| `experience_review()` | Review an experience with a rating (0-5) and comment. Automatically updates the experience's average rating and review count. |
| `experience_search_global()` | Cross-KB global experience search -- QDCVR pipeline (isomorphic with document search). |
| `experience_search_smart()` | Intelligent multi-path experience retrieval -- the RECOMMENDED entry point for experience search. |
| `experience_summary()` | Get experience statistics summary, including total count, distribution by category, distribution by severity, total applications, average rating, top 5 experiences. |
| `experience_sync_kb()` | E6: Mark entire KB for sync (stale/orphan experiences marked needs_sync). |
| `experience_update()` | Update an experience record. Only pass fields to update; omitted fields stay unchanged. |

### 冥想（自动洞察调度）（6）

| 工具 | 说明 |
|------|------|
| `experience_meditation_config_get()` | Get meditation config for a KB. |
| `experience_meditation_config_update()` | Update meditation config for a KB. Only pass fields to change. |
| `experience_meditation_history()` | List recent meditation runs, optionally filtered by KB. |
| `experience_meditation_run()` | Manually trigger a meditation run. Optionally scoped to one KB. |
| `experience_meditation_status()` | Get meditation status: scheduler, harness health, circuit breaker, per-KB configs. |
| `experience_meditation_task_status()` | Check the status of a non-blocking meditation run. |

### 标签（2）

| 工具 | 说明 |
|------|------|
| `kb_tags_cleanup()` | Detect and clean up orphan tags (tags referenced by 0 documents). |
| `kb_tags_list()` | List all registered tags in the system. |

### 解析（非阻塞）（3）

| 工具 | 说明 |
|------|------|
| `parse_doc()` | Parse a document (PDF / Image / Word / Excel) into Markdown. |
| `parse_doc_batch()` | Batch: parse multiple documents (PDF / Image / Word / Excel) into Markdown. |
| `parse_task_status()` | Check the status of a non-blocking parse task. |

### 🧠 SOUL 人格（20）

| 工具 | 说明 |
|------|------|
| `soul_ask()` | 人格注入问答: 人格一致 + 知识增强 + 可溯源引用 + PAS 分。 |
| `soul_calibrate()` | 校准: 对校准集重跑自评,输出漂移报告;提示词变更自动全量重跑。 |
| `soul_checkpoint()` | 生成时间戳快照(5 人格文档 + soul-config SHA256 + memories/drafts 清单+hash)。 |
| `soul_config_update()` | 更新 SOUL 配置(kb_scope/domain_labels/supported_task_types/route_weight)。 |
| `soul_delete()` | 删除 SOUL: 先 checkpoint(快照保留)→ 删 KB(web 层)→ 清理路由缓存 + tombstone。 |
| `soul_eval()` | 单条四维自评(接地性/完整性/思维一致/信息增益)。 |
| `soul_evaluate()` | 评价 Agent 四维人格评分(RL 奖励信号): identity/values/thinking/language + overall。 |
| `soul_export()` | 导出训练数据 JSONL(供 LoRA/DPO): question/evidence_paths/answer/scores/persona。 |
| `soul_gen_cognition_drafts()` | 生成认知草稿(策略更新建议): 即时评价后, 低分维度产出优化行 → cognition-drafts/。 |
| `soul_init()` | 创建新 SOUL: 模板复制 4 文档 + soul-config + 初始 profile + 索引。 |
| `soul_learn()` | 自主学习: 提问→带引用自答→四维自评(双判官)→蒸馏(人格记忆+知识经验)。 |
| `soul_learn_all()` | 全库自举: 遍历全部 SOUL × kb_scope 批量增量学习。 |
| `soul_list()` | 列出全部 SOUL 库(排除模板)。 |
| `soul_qdcvr_ask()` | QDCVR + SOUL 组合问答: 先按 knowledgebase-search skill 流程检索知识, |
| `soul_reflect()` | 反思: 认知草稿 vs 人格定义结构化 diff 报告(先自动 checkpoint)。 |
| `soul_review_drafts()` | 草稿审批闭环: list/approve/reject 人格记忆或认知草稿。 |
| `soul_rollback()` | 回滚到检查点(memories/ + cognition-drafts/;宪法层永不回滚)。 |
| `soul_router()` | 独立路由工具: 返回候选 SOUL 排序(可审计入口)。 |
| `soul_status()` | SOUL 学习指标: 草稿/记忆/缺口/判官分歧/路由统计/成本。 |
| `soul_train_rl()` | RL 强化训练: 好奇心探索(learn) × 评价 Agent(reward) × 策略更新(认知草稿)。 |
## 📡 客户端库

`kb_client/` 包包含所有 HTTP 逻辑，与 MCP 工具定义清晰分离：

```python
from kb_client import KbClient

client = KbClient(
    web_url="http://localhost:6789",
    backend_url="http://localhost:8765",
)

# KB 操作
kbs = client.list_kbs()
client.create_kb(name="Research Papers", description="...")

# 搜索
results = client.search_two_stage(query="transformer architecture")

# 解析
task_id = client.parse_doc(file_path="/path/to/paper.pdf", kb_id="kb-123")
status = client.get_parse_status(task_id)
```

客户端处理所有边界情况：代理回退、`trust_env=False` 防止 HTTPS_PROXY 劫持、路径规范化、API 响应解析。

## ⚙️ 配置

`kb-mcp/config.py` 从**根目录 `config.yml`** 和环境变量读取 URL。无硬编码路径或端口。

| 变量 | 来源 | 用途 |
|------|------|------|
| `BACKEND_URL` | 根 config.yml 或环境变量 | 写操作的后端 API |
| `WEB_URL` | 根 config.yml 或环境变量 | 文件系统读操作的 Web 代理 |
| `APP_MODE` | 环境变量 (`dev` / `prod`) | 选择 config.yml 的 dev 或 prod 段 |
| `TREE_STORAGE_PATH` | 环境变量 | KB 文件存储路径（用于直接读取） |

monorepo 根目录的 `.mcp.json` 为 Claude Code 自动配置 kb-mcp：

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

> **注意：** `.mcp.json` 不支持 `cwd` 字段。请使用 `--directory kb-mcp`（所有平台通用）。

## 📁 项目结构

```
kb-mcp/
├── server.py                # FastMCP 服务器 — 94 @mcp.tool() 定义（零 HTTP 代码）
├── project_manager.py       # 服务生命周期 + 版本/更新（委托 ragctl）
├── task_registry.py         # 进程内异步后台任务管理器（解析作业）
├── config.py                # 从共享 config.yml 读取 URL（零硬编码路径）
├── plugin_install.py        # 全局注册：ragctl → ~/.local/bin、MCP → ~/.claude.json → mcpServers
├── kb_client/
│   └── client.py            # 所有 HTTP 逻辑（server.py 零 HTTP — 委托至此）
├── pyproject.toml           # 3 个依赖：mcp + httpx + pyyaml
├── uv.lock                  # 锁定依赖版本
├── test_smoke.py            # 导入冒烟测试（快速，无需服务运行）
└── tests/                   # 集成测试脚本
```

## 🔧 技术栈

| 组件 | 技术 |
|------|------|
| MCP 框架 | FastMCP (Python) |
| HTTP 客户端 | httpx（带 `trust_env=False`） |
| 配置解析 | PyYAML |
| 异步任务 | 进程内任务注册表（无 Celery、无 Redis） |
| 包管理器 | uv（hatchling 构建） |
| 传输方式 | stdio（主要）+ SSE（可选） |

## 🤝 贡献

1. Fork → 功能分支 → 提交 → 推送 → PR
2. 新增工具：在 `server.py` 加 `@mcp.tool()`，HTTP 逻辑放 `kb_client/client.py` — 保持清晰分离
3. 用 `uv run python test_smoke.py` 做导入完整性检查；完整集成测试需运行中的服务
4. 如需新增依赖，请保持轻量 — kb-mcp 设计目标为快速启动

## 📄 许可证

MIT © [kingdol](https://github.com/kingdol666) · 隶属于 [RAG Knowledge Platform](https://github.com/kingdol666/rag-knowledge)
---

<div align="center">

<sub>隶属于</sub>
<a href="https://github.com/kingdol666/rag-knowledge"><b>RAG Knowledge Platform</b></a>
<br>
⭐ <a href="https://github.com/kingdol666/rag-knowledge">在 GitHub 上给我们点星</a> ⭐

</div>
