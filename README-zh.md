<h1 align="center">
  <img src="./docs/images/logo.svg" alt="RAG Knowledge Platform" width="96" />
  <br/>
  RAG Knowledge Platform
</h1>

<p align="center">
  <strong>企业级文档智能与 Agentic 知识库平台</strong><br/>
  <em>PDF 解析 · QDCVR 语义搜索 · Neo4j 知识图谱 · 经验库<br/>76 个 MCP 工具 · 14 个 Claude Code 技能 · 静默无头启动 · 跨平台</em>
</p>

<p align="center">
  <a href="#-三种安装方式"><img src="https://img.shields.io/badge/%E5%BF%AB%E9%80%9F%E5%BC%80%E5%A7%8B-3%20%E7%A7%8D%E6%96%B9%E5%BC%8F-blue?style=for-the-badge&logo=rocket" /></a>
  <a href="https://github.com/kingdol666/rag-knowledge/stargazers"><img src="https://img.shields.io/github/stars/kingdol666/rag-knowledge?style=for-the-badge&color=yellow" /></a>
  <a href="#-核心特性"><img src="https://img.shields.io/badge/%E7%89%B9%E6%80%A7-8%20%E5%A4%A7%E6%94%AF%E6%9F%B1-9cf?style=for-the-badge" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" /></a>
  <a href="https://github.com/kingdol666/rag-knowledge/releases"><img src="https://img.shields.io/github/v/release/kingdol666/rag-knowledge?style=for-the-badge&color=blueviolet" /></a>
  <a href="#-platforms"><img src="https://img.shields.io/badge/platform-Win%20%7C%20Linux%20%7C%20macOS-lightgrey?style=for-the-badge" /></a>
  <a href="#-mcp-工具-76"><img src="https://img.shields.io/badge/MCP-76%20tools-blueviolet?style=for-the-badge&logo=code" /></a>
  <a href="#-技能-14"><img src="https://img.shields.io/badge/Skills-14-orange?style=for-the-badge&logo=openai" /></a>
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

## 📌 目录

