<h1 align="center">
  <img src="./docs/images/logo.svg" alt="RAG Knowledge Platform" width="120" />
  <br/>
  RAG Knowledge Platform
</h1>

<p align="center">
  <strong>企业级文档智能与 Agentic 知识库平台</strong><br/>
  <em>PDF 解析 · 语义搜索 · 知识图谱 · 经验库 · MCP 原生 · 静默无头启动</em>
</p>

<p align="center">
  <a href="#-快速开始"><img src="https://img.shields.io/badge/%E5%BF%AB%E9%80%9F%E5%BC%80%E5%A7%8B-4%20%E6%AD%A5-blue?style=for-the-badge" /></a>
  <a href="#-核心特性"><img src="https://img.shields.io/badge/%E7%89%B9%E6%80%A7-%E8%A7%81%E4%B8%8B%E6%96%87-9cf?style=for-the-badge" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" /></a>
  <a href="#-platforms"><img src="https://img.shields.io/badge/platform-Win%20%7C%20Linux%20%7C%20macOS-lightgrey?style=for-the-badge" /></a>
  <a href="#-mcp-工具-74"><img src="https://img.shields.io/badge/MCP-74%20tools-blueviolet?style=for-the-badge" /></a>
  <a href="#-技能-13"><img src="https://img.shields.io/badge/Skills-13-orange?style=for-the-badge" /></a>
  <a href="#-静默无头运行"><img src="https://img.shields.io/badge/startup-silent%20%26%20headless-success?style=for-the-badge" /></a>
</p>

---

<p align="center">
  <sub><a href="./README.md">English</a> · <a href="./README-zh.md"><b>中文</b></a></sub>
</p>

---

## 📌 目录

