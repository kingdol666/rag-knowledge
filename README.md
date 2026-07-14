# RAG Knowledge Platform

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.139%2B-009688)](https://fastapi.tiangolo.com)
[![Nuxt](https://img.shields.io/badge/Nuxt-3.x-00DC82)](https://nuxt.com)
[![Neo4j](https://img.shields.io/badge/Neo4j-5.20-008CC1)](https://neo4j.com)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-1.5%2B-1E1E1E)](https://www.trychroma.com)
[![Tauri](https://img.shields.io/badge/Tauri-2.x-desktop-blueviolet)](https://tauri.app)
[![MCP](https://img.shields.io/badge/MCP-73%20tools-orange)](https://modelcontextprotocol.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> 本地优先、Agent 原生的知识库平台。将 PDF/DOCX/Excel/PPTX/图片解析为结构化 Markdown，通过关键词 + 向量 + 知识图谱三路检索，并以 MCP 工具层暴露全部能力——人类和 AI Agent 都能通过统一接口管理和查询知识库。

---

## 目录

- [项目简介](#项目简介)
- [核心特性](#核心特性)
- [系统架构](#系统架构)
- [目录结构](#目录结构)
- [桌面控制台（Tauri）](#桌面控制台tauri)
- [ragctl CLI](#ragctl-cli)
- [快速开始](#快速开始)
  - [环境要求](#环境要求)
  - [1. 克隆仓库](#1-克隆仓库)
  - [2. 配置](#2-配置)
  - [3. 启动 Neo4j（可选）](#3-启动-neo4j可选)
  - [4. 安装 MinerU OCR 引擎（可选）](#4-安装-mineru-ocr-引擎可选)
  - [5. 启动平台](#5-启动平台)
  - [6. 验证服务](#6-验证服务)
- [跨平台启动](#跨平台启动)
- [使用指南](#使用指南)
  - [Web UI 操作](#web-ui-操作)
  - [MCP / Agent 操作](#mcp--agent-操作)
  - [REST API 调用](#rest-api-调用)
- [MCP 工具参考](#mcp-工具参考)
- [Skill 体系](#skill-体系)
- [Agent 驱动](#agent-驱动)
- [配置详解](#配置详解)
- [设计理念](#设计理念)
- [故障排查](#故障排查)
- [已知限制与路线图](#已知限制与路线图)
- [许可证](#许可证)

---

## 项目简介

RAG Knowledge Platform 将本地文档转化为可搜索、可溯源、Agent 可访问的知识库。

围绕三个核心理念构建：

1. **本地优先** — 所有文件、索引、元数据都保存在本机磁盘，不上传云端，可版本控制、可手动修复。
2. **多信号检索** — 融合关键词搜索（BM25）、语义检索（BGE-M3 + ChromaDB）、知识图谱遍历（Neo4j），三路互补降低幻觉。
3. **Agent 原生** — 全部能力以 73 个 MCP 工具暴露，Claude Code、Cursor 或任何 MCP 兼容 Agent 可直接管理和查询知识库。

### 支持的文件格式

| 类型 | 格式 | 处理方式 |
|------|------|----------|
| PDF | `.pdf` | MinerU OCR/VLM → Markdown |
| Word | `.docx`, `.doc` | MinerU 解析 → Markdown |
| Excel | `.xlsx`, `.xls` | MinerU 解析 → Markdown |
| PPT | `.pptx`, `.ppt` | MinerU 解析 → Markdown |
| 图片 | `.jpg`, `.png`, `.bmp`, `.tiff` | MinerU OCR → Markdown |
| 文本 | `.md`, `.txt`, `.csv`, `.json`, `.yaml`, `.yml`, `.xml`, `.html`, `.log` | 直接入库 |
| 代码 | `.py`, `.js`, `.ts`, `.sh` | 直接入库 |
| 内存文本 | 任意文本内容 | 直接入库 |
| 二进制 | 图片、压缩包等 | 仅元数据存储 |

---

## 核心特性

| 特性 | 描述 |
|------|------|
| **PDF/文档解析** | MinerU OCR/VLM 引擎提取文本、表格、图片，输出结构化 Markdown |
| **知识库管理** | UUID 化知识库、树形文件系统、标签体系、描述管理、子知识库 |
| **关键词搜索** | jieba 分词 + BM25 全文检索，跨知识库搜索 |
| **向量检索** | BGE-M3 嵌入 + ChromaDB 语义检索，支持相似度阈值过滤 |
| **知识图谱** | Neo4j 存储文档关系，基于元数据（标签/同KB）构建跨库关联 |
| **两阶段检索** | BM25 + 图谱扩展召回 → 向量精排，主推荐检索策略 |
| **企业级多策略检索** | 三路并行召回（Agentic KB 判断 + BM25+向量 + 纯向量跨库）→ 交叉验证 → 内容重排 |
| **经验库** | 实践经验结构化存储（场景/方案/教训/指标），支持评审与应用追踪 |
| **MCP Server** | 73 个工具覆盖 KB CRUD、文档管理、解析、搜索、图谱、经验库全场景 |
| **Claude Code Skills** | 11 个 Skill 定义 Agent 自治工作流：入库、整理、搜索、验证、批量操作等 |
| **Web 控制台** | Nuxt 3 + Ant Design Vue 界面，文件浏览、上传解析、搜索一体化 |
| **桌面控制台（Tauri）** | 跨平台桌面应用：零依赖一键引导 + 配置可视化编辑 + 服务管控 + ragctl 终端 |
| **ragctl CLI** | 统一命令行：start/stop/status/health/doctor/config/logs/install/test/mcp/kb |

---

## 系统架构

### 服务拓扑

```text
┌─────────────────────────────────────────────────────────────────┐
│  Agent / Claude Code                                            │
│  .claude/skills/*  →  Archival Agent  →  MCP tools              │
└────────────────────────────┬────────────────────────────────────┘
                             │ stdio / MCP
┌────────────────────────────▼────────────────────────────────────┐
│  kb-mcp (MCP Server)                                           │
│  73 MCP tools (search, parse, manage, graph, experience, ...)  │
│  启动时自动检测后端/前端状态，未运行则自动拉起                      │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP
┌────────────────────────────▼────────────────────────────────────┐
│  Web Layer (Nuxt 3 + Ant Design Vue)                           │
│  web/pages/*  +  web/server/api/*  (代理后端，无 CORS 问题)      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ server/services/                                         │  │
│  │   tree-file-system-service.ts   ← .tree-fs.json 管理      │  │
│  │   knowledge-base-yaml-service.ts ← .knowledge-base.yml    │  │
│  │   kb-search-service.ts          ← 关键词搜索（直读文件）    │  │
│  │   pdf-parse-service.ts          ← 后端解析代理             │  │
│  │   tag-management-service.ts      ← 标签注册表              │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP (server-to-server)
┌────────────────────────────▼────────────────────────────────────┐
│  Backend (FastAPI + uvicorn)                                   │
│  parse  ·  search  ·  vector  ·  graph  ·  health              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ MinerU OCR Engine (ephemeral port)                       │  │
│  │ 子进程管理，绑定 Windows Job Object，端口自动分配           │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│  Storage                                                       │
│  文件系统:  storage/tree-file-system/{kb-name}/                 │
│  元数据:    .tree-fs.json + .knowledge-base.yml                │
│  向量库:    chroma_db/                                         │
│  图谱库:    Neo4j (Docker)                                     │
│  模型缓存:  models_cache/                                      │
└─────────────────────────────────────────────────────────────────┘
```

### 检索流程

```text
用户查询
    │
    ├──► [Stage 1] 关键词搜索 (BM25) ──┐
    ├──► [Stage 1] 图谱邻居扩展 (Neo4j) ┤
    │                                   ▼
    │                        候选文档集 (去重合并)
    │                                   │
    │                    [Stage 2] 向量精排 (BGE-M3 + ChromaDB)
    │                                   │
    └───────────────────────────────────►最终结果 (含来源文档路径)
```

### 企业级多策略检索（跨库盲区补偿）

当标准两阶段搜索返回候选来源 < 2 个知识库时，自动升级为三路并行召回：

```text
Phase 1: 并行三路召回
  ├── Path A: kb_catalog() → Agent 判断相关 KB
  ├── Path B: kb_search_two_stage() → BM25 + 向量
  └── Path C: kb_search_vector(kb_id="") → 纯向量跨库语义

Phase 2: 交叉验证 + 去重 (A+B+C → 合并)
Phase 3: 短内容过滤 (<50 字 → 降级 P2)
Phase 4: 内容重排 (Agent 逐条读内容，0-8 评分)
Phase 5: 融合展示 (P0→P1 优先, P2 隐藏, 盲区声明)
```

### 解析数据流

```text
浏览器 POST /api/parse/file-vt
    │
    ▼
Nuxt Server (代理层)
    │  调用后端 /api/v1/parse/file/vt
    ▼
FastAPI Backend
    │  调度 MinerU 子进程
    ▼
MinerU OCR Engine (临时端口)
    │  PDF → Markdown 转换
    ▼
Backend 返回 markdown_path
    │
    ▼
Nuxt Server 读取 markdown_path 文件
    │  回填内容，写入知识库
    ▼
TreeFileSystemService.uploadFile()
    │  更新 .tree-fs.json + .knowledge-base.yml + 磁盘文件
```

### 读写路径分离

- **写入**（创建/更新/删除/移动）→ HTTP API（Nuxt → Backend），原子操作，三层同步
- **读取**（搜索/列表/目录）→ 直接读取 `.tree-fs.json` + `.knowledge-base.yml`，零后端负载

---

## 目录结构

```text
rag-knowledge/
├── config.yml                    # 全局配置（端口、向量、图谱、搜索等）
├── config.yml.example            # 配置模板
├── .env                          # 环境变量（端口、密码、路径等）
├── .env.example                  # 环境变量模板
├── .mcp.json                     # Claude Code MCP 连接配置
├── docker-compose.yml            # Neo4j 容器编排
├── start.bat                     # Windows 一键启动脚本
├── start.sh                      # Linux/macOS 一键启动脚本
│
├── backend/                      # [Git Submodule] FastAPI 后端
│   ├── main.py                   # 入口：端口探测 → uvicorn 启动
│   ├── config.yml                # MinerU 专用配置
│   ├── app/
│   │   ├── main.py               # FastAPI 应用工厂 + lifespan
│   │   ├── config.py             # 配置单例（读取 config.yml + .env）
│   │   ├── api/routes/           # 路由：health, parse, search, graph
│   │   ├── services/             # 服务层：mineru, vector, graph, keyword
│   │   └── utils/                # 工具：路径解析、模型下载、MinerU 子进程管理
│   ├── tests/                    # 单元测试 + 集成测试
│   └── pyproject.toml            # Python 依赖（uv 管理）
│
├── web/                          # [Git Submodule] Nuxt 3 前端
│   ├── start.mjs                 # 启动脚本（读取 config.yml 解析端口）
│   ├── nuxt.config.ts            # Nuxt 配置
│   ├── server/
│   │   ├── api/                  # Nuxt Server 路由（代理后端）
│   │   │   ├── filesystem/       # 文件树 CRUD
│   │   │   ├── parse/            # PDF 解析代理 + KB 注册
│   │   │   ├── kb/               # KB 搜索、目录、文档 CRUD、标签
│   │   │   ├── graph/            # 图谱 API 代理
│   │   │   └── preview/          # 文件预览
│   │   └── services/             # 核心业务逻辑
│   │       ├── tree-file-system-service.ts      # .tree-fs.json 管理
│   │       ├── knowledge-base-yaml-service.ts   # .knowledge-base.yml 管理
│   │       ├── kb-search-service.ts             # 关键词搜索
│   │       ├── pdf-parse-service.ts             # 后端解析代理
│   │       └── tag-management-service.ts        # 标签注册表
│   ├── composables/              # Vue 组合式函数
│   ├── pages/                    # 页面组件
│   ├── types/                    # TypeScript 类型定义
│   └── storage/tree-file-system/ # 知识库磁盘存储
│
├── kb-mcp/                       # MCP Server（本地模块，非 Submodule）
│   ├── server.py                 # 73 个 MCP 工具定义
│   ├── client.py                 # KbClient 快速测试脚本
│   ├── kb_client/client.py       # HTTP 客户端（全部 HTTP 逻辑）
│   ├── config.py                 # 配置读取（从 config.yml 解析 URL）
│   ├── task_registry.py          # 异步后台任务管理（解析任务）
│   └── pyproject.toml            # MCP + httpx 依赖
│
├── command/                      # ragctl CLI（Node.js 统一管理器）
│   ├── ragctl.js                 # start/stop/status/health/doctor/config/logs/install/test/mcp/kb
│   ├── ragctl                    # Linux/macOS 入口
│   └── ragctl.bat                # Windows 入口
│
├── src-tauri/                    # Tauri v2 桌面控制台
│   ├── Cargo.toml                # Rust 依赖（tauri 2 / reqwest / tokio / serde_yaml）
│   ├── tauri.conf.json           # 窗口 / bundle / withGlobalTauri 配置
│   ├── capabilities/default.json # 权限（core:default）
│   ├── icons/                    # cargo tauri icon 全套
│   ├── frontend/index.html       # 控制面板 SPA（vanilla JS + Tauri invoke）
│   └── src/
│       ├── main.rs               # Tauri Builder + 命令注册
│       └── commands.rs           # 启动/检测/引导/配置/日志/ragctl 全部命令
│
├── .claude/                      # Claude Code 配置
│   ├── agents/
│   │   └── knowledge-admin.md    # Archival Agent 定义
│   └── skills/                   # 11 个 Skill 定义
│       ├── knowledgebase/                # 主分发器
│       ├── knowledgebase-ingest/         # 文档入库
│       ├── knowledgebase-manage/         # 文档/KB 管理
│       ├── knowledgebase-organize/       # 全库整理重组
│       ├── knowledgebase-search/         # VFCR 检索
│       ├── knowledgebase-search-enterprise/ # 企业级多策略检索
│       ├── knowledgebase-list/           # 列表浏览
│       ├── knowledgebase-verify/         # 完整性校验
│       ├── knowledgebase-batch/          # 批量操作
│       ├── knowledgebase-experience/     # 经验库管理
│       ├── knowledgebase-experience-summarize/ # 经验总结入库
│       └── knowledgebase-graph/          # 知识图谱
│
├── storage/                      # 运行时文件存储
│   └── tree-file-system/         # 知识库根目录
│       ├── .tree-fs.json         # 全局文件树索引
│       └── {kb-name}/
│           ├── .knowledge-base.yml  # 单 KB 文档索引
│           ├── doc1.md
│           └── images/
│
├── chroma_db/                    # ChromaDB 向量数据库持久化
├── models_cache/                 # Embedding 模型缓存
├── tests/                        # 端到端自动化测试
│   └── test_all_skills.py        # 全量 Skill + MCP 工具测试
└── docs/
    └── ARCHITECTURE.md           # 详细架构文档
```

---

## 快速开始

> 🚀 **最推荐：桌面控制台一键启动** — 全新机器（零依赖）也能一键拉起。详见 [桌面控制台（Tauri）](#桌面控制台tauri)。下面是传统手动方式。

### 环境要求

| 组件 | 版本要求 | 用途 |
|------|----------|------|
| Python | 3.12（精确） | 后端 + MCP Server |
| [uv](https://docs.astral.sh/uv/) | 最新版 | Python 依赖管理 |
| Node.js | ≥ 18（推荐 LTS 22） | 前端 |
| npm | 随 Node.js 安装 | 前端依赖 |
| Git | 支持子模块 | 克隆仓库 |
| Docker / Docker Compose | 可选 | Neo4j 知识图谱 |

> **跨平台支持**：Windows / Linux / macOS 一等支持。`backend/pyproject.toml` 通过 marker 条件源适配三平台 — Windows 与 Linux x86_64 走 PyTorch cu130 索引（NVIDIA CUDA），macOS 与 Linux aarch64 自动回退 PyPI（CPU/MPS）。`uv sync` 在三平台均可直接通过，无需手动替换 wheel。

### 1. 克隆仓库

```bash
git clone --recursive https://github.com/kingdol666/rag-knowledge.git
cd rag-knowledge
```

如果已经克隆但没有 `--recursive`：

```bash
git submodule update --init --recursive
```

## 桌面控制台（Tauri）

本项目提供一个 **Tauri v2 桌面控制台**，把整个平台包装成一个桌面应用：一个窗口管所有服务，**全新机器（零依赖）也能一键拉起**。

### 启动桌面控制台

```bash
cd src-tauri
cargo tauri dev      # 开发模式（首次编译 ~1-2 分钟，之后秒级）
```

打包成 Windows 安装器：

```bash
cd src-tauri
cargo tauri build    # 产出 src-tauri/target/release/bundle/nsis/RAG Knowledge_1.0.0_x64-setup.exe
```

### 桌面控制台功能

| 功能 | 说明 |
|------|------|
| **🚀 一键引导** | 检测 + 自动安装全部依赖。零依赖机器也能跑 |
| **🔍 依赖检查** | 8 项依赖卡片实时状态（uv/python/node/docker/submodules/backend_deps/web_deps/models_embedding），每项可单独安装 |
| **▶ 一键启动** | backend → 等就绪 → web 串行拉起 |
| **📡 服务管控** | 各组件单独启动/停止（backend/web/neo4j），状态卡片每 6s 自动刷新 |
| **📝 配置可视化** | 递归渲染 config.yml + .env 表单，改完「💾 保存并热重载」（backend 运行中即生效，写盘前自动备份 .bak） |
| **🖥️ 控制台** | backend/web/mineru 实时日志 + ragctl 指令终端（status/health/doctor/logs/kb list/mcp tools…） |
| **🌐 打开 Web UI** | 系统浏览器打开 Nuxt 前端（完整 KB 业务功能） |

### 零依赖一键引导流程

桌面控制台的「🚀 一键引导」会按顺序执行（全程流式进度日志）：

```
1. 装 uv          → Win PowerShell irm / Unix curl 官方安装器（单二进制）
2. 装 Python 3.12 → uv python install（用户无需预装 Python）
3. 初始化子模块   → git submodule update --init --recursive
4. 装后端依赖     → uv sync（torch/transformers/mineru，~3.8GB）
5. 下载模型       → bge-m3（~2.2GB，断点续传 + hf-mirror 镜像）
6. 装前端依赖     → npm install（检测到 Node 时）
```

每步幂等（已就绪则跳过），失败中断并报错。

### 跨平台

桌面控制台基于 Tauri v2，支持 Windows / Linux / macOS：
- uv 安装：Windows `irm https://astral.sh/uv/install.ps1 | iex`；Linux/macOS `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Python：由 `uv python install` 统一下载管理（不依赖系统 Python）
- 子进程 PATH 自动富化（`~/.local/bin` + `~/.cargo/bin`），引导装的 uv 能被后续 spawn 找到

> **Node.js 是唯一需用户预装的**：uv 只管 Python；web/前端/Claude Code 依赖 node。桌面控制台会检测并提示（不会阻塞 backend 引导）。

### 配置可视化

桌面控制台的「配置可视化编辑」递归渲染 config.yml + backend/config.yml + .env 的全部字段：

- **8 个分组**：Server / Storage / Vector / Embedding / Graph / Search / MinerU / 环境变量
- **类型自动转换**：bool / int / float / array（逗号分隔）正确写回
- **热重载**：保存后 best-effort 调 `/api/v1/config/reload`，运行中的 backend 即时生效（无需重启）
- **备份**：写 config.yml / .env 前自动备份 `.bak`

---

## ragctl CLI

命令行统一管理工具（Node.js，零外部依赖除 js-yaml）：

```bash
ragctl <command> [subcommand] [options]
```

| 命令 | 说明 |
|------|------|
| `ragctl start [backend\|web\|neo4j\|mcp\|all]` | 启动服务（dev 开终端窗口 / prod 后台静默） |
| `ragctl stop [backend\|web\|neo4j\|mcp\|all]` | 停止服务（按端口 + PID 双定位） |
| `ragctl status` | 显示所有服务状态 + 配置摘要（backend/web/neo4j/mineru/mcp） |
| `ragctl restart [service]` | 重启服务 |
| `ragctl health` | 全服务 HTTP 健康检查 |
| `ragctl doctor` | 诊断环境（Python/uv/node/npm/docker/端口/配置一致性） |
| `ragctl config show\|get\|set\|reload\|edit` | 配置管理（支持热重载） |
| `ragctl logs [backend\|web\|mineru] --lines N` | 查看日志尾部 |
| `ragctl install [backend\|web\|mcp\|all]` | 安装依赖（uv sync / npm install） |
| `ragctl test [backend\|web\|mcp]` | 运行测试套件 |
| `ragctl mcp start\|stop\|status\|tools` | MCP server 管理 |
| `ragctl kb list\|search\|stats` | 知识库快速操作 |

**dev/prod 终端可见性**：
- **dev**（默认）：`start` 打开可见终端窗口实时显示日志，关闭窗口即停服务
- **prod**：`start --mode prod` 后台静默启动（守护进程式，日志写文件）

**示例**：

```bash
ragctl status                      # 查看全部服务状态
ragctl start all                   # dev 模式一键启动（弹终端窗口）
ragctl start all --mode prod       # prod 模式后台启动
ragctl doctor                      # 环境诊断
ragctl config set server.dev.backend_port 9000   # 改端口 + 热重载
ragctl logs backend --lines 100    # 看 backend 日志
ragctl kb search "PET 双向拉伸"     # CLI 检索
```

---

## 跨平台启动

| 平台 | GPU | dev 启动 | prod 启动 |
|------|-----|----------|-----------|
| Windows | NVIDIA CUDA | `start.bat dev` | `start.bat prod` |
| Windows | 无 | `start.bat dev`（CPU） | `start.bat prod` |
| Linux x86_64 | NVIDIA | `./start.sh dev` | `./start.sh prod` |
| Linux x86_64 | 无 | `./start.sh dev`（CPU） | `./start.sh prod` |
| Linux aarch64 | — | `./start.sh dev`（CPU） | `./start.sh prod` |
| macOS Apple Silicon | MPS | `./start.sh dev` | `./start.sh prod` |
| macOS Intel | 无 | `./start.sh dev`（CPU） | `./start.sh prod` |

**GPU 后端自动选择**（无需配置）：
- `torch.cuda.is_available()` → `cuda`（Windows/Linux + NVIDIA）
- `torch.backends.mps.is_available()` → `mps`（macOS Apple Silicon）
- 否则 → `cpu`

**通用依赖**（三平台）：Python 3.12 · uv · Node.js ≥18 · npm · Git · Docker（可选，Neo4j 图谱）

**模型下载镜像**（可选）：默认中国镜像 hf-mirror.com；海外设 `HF_ENDPOINT=https://huggingface.co`

### 2. 配置

```bash
# 环境变量
cp .env.example .env

# 全局配置
cp config.yml.example config.yml
```

编辑 `.env`（按需修改端口）：

```env
APP_MODE=dev
BACKEND_PORT=8765
WEB_PORT=6789
TREE_STORAGE_PATH=./storage/tree-file-system
NEO4J_PASSWORD=123456
```

编辑 `config.yml` 启用/禁用功能（默认全部启用）：

```yaml
vector:
  enabled: true

graph:
  enabled: true
  password: "123456"   # 或使用 ${NEO4J_PASSWORD} 从 .env 读取
```

> **配置优先级**：环境变量 > config.yml > 代码内部默认值

### 3. 启动 Neo4j（可选）

知识图谱功能需要 Neo4j。如果不需要图谱功能，可跳过此步。

```bash
docker compose up -d neo4j
```

- Neo4j Browser: [http://localhost:7474](http://localhost:7474)
- Bolt URI: `bolt://127.0.0.1:7687`
- 默认用户名: `neo4j`
- 密码: 由 `.env` 中 `NEO4J_PASSWORD` 决定

> 如果图谱功能启用但 Neo4j 未运行，图谱相关功能返回空结果，不会导致后端崩溃。

### 4. 安装 MinerU OCR 引擎（可选）

PDF/DOCX/Excel/PPTX/图片解析需要 MinerU。如果只需处理纯文本/Markdown，可跳过。

> `uv sync` 已含 `mineru[core]` 依赖，**无需手动安装**。首次解析时自动下载模型（默认 ModelScope 镜像；海外可设 `HF_ENDPOINT=https://huggingface.co` 切换 HuggingFace 直连）。

MinerU 的配置在 `backend/config.yml`：

```yaml
mineru:
  enabled: true
  host: "127.0.0.1"
  start_on_boot: true           # 后端启动时自动拉起 MinerU
  startup_timeout: 60
  model_source: modelscope      # 或 huggingface
```

> MinerU 端口是**临时自动分配**的，不固定。后端通过 `MineruApiManager(port=None)` 自动选择空闲端口，避免与常用开发端口冲突。请勿在代码中硬编码端口。

### 5. 启动平台

#### 方式一：一键启动（推荐）

**Windows:**

```bat
start.bat dev
```

**Linux / macOS:**

```bash
./start.sh dev
```

这会打开两个终端窗口：
- **后端终端**：FastAPI 服务，端口来自 `config.yml`（dev 模式默认 8765）
- **前端终端**：Nuxt 3 服务，端口来自 `config.yml`（dev 模式默认 6789）

> `start.bat` / `start.sh` 支持参数：`dev`（热重载）、`prod`（生产模式）

#### 方式二：手动启动各服务

**启动后端：**

```bash
cd backend
uv sync                    # 首次安装依赖
APP_MODE=dev uv run python main.py
```

**启动前端：**

```bash
cd web
npm install                # 首次安装依赖
APP_MODE=dev npm run dev
```

#### 方式三：通过 Claude Code 自动启动

kb-mcp 在启动时会自动检测后端和前端状态。如果未运行，会自动拉起：

```bash
# 在 Claude Code 中直接使用 kb-mcp 工具即可
# kb-mcp 会自动检测并启动所需服务
```

### 6. 验证服务

| 服务 | 地址 | 说明 |
|------|------|------|
| Web UI | [http://localhost:6789](http://localhost:6789) | Nuxt 3 前端界面 |
| 后端 API | [http://localhost:8765/api/v1/health](http://localhost:8765/api/v1/health) | 健康检查 |
| API 文档 | [http://localhost:8765/docs](http://localhost:8765/docs) | FastAPI Swagger UI |
| Neo4j Browser | [http://localhost:7474](http://localhost:7474) | 图谱可视化（需 Docker） |

---

## 使用指南

### Web UI 操作

#### 创建知识库

1. 打开 [http://localhost:6789](http://localhost:6789)
2. 进入 **文件系统** 页面
3. 在文件树空白处右键 → **新建知识库**
4. 输入名称和描述

#### 上传并解析 PDF

1. 选中一个知识库文件夹
2. 点击 **上传文件** 或拖拽 PDF 到目标位置
3. 右键已上传的文件 → **解析文档**
4. 等待解析任务完成（状态会在界面更新）

#### 搜索知识库

1. 进入 **知识库搜索** 页面
2. 输入关键词进行搜索
3. 搜索结果会显示匹配的文档及其路径

### MCP / Agent 操作

配置好 `.mcp.json` 后，在 Claude Code 中可以直接使用自然语言操作知识库：

#### 入库流程

```text
用户: "帮我把这份 PDF 解析入库"
Agent 执行:
  1. kb_list()                    → 查看现有知识库
  2. parse_doc(file_path="...")    → 非阻塞解析
  3. parse_task_status(task_id)    → 轮询直到完成
  4. kb_doc_create(kb_id, name, content, description) → 存入知识库
  5. kb_index_document(kb_id, doc_path) → 构建向量+图谱索引
```

#### 搜索流程

```python
# 两阶段检索（推荐）
kb_search_two_stage(
    query="汽轮机振动分析",
    top_k=5
)

# 纯向量检索
kb_search_vector(
    query="what causes turbine vibration",
    top_k=5
)

# 关键词搜索
kb_search(
    query="turbine failure",
    top_k=10
)
```

#### 知识图谱

```python
# 构建图谱
kb_graph_build_all(force=True)

# 查看统计
kb_graph_stats()

# 查找跨知识库桥梁文档
kb_graph_cross_kb_documents(min_kbs=2)

# 查找文档间关系路径
kb_graph_document_paths(doc_a="KB1/doc1.md", doc_b="KB2/doc2.md")
```

### REST API 调用

**关键词搜索：**

```bash
curl "http://localhost:8765/api/v1/search/?query=turbine%20failure&top_k=10"
```

**向量搜索：**

```bash
curl -X POST http://localhost:8765/api/v1/search/vector \
  -H "Content-Type: application/json" \
  -d '{"query": "what causes turbine vibration", "top_k": 5}'
```

**两阶段搜索（推荐）：**

```bash
curl -X POST http://localhost:8765/api/v1/search/two-stage \
  -H "Content-Type: application/json" \
  -d '{"query": "turbine vibration analysis", "top_k": 5}'
```

**图谱搜索：**

```bash
curl "http://localhost:8765/api/v1/graph/search?keyword=turbine&limit=20"
```

**重建索引：**

```bash
curl -X POST http://localhost:8765/api/v1/search/reindex \
  -H "Content-Type: application/json" \
  -d '{"kb_id": "<kb-uuid>", "force": true}'
```

---

## MCP 工具参考

kb-mcp 提供 **73 个 MCP 工具**，覆盖知识库全生命周期管理。所有工具返回 JSON 字符串。

### 健康检查（2 个）

| 工具 | 说明 |
|------|------|
| `health_check()` | 检查后端、前端、MinerU 状态 |
| `backend_status()` | 后端权威状态（MinerU 健康以此为准） |

### 知识库 CRUD（4 个）

| 工具 | 说明 |
|------|------|
| `kb_list()` | 列出所有知识库（id/name/desc/docCount） |
| `kb_create(name, description, parent_id)` | 创建知识库，parent_id 可创建子知识库 |
| `kb_update(kb_id, name, description)` | 更新知识库名称/描述 |
| `kb_delete(kb_id)` | 删除知识库（不可恢复） |

### 知识库目录（3 个，Agent 优化）

| 工具 | 说明 |
|------|------|
| `kb_catalog()` | 轻量级 KB 概览（仅 id+描述，最少上下文） |
| `kb_doc_catalog(kb_id)` | 轻量级文档扫描（无 file_size/tags） |
| `fs_catalog_all(include_files)` | 一次性获取扁平文件树 |

### 文档管理（9 个）

| 工具 | 说明 |
|------|------|
| `kb_get_documents(kb_id)` | 获取 KB 内所有文档元信息 |
| `kb_doc_read(kb_id, doc_path, doc_id, max_chars, offset, limit)` | 读取文档内容 |
| `kb_doc_create(kb_id, name, content, description)` | 创建文档（原子：文件+.tree-fs.json+.yml） |
| `kb_doc_update_meta(kb_id, doc_path, name, description)` | 更新文档元信息（重命名同步路径） |
| `kb_doc_update_content(kb_id, doc_path, content)` | 更新文档内容（同步 file_size） |
| `kb_doc_delete(kb_id, doc_path)` | 删除文档 |
| `kb_doc_batch_delete(kb_id, doc_paths)` | 批量删除（⚠️ 需完整路径） |
| `kb_doc_move(doc_path, target_kb_id)` | 移动文档到另一个 KB |
| `preview_file(node_id, path)` | 按 UUID 或路径预览文件 |

### 文件系统（9 个）

| 工具 | 说明 |
|------|------|
| `fs_get_tree(include_files, max_depth)` | 获取完整文件树 |
| `fs_get_children(parent_id)` | 获取子节点 |
| `fs_get_node(node_id)` | 获取单个节点 |
| `fs_get_count()` | 获取文件/文件夹计数 |
| `fs_create_folder(name, parent_id, description, is_knowledge_base)` | 创建文件夹/知识库 |
| `fs_create_file(name, parent_id, description)` | 创建文件（仅元数据） |
| `fs_update_node(node_id, name, description)` | 更新节点 |
| `fs_delete_node(node_id)` | 删除节点（递归，不可恢复） |
| `fs_upload_file(file_path, parent_id, description)` | 上传本地文件 |

### 解析（4 个，非阻塞）

| 工具 | 说明 |
|------|------|
| `parse_doc(file_path, use_ocr)` | 非阻塞解析单个文件，返回 task_id |
| `parse_doc_batch(file_paths, use_ocr)` | 批量解析，单个 task_id 管理全部 |
| `parse_task_status(task_id)` | 查询解析任务状态 |
| `parse_tasks_list(status)` | 列出会话内的解析任务 |

### 标签（4 个）

| 工具 | 说明 |
|------|------|
| `kb_tags_list()` | 列出所有标签 |
| `kb_tag_create(tag)` | 创建标签（≤50 字符，自动去重） |
| `kb_doc_update_tags(kb_id, doc_path, tags)` | 更新文档标签 |
| `kb_doc_get_by_tag(tag, kb_id)` | 按标签查找文档 |

### 搜索（6 个）

| 工具 | 说明 |
|------|------|
| `kb_search(query, top_k)` | 元数据搜索（name+description，非全文） |
| `kb_search_vector(query, kb_id, top_k, score_threshold, balance_kbs)` | 纯向量语义搜索 |
| `kb_search_batch_vector(query_doc_paths, kb_id, top_k, score_threshold)` | 批量向量相似度查询 |
| `kb_search_two_stage(query, kb_id, stage1_top_k, stage2_top_k, ...)` | 两阶段精准检索（推荐首选） |
| `kb_search_stats(kb_id)` | 向量索引统计 |

### 向量索引（3 个）

| 工具 | 说明 |
|------|------|
| `kb_index_document(kb_id, doc_path, doc_id, ...)` | 单文档向量+图谱索引 |
| `kb_batch_index(kb_id, doc_paths, force)` | 批量索引 |
| `kb_reindex(kb_id, force)` | 重建整个 KB 的索引 |

### 知识图谱（17 个）

| 工具 | 说明 |
|------|------|
| `kb_graph_search(keyword, limit)` | 搜索图谱文档节点 |
| `kb_graph_search_kbs(keyword, limit)` | 搜索 KB 节点 |
| `kb_graph_search_tags(keyword, limit)` | 搜索标签节点 |
| `kb_graph_neighbors(node_id, node_type, depth)` | 获取邻居子图 |
| `kb_graph_stats()` | 图谱统计信息 |
| `kb_graph_health()` | Neo4j 健康探测 |
| `kb_graph_document(doc_path, limit)` | 单文档图谱视图 |
| `kb_graph_document_related(doc_path, limit)` | 关联文档 |
| `kb_graph_documents_by_tag(tag_name, limit)` | 按标签查文档 |
| `kb_graph_kb_overview(kb_id)` | KB 级图谱概览 |
| `kb_graph_build_kb(kb_id, force)` | 构建单 KB 图谱 |
| `kb_graph_build_all(force)` | 构建全库图谱 |
| `kb_graph_cross_kb_documents(min_kbs, limit)` | 跨库桥梁文档 |
| `kb_graph_document_paths(doc_a, doc_b, max_depth)` | 文档间最短路径 |
| `kb_graph_central_documents(kb_id, top_n)` | 核心文档（度中心性） |
| `kb_graph_delete_document(doc_path)` | 删除文档图谱数据 |
| `kb_graph_delete_kb(kb_id)` | 删除 KB 图谱数据 |

### 经验库（12 个）

| 工具 | 说明 |
|------|------|
| `experience_create(kb_id, title, scenario, ...)` | 创建经验记录 |
| `experience_read(kb_id, exp_id)` | 读取单条经验 |
| `experience_list(kb_id, scenario, ...)` | 列出经验 |
| `experience_update(kb_id, exp_id, ...)` | 更新经验 |
| `experience_delete(kb_id, exp_id)` | 删除经验 |
| `experience_apply(kb_id, exp_id, user, ...)` | 记录经验应用 |
| `experience_review(kb_id, exp_id, reviewer, ...)` | 评审经验 |
| `experience_find_by_scenario(kb_id, scenario)` | 按场景查找 |
| `experience_summary(kb_id)` | 经验库摘要 |
| `experience_search(kb_id, query, top_k)` | 关键词搜索经验 |
| `experience_search_vector(kb_id, query, top_k)` | 向量搜索经验 |
| `experience_search_global(query, top_k)` | 全局跨库搜索经验 |

---

## Skill 体系

项目包含 **11 个 Claude Code Skill**，定义 Agent 自治工作流。通过 `.claude/skills/` 目录组织，由 `knowledgebase` 主分发器根据用户意图自动路由。

### Skill 列表

| Skill | 触发词 | 工作流 |
|-------|--------|--------|
| **knowledgebase** | 任意 KB 相关操作 | 主分发器，场景诊断 → 路由到子 Skill |
| **knowledgebase-ingest** | 上传、存储、解析、导入 | A0→A9：调研 → 获取内容 → 分析分类 → 匹配/创建 KB → 按文件类型路由存储 → 分配标签 → 构建索引 → 验证 |
| **knowledgebase-manage** | 移动、改名、删除、合并 | M1→M6：确认 → 执行 → 重建索引 → 验证 |
| **knowledgebase-organize** | 整理、清洗、重组、审计 | O0→O14：定义标准 → 深度调研 → 审计 → 重分类 → 执行修复 → 验证 → 索引覆盖审计 → 三层一致性清洗 → 图谱重建 |
| **knowledgebase-search** | 搜索、查询、问答、检索 | VFCR：两阶段快速召回 → 内容验证（读 3000 字，0-8 评分）→ 命中（≥6）即退；未命中则扩展召回 |
| **knowledgebase-search-enterprise** | 跨库搜索、盲区补偿 | 三路并行召回 → 交叉验证 → 短内容过滤 → 内容重排 → 融合展示 |
| **knowledgebase-list** | 查看、列出、浏览 | L1→L3：全局清单 → KB 详情 → 文件树浏览 |
| **knowledgebase-verify** | 校验、核对、完整性 | V1→V6：健康检查 → 三层元数据一致性 → 解析质量 → 索引覆盖 → 结构化报告 |
| **knowledgebase-batch** | 批量、全量、所有文档 | B1→B7：批量标签 → 批量描述 → 目录批量入库 → 批量移动 → 跨库去重 → 导出摘要 → 图谱重建 |
| **knowledgebase-experience** | 经验、评分、评审、应用 | 创建 → 检索（P0/P1/P2 可信度分级）→ 应用 → 评审 → 摘要 |
| **knowledgebase-experience-summarize** | 记录经验、总结、保存教训 | 场景诊断 → LLM 提炼 → 用户确认 → experience_create → 验证 |
| **knowledgebase-graph** | 图谱、知识图谱、关系 | 构建 → 查询 → 跨库分析 → 路径发现 → 核心文档 → 清理 |

### 场景诊断矩阵

Agent 根据用户消息自动路由到对应 Skill：

```
用户消息 → knowledgebase (主分发器)
    │
    ├─ "上传/解析/导入"     → knowledgebase-ingest
    ├─ "移动/改名/删除/合并" → knowledgebase-manage
    ├─ "整理/清洗/审计"     → knowledgebase-organize
    ├─ "搜索/查询/问答"     → knowledgebase-search
    │    └─ 跨库盲区         → knowledgebase-search-enterprise (自动升级)
    ├─ "查看/列出/浏览"     → knowledgebase-list
    ├─ "校验/核对/完整性"   → knowledgebase-verify
    ├─ "批量/全量/所有"     → knowledgebase-batch
    ├─ "经验/评分/评审"     → knowledgebase-experience
    ├─ "记录经验/总结"      → knowledgebase-experience-summarize
    ├─ "图谱/关系"          → knowledgebase-graph
    └─ 多种混合             → 按优先级排序执行
```

### 经验可信度模型

| 等级 | 条件 | 行为 |
|------|------|------|
| **P0 强推荐** | 场景精确匹配 ∧ 向量 ≥ 0.65 ∧ 评分 ≥ 4 | 置顶推荐 |
| **P1 参考** | 向量 ≥ 0.55 ∧ 评分 ≥ 3 | 推荐，标注可信度 |
| **P2 灰区** | 0.45 ≤ 向量 < 0.55 | 默认抑制，仅展开时显示 |
| **丢弃** | 向量 < 0.45 或不同设备/部件 | 永不呈现 |

---

## Agent 驱动

### Archival Agent

项目通过 `.claude/agents/knowledge-admin.md` 定义了 **Archival** — 知识库管理员 Agent。

**身份**：23 年信息科学经验的知识管理专家，拥有全部 73 个 MCP 工具的调用权限。

**工作流程**：

```text
Step 0 — 场景诊断：分析用户意图 → 路由到对应子 Skill
Step 1 — 调研：kb_list() + kb_tags_list() → 了解现状
Step 2 — 执行：调用子 Skill 的流程
Step 3 — 反思：扫描潜在问题（重叠 KB、缺失标签等）
Step 4 — 审计日志：大批量操作写入 changelog
```

**设计原则**：

- **决策者而非菜单**：用户说"存这个"，Agent 自己判断放到哪个 KB，然后告知结果
- **原子操作**：磁盘文件 + `.tree-fs.json` + `.knowledge-base.yml` 三层同步
- **先调研后执行**：任何修改前先 `kb_list()` + `kb_tags_list()`
- **索引显式触发**：创建文档后必须手动 `kb_index_document()`
- **错误递进恢复**：重试 → 备选工具 → 清晰报告

### MCP 连接配置

项目根目录 `.mcp.json` 自动连接 Claude Code 与 kb-mcp：

```json
{
  "mcpServers": {
    "kb-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "kb-mcp", "python", "server.py"],
      "env": { "APP_MODE": "dev" }
    }
  }
}
```

kb-mcp 启动时会自动检测后端/前端是否运行，未运行则自动拉起。

---

## 配置详解

### 配置文件总览

| 文件 | 用途 |
|------|------|
| `.env` | 环境变量（端口、密码、路径、超时） |
| `config.yml` | 全局配置（端口、向量、图谱、搜索权重） |
| `backend/config.yml` | MinerU 专用配置 |
| `.mcp.json` | MCP Server 连接配置 |

### 配置优先级

```
环境变量 (.env) > config.yml > 代码内部默认值
```

### .env 关键变量

```env
# 运行模式
APP_MODE=dev                    # dev=热重载, prod=生产

# 后端
BACKEND_PORT=8765               # 后端端口
# BACKEND_URL=http://localhost:8765  # 完整URL（设置后PORT被忽略）

# 前端
WEB_PORT=6789                   # 前端端口

# 存储
TREE_STORAGE_PATH=./storage/tree-file-system

# Neo4j
NEO4J_PASSWORD=123456

# MCP 超时
# MCP_HTTP_TIMEOUT=30           # HTTP 请求超时
# MCP_PARSE_TIMEOUT=300         # PDF 解析超时
```

### config.yml 完整配置

```yaml
server:
  cors_origins: ["*"]
  dev:
    host: "0.0.0.0"
    backend_port: 8765
    frontend_port: 6789
    backend_url: "http://localhost:8765"
  prod:
    host: "0.0.0.0"
    backend_port: 8001
    frontend_port: 3000
    backend_url: "http://localhost:8001"

storage:
  tree_fs_root: "./storage/tree-file-system"

vector:
  enabled: true
  persist_dir: "./chroma_db"
  collection_prefix: "kb_"
  chunk_size: 500
  chunk_overlap: 50
  top_k: 5
  score_threshold: 0.35
  experience_score_threshold: 0.55

embedding:
  model_name: "BAAI/bge-m3"
  cache_dir: "./models_cache"
  device: "auto"                # auto → CUDA if available, else CPU
  batch_size: 32
  normalize: true

graph:
  enabled: true
  uri: "bolt://127.0.0.1:7687"
  username: "neo4j"
  password: "123456"
  database: "neo4j"
  pool:
    max_connection_pool_size: 50
    connection_acquisition_timeout: 30
    max_connection_lifetime: 3600
  retry:
    max_attempts: 3
    base_delay: 0.5

search:
  two_stage:
    enabled: true
    stage1_top_k: 20
    stage2_top_k: 5
    stage1_keyword_weight: 0.5
    stage1_graph_weight: 0.5
    graph_neighbor_depth: 1
    min_candidates: 3
```

### 存储模型

```text
storage/tree-file-system/
├── .tree-fs.json                    # 全局索引：所有文件夹+文件的元数据
├── {knowledge-base-name}/
│   ├── .knowledge-base.yml          # 单 KB 文档索引（name, description, path, tags, metadata）
│   ├── doc1.md                      # 解析/上传的 Markdown 文档
│   ├── doc2.md
│   └── images/                      # 从 PDF 提取的图片
```

- `.tree-fs.json` — 权威树结构，文件夹/文件 CRUD 总是先更新它
- `.knowledge-base.yml` — 每个 KB 的搜索索引，`kb_search` 直接读取

---

## 设计理念

### 1. 本地优先，文件为中心

文档以纯 Markdown 文件存储，元数据以 YAML 存储，索引是派生数据而非主数据。语料库可移植、可版本控制、可手动修复。

### 2. UUID 身份，路径为位置

每个知识库有 UUID v4 身份。重命名或移动 KB 改变路径但不改变 ID，外部引用保持稳定。

### 3. 检索是流水线，不是单一算法

没有单一检索方法是完美的。平台融合：
- **关键词**：精确术语匹配
- **向量**：语义相似性
- **图谱**：关系上下文
- **两阶段**：复杂查询的精准组合

每个信号都是可选的，且优雅降级。

### 4. Agent 原生

所有操作以 MCP 工具暴露。Web UI 是一个客户端，Claude Code（通过 Skills）是另一个。系统设计为 Agent 驱动与人工驱动并重。

### 5. 显式验证

Skills 和批量操作强调"先调研，后执行，再验证"。健康记分卡量化集合质量随时间的变化。

### 6. 原子操作

三层元数据（磁盘文件 + `.tree-fs.json` + `.knowledge-base.yml`）在一次 API 调用中同步更新。一层失败则整个操作失败。

---

## 故障排查

### 子模块缺失

```bash
git submodule update --init --recursive
```

### 端口被占用

后端在启动前会探测端口，如果被占用会拒绝启动并报错。

**Windows:**

```powershell
# 查找占用进程
Get-NetTCPConnection -LocalPort 8765 -State Listen |
  ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```

**Linux / macOS:**

```bash
lsof -ti:8765 | xargs kill -9
```

或修改 `.env` 中的 `BACKEND_PORT` 使用其他端口。

### Embedding 模型下载缓慢

首次向量搜索会触发 `BAAI/bge-m3` 模型下载（约 2GB），可能需要数分钟。模型缓存在 `models_cache/`。可配置 `model_source: modelscope` 使用国内镜像加速。

### Neo4j 连接失败

图谱功能启用但 Neo4j 未运行时，图谱功能返回空结果，不会崩溃。

```bash
# 启动 Neo4j
docker compose up -d neo4j

# 检查状态
docker compose ps neo4j

# 查看日志
docker compose logs -f neo4j
```

### HTTPS_PROXY 劫持 localhost

如果设置了 `HTTPS_PROXY` 环境变量，localhost 请求可能被代理到 7890 等端口。kb-mcp 和后端的 `httpx` 调用使用 `trust_env=False` 避免此问题。新增 httpx 调用时请保持一致。

### Web 显示"Backend unavailable"

检查：
1. 后端是否在 `config.yml` 配置的端口运行
2. `.env` 中 `BACKEND_URL` 是否与后端端口匹配
3. 防火墙是否阻止 localhost 通信

### MinerU 解析失败

1. 检查后端日志 `backend/logs/mineru-api.log`
2. 确认 MinerU 已安装：`cd backend && uv pip list | grep mineru`（`uv sync` 已含 `mineru[core]`）
3. 使用 `backend_status()` 获取权威状态（`health_check()` 可能误报）
4. MinerU 端口是临时分配的，不要硬编码

### kb-mcp 启动时自动拉起服务

kb-mcp 在 `main()` 启动前执行健康检查：
1. 探测后端 `/api/v1/health`
2. 探测前端 `/api/kb/catalog`
3. 未运行则自动拉起（dev 模式可见窗口，prod 模式后台静默）
4. 等待最多 30 秒直到服务就绪

---

## Claude Code 智能对话

Web 端（`/claude-chat`）集成了完整的 **Claude Agent SDK** 客户端，提供：

| 功能 | 说明 |
|------|------|
| 🤖 SDK 流式对话 | 通过 `@anthropic-ai/claude-agent-sdk` 实现 SSE 实时流式交互 |
| 📎 多模态附件 | 支持图片/PDF/文档上传，自动转 SDK content block（image/document/text） |
| 🧠 智能滚动 | 在底部自动跟随，向上阅读时显示"↓ 新消息"+ 未读计数 |
| ✍️ 打字机渲染 | `includePartialMessages` 启用 token 级增量渲染 + 闪烁光标 |
| 🛠️ 工具调用渲染 | 37个内置工具分类展示 + MCP 工具 + tool_use/result 配对渲染 |
| 📋 任务/计划/审批 | TodoWrite / ExitPlanMode / AskUserQuestion 全渲染 |
| 🔐 权限交互 | canUseTool 回调 → SSE permission_request → 审批框 → Promise resolve |
| 💾 历史持久化 | SQLite 存储所有会话消息，支持加载/继续/删除 |
| 📁 工作区管理 | 保存/切换/置顶/验证工作目录，与 .claude/skills + .mcp.json 自动关联 |
| 🎨 Skills 发现 | 扫描 `.claude/skills/*/SKILL.md` 解析 frontmatter 展示描述 |

**使用方式**：设置 `ANTHROPIC_API_KEY` 环境变量后，访问页面直接对话。

---

## 已知限制与路线图

| 限制 | 状态 | 影响 |
|------|------|------|
| 层次化KB搜索穿透 | ⚠️ Workaround | 父KB搜索返回子KB容器（content为空），需手动穿透子KB检索 |
| 解析后自动索引 | ✅ 已实现 | `kb_doc_save_parsed` 不自动索引，需手动 `kb_index_document` |
| 向量/图谱搜索 UI | ⚠️ API就绪 | Web搜索页仅调关键词搜索，Server路由已就绪但UI未对接 |
| 图谱可视化页面 | ⚠️ API就绪 | 图谱API完整，但无专用 `/graph` 页面 |
| 来源溯源 UI | 部分 | 结果显示文档路径但无 chunk/score/片段 |
| 语义分块 | 待实现 | 固定 500 字符分块可能破坏语义边界 |
| 经验启发提取质量 | ⚠️ Workaround | heuristic 模式产生低质候选，推荐 prepare+LLM 精炼模式 |
| 标签注册表孤儿标签 | 🟢 低影响 | 历史上标签残留于注册表（0文档引用），不影响搜索质量 |
| 图谱子KB命名 | 🟢 低影响 | 子KB节点仅显示UUID，通过 graph_document 可查完整路径 |
| 跨平台支持 | ✅ 全面 | Win/Linux/macOS 一等支持；pyproject.toml marker条件源适配三平台 |

---

## 许可证

MIT