- [🚀 三种安装方式](#-三种安装方式)
- [✅ 前置要求](#-前置要求)
- [💡 为什么选择这个项目](#-为什么选择这个项目)
- [🌟 核心特性](#-核心特性)
- [🖥️ 使用方式](#️-使用方式)
- [📋 CLI 命令参考](#-cli-命令参考)
- [🔌 MCP 工具（76）](#-mcp-工具76)
- [🎯 技能（14）](#-技能14)
- [🏗️ 架构](#️-架构)
- [⚙️ 配置](#️-配置)
- [🤫 静默运行](#-静默运行)
- [🛠️ 故障排查](#️-故障排查)
- [❓ 常见问题](#-常见问题)
- [📁 项目结构](#-项目结构)
- [🔧 技术栈](#-技术栈)
- [🤝 贡献](#-贡献)

---

## 🚀 三种安装方式

> [!IMPORTANT]
> **仅支持以下三种安装方式。** 每种方式都能产生完整可用的平台 — 选择最适合你的。

| 方式 | 适合人群 | 最终结果 |
|------|---------|---------|
| **[A. Claude Code 插件](#方式-a-claude-code-插件推荐)** · *推荐* | 使用 Claude Code，希望全局可用 | 14 个技能 + 76 个 MCP 工具在**任意目录**、任意 Claude Code 会话中可用 |
| **[B. Skills 复制 + 初始化向导](#方式-b-skills-复制--初始化向导)** | 不想装插件，但仍需要引导式安装 | Skills 复制到 `~/.claude/skills/`；项目 clone 到你指定路径；`/knowledgebase-init` 完成后续工作 |
| **[C. Git Clone + 本地项目](#方式-c-git-clone--本地项目)** | 需要完全手动控制，所有内容在一个目录内 | 所有内容在项目目录内；skills + MCP 仅在此目录打开 Claude Code 时加载 |

---

### 方式 A: Claude Code 插件 · *推荐*

最快的方式。插件将 skills 安装到全局，在**任意 Claude Code 会话、任意目录、任意项目**中可用。

```bash
# 第一步 — 安装插件（一条命令，约 30 秒）
claude plugin marketplace add kingdol666/rag-knowledge
claude plugin install rag-knowledge

# 第二步 — 启动初始化向导（直接说）
"初始化知识库"
# 或者
"set up the knowledge base"
```

`knowledgebase-init` 技能会检测你的操作系统、检查前置条件、自动定位/克隆项目、安装所有依赖、引导你完成 10 个交互式配置问题、全局注册 `ragctl`、启动所有服务 — 全程静默，零终端窗口。

**安装完成后你将获得：**
- `ragctl` 在任意终端可用
- 14 个 skills 在任意 Claude Code 目录可用
- 76 个 MCP 工具全局可用（插件的 `mcpServers` 声明提供了全局 kb-mcp）
- Web UI：`http://localhost:6789`（dev）或 `http://localhost:3000`（prod）
- Claude Chat：`http://localhost:6789/claude-chat`

<details>
<summary><b>🧙 每个阶段详解</b></summary>

| 阶段 | 内容 |
|------|------|
| 0 | 检测操作系统（Windows / Linux / macOS） |
| 1 | 检查前置条件（uv、node、git、docker）—— 缺失时给出安装命令 |
| 2 | 自动定位项目（插件缓存 → git root → CWD 搜索 → 询问用户 + clone） |
| 3 | 确认依赖安装（约 6 GB 总计，10–30 分钟） |
| 4 | 执行 `ragctl setup` — 安装所有依赖 + BGE-M3 模型 |
| 5 | 根据 10 个交互式配置问题写入 `.env` |
| 6 | 全局注册 `ragctl`（`~/.local/bin`） |
| 7 | （可选）全局注册 kb-mcp 到 `~/.claude.json` — 默认跳过，因插件已覆盖 |
| 8 | 启动 Neo4j 容器（如用户选择启用） |
| 9 | 静默启动所有服务 |
| 10 | 全链路验证 — 后端健康、MCP 工具、KB 列表、搜索、图谱健康 |
| 11 | 安装报告 — 端口、URL、后续步骤 |
</details>

> [!NOTE]
> **插件安装已提供全局 MCP 覆盖。** `plugin.json` 中的 `mcpServers` 字段为所有 Claude Code 会话注册 kb-mcp。初始化向导的阶段 7 会询问是否也要写入 `~/.claude.json` — 默认是"跳过"，因为插件已经处理了。

---

### 方式 B: Skills 复制 + 初始化向导

不想安装插件，但仍想要引导式交互安装时使用此方式。手动将 skills 复制到全局 skills 目录；初始化技能会识别已有项目并完成后续配置。

```bash
# 第一步 — Clone 仓库到你想要的位置
git clone https://github.com/kingdol666/rag-knowledge.git ~/rag-knowledge

# 第二步 — 复制 skills 和 agent 到全局 Claude Code 目录
mkdir -p ~/.claude/skills ~/.claude/agents

# 复制所有 knowledgebase skills
cp -r ~/rag-knowledge/.claude/skills/knowledgebase* ~/.claude/skills/

# 复制 Archival agent
cp ~/rag-knowledge/.claude/agents/knowledge-admin.md ~/.claude/agents/

# 第三步 — 启动初始化向导（在任意 Claude Code 会话中）
"初始化知识库"
# 或者
"/knowledgebase-init"
```

初始化技能会检测 `~/rag-knowledge` 中的已有项目（通过 Phase 2 自动检测），然后：

1. **前置检查** — 验证 uv、node、git 是否已安装；缺失的自动安装
2. **安装依赖** — `ragctl setup`（所有依赖 + BGE-M3 模型）
3. **交互配置** — 10 个问题（端口、存储、认证、Neo4j、模型源…）
4. **全局注册** — `ragctl install`（ragctl 在任意终端可用）
5. **可选 MCP 全局** — 写入 kb-mcp 到 `~/.claude.json` → `mcpServers`（由你选择 Y/n）

> [!NOTE]
> 阶段 7 全局 MCP 注册后，**重启 Claude Code**（或 `/mcp` 重连）使新的全局 MCP 配置生效。

> [!WARNING]
> 复制 skills 后，**重启 Claude Code** 使新 skills 出现。初始化向导（`/knowledgebase-init`）通过在任意 Claude Code 会话中说"初始化知识库"或"set up the knowledge base"来触发。

**安装完成后你将获得：**
- `ragctl` 在任意终端全局可用
- 项目代码位于 `~/rag-knowledge`（或你选择的路径）
- Skills 全局可用（已复制到 `~/.claude/skills/`）
- MCP 工具全局可用（如果你在阶段 7 选择了 Y）

---

### 方式 C: Git Clone + 本地项目

所有内容在一个目录内 — skills 和 MCP 仅在**项目目录内**打开 Claude Code 时加载。

```bash
# 第一步 — Clone 仓库
git clone https://github.com/kingdol666/rag-knowledge.git
cd rag-knowledge

# 第二步 — 一键安装
# Windows (PowerShell)
./ragctl setup

# Linux / macOS (Bash)
./ragctl setup

# 第三步 — 启动所有服务
# Windows
./ragctl up

# Linux / macOS
./ragctl up

# 第四步 — 在此目录打开 Claude Code
claude
```

当 Claude Code 在 `rag-knowledge/` 内启动时，自动加载：
- **`.mcp.json`**（项目根目录） → kb-mcp MCP 服务器（76 个工具）
- **`.claude/skills/*`** → 全部 14 个 knowledgebase skills
- **`.claude/agents/knowledge-admin.md`** → Archival agent

**手动逐步安装（代替 `ragctl setup`）：**

```bash
# 安装后端依赖
cd backend && uv sync && cd ..

# 安装 kb-mcp 依赖
cd kb-mcp && uv sync && cd ..

# 安装前端依赖
cd web && npm install && cd ..

# 创建 .env
cp .env.example .env

# （可选）预下载 BGE-M3 模型
./ragctl model

# 启动
./ragctl up
```

**安装完成后你将获得：**
- 所有内容位于 `rag-knowledge/` 目录内
- Skills + MCP 仅在此目录打开 Claude Code 时自动加载
- `ragctl` 在项目根目录下通过 `./ragctl` 使用
- 可选：运行 `./ragctl install` 将 `ragctl` 注册到全局

---

### ✅ 验证一切正常

```bash
# 检查所有服务（dev + prod 并排显示）
ragctl status

# 健康检查
curl http://localhost:8765/api/v1/health   # 后端 (dev)
curl http://localhost:6789                  # Web UI (dev)

# MCP 连接测试（在 Claude Code 中运行）
kb_search query="test"

# 打开 UI
start http://localhost:6789      # Windows
open http://localhost:6789       # macOS
xdg-open http://localhost:6789   # Linux
```

---

## ✅ 前置要求

只需提前安装以下工具 — `ragctl setup` 会处理其余一切。

| 工具 | 版本 | 是否必需 | 说明 |
|------|------|----------|------|
| **Git** | 任意 | ✅ 必需 | 克隆仓库 |
| **Node.js** | ≥ 18（推荐 22） | ✅ 必需 | `ragctl` CLI + Nuxt 前端 |
| **uv** | ≥ 0.7 | ⚡ 自动安装 | Python 包管理器 — 缺失时 `ragctl setup` 自动安装 |
| **Python** | 3.12 | ⚡ 通过 uv | uv 管理 Python 环境，无需手动安装 Python |
| **Docker** | 任意 | 📋 可选 | 仅 Neo4j 图谱需要。解析/搜索/经验功能无需 |
| **Rust** | stable | 📋 可选 | 仅构建 Tauri 桌面应用时需要 |

**资源需求：**
- **磁盘：** 约 5 GB 总计
- **网络：** 首次运行下载 BGE-M3（约 2.2 GB）。默认源为 **ModelScope**（阿里云 CDN，国内最快）。海外用户可在 config.yml 中设置 `embedding.model_source: huggingface`。

<details>
<summary><b>📦 各组件安装位置</b></summary>

| 组件 | 位置 | 大小 |
|------|------|------|
| uv（Python 包管理） | `~/.local/bin/uv` | ~15 MB |
| Backend venv | `backend/.venv/` | ~2 GB（torch + transformers + mineru） |
| kb-mcp venv | `kb-mcp/.venv/` | ~50 MB（mcp + httpx + pyyaml） |
| Web deps | `web/node_modules/` | ~500 MB |
| CLI deps | `command/node_modules/` | ~5 MB（js-yaml） |
| BGE-M3 模型 | `~/.cache/modelscope/` 或 `~/.cache/huggingface/` | ~2.2 GB |
| Neo4j（可选） | Docker volume | ~600 MB |

所有路径均可配置。不污染系统级 Python / Node。
</details>

---

## 💡 为什么选择这个项目

> RAG Knowledge Platform 有何不同？

| 传统知识库工具 | RAG Knowledge Platform |
|---|---|
| 搜索、存储、AI 层各自分离 | **统一**：文档解析 → 索引 → 搜索 → 图谱 → 经验 — 一条流水线 |
| 手动设置，复杂 CLI | **一条命令或一句话**：`ragctl setup` 或"初始化知识库" |
| 难以与 Agent 集成 | **原生**：76 个 MCP 工具 + 14 个 Claude Code 技能，任意 MCP 客户端可用 |
| dev/prod 配置分离 | **单一配置**：`config.yml` 是唯一真相源；`--appmode` 运行时切换 |
| 终端窗口杂乱 | **静默无头**：所有启动器启动服务零终端窗口 |
| 无结构化知识复用 | **经验库**：E0–E12 全生命周期，P0/P1/P2 可信度分级 |
| 单 KB 搜索 | **多策略**：BM25 + 向量 + 标签语义 + 图谱扩展 + 跨库企业搜索 |

---

## 🌟 核心特性

<p align="center">
  <img src="./docs/images/rag-pipeline.png" alt="QDCVR Agentic-First Enterprise Retrieval Pipeline — 6-stage architecture" width="960" />
</p>

| 支柱 | 内容 |
|------|------|
| 📄 **文档解析** | PDF / Word / Excel / PPT / 图片 → Markdown（MinerU OCR 引擎） |
| 🧠 **QDCVR 检索** | 查询驱动·内容验证检索 — 独立 0–8 内容评分。*向量负责快，内容负责准。* |
| 🔍 **多策略搜索** | BM25 + 向量两阶段召回 · 跨库企业搜索 · 标签语义 + 图谱扩展 · balance_kbs |
| 📊 **知识图谱** | Neo4j 驱动 · 14 个图谱工具 · 实体/关系图谱 · 跨库文档桥梁 · 中心性发现 · 路径查询 |
| 💡 **经验库** | E0–E12 全生命周期 · 结构化 problem→solution→lessons · P0/P1/P2 可信度分级 · 失效检测 · 衰减周期 · 草稿审批流程 |
| 🔌 **76 个 MCP 工具** | KB CRUD · 搜索 · 图谱 · 经验 · 解析 · 标签 · 向量/索引 · 服务生命周期 · 全 MCP 原生 · 非阻塞解析 |
| 🎯 **14 个 Claude Code 技能** | 自然语言命令 · 中英双语触发 · 自动路由到 Archival agent · 自包含适合全局插件 · init + update + 12 个 Archival |
| 🤫 **静默无头** | 所有启动器（`ragctl`、`start.bat/.sh`、Tauri）**零终端窗口**启动 · dev 和 prod 行为一致 · 所有日志统一输出 |

---

## 🖥️ 使用方式

四种界面，一个后端。选择最适合你的方式。

### 1. Claude Code · *自然语言*

安装完成后，用中文或英文描述你的需求：

```text
"把 ./papers 里所有 PDF 入库到一个新的 'ML-research' 知识库"
  → knowledgebase-ingest（A0→A9 质量门控）

"搜索：PET 双向拉伸的工艺参数是什么？"
  → QDCVR → 带来源 + 可信度的内容验证答案

"记录这个排查经验"
  → knowledgebase-experience-summarize → 结构化教训

"整理全部知识库——修正标签、描述，移动错位文档"
  → knowledgebase-organize（O0→O13）
```

如果服务未运行，**Archival agent 会通过 `kb_project_start` 静默启动** — 无需终端，无需手动操作。

### 2. CLI · `ragctl`

```bash
ragctl up                     # 启动所有服务（静默，dev 模式）
ragctl up --appmode prod      # prod 端口（8001/3000）
ragctl up --force             # 强制重启
ragctl status                 # 双模式：dev + prod 并排显示
ragctl logs web --tail        # 实时跟踪前端日志
ragctl restart backend -f     # 强制重启单个服务
ragctl down --appmode prod    # 仅停止 prod（共享 Neo4j 保留）
```

#### `--` 参数

| 参数 | 别名 | 用途 |
|------|------|------|
| `--appmode dev\|prod` | `--mode`, `-m` | 选择端口组 |
| `--port-backend N` | `--backend-port` | 覆盖后端端口 |
| `--port-web N` | `--web-port` | 覆盖前端端口 |
| `--no-neo4j` / `--no-backend` / `--no-web` | — | 跳过某个服务 |
| `--only SERVICE` | — | 仅操作指定服务 |
| `--force` | `-f` | 强制先停后启 |
| `--tail` | — | 实时跟踪日志 |

### 3. MCP 客户端 · *任意 agent*

```python
kb_project_start(backend=True, web=True, wait=True)   # 静默启动
kb_search_two_stage(query="reinforcement learning", balance_kbs=True)
experience_search_global(query="ConnectError troubleshooting")
kb_graph_cross_kb_documents(min_kbs=2)
```

### 4. Web UI

打开 `http://localhost:6789` — 浏览 KB、搜索文档、探索图谱、通过 Agent SDK 与 Claude 对话。

---

## 📋 CLI 命令参考

| 命令 | 描述 |
|------|------|
| `ragctl setup` · `init` | 一键完整部署 |
| `ragctl check` | 全面环境审计（含修复提示） |
| `ragctl up` / `down` | 启动 / 停止所有服务（静默，无终端） |
| `ragctl up --appmode prod` | 使用 prod 端口启动（8001 / 3000） |
| `ragctl up --force` / `--no-neo4j` | 强制重启 / 跳过 Neo4j |
| `ragctl start` / `stop` / `restart` [svc] | 单服务生命周期（`backend`\|`web`\|`neo4j`\|`all`） |
| `ragctl restart [svc] -f` | 强制重启单个服务 |
| `ragctl status [--appmode X]` | 双模式状态：端口 + HTTP 健康 + PID + MinerU |
| `ragctl logs [svc] [--tail] [--lines N]` | 查看 / 实时跟踪日志 |
| `ragctl deps` | 安装所有依赖（实时进度） |
| `ragctl model` | 预下载 BGE-M3 嵌入模型（~2.2 GB）。支持 `--source modelscope\|hf-mirror\|huggingface` |
| `ragctl version` | 显示本地 VERSION + git SHA vs GitHub 远程 |
| `ragctl update` | 检查 GitHub 并拉取最新版（含可选依赖重装） |
| `ragctl update --check` | 仅对比版本（dry-run，不 pull） |
| `ragctl install` | 全局注册 `ragctl` → `~/.local/bin` |
| `ragctl desktop` · `ui` | 启动 Tauri 桌面控制台 |
| `ragctl clean` | 清理 MinerU 解析产物 + 缓存（`--model` 需二次确认） |
| `ragctl help` | 显示所有命令 |

---

## 🔌 MCP 工具（76）

全部通过 `mcp__kb-mcp__*` 从 Claude Code 或任意 MCP 客户端访问。

| 类别 | 数量 | 关键工具 |
|------|------|---------|
| **服务生命周期** | 6 | `kb_project_start`、`kb_project_status`、`kb_project_preflight`、`kb_project_version`、`kb_project_update`、`backend_status` |
| **KB CRUD** | 7 | `kb_list`、`kb_create`、`kb_update`、`kb_delete`、`kb_catalog`、`kb_doc_catalog`、`kb_get_documents` |
| **文档 CRUD** | 7 | `kb_doc_read`、`kb_doc_create`、`kb_doc_update_meta`、`kb_doc_update_content`、`kb_doc_delete`、`kb_doc_batch_delete`、`kb_doc_move` |
| **文件系统** | 4 | `fs_get_tree`、`fs_get_children`、`fs_get_count`、`fs_upload_file` |
| **解析** | 4 | `parse_doc`、`parse_doc_batch`、`parse_task_status`、`kb_doc_save_parsed` |
| **标签** | 4 | `kb_tags_list`、`kb_doc_update_tags`、`kb_doc_get_by_tag`、`kb_tags_cleanup` |
| **搜索** | 4 | `kb_search`、`kb_search_vector`、`kb_search_two_stage`、`kb_search_stats` |
| **向量/索引** | 4 | `kb_index_document`、`kb_batch_index`、`kb_reindex`、`kb_cleanup_orphan_collections` |
| **知识图谱** | 14 | `kb_graph_search` · `kb_graph_kb_overview` · `kb_graph_build` · `kb_graph_cross_kb_documents` · … |
| **经验** | 22 | `experience_create` · `experience_search_global` · `experience_search_smart` · `experience_dashboard` · `experience_extract` · … |

---

## 🎯 技能（14）

| 技能 | 流程 | 用途 |
|------|------|------|
| **knowledgebase** | Router | 将用户意图路由到正确子技能 |
| **knowledgebase-init** | Phase 0→11 | 引导式全新安装向导（主 agent） |
| **knowledgebase-update** | Phase 0→5 | 版本检查 + 安全 GitHub pull（主 agent） |
| **knowledgebase-ingest** | A0→A9 | 带质量门控的文档入库 |
| **knowledgebase-search** | Step 0–6 | QDCVR 内容验证检索 |
| **knowledgebase-search-enterprise** | Phase 0–5 | 多策略跨库搜索 |
| **knowledgebase-manage** | M1→M6 | 文档和知识库管理 |
| **knowledgebase-organize** | O0→O13 | 全库重组 |
| **knowledgebase-verify** | V1→V9 | 完整性与质量验证 |
| **knowledgebase-list** | L1→L3 | 只读浏览 |
| **knowledgebase-graph** | — | Neo4j 图谱构建/查询/分析 |
| **knowledgebase-experience** | E0→E12 | 经验生命周期管理 |
| **knowledgebase-experience-summarize** | S1→S5 | 经验提炼并持久化 |
| **knowledgebase-batch** | B1→B7 | 大批量操作 |

> [!NOTE]
> 所有 skills 都是**自包含**的 — 不依赖外部 CLAUDE.md。12 个 skills 委托给 Archival agent 执行；`init` 和 `update` 由主 agent 直接执行。

---

## 🏗️ 架构

```
Browser / Claude Code / MCP Client
        │
        ▼
┌──────────────────┐
│  Nuxt 3 Web UI   │  port 6789 (dev) / 3000 (prod)
│  (代理层)         │
└────────┬─────────┘
         │  server-to-server
         ▼
┌──────────────────┐
│  FastAPI 后端     │  port 8765 (dev) / 8001 (prod)
│  + MinerU OCR     │  临时端口
└────────┬─────────┘
         │  文件读取
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

> **原则：** 写入 → HTTP API（后端/Web 代理）。读取 → 直接文件访问（`.tree-fs.json` + `.knowledge-base.yml`）。

---

## ⚙️ 配置

**`config.yml`**（仓库根）是端口的**唯一真相源**。**`.env`** 覆盖它，由 `ragctl setup` 创建。

| 变量 | 默认（dev / prod） | 用途 |
|------|---------------------|------|
| `APP_MODE` | `dev` | 选择 config.yml 段落 |
| `BACKEND_PORT` | `8765` / `8001` | FastAPI 端口 |
| `WEB_PORT` | `6789` / `3000` | Nuxt Web 端口 |
| `BACKEND_URL` | 自动推导 | 完整后端 URL |
| `HF_ENDPOINT` | `https://hf-mirror.com` | 模型下载镜像（作为 fallback） |
| `TREE_STORAGE_PATH` | `./storage/tree-file-system` | KB 数据存储路径 |
| `NEO4J_PASSWORD` | （来自 docker-compose） | 图谱数据库认证 |

运行时切换模式，无需编辑 `.env`：

```bash
ragctl up --appmode prod       # 后端 → 8001，前端 → 3000
ragctl status                  # 同时显示 dev + prod
ragctl down --appmode prod     # 仅停止 prod（Neo4j 保留）
```

---

## 🤫 静默运行

所有启动器在 dev 和 prod 下均以**零终端窗口**启动服务。输出流向**三个同步表面** — 全部读取相同的日志文件：

| 表面 | 命令 |
|------|------|
| 📄 磁盘文件 | `backend/logs/desktop-stdout.log` · `web/logs/desktop-stdout.log` · `backend/logs/mineru-api.log` |
| 🖥️ Tauri 桌面控制台 | 实时日志流（跟踪完全相同的文件） |
| ⌨️ `ragctl logs` | CLI 查看器 + 实时跟踪 |

```bash
ragctl logs backend            # 最近 80 行
ragctl logs web --tail         # 实时跟踪（Ctrl+C 退出）
ragctl logs mineru --lines 200 # 200 行 OCR 输出
```

> [!TIP]
> 无论用哪个启动器启动服务 — `ragctl`、Tauri、MCP 的 `kb_project_start` — 都写入相同的文件。任何一个都能监控另一个启动的服务。

---

## 🛠️ 故障排查

| 症状 | 可能原因 | 解决 |
|------|---------|------|
| MCP 无法连接 | `uv` 不在 PATH（新终端） | `ragctl setup` 会安装 uv；重开终端 |
| 后端无法启动 | 依赖未安装 | `ragctl setup`（或 `cd backend && uv sync`） |
| 前端无法启动 | `node_modules` 缺失 | `ragctl setup`（或 `cd web && npm install`） |
| `backend/` 或 `web/` 为空 | 仓库克隆不完整 | `ragctl setup` |
| 图谱查询失败（搜索正常） | Neo4j 未运行 | `ragctl start neo4j`（需 Docker） |
| BGE 模型下载慢/失败 | 到 HuggingFace 的网络问题 | 设置 `HF_ENDPOINT=https://huggingface.co`（海外）或确认 config.yml 中 `model_source: modelscope` |
| 端口被占用 | 上次服务仍在运行 | `ragctl down` 然后 `ragctl up` |
| Skills 在 /skills 中不显示 | 不在项目目录（方式 C） | `cd rag-knowledge` 并重启 Claude Code |
| `ragctl` 全局不可用 | 跳过了 `ragctl install` | 在项目根目录执行 `ragctl install` |

---

## ❓ 常见问题

<details>
<summary><b>真的不弹终端窗口吗？</b></summary>

真的。已验证：Windows 上 `windowsHide` + 直接二进制启动（无 `cmd.exe` 包装）；POSIX 上 `start_new_session`。
</details>

<details>
<summary><b>dev 和 prod 有什么区别？</b></summary>

端口和配置。dev：后端 `8765` / 前端 `6789`。prod：后端 `8001` / 前端 `3000`。通过 `--appmode prod` 切换。两者都完全静默。`ragctl status` 同时显示两种模式。
</details>

<details>
<summary><b>我的数据存在哪里？</b></summary>

全部本地 — `$TREE_STORAGE_PATH`（KB 文件）+ Neo4j（图谱）+ ChromaDB（向量）。无云，无遥测。
</details>

<details>
<summary><b>需要 Docker 吗？</b></summary>

仅 Neo4j 知识图谱需要。解析、搜索、经验功能无需。
</details>

<details>
<summary><b>没有 Claude Code 能用吗？</b></summary>

能。`http://localhost:6789` 的 Web UI 功能完整，任意 MCP 客户端也能调用 76 个工具。
</details>

<details>
<summary><b>应该选择哪种安装方式？</b></summary>

- **插件**（方式 A）—— 最简单。Skills 和 MCP 全局可用。适合大多数用户。
- **Skills 复制**（方式 B）—— 不想用插件但仍要全局 skills 和引导式初始化。
- **本地项目**（方式 C）—— 所有内容在一个文件夹里。Skills 和 MCP 仅在项目目录内打开 Claude Code 时加载。
</details>

<details>
<summary><b>安装后如何更新？</b></summary>

在 Claude Code 中说"更新知识库"或 `/knowledgebase-update`，或在终端运行 `ragctl update`。更新默认使用 `git pull --ff-only` — 脏工作区受保护。
</details>

---

## 📁 项目结构

```
rag-knowledge/
├── backend/              ← FastAPI + MinerU OCR 引擎
├── web/                  ← Nuxt 3 + Ant Design Vue（含 Claude Chat + Agent SDK）
├── kb-mcp/               ← MCP 服务器 — 76 个工具
├── command/              ← ragctl CLI（Node.js、js-yaml）
├── src-tauri/            ← Tauri v2 桌面应用（Rust）
├── .claude/              ← Claude Code skills（14）+ Archival agent
├── .claude-plugin/       ← 插件 + marketplace 清单
├── .mcp.json             ← kb-mcp MCP 自动连接（本地项目）
├── config.yml            ← 中央配置（单一真相源）
├── docker-compose.yml    ← Neo4j 容器
├── .env.example          ← 环境变量模板
├── VERSION               ← 语义版本号（ragctl version/update 使用）
├── ragctl / ragctl.bat   ← CLI 入口（Linux·macOS / Windows）
├── start.bat / start.sh  ← 静默启动器（委托给 ragctl up）
└── README.md
```

---

## 🔧 技术栈

| 组件 | 技术 |
|------|------|
| 后端 | Python 3.12 · FastAPI · MinerU OCR · ChromaDB |
| 前端 | TypeScript · Nuxt 3 · Ant Design Vue · "Nocturne Atelier" 主题 |
| Claude Chat | Vue 3 · Anthropic Claude Agent SDK（SSE 流式） · SQLite 历史 · 生产级消息队列 |
| MCP 服务器 | Python · FastMCP · httpx |
| CLI | Node.js · js-yaml |
| 桌面 | Rust · Tauri v2 · reqwest · tokio |
| 图谱 | Neo4j 5.20（Docker） |
| 嵌入 | BGE-M3 (1024-dim) · sentence-transformers |
| 搜索 | BM25 + 向量两阶段 · QDCVR 流水线 |

---

## 🤝 贡献

1. Fork → 功能分支 → commit → push → PR
2. 提交前 `ragctl check` 应通过
3. 跨平台：若改动启动/脚本，请在 Win + Linux（或 macOS）测试
4. 详见 [CLAUDE.md](CLAUDE.md) — 架构细节和开发约定

---

## 📄 许可证

MIT © [kingdol](https://github.com/kingdol666)