- [🌟 核心特性](#-核心特性)
- [🌟 特性](#-特性)
- [🏗️ 架构](#️-架构-1)
- [✅ 前置要求](#-前置要求)
- [🚀 快速开始](#-快速开始)
- [📦 安装](#-安装) — 5 种方式
- [🖥️ 使用](#️-使用-1) — 4 种界面
- [⚙️ 配置](#️-配置-1)
- [📋 命令](#-命令)
- [🔌 MCP 工具（74）](#-mcp-工具74)
- [🎯 技能（13）](#-技能13)
- [🤫 静默无头运行](#-静默无头运行)
- [🛠️ 故障排查](#️-故障排查)
- [❓ 常见问题](#-常见问题)
- [📁 项目结构](#-项目结构-1)
- [🤝 贡献](#-贡献)
- [📄 许可证](#-许可证)

## 🌟 核心特性

**文档智能**
- 📄 **多格式解析** — PDF / Word / Excel / PPT / 图片 → Markdown（MinerU OCR）
- 🧠 **QDCVR 检索** — 查询驱动·内容验证检索，0–8 分独立评分。*向量负责快，内容负责准。*
- 🔍 **多策略搜索** — BM25+向量两阶段、跨库企业搜索、标签/图谱扩展
- 📊 **Neo4j 知识图谱** — 实体、关系、跨库文档联动、核心文档发现
- 💡 **经验库（E0–E12）** — 结构化教训，P0/P1/P2 可信度分级、衰减周期、草稿审批

**集成与运维**
- 🔌 **74 个 MCP 工具** — KB 全生命周期、搜索、图谱、经验、解析 + 静默服务管理
- 🎯 **13 个 Claude Code 技能** — 自然语言命令，中英双语触发
- 🤫 **静默无头启动** — 所有启动器（`ragctl`、`start.bat/.sh`、Tauri）**零终端窗口**，dev == prod
- 📓 **统一日志** — 磁盘文件 · Tauri 控制台 · `ragctl logs`，三处读同一批文件
- 🖥️ **Tauri 桌面控制台** — 可视化启停、依赖安装、实时日志、配置编辑
- ⚡ **一键部署** — `ragctl setup` 安装 uv、子模块、依赖、BGE-M3 模型
- 🌍 **跨平台** — Windows · Linux · macOS，零云依赖，全部本地运行

## 🏗️ 架构

<p align="center">
  <img src="./docs/images/rag-architecture.png" alt="RAG Knowledge Platform 系统架构" width="960" />
</p>

<p align="center">
  <img src="./docs/images/rag-pipeline.png" alt="QDCVR 智能驱动企业级检索流水线" width="960" />
</p>

三个可互换的启动器 —— **`ragctl`**、**Tauri 桌面**、**MCP `kb_project_start`** —— 都写入同一批日志文件，所以任何一个都能启动项目，任何一个都能监控。

## ✅ 前置要求

只需提前装两个工具 —— `ragctl setup` 会自动安装其余一切。

| 工具 | 版本 | 是否必需 | 说明 |
|------|------|----------|------|
| **Git** | 任意 | ✅ 必需 | 克隆 + 子模块 |
| **Node.js** | ≥ 22 | ✅ 必需 | `ragctl` CLI + Nuxt 前端 |
| **uv** | ≥ 0.7 | ⚡ 自动安装 | Python 包管理器 —— 缺失时 `ragctl setup` 自动装 |
| **Python** | 3.12 | ⚡ 经 uv | uv 管理 Python 环境，无需手动安装 |
| **Docker** | 任意 | 📋 可选 | 仅 Neo4j 图谱需要。解析/搜索/经验功能无需 |
| **Rust** | stable | 📋 可选 | 仅构建 Tauri 桌面应用时需要（`ragctl desktop`） |

**磁盘空间：** 约 5 GB（Python 依赖 ~2 GB · 前端依赖 ~0.5 GB · BGE-M3 模型 ~2.2 GB · Neo4j 镜像可选）。

**网络：** 首次运行会从 HuggingFace 下载 BGE-M3 嵌入模型。默认镜像 `hf-mirror.com`（国内快）；海外可设 `HF_ENDPOINT=https://huggingface.co`。

<details>
<summary><b>📦 各组件安装位置</b></summary>

| 组件 | 位置 | 大小 |
|------|------|------|
| uv（Python 包管理） | `~/.local/bin/uv` | ~15 MB |
| Backend Python 环境 | `backend/.venv/` | ~2 GB（torch + transformers + mineru） |
| kb-mcp Python 环境 | `kb-mcp/.venv/` | ~50 MB（mcp + httpx + pyyaml） |
| Web node_modules | `web/node_modules/` | ~500 MB |
| CLI node_modules | `command/node_modules/` | ~5 MB（js-yaml） |
| BGE-M3 模型 | `~/.cache/huggingface/` | ~2.2 GB |
| Neo4j（可选） | Docker 卷 | ~600 MB |

所有路径均可配置，不污染系统级 Python / Node。
</details>

## 🚀 快速开始

两条等效路径。**A** 最新鲜（装插件后让它自动拉取并配置项目），**B** 是经典克隆运行。

### 路径 A — 通过 Claude Code 插件（自动拉取 + 引导配置）

```bash
# 1. 从 GitHub 注册插件（一次性）
claude plugin marketplace add kingdol666/rag-knowledge
claude plugin install rag-knowledge

# 2. 在任意目录打开 Claude Code，直接说：
#    "初始化知识库"   （或  "set up the knowledge base"）
```

`knowledgebase-init` 技能会**克隆仓库、安装一切（`ragctl setup`）、带你完成 12 项配置、启动服务** —— 全程引导、全程静默，无终端、无手动操作。

### 路径 B — 通过 git clone（经典）

```bash
# 1. 克隆（递归拉取 backend + web 子模块）
git clone --recursive https://github.com/kingdol666/rag-knowledge.git
cd rag-knowledge

# 2. 一键部署 — uv + 依赖 + 模型 + .env（首次 5–30 分钟）
./ragctl setup          # Linux / macOS
ragctl setup            # Windows

# 3. 静默启动全部服务（无终端窗口）
ragctl up               # → http://localhost:6789
```

> 在**项目目录内**打开 Claude Code 会自动加载 13 个技能 + kb-mcp MCP 服务器（无需安装——这是项目级插件机制）。

### 检查健康状态

```bash
ragctl status           # backend/web/neo4j/mineru + HTTP 健康 + PID
ragctl logs backend --tail   # 实时跟踪后端日志（Ctrl+C 退出）
```

完成 —— 一个完整的知识库，74 个 MCP 工具 + 13 个技能已接入 Claude Code。详见[使用](#️-使用-1)。

## 📦 安装

任选一种，产物完全相同。

### 方式 1 — Claude Code 插件（marketplace）· *最新鲜体验*

```bash
claude plugin marketplace add kingdol666/rag-knowledge   # 添加 marketplace
claude plugin install rag-knowledge                      # 安装 13 技能插件
```

然后在 Claude Code 里说 *"初始化知识库"* → `knowledgebase-init` 技能克隆仓库、运行 `ragctl setup`、配置、启动服务。（本地开发检出而非 GitHub？用 `claude plugin marketplace add "./"`。）

该技能会**自动全局注册 `ragctl`**（`ragctl install` → `~/.local/bin`）和**自动全局注册 `kb-mcp`**（`~/.claude/.mcp.json` + `RAG_PROJECT_ROOT`），所以配置完成后整套系统**在任何目录、任何 Claude Code 会话中皆可用** —— 13 个技能 + 74 个 MCP 工具 + `ragctl` CLI。在任意位置重启 Claude Code 后说"搜索知识库"即可。

### 方式 2 — 一键 CLI（`ragctl setup`）

```bash
git clone --recursive https://github.com/kingdol666/rag-knowledge.git
cd rag-knowledge
ragctl setup
```

`ragctl setup` 自动完成：
1. 安装 **uv**（Python 包管理器，若缺失）
2. 初始化 **git 子模块**（`backend/`、`web/`）
3. 从 `.env.example` 创建 **`.env`**
4. 安装全部依赖 — 后端 (`uv sync`)、前端 (`npm install`)、kb-mcp (`uv sync`)、CLI
5. 预下载 **BGE-M3 嵌入模型**（约 2.2 GB，默认走 `hf-mirror.com` 镜像）

**前置要求：** `git` + `node` 22+。`uv`、Python 依赖、模型自动安装。Docker 可选（仅 Neo4j 图谱功能需要）。详见[✅ 前置要求](#-前置要求)。

### 方式 3 — 引导向导（Claude Code 技能）

首次推荐。[安装插件](#方式-1--claude-code-插件marketplace--最新鲜体验) 后，打开 Claude Code 说：

> *"初始化知识库"* / *"set up the knowledge base"*

`knowledgebase-init` 技能运行 **11 阶段交互向导**：平台检测 → 前置检查 → 克隆/更新 → `ragctl setup` → 12 项决策（模式/端口/存储/认证/MinerU/Neo4j/HF 镜像…）→ 写 `.env` → 全局注册 `ragctl` → 启动服务 → 全链路验证。

### 方式 4 — 手动

```bash
git clone --recursive https://github.com/kingdol666/rag-knowledge.git
cd rag-knowledge

# 子模块（若未用 --recursive 克隆）
git submodule update --init --recursive

# Python 环境
cd backend && uv sync && cd ..
cd kb-mcp  && uv sync && cd ..

# 前端依赖
cd web && npm install && cd ..

# 配置
cp .env.example .env

# 模型（可选 — 首次向量索引时自动下载）
HF_ENDPOINT=https://hf-mirror.com ragctl model

# 启动
ragctl up
```

### 方式 5 — Tauri 桌面应用

桌面控制台提供 **一键引导**、环境检查、服务启停、实时日志、配置编辑。

```bash
cd src-tauri
cargo tauri build                 # 构建桌面二进制（首次）
# 然后从文件管理器启动，或：
ragctl desktop                    # 启动已构建的 Tauri 二进制
```

开发时可用 `cargo tauri dev`。

> **技能 + MCP 说明：** 13 个 knowledgebase 技能通过[方式 1](#方式-1--claude-code-插件marketplace--最新鲜体验)（`claude plugin install`）注册，或在项目目录内打开 Claude Code 时自动加载。`kb-mcp` MCP 服务器（74 工具）通过 `.mcp.json` 自动连接；首次 `uv run` 自动同步其 3 个轻量依赖，无需手动操作。

## 🖥️ 使用

可从 **四种界面** 中的任意一种驱动，都连同一个后端。

### 界面 1 — Claude Code（自然语言）

[安装插件](#方式-1--claude-code-插件marketplace--最新鲜体验) 后，直接描述需求。`knowledgebase` 调度器会路由每个请求：

```
你："把 ./papers 里所有 PDF 入库到一个新的 'ML-research' 知识库"
  → knowledgebase-ingest（A0→A9 质量门控：去重→解析→打标→存储→索引→验证）

你："搜索：PET 双向拉伸的工艺参数是什么？"
  → knowledgebase-search（QDCVR）→ 带来源+可信度的内容验证答案

你："整理全部知识库——修正标签、描述，移动错位文档"
  → knowledgebase-organize（O0→O13）

你："记录这个排查经验"
  → knowledgebase-experience-summarize → 带 P0/P1/P2 分级的结构化教训
```

如果服务没开，**Archival 代理会通过 `kb_project_start` MCP 工具静默拉起** —— 无终端、无手动操作。

### 界面 2 — CLI（`ragctl`）

```bash
ragctl up                          # 启动全部服务（静默，dev 模式）
ragctl up --appmode prod           # 用 prod 端口启动（后端 8001，前端 3000）
ragctl up --force                  # 强制重启（先停后启）
ragctl up --no-neo4j               # 不启动 Neo4j
ragctl status                      # 同时显示 dev + prod 双模式状态
ragctl status --appmode dev        # 仅显示一个模式
ragctl logs web --tail             # 实时跟踪前端日志
ragctl restart backend -f          # 强制重启单个服务
ragctl start backend --port-backend 9000   # 自定义端口启动
ragctl down --appmode prod         # 仅停止 prod 服务（保留共享 Neo4j）
ragctl install                     # 全局注册 ragctl（~/.local/bin）
ragctl desktop                     # 启动 Tauri GUI
ragctl check                       # 全面环境审计（含修复提示）
```

#### `--` 二级参数

| 参数 | 别名 | 作用 |
|------|------|------|
| `--appmode dev\|prod` | `--mode`, `-m` | 选择模式（默认：`.env APP_MODE` 或 `dev`） |
| `--port-backend N` | `--backend-port` | 覆盖后端端口 |
| `--port-web N` | `--web-port` | 覆盖前端端口 |
| `--no-neo4j` | — | 跳过 Neo4j |
| `--no-backend` / `--no-web` | — | 跳过某个服务 |
| `--only SERVICE` | — | 仅操作指定服务 |
| `--force` | `-f` | 强制先停后启 |
| `--timeout N` | — | 覆盖启动超时（秒） |
| `--lines N` | `-n` | 显示日志行数 |
| `--tail` | — | 实时跟踪日志 |

完整[命令](#-命令)表。

### 界面 3 — Tauri 桌面控制台

```bash
ragctl desktop                     # 或：cd src-tauri && cargo tauri dev
```

可视化仪表盘：启停服务、安装依赖、实时日志（与 `ragctl` 同一文件）、编辑 `config.yml`。

### 界面 4 — 任意 MCP 客户端

74 个工具经 MCP 暴露，任何 MCP 兼容代理都能用：

```python
# 示例：从 Python MCP 客户端
kb_project_start(backend=True, web=True, wait=True)   # 静默无头启动
kb_search_two_stage(query="CNN-LSTM 故障预测", balance_kbs=True)
kb_graph_search(keyword="汽轮机")
experience_search_global(query="磨煤机振动")
```

## ⚙️ 配置

**`config.yml`**（仓库根）是端口唯一真相源。**`.env`** 覆盖它，由 `ragctl setup` 从 `.env.example` 创建。

| 变量 | 默认（dev / prod） | 用途 |
|------|---------------------|------|
| `APP_MODE` | `dev` | 选择 config.yml 段（dev 或 prod 端口） |
| `BACKEND_PORT` | `8765` / `8001` | FastAPI 后端端口 |
| `WEB_PORT` | `6789` / `3000` | Nuxt 前端端口 |
| `BACKEND_URL` | 推导 | 后端完整 URL（给 kb-mcp / 前端代理） |
| `HF_ENDPOINT` | `https://hf-mirror.com` | 模型下载镜像（海外可改 `https://huggingface.co`） |
| `TREE_STORAGE_PATH` | `web/storage/tree-file-system` | KB 文件磁盘路径 |
| `NEO4J_PASSWORD` | （来自 docker-compose） | Neo4j 认证（图谱功能） |
| `KB_AUTH_TOKEN` | *（空）* | 可选 Bearer 认证 |

运行时切模式，无需改 `.env`：

```bash
ragctl up --appmode prod           # 后端 → 8001，前端 → 3000
ragctl status                      # 同时显示 dev + prod 双模式
ragctl down --appmode prod         # 仅停止 prod（保留共享 Neo4j）
```

## 📋 命令

| 命令 | 描述 |
|------|------|
| `ragctl setup` | 一键完整部署（uv + 子模块 + 依赖 + 模型 + .env） |
| `ragctl check` | 全面环境审计（含修复提示） |
| `ragctl up` / `down` | 启动 / 停止所有服务（**静默，无终端**） |
| `ragctl up --appmode prod` | 用 prod 端口启动（8001 / 3000） |
| `ragctl up --force` | 强制重启（先停后启） |
| `ragctl up --no-neo4j` | 不启动 Neo4j（跳过 Docker） |
| `ragctl start [backend\|web\|neo4j\|all]` | 启动指定服务 |
| `ragctl stop [backend\|web\|neo4j\|all]` | 停止指定服务 |
| `ragctl restart [服务] [-f]` | 重启服务（-f = 强制停+启） |
| `ragctl status [--appmode X]` | 双模式状态：端口 + HTTP 健康 + PID + MinerU |
| `ragctl logs [服务] [--tail] [--lines N]` | 查看 / 实时跟踪日志（backend/web/mineru） |
| `ragctl deps` | 安装所有依赖（实时进度） |
| `ragctl model` | 预下载 BGE-M3 嵌入模型 |
| `ragctl install` | 全局注册 ragctl → `~/.local/bin`（任意目录可用） |
| `ragctl desktop` \| `ui` | 启动 Tauri 桌面控制台（与 ragctl 共享日志） |
| `ragctl help` | 显示所有命令 |

## 🔌 MCP 工具（74）

全部通过 `mcp__kb-mcp__*` 从 Claude Code 或任意 MCP 客户端访问。分类精选：

| 类别 | 示例 |
|------|------|
| **服务生命周期** | `kb_project_start`、`kb_project_status`、`kb_project_preflight`、`backend_status` |
| KB CRUD | `kb_list`、`kb_create`、`kb_update`、`kb_delete`、`kb_catalog` |
| 文档 CRUD | `kb_doc_create`、`kb_doc_read`、`kb_doc_update_content`、`kb_doc_save_parsed`、`kb_doc_move` |
| 搜索 | `kb_search`、`kb_search_vector`、`kb_search_two_stage`、`kb_search_stats` |
| 文件系统 | `fs_get_tree`、`fs_get_children`、`fs_get_count`、`fs_upload_file` |
| 知识图谱 | `kb_graph_health`、`kb_graph_search`、`kb_graph_kb_overview`、`kb_graph_build` |
| 经验 | `experience_create`、`experience_search_global`、`experience_dashboard`、`experience_extract` |
| 标签 + 清理 | `kb_tags_list`、`kb_tags_cleanup`、`kb_cleanup_orphan_collections` |
| 解析（非阻塞） | `parse_doc`、`parse_doc_batch`、`parse_task_status` |

**服务生命周期工具（静默）：**

| 工具 | 返回 |
|------|------|
| `kb_project_preflight()` | 项目**是否已配置**？`.env`/子模块/依赖检查 + 精确修复命令 |
| `kb_project_status()` | 服务**是否在运行**？端口 + HTTP 健康 + PID + MinerU + 日志路径 + `ready` |
| `kb_project_start(backend, web, neo4j, mode, wait)` | 静默拉起服务（无头、落盘日志、幂等）。`wait=true` 阻塞到 HTTP 就绪 |

## 🎯 技能（13）

| 技能 | 流程 | 用途 |
|------|------|------|
| **knowledgebase** | 路由 | 调度用户意图到正确子技能 |
| **knowledgebase-init** | 阶段 0→11 | 全新安装引导向导（部署+配置+启动） |
| **knowledgebase-ingest** | A0→A9 | 带质量门控的文档入库 |
| **knowledgebase-search** | 步骤0→6 | QDCVR 内容验证检索 |
| **knowledgebase-search-enterprise** | 阶段0→5 | 多策略跨库搜索 |
| **knowledgebase-manage** | M1→M6 | 文档与知识库管理 |
| **knowledgebase-organize** | O0→O13 | 全库重组 |
| **knowledgebase-verify** | V1→V9 | 完整性与质量验证 |
| **knowledgebase-list** | L1→L3 | 只读浏览 |
| **knowledgebase-graph** | — | Neo4j 图谱构建/查询/分析 |
| **knowledgebase-experience** | E0→E12 | 经验生命周期 |
| **knowledgebase-experience-summarize** | S1→S5 | 经验提炼入库 |
| **knowledgebase-batch** | B1→B7 | 大批量操作 |

## 🤫 静默无头运行

所有启动器在 dev/prod 下都**零终端窗口**启动。输出流向**三处同步表面**：

| 表面 | 位置 |
|------|------|
| 📄 磁盘日志文件 | `backend/logs/desktop-stdout.log` · `web/logs/desktop-stdout.log` · `backend/logs/mineru-api.log` |
| 🖥️ Tauri 桌面控制台 | 实时日志流（跟踪这些文件） |
| ⌨️ `ragctl logs [服务]` | CLI 查看器 + 实时跟踪（`--tail` / `-f`） |

```bash
ragctl logs backend          # 最近 80 行
ragctl logs web --tail       # 实时跟踪（Ctrl+C 退出）
ragctl logs mineru -n 200    # MinerU 输出 200 行
```

因为 `ragctl`、Tauri、MCP `kb_project_start` 都写同一批文件，**无论哪个启动器启动的服务，三者都能监控**。

## 🛠️ 故障排查

| 症状 | 可能原因 | 解决 |
|------|---------|------|
| **MCP 连不上**（Claude Code） | `uv` 不在 PATH（新终端） | `ragctl setup` 会装 uv；重开终端/Claude Code 让 PATH 刷新（ragctl 自动探测 `~/.local/bin` + `~/.cargo/bin`） |
| **`kb_project_start` 返回 preflight 错误** | 项目尚未配置 | 先 `ragctl setup`，再重试（或调用 `kb_project_preflight` 看具体缺什么） |
| **后端起不来** | 后端依赖未装 | `ragctl setup`（或 `cd backend && uv sync`）；看 `ragctl logs backend` |
| **前端起不来** | `web/node_modules` 缺失 | `ragctl setup`（或 `cd web && npm install`） |
| **`backend/` 或 `web/` 是空的** | 子模块未初始化 | `git submodule update --init --recursive`（或 `ragctl setup`） |
| **`--mode prod` 用 dev 端口** | `web` 子模块旧版（修复前的 `start.mjs`） | 更新 web 子模块，见下方[web 子模块说明](#web-子模块说明) |
| **图谱查询失败**（搜索正常） | Neo4j 没开 | `ragctl start neo4j`（需 Docker） |
| **BGE 模型下载慢/失败** | 到 HuggingFace 的网络 | `HF_ENDPOINT` 默认 `hf-mirror.com` 镜像。覆盖：`set HF_ENDPOINT=https://huggingface.co` |
| **端口被占用** | 上次服务还在跑 | `ragctl down` 再 `ragctl up`；或 `ragctl restart <服务>` |
| **kb-mcp 启动提示 "not set up"** | 新克隆，未运行 `ragctl setup` | MCP 启动时会打印明确警告 —— 运行 `ragctl setup`，再重启 Claude Code |

<a id="web-子模块说明"></a>
> **web 子模块说明：** `web/start.mjs` 已修复，使运行时环境变量覆盖优先于 `.env`（`--mode prod` 用 prod 端口所必需）。该修复在 `web` 子模块内 —— 需提交到 `rag-knowledge-frondend` 仓库并更新子模块指针，全新克隆才能继承：
> ```bash
> cd web && git add start.mjs && git commit -m "fix: runtime env wins over .env for --mode overrides" && git push
> cd .. && git add web && git commit -m "chore: bump web submodule"
> ```

## ❓ 常见问题

**真的不弹终端窗口吗？** 是的。PowerShell 实测：服务全部运行时，`python.exe` 和 `node.exe` 拥有**零**可见窗口。Windows 用 `windowsHide` + 直接二进制启动（无 `cmd.exe` 包装）；POSIX 用 `start_new_session`。

**dev 和 prod 有什么区别？** 端口和配置。dev：后端 `8765` / 前端 `6789`。prod：后端 `8001` / 前端 `3000`。用 `--mode prod` 切换。两者都完全静默。

**我的数据在哪？** 全部本地 —— `web/storage/tree-file-system/`（KB 文件）+ Neo4j（图谱）。无云、无遥测。

**需要 Docker 吗？** 仅 Neo4j 知识图谱需要。其他功能（解析、搜索、经验）不需要。

**没有 Claude Code 能用吗？** 能。`http://localhost:6789` 的 Web UI 功能完整，任意 MCP 客户端也能直接调用 74 个工具。

## 📁 项目结构

```
rag-knowledge/
├── backend/             ← [子模块] FastAPI + MinerU OCR
├── web/                 ← [子模块] Nuxt 3 + Ant Design Vue
├── kb-mcp/              ← MCP 服务器 — 74 工具（+ project_manager.py 生命周期）
├── command/             ← ragctl CLI（Node.js）
├── src-tauri/           ← Tauri 桌面应用（Rust）
├── .claude/             ← Claude Code 技能（13）+ archival 代理
├── .claude-plugin/      ← 插件 + marketplace 清单（claude plugin install）
├── .mcp.json            ← kb-mcp MCP 自动注册
├── config.yml           ← 中央配置（端口唯一真相源）
├── docker-compose.yml   ← Neo4j 容器
├── ragctl / ragctl.bat  ← CLI 入口（Linux·macOS / Windows）
└── start.bat / start.sh ← 静默启动器（委托给 ragctl up）
```

## 🔧 技术栈

| 组件 | 技术 |
|------|------|
| 后端 | Python 3.12 · FastAPI · MinerU OCR · ChromaDB |
| 前端 | TypeScript · Nuxt 3 · Ant Design Vue |
| MCP 服务器 | Python · FastMCP · httpx |
| CLI | Node.js · js-yaml |
| 桌面 | Rust · Tauri v2 · reqwest · tokio |
| 图谱 | Neo4j（Docker） |
| 嵌入 | BGE-M3 (1024维) · sentence-transformers |
| 搜索 | BM25 + 向量两阶段 · QDCVR 流水线 |

## 🤝 贡献

1. Fork → 功能分支 → 提交 → 推送 → PR
2. 提交前 `ragctl check` 应通过
3. 跨平台：若改动启动/脚本，请在 Win + Linux（或 macOS）测试

## 📄 许可证

MIT © [kingdol](https://github.com/kingdol666)

