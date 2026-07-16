<h1 align="center">
  <img src="./src-tauri/icons/128x128.png" alt="RAG Knowledge Platform" width="80" />
  <br/>
  RAG Knowledge Platform
</h1>

<p align="center">
  <strong>Enterprise-Grade Document Intelligence & Agentic Knowledge Base</strong><br/>
  <em>PDF Parsing · Semantic Search · Knowledge Graph · Experience Library · MCP-Native</em>
</p>

<p align="center">
  <a href="#-quick-start"><img src="https://img.shields.io/badge/Quick%20Start-5%20minutes-blue?style=for-the-badge" /></a>
  <a href="#"><img src="https://img.shields.io/badge/build-passing-brightgreen?style=for-the-badge" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" /></a>
  <a href="#"><img src="https://img.shields.io/badge/platform-Win%20%7C%20Linux%20%7C%20macOS-lightgrey?style=for-the-badge" /></a>
  <a href="#-mcp-tools"><img src="https://img.shields.io/badge/MCP-74%20tools-blueviolet?style=for-the-badge" /></a>
  <a href="#-skills"><img src="https://img.shields.io/badge/Skills-12-orange?style=for-the-badge" /></a>
</p>

---

<details open>
<summary><b>📖 English</b> (click <b>中文</b> below for Chinese)</summary>

## 🌟 Overview

RAG Knowledge Platform transforms PDFs, Office documents, and research papers into a **searchable, graph-connected, experience-driven knowledge base** — accessible through a beautiful Web UI or directly via Claude Code / any MCP-compatible AI agent.

**Why it stands out:**
- 🧠 **QDCVR Retrieval** — Query-Driven, Content-Verified Retrieval with 0-8 independent scoring. Vectors are fast; content is accurate.
- 📊 **Neo4j Knowledge Graph** — 497 nodes · 3,939 edges · 140 documents across 11 KBs.
- 💡 **Experience Library (E0-E12)** — Structured lessons with P0/P1/P2 credibility tiers, decay cycles, and document linkage.
- 🔌 **74 MCP Tools** — Full KB CRUD, semantic search, graph queries, experience lifecycle for AI agents.
- ⚡ **One-Click Setup** — `ragctl setup` installs uv, Python, all dependencies, and the BGE-M3 model.
- 🖥️ **Tauri Desktop** — Visual dashboard for service management, dependency installs, real-time logs, and config editing.
- 🌍 **Cross-Platform** — Windows, Linux, macOS. Zero cloud dependencies — everything runs locally.

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                       Claude Code / AI Agent                    │
│                              │  (MCP stdio)                     │
│                    ┌─────────▼──────────────────────┐           │
│                    │   kb-mcp MCP Server             │           │
│                    │   74 tools · FastMCP · Python   │           │
│                    └──────┬──────────────┬───────────┘           │
│                           │ HTTP         │ direct file IO        │
│                ┌──────────▼──┐    ┌──────▼──────────────┐       │
│                │  Nuxt 3 Web  │    │  FastAPI Backend    │       │
│                │  (proxy)    │◄───│  (parse + MinerU)   │       │
│                │  port 6789   │    │  port 8765          │       │
│                └──────────────┘    └──────┬──────────────┘       │
│                                           │ subprocess           │
│                                    ┌──────▼──────────┐          │
│                                    │  MinerU OCR      │          │
│                                    │  (ephemeral port) │          │
│                                    └─────────────────┘          │
│                                                                  │
│   Storage:  .tree-fs.json + .knowledge-base.yml + Neo4j         │
│   Models:   BGE-M3 (1024-dim) · MinerU OCR models                │
└──────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- **Node.js** 18+ (for web frontend and CLI)
- **uv** (Python package manager — auto-installed by `ragctl setup`)
- **Docker** (optional, for Neo4j)
- **Git** (for submodules)

### One-Click Setup

