# 🧠 RAG Knowledge Platform

<p align="center">
  <b>AI-Powered Knowledge Base Management System</b><br>
  <sub>智能知识库管理平台 — 文档解析 · 向量检索 · 知识图谱 · 经验库</sub>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.12-blue" alt="Python">
  <img src="https://img.shields.io/badge/node-18%2B-green" alt="Node.js">
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey" alt="Platform">
  <img src="https://img.shields.io/badge/license-MIT-yellow" alt="License">
  <img src="https://img.shields.io/badge/tools-74%20MCP-orange" alt="MCP Tools">
</p>

---

## 📖 Language / 语言

- [English](#english) | [中文](#中文)

---

<div id="english">

## 🚀 Quick Start

```bash
# 1. Clone & enter
git clone --recursive <repo-url> rag-knowledge
cd rag-knowledge

# 2. One-command setup (first time only, ~3-5 min)
./ragctl init          # Windows: ragctl init

# 3. Start all services (~20-40 sec)
./ragctl up            # Windows: ragctl up

# 4. Verify
./ragctl health

# Done! Open browser → http://localhost:6789
```

### Prerequisites

| Tool | Version | Purpose |
|------|:-------:|---------|
| [Node.js](https://nodejs.org/) | 18+ | Runtime (CLI + Web) |
| [uv](https://docs.astral.sh/uv/) | latest | Python package manager |
| [Docker](https://www.docker.com/) | latest | Neo4j graph database _(optional)_ |

`ragctl init` handles everything else automatically.

---

## 🎮 Launcher — `ragctl`

**ragctl** is the unified CLI — identical on Windows, Linux, and macOS.

| Platform | Command |
|----------|---------|
| Windows | `ragctl` or `ragctl.bat` or `ragctl.cmd` |
| Linux / macOS | `./ragctl` |

### All Commands

```bash
ragctl init              # First-time setup (install everything)
ragctl up                # Start all services (Neo4j → Backend → Web)
ragctl down              # Stop all services (Web → Backend → Neo4j)
ragctl status            # Show service status (PID/port/health)
ragctl health            # Full health check (5 services)
ragctl doctor            # Diagnose common issues (19 checks)
ragctl logs <service>    # View logs (backend/web/mineru)
ragctl config show       # Show full configuration
ragctl config set <k> <v>  # Change configuration (hot-reload)
ragctl start <service>   # Start specific service
ragctl stop <service>    # Stop specific service
ragctl restart <service> # Restart service
ragctl install <target>  # Install dependencies (backend/web/mcp/all)
ragctl test <target>     # Run tests (backend/web/mcp/all)
ragctl mcp tools         # List all 74 MCP tools
ragctl kb list           # List knowledge bases
ragctl kb search <q>     # Search knowledge bases
ragctl kb stats          # Knowledge base statistics
```

### First-Time Flow

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│ ragctl init  │ ──▶ │ ragctl up    │ ──▶ │ Open Browser │
│ ~3-5 min     │     │ ~20-40 sec   │     │ :6789        │
└─────────────┘     └──────────────┘     └─────────────┘
  ✓ Check deps        ✓ Neo4j start       Web UI ready
  ✓ Init submodules    ✓ Backend start
  ✓ Install deps       ✓ Web start
  ✓ Create .env
  ✓ Verify everything
```

---

## 🏗 Architecture

```
┌──────────────────────────────────────────────────────┐
│                    Claude Code / AI Agent            │
│         (AI-powered KB management via MCP)           │
└──────────────┬──────────────────────┬────────────────┘
               │ MCP (stdio)          │
               ▼                      ▼
┌──────────────────────┐   ┌──────────────────────────┐
│   kb-mcp MCP Server  │   │   Nuxt 3 Web (port 6789) │
│   74 tools · Python   │   │   UI + Server API Proxy  │
└──────────┬───────────┘   └────────────┬─────────────┘
           │ HTTP                        │ HTTP
           ▼                             ▼
┌──────────────────────────────────────────────────────┐
│         FastAPI Backend (port 8765)                   │
│    Parse scheduling · MinerU OCR · Config             │
└──────────────────────┬───────────────────────────────┘
           │               │                │
           ▼               ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  MinerU OCR  │  │   ChromaDB   │  │    Neo4j     │
│  PDF→Markdown│  │  Vector DB   │  │   Graph DB   │
└──────────────┘  └──────────────┘  └──────────────┘
```

**3-Layer Metadata**: Every write atomically syncs disk `.md` + `.tree-fs.json` + `.knowledge-base.yml`.

**Dependency chain**: filesystem ops → Web proxy (6789) · search/graph/experience ops → Backend directly (8765).

---

## 🧩 Features

### 12 Skill Workflows

| Skill | Purpose | Flow |
|-------|---------|------|
| list | Browse & discover KBs | L1→L3 |
| search | QDCVR semantic retrieval | Step 0→6 |
| verify | Integrity & quality audit | V1→V9 |
| ingest | Document ingestion pipeline | A0→A9 |
| manage | Move/rename/delete/merge | M1→M6 |
| organize | Full collection restructuring | O0→O13 |
| batch | Bulk operations | B1→B7 |
| experience | Experience lifecycle (E0-E12) | Create→Retrieve→Clean |
| graph | Knowledge graph query | Build→Query→Analyze |
| enterprise | Cross-KB enterprise search | Phase 0→5 |
| summarize | Auto-extract experiences | Scene→Draft→Persist |
| dispatcher | Scenario routing | Keyword→Sub-skill |

### Enterprise-Grade Retrieval (QDCVR)

```
User Query
  → Step 0: Intent analysis + query rewrite
  → Step 1: Smart KB selection (kb_catalog → agentic)
  → Step 2: Two-stage vector recall (BM25 + embedding)
  → Step 2.5: Doc dedup + hard threshold + short-content guard
  → Step 3: Content verification (read 3000 chars, score 0-8)
  → Step 6: Answer + sources + confidence + blind spots
```

---

## 📁 Project Structure

```
rag-knowledge/
├── ragctl / ragctl.bat / ragctl.cmd   # CLI launchers (all platforms)
├── start.sh / start.bat               # Legacy launchers
├── config.yml                         # Shared configuration
├── .env.example                       # Environment template
├── .mcp.json                          # MCP server config
├── CLAUDE.md                          # AI coding instructions
├── README.md                          # This file
├── backend/                           # [submodule] FastAPI + MinerU
├── web/                               # [submodule] Nuxt 3 frontend
├── kb-mcp/                            # MCP server (74 tools)
│   ├── server.py                      # MCP tool definitions
│   └── kb_client/client.py            # HTTP client layer
├── command/                           # ragctl CLI source
│   ├── ragctl.js                      # Main CLI (1800+ lines)
│   └── package.json
├── .claude/
│   ├── agents/knowledge-admin.md      # Archival Agent definition
│   └── skills/                        # 12 Skill workflows
├── scripts/                           # Service start scripts
└── docs/                              # Documentation
```

---

## ⚙️ Configuration

### config.yml

```yaml
server:
  dev:  { backend_port: 8765, frontend_port: 6789 }
  prod: { backend_port: 8001, frontend_port: 3000 }
vector: { enabled: true }
graph:  { enabled: true, uri: "bolt://127.0.0.1:7687" }
```

### .env (overrides config.yml)

```bash
APP_MODE=dev          # dev | prod
# BACKEND_PORT=9000   # Override port
# NEO4J_PASSWORD=xxx  # Graph DB password
```

Priority: `.env` > `config.yml` > defaults.

---

## 🛠 Development

```bash
ragctl install all              # Install all dependencies
ragctl test backend             # Run backend tests
ragctl test mcp                 # Run MCP tests
ragctl start backend            # Start backend only
ragctl logs backend --lines 100 # View logs
```

### MCP Tool Development

```bash
cd kb-mcp
uv run python server.py          # stdio mode (Claude Code)
uv run python server.py --http   # SSE mode (debugging)
```

---

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| Port in use | `ragctl doctor` shows PID. `ragctl down` to stop. |
| Missing submodule | `git submodule update --init --recursive` |
| npm install fails | Node.js >= 18 required: `node --version` |
| uv sync fails | Install uv: https://docs.astral.sh/uv/ |
| Neo4j not running | `docker compose up -d neo4j` |
| MinerU parse fails | `ragctl health` → check MinerU status |
| MCP tools missing | Restart Claude Code. Verify `.mcp.json` exists. |
| Everything broken | `ragctl doctor` for full diagnostics (19 checks) |

---

## 📊 System Status

| Component | Detail |
|-----------|--------|
| MCP Tools | 74 (CRUD + Search + Graph + Experience) |
| Skills | 12 (full lifecycle workflows) |
| Platforms | Windows · Linux · macOS |
| Vector DB | ChromaDB + bge-m3 (bilingual) |
| Graph DB | Neo4j (497 nodes / 3959 edges) |
| OCR | MinerU (PDF/Office/Image → Markdown) |
| Frontend | Nuxt 3 + Ant Design Vue |
| Backend | FastAPI + Python 3.12 |

---

</div>

<div id="中文">

## 🚀 快速开始

```bash
# 1. 克隆项目
git clone --recursive <repo-url> rag-knowledge
cd rag-knowledge

# 2. 一键初始化（仅第一次，约3-5分钟）
./ragctl init          # Windows: ragctl init

# 3. 一键启动全部服务（约20-40秒）
./ragctl up            # Windows: ragctl up

# 4. 验证服务状态
./ragctl health

# 完成！浏览器打开 → http://localhost:6789
```

### 依赖要求

| 工具 | 版本 | 用途 |
|------|:----:|------|
| [Node.js](https://nodejs.org/) | 18+ | 运行时 (CLI + Web) |
| [uv](https://docs.astral.sh/uv/) | latest | Python 包管理器 |
| [Docker](https://www.docker.com/) | latest | Neo4j 图数据库 _(可选)_ |

`ragctl init` 自动处理子模块初始化、依赖安装、环境配置等所有步骤。

---

## 🎮 启动器 — `ragctl`

**ragctl** 是统一命令行工具，Windows / Linux / macOS 用法完全一致。

| 平台 | 命令 |
|------|------|
| Windows | `ragctl` 或 `ragctl.bat` 或 `ragctl.cmd` |
| Linux / macOS | `./ragctl` |

### 全部命令

```bash
ragctl init              # 首次初始化（安装所有依赖）
ragctl up                # 一键启动全部服务 (Neo4j → Backend → Web)
ragctl down              # 一键停止全部服务 (Web → Backend → Neo4j)
ragctl status            # 查看服务状态 (PID/端口/健康)
ragctl health            # 完整健康检查 (5 项服务)
ragctl doctor            # 诊断常见问题 (19 项检查)
ragctl logs <service>    # 查看日志 (backend/web/mineru)
ragctl config show       # 显示完整配置
ragctl config set <k> <v>  # 修改配置 (热重载)
ragctl start <service>   # 启动指定服务
ragctl stop <service>    # 停止指定服务
ragctl restart <service> # 重启服务
ragctl install <target>  # 安装依赖 (backend/web/mcp/all)
ragctl test <target>     # 运行测试 (backend/web/mcp/all)
ragctl mcp tools         # 列出所有 74 个 MCP 工具
ragctl kb list           # 列出知识库
ragctl kb search <q>     # 搜索知识库
ragctl kb stats          # 知识库统计
```

### 首次使用流程

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│ ragctl init  │ ──▶ │ ragctl up    │ ──▶ │ 打开浏览器  │
│ 约3-5分钟    │     │ 约20-40秒    │     │ :6789       │
└─────────────┘     └──────────────┘     └─────────────┘
  ✓ 检查依赖          ✓ 启动 Neo4j          Web UI 就绪
  ✓ 初始化子模块       ✓ 启动 Backend
  ✓ 安装依赖           ✓ 启动 Web
  ✓ 创建 .env
  ✓ 全部验证
```

---

## 🏗 系统架构

```
┌──────────────────────────────────────────────────────┐
│                  Claude Code / AI Agent               │
│            (通过 MCP 协议进行智能 KB 管理)             │
└──────────────┬──────────────────────┬────────────────┘
               │ MCP (stdio)          │
               ▼                      ▼
┌──────────────────────┐   ┌──────────────────────────┐
│  kb-mcp MCP 服务器   │   │  Nuxt 3 Web (端口 6789)  │
│  74 工具 · Python    │   │  前端界面 + API 代理层    │
└──────────┬───────────┘   └────────────┬─────────────┘
           │ HTTP                        │ HTTP
           ▼                             ▼
┌──────────────────────────────────────────────────────┐
│        FastAPI 后端 (端口 8765)                       │
│    解析调度 · MinerU OCR · 配置管理                   │
└──────────────────────┬───────────────────────────────┘
           │               │                │
           ▼               ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  MinerU OCR  │  │   ChromaDB   │  │    Neo4j     │
│  PDF→Markdown│  │  向量数据库   │  │  图数据库    │
└──────────────┘  └──────────────┘  └──────────────┘
```

**三层元数据**：每次写入原子同步 磁盘 `.md` + `.tree-fs.json` + `.knowledge-base.yml`。

**依赖链**：filesystem 操作走 Web 代理 (6789) · 搜索/图谱/经验操作直连 Backend (8765)。

---

## 🧩 功能特性

### 12 个技能工作流

| 技能 | 用途 | 流程 |
|------|------|------|
| list | 浏览发现知识库 | L1→L3 |
| search | QDCVR 语义检索 | Step 0→6 |
| verify | 完整性质量审计 | V1→V9 |
| ingest | 文档入库流水线 | A0→A9 |
| manage | 移动/改名/删除/合并 | M1→M6 |
| organize | 全库整理重构 | O0→O13 |
| batch | 批量操作 | B1→B7 |
| experience | 经验全生命周期 (E0-E12) | 创建→检索→清理 |
| graph | 知识图谱查询分析 | 构建→查询→分析 |
| enterprise | 企业级跨库多策略检索 | Phase 0→5 |
| summarize | 自动提取经验 | 场景→草稿→入库 |
| dispatcher | 场景智能路由 | 关键词→子技能 |

### 企业级 QDCVR 检索

```
用户查询
  → Step 0: 意图分析 + 查询改写
  → Step 1: 智能选库 (kb_catalog → Agent 判断)
  → Step 2: 两阶段向量召回 (BM25 + 语义向量, balance_kbs)
  → Step 2.5: 文档去重 + 硬阈值 + 短内容降级
  → Step 3: 内容裁决 (读 3000 字正文, 0-8 独立打分)
  → Step 6: 综合回答 + 来源 + 置信度 + 盲点声明
```

**核心原则**：向量定候选，内容定去留。内容分 > 向量分。宁可不给，不要错给。

### 经验库 (P0/P1/P2 分级)

| 级别 | 条件 | 动作 |
|------|------|------|
| P0 Strong | vector≥0.65 + content≥6 + rating≥4 | 直接引用，置顶 |
| P1 Reference | vector≥0.45 + content≥4 | 采用并标注 |
| P2 Weak | vector≥0.35 + content≥3 | 默认抑制 |
| Discard | 内容验证不过 OR vector<0.35 | 永不返回 |

---

## 📁 项目结构

```
rag-knowledge/
├── ragctl / ragctl.bat / ragctl.cmd   # CLI 启动器（全平台）
├── start.sh / start.bat               # 传统启动脚本（备用）
├── config.yml                         # 共享配置文件
├── .env.example                       # 环境变量模板
├── .mcp.json                          # MCP 服务器配置
├── CLAUDE.md                          # AI 编程指令
├── README.md                          # 本文件
├── backend/                           # [子模块] FastAPI + MinerU
├── web/                               # [子模块] Nuxt 3 前端
├── kb-mcp/                            # MCP 服务器 (74 工具)
│   ├── server.py                      # MCP 工具定义
│   └── kb_client/client.py            # HTTP 客户端层
├── command/                           # ragctl CLI 源码
│   ├── ragctl.js                      # 主 CLI (1800+ 行)
│   └── package.json
├── .claude/
│   ├── agents/knowledge-admin.md      # 知识库管理 Agent
│   └── skills/                        # 12 个技能工作流
├── scripts/                           # 服务启动脚本
└── docs/                              # 文档目录
    ├── ARCHITECTURE.md                # 详细架构文档
    ├── OPTIMIZATION-PLAN.md           # 优化计划
    └── PRODUCTION-PLAN.md             # 生产化路线图
```

---

## ⚙️ 配置说明

### config.yml

```yaml
server:
  dev:  { backend_port: 8765, frontend_port: 6789 }
  prod: { backend_port: 8001, frontend_port: 3000 }
vector: { enabled: true }
graph:  { enabled: true, uri: "bolt://127.0.0.1:7687" }
```

### .env (覆盖 config.yml)

```bash
APP_MODE=dev          # dev (开发模式) | prod (生产模式)
# BACKEND_PORT=9000   # 覆盖后端端口
# WEB_PORT=3000       # 覆盖前端端口
# NEO4J_PASSWORD=xxx  # 图数据库密码
```

优先级：**`.env` > `config.yml` > 代码默认值**

---

## 🛠 开发指南

```bash
ragctl install all              # 安装所有依赖
ragctl test backend             # 运行后端测试
ragctl test mcp                 # 运行 MCP 测试
ragctl start backend            # 只启动后端
ragctl logs backend --lines 100 # 查看后端日志
```

### MCP 工具开发

```bash
cd kb-mcp
uv run python server.py          # stdio 模式 (Claude Code 加载)
uv run python server.py --http   # SSE 模式 (调试用)
```

新增工具后需重启 Claude Code 重新加载 MCP。

---

## 🔧 故障排查

| 问题 | 解决方案 |
|------|----------|
| 端口被占用 | `ragctl doctor` 显示 PID。`ragctl down` 停止。 |
| 子模块未初始化 | `git submodule update --init --recursive` |
| npm install 失败 | 检查 Node.js >= 18: `node --version` |
| uv sync 失败 | 安装 uv: https://docs.astral.sh/uv/ |
| Neo4j 未运行 | `docker compose up -d neo4j` |
| MinerU 解析失败 | `ragctl health` 检查 MinerU 状态 |
| MCP 工具不可用 | 重启 Claude Code。确认 `.mcp.json` 存在。 |
| Web 服务挂了 | `ragctl logs web` 查看日志，`ragctl restart web` |
| 全部出问题 | `ragctl doctor` 完整诊断 (19 项检查) |

### 常用诊断命令

```bash
ragctl doctor           # 检查 Python/Node/uv/Docker/配置/子模块/依赖/端口
ragctl health           # 检查 Backend/Web/Neo4j/MinerU/Config 健康状况
ragctl status           # 查看所有服务 PID/端口/运行状态
ragctl logs backend     # 查看后端日志（最近 50 行）
ragctl logs backend -n 200  # 最近 200 行
```

---

## 📊 系统状态一览

| 组件 | 详情 |
|------|------|
| MCP 工具 | 74 个 (CRUD + 搜索 + 图谱 + 经验) |
| 技能工作流 | 12 个 (完整生命周期) |
| 支持平台 | Windows · Linux · macOS |
| 向量引擎 | ChromaDB + bge-m3 (中英双语) |
| 图谱引擎 | Neo4j (497 节点 / 3959 边) |
| OCR 引擎 | MinerU (PDF/Office/图片 → Markdown) |
| 前端框架 | Nuxt 3 + Ant Design Vue |
| 后端框架 | FastAPI + Python 3.12 |

---

## 📚 文档索引

| 文档 | 内容 |
|------|------|
| [CLAUDE.md](CLAUDE.md) | AI 编程指令（完整系统规范） |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | 详细架构与开发指南 |
| [OPTIMIZATION-PLAN.md](docs/OPTIMIZATION-PLAN.md) | 5 阶段优化计划与验收标准 |
| [PRODUCTION-PLAN.md](docs/PRODUCTION-PLAN.md) | 生产化路线图 |
| [skill-test-report-20260715.md](docs/skill-test-report-20260715.md) | 技能场景测试报告 (9.4/10) |

---

</div>

---

<p align="center">
  <sub>Built with ❤️ by the RAG Knowledge Platform Team · 2026</sub>
</p>