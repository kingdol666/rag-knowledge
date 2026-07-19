<h1 align="center">
  <img src="../docs/images/logo.svg" alt="kb-mcp" width="80" />
  <br/>
  kb-mcp
</h1>

<p align="center">
  <strong>MCP 服务器 · 74 个工具 · KB 全生命周期 · 搜索 · 图谱 · 经验</strong><br/>
  <em>连接 Claude Code 代理与 RAG Knowledge Platform 的 MCP 工具层</em>
</p>

<p align="center">
  <a href="#-快速开始"><img src="https://img.shields.io/badge/%E5%BF%AB%E9%80%9F%E5%BC%80%E5%A7%8B-3%20%E6%AD%A5-blue?style=for-the-badge" /></a>
  <a href="#-工具74"><img src="https://img.shields.io/badge/MCP-74%20%E5%B7%A5%E5%85%B7-blueviolet?style=for-the-badge" /></a>
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
- [🔌 工具（74）](#-工具74)
- [📡 客户端库](#-客户端库)
- [⚙️ 配置](#️-配置)
- [📁 项目结构](#-项目结构)
- [🔧 技术栈](#-技术栈)
- [🤝 贡献](#-贡献)
- [📄 许可证](#-许可证)

## 🌟 概述

`kb-mcp` 是 MCP（Model Context Protocol）服务器，将 Claude Code（或任何 MCP 兼容代理）桥接到 RAG Knowledge Platform。提供 **74 个工具**，按 13 个类别组织 — 足以在不离开代理对话的情况下管理生产知识库的方方面面。

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
│         ~74 @mcp.tool() 定义              │
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
| **服务生命周期**（启动、停止、状态） | `server.py` → `project_manager.py` → 子进程管理 | 直接进程控制，实现静默无头启动 |

## 🚀 快速开始

```bash
# 1. 安装（3 个轻量依赖：mcp + httpx + pyyaml）
uv sync

# 2. 独立运行（stdio 模式 — 供 MCP 客户端使用）
uv run python server.py

# 3. SSE 模式运行（供 HTTP 传输使用）
uv run python server.py --http
```

> **通常无需手动运行 kb-mcp。** Claude Code 在打开项目时通过 `../.mcp.json` 自动启动。首次 `uv run` 自动同步依赖。全局使用时，`claude plugin install rag-knowledge` 将其注册到 `~/.claude/.mcp.json`。

## 🔌 工具（74）

所有工具可通过 `mcp__kb-mcp__*` 从任何 MCP 客户端访问。按领域组织：

### 服务生命周期（4）— 静默、无头管理

| 工具 | 说明 |
|------|------|
| `kb_project_start(backend, web, neo4j, mode, wait)` | 静默启动服务（无头、日志落盘、幂等）。`wait=true` 阻塞至 HTTP 就绪。 |
| `kb_project_status()` | 服务是否运行？端口 + HTTP 健康 + PID + MinerU + 日志路径 + `ready` 布尔值。 |
| `kb_project_preflight()` | 项目是否已配置？`.env`/子模块/依赖检查 + 精确 `fix` 命令。 |
| `backend_status()` | 快速后端健康检查。 |

### KB 增删改查（6）

| 工具 | 说明 |
|------|------|
| `kb_list()` | 列出所有知识库及元数据。 |
| `kb_create(name, description, parent_id)` | 创建新 KB（可选作为子 KB）。 |
| `kb_update(kb_id, name, description)` | 更新 KB 元数据。 |
| `kb_delete(kb_id)` | 删除 KB 及其所有文档。 |
| `kb_catalog()` | Agentic 优先的 KB 扫描 — 名称、描述、文档数、标签词汇表。 |
| `kb_doc_catalog(kb_id)` | 按 KB 的文档扫描 — 每个文档的元数据概览。 |

### 文档增删改查（9）

| 工具 | 说明 |
|------|------|
| `kb_doc_create(kb_id, name, content, description)` | 创建新文档（含内容 + 元数据）。 |
| `kb_doc_read(kb_id, doc_path)` | 读取完整文档内容（用于内容验证步骤）。 |
| `kb_doc_update_meta(kb_id, doc_path, name, description)` | 更新文档元数据。 |
| `kb_doc_update_content(kb_id, doc_path, content)` | 替换文档内容。 |
| `kb_doc_delete(kb_id, doc_path)` | 删除单个文档。 |
| `kb_doc_batch_delete(kb_id, doc_paths)` | 批量删除文档。 |
| `kb_doc_move(doc_path, target_kb_id)` | 移动文档至不同 KB。 |
| `kb_doc_save_parsed(kb_id, doc_path, ...)` | 保存解析后内容（OCR 后）— 不同于 `kb_doc_create`。 |
| `kb_get_documents(kb_id)` | 列出 KB 内所有文档及完整元数据。 |

### 搜索（4）

| 工具 | 说明 |
|------|------|
| `kb_search(query, kb_ids)` | 跨 KB 元数据关键词搜索。 |
| `kb_search_vector(query, kb_id)` | 语义向量搜索（BGE-M3 1024 维）。 |
| `kb_search_two_stage(query, balance_kbs)` | **主要搜索工具。** BM25 召回 → 向量重排，支持跨 KB 均衡。 |
| `kb_search_stats()` | 搜索索引统计（文档数、chunk 数、集合大小）。 |

### 文件系统（4）

| 工具 | 说明 |
|------|------|
| `fs_get_tree()` | 完整文件树及元数据（文件夹、文件、大小、日期）。 |
| `fs_get_children(node_path)` | 指定文件夹节点的子节点。 |
| `fs_get_count()` | 文件和文件夹总数。 |
| `fs_upload_file(path, content)` | 上传并注册文件至文件系统。 |

### 知识图谱（14）

| 子类别 | 工具 |
|--------|------|
| **健康 & 统计** | `kb_graph_health()`, `kb_graph_stats()` |
| **搜索** | `kb_graph_search(keyword, node_type)` — `node_type`: all（默认）/ document / kb / tag |
| **探索** | `kb_graph_neighbors(node_id)`, `kb_graph_kb_overview(kb_id)`, `kb_graph_cross_kb_documents()` |
| **文档中心** | `kb_graph_document(doc_path)`, `kb_graph_document_related(doc_path)`, `kb_graph_document_paths(doc_path)`, `kb_graph_documents_by_tag(tag)` |
| **中心度** | `kb_graph_central_documents(kb_id)` |
| **构建 & 清理** | `kb_graph_build(kb_id)`（空 = 全库）, `kb_graph_delete_document(doc_path)`, `kb_graph_delete_kb(kb_id)` |

### 经验（22）

| 子类别 | 工具 |
|--------|------|
| **增删改查** | `experience_create()`, `experience_read(id)`, `experience_list()`, `experience_update()`, `experience_delete()` |
| **操作** | `experience_apply(id)`, `experience_review(id, rating, comment)`, `experience_summary(kb_id)` |
| **搜索** | `experience_search(query)`, `experience_search_vector(query)`, `experience_search_global(query)`, `experience_search_smart(query)`（推荐入口）, `experience_rerank(query, exps)` |
| **提取 & 草稿** | `experience_extract(mode, kb_id)`, `experience_drafts_list()`, `experience_draft_read(id)`, `experience_draft_approve(id)`, `experience_draft_reject(id)` |
| **健康** | `experience_check_stale(kb_id)`（空 = 全库）, `experience_sync_kb(kb_id)`, `experience_dashboard()`, `experience_apply_decay()` |

### 标签 & 清理（4）

| 工具 | 说明 |
|------|------|
| `kb_tags_list(kb_id)` | 列出所有标签及文档引用数。 |
| `kb_doc_update_tags(doc_path, tags)` | 设置文档标签。 |
| `kb_doc_get_by_tag(tag)` | 按标签查找文档。 |
| `kb_tags_cleanup(dry_run)` | 移除孤儿标签（0 文档引用）。 |

### 解析（3）— 非阻塞

| 工具 | 说明 |
|------|------|
| `parse_doc(file_path, kb_id)` | 提交文件异步解析。立即返回 `task_id`。 |
| `parse_doc_batch(file_paths, kb_id)` | 批量提交文件解析。 |
| `parse_task_status(task_id)` | 轮询解析任务状态（等待中 → 处理中 → 完成/失败）。 |

### 向量索引（3）

| 工具 | 说明 |
|------|------|
| `kb_index_document(doc_path, kb_id)` | 将单个文档索引至向量存储。 |
| `kb_batch_index(kb_id)` | 批量索引 KB 中所有未索引文档。 |
| `kb_reindex(kb_id, force)` | 重建 KB 向量索引。`force=true` 覆盖已有索引。 |

### 清理（1）

| 工具 | 说明 |
|------|------|
| `kb_cleanup_orphan_collections(dry_run)` | 检测并移除孤儿 ChromaDB 集合。 |

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
├── server.py                # FastMCP 服务器 — ~74 @mcp.tool() 定义（零 HTTP 代码）
├── project_manager.py       # 服务生命周期：启动/停止/状态（子进程管理）
├── task_registry.py         # 进程内异步后台任务管理器（解析作业）
├── config.py                # 从共享 config.yml 读取 URL（零硬编码路径）
├── plugin_install.py        # 全局注册：ragctl → ~/.local/bin、MCP → ~/.claude/.mcp.json
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

MIT · 隶属于 [RAG Knowledge Platform](https://github.com/kingdol666/rag-knowledge)