```bash
git clone --recursive https://github.com/kingdol666/rag-knowledge.git
cd rag-knowledge

# One command installs everything
./ragctl setup          # Linux / macOS
ragctl setup            # Windows

# Start all services
./ragctl up
ragctl up

# Open → http://localhost:6789
```

### Manual Install

```bash
ragctl deps             # Install all dependencies (real-time progress)
ragctl model            # Pre-download BGE-M3 embedding model (~2.2GB)
git submodule update --init --recursive
cp .env.example .env
```

### Desktop App (Tauri)

```bash
cd src-tauri
cargo build --release
# Output: src-tauri/target/release/rag-knowledge-desktop
```

The desktop app provides **one-click bootstrap**, **comprehensive environment check**, **service start/stop**, **real-time log streaming**, and **visual config editing**.

## 📋 Commands

| Command | Description |
|---------|-------------|
| `ragctl setup` | One-click full deployment |
| `ragctl check` | 22-point environment audit |
| `ragctl up` / `down` | Start / stop all services |
| `ragctl status` | Service status overview |
| `ragctl deps` | Install all dependencies |
| `ragctl model` | Download BGE-M3 embedding model |
| `ragctl logs [svc]` | View service logs |
| `ragctl doctor` | Diagnose common issues |
| `ragctl config show` | Show current configuration |

## 📁 Project Structure

```
rag-knowledge/
├── backend/             ← [submodule] FastAPI + MinerU OCR engine
├── web/                 ← [submodule] Nuxt 3 + Ant Design Vue
├── kb-mcp/              ← MCP server — 74 tools for KB operations
├── command/             ← ragctl CLI (Node.js)
├── src-tauri/           ← Tauri desktop application (Rust)
├── .claude/             ← Claude Code skills (12) + agents
├── config.yml           ← Central configuration
├── docker-compose.yml   ← Neo4j container
├── ragctl               ← CLI entry (Linux/macOS)
├── ragctl.bat / .cmd    ← CLI entry (Windows)
└── start.bat / start.sh ← Legacy launchers
```

## 🔧 Tech Stack

| Component | Technology |
|-----------|-----------|
| **Backend** | Python 3.12 · FastAPI · MinerU OCR · ChromaDB |
| **Frontend** | TypeScript · Nuxt 3 · Ant Design Vue · marked |
| **MCP Server** | Python · FastMCP · httpx |
| **CLI** | Node.js · js-yaml |
| **Desktop** | Rust · Tauri v2 · reqwest · tokio |
| **Graph** | Neo4j (Docker) |
| **Embedding** | BGE-M3 (1024-dim) · sentence-transformers |
| **Search** | BM25 + Vector two-stage · QDCVR pipeline |

## 🎯 Skills (12)

| Skill | Flow | Purpose |
|-------|------|---------|
| **knowledgebase** | Router | Dispatch user intent to the correct sub-skill |
| **knowledgebase-ingest** | A0→A9 | Document ingestion with quality gates |
| **knowledgebase-search** | Step0→6 | QDCVR retrieval with content verification |
| **knowledgebase-search-enterprise** | Phase0→5 | Multi-strategy cross-KB search |
| **knowledgebase-manage** | M1→M6 | Document and KB administration |
| **knowledgebase-organize** | O0→O13 | Full collection restructuring |
| **knowledgebase-verify** | V1→V9 | Integrity and quality validation |
| **knowledgebase-list** | L1→L3 | Read-only browsing |
| **knowledgebase-graph** | — | Neo4j graph build, query, analysis |
| **knowledgebase-experience** | E0→E12 | Experience lifecycle management |
| **knowledgebase-experience-summarize** | S1→S5 | Distill and persist structured experiences |
| **knowledgebase-batch** | B1→B7 | High-volume batch operations |

## 🔌 MCP Tools

74 tools across 7 categories, all accessible via `mcp__kb-mcp__*`:

| Category | Tools | Examples |
|----------|:-----:|----------|
| KB CRUD | 6 | `kb_list`, `kb_create`, `kb_update`, `kb_delete` |
| Document CRUD | 10 | `kb_doc_create`, `kb_doc_read`, `kb_doc_update_content`, `kb_doc_delete` |
| Vector Search | 4 | `kb_search_vector`, `kb_search_two_stage`, `kb_search_stats` |
| File System | 3 | `fs_get_tree`, `fs_get_children`, `fs_get_count` |
| Knowledge Graph | 16 | `kb_graph_health`, `kb_graph_search`, `kb_graph_kb_overview` |
| Experience | 21 | `experience_create`, `experience_search_global`, `experience_dashboard` |
| Tags + Cleanup | 4 | `kb_tags_list`, `kb_tags_cleanup`, `kb_cleanup_orphan_collections` |

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push (`git push origin feature/amazing`)
5. Open a Pull Request

## 📄 License

MIT © [kingdol](https://github.com/kingdol666)

---

</details>

<details>
<summary><b>🇨🇳 中文</b></summary>

## 🌟 概述

RAG Knowledge Platform 将 PDF、Office 文档和研究论文转化为**可搜索、图谱连接、经验驱动**的知识库——通过美观的 Web UI 或 Claude Code / 任何 MCP 兼容 AI 代理直接访问。

**核心优势：**
- 🧠 **QDCVR 检索** — 查询驱动·内容验证检索，0-8 分独立评分。
- 📊 **Neo4j 知识图谱** — 497 节点 · 3,939 边 · 11 知识库 · 140 文档。
- 💡 **经验库 (E0-E12)** — P0/P1/P2 可信度分级、衰减周期、文档联动。
- 🔌 **74 个 MCP 工具** — KB CRUD、语义搜索、图谱查询、经验生命周期。
- ⚡ **一键部署** — `ragctl setup` 安装 uv、Python、全部依赖和 BGE-M3 模型。
- 🖥️ **Tauri 桌面** — 可视化仪表盘管理服务、安装依赖、实时日志、配置编辑。
- 🌍 **跨平台** — Windows、Linux、macOS，零云依赖。

## 🚀 快速开始

```bash
git clone --recursive https://github.com/kingdol666/rag-knowledge.git
cd rag-knowledge

# 一键部署
./ragctl setup       # Linux / macOS
ragctl setup         # Windows

# 启动所有服务
ragctl up

# 打开浏览器 → http://localhost:6789
```

## 📋 命令速查

| 命令 | 描述 |
|------|------|
| `ragctl setup` | 一键完整部署 |
| `ragctl check` | 22 项环境审计 |
| `ragctl up` / `down` | 启动 / 停止所有服务 |
| `ragctl status` | 服务状态 |
| `ragctl deps` | 安装所有依赖 |
| `ragctl model` | 下载 BGE-M3 模型 |
| `ragctl logs [svc]` | 查看日志 |
| `ragctl doctor` | 诊断问题 |

## 🎯 12 个技能

| 技能 | 流程 | 用途 |
|------|------|------|
| **knowledgebase** | 路由 | 调度用户意图到正确子技能 |
| **knowledgebase-ingest** | A0→A9 | 带质量门控的文档入库 |
| **knowledgebase-search** | 步骤0→6 | QDCVR 内容验证检索 |
| **knowledgebase-search-enterprise** | 阶段0→5 | 多策略跨库搜索 |
| **knowledgebase-manage** | M1→M6 | 文档与知识库管理 |
| **knowledgebase-organize** | O0→O13 | 全库重组 |
| **knowledgebase-verify** | V1→V9 | 完整性与质量验证 |
| **knowledgebase-list** | L1→L3 | 只读浏览 |
| **knowledgebase-graph** | — | Neo4j 图谱 |
| **knowledgebase-experience** | E0→E12 | 经验生命周期 |
| **knowledgebase-experience-summarize** | S1→S5 | 经验提炼入库 |
| **knowledgebase-batch** | B1→B7 | 大批量操作 |

## 📄 许可证

MIT © [kingdol](https://github.com/kingdol666)

</details>
