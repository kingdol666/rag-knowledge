<h1 align="center">
  <img src="../docs/images/logo.svg" alt="RAG Knowledge Backend" width="80" />
  <br/>
  RAG Knowledge Backend
</h1>

<p align="center">
  <strong>FastAPI 后端 · MinerU OCR 引擎 · 向量搜索 · 知识图谱</strong><br/>
  <em>RAG Knowledge Platform 的文档智能引擎</em>
</p>

<p align="center">
  <a href="#-快速开始"><img src="https://img.shields.io/badge/%E5%BF%AB%E9%80%9F%E5%BC%80%E5%A7%8B-3%20%E6%AD%A5-blue?style=for-the-badge" /></a>
  <a href="#-api-参考"><img src="https://img.shields.io/badge/API-64%20%E7%AB%AF%E7%82%B9-009688?style=for-the-badge" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" /></a>
  <a href="#-跨平台"><img src="https://img.shields.io/badge/platform-Win%20%7C%20Linux%20%7C%20macOS-lightgrey?style=for-the-badge" /></a>
  <a href="#-技术栈"><img src="https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge" /></a>
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
- [📡 API 参考](#-api-参考)
- [⚙️ 配置](#️-配置)
- [🧪 测试](#-测试)
- [📁 项目结构](#-项目结构)
- [🌍 跨平台](#-跨平台)
- [🔧 技术栈](#-技术栈)
- [🤝 贡献](#-贡献)
- [📄 许可证](#-许可证)

## 🌟 概述

后端是 RAG Knowledge Platform 的计算核心。提供：

- **📄 PDF 解析** — MinerU OCR 引擎将 PDF/Word/Excel/PPT/图片 → Markdown。异步提交、批量 SSE 流式进度、离线模型自动下载。
- **🔍 向量搜索** — ChromaDB 语义搜索，BGE-M3 嵌入（1024 维）。BM25 + 向量两阶段检索。
- **🕸️ 知识图谱** — Neo4j 实体抽取、跨文档关系挖掘、中心度分析。基于 transformers pipeline 的 NER。
- **💡 经验引擎** — 结构化教训提取（启发式 + LLM 精炼）、可信度评分、衰减周期、草稿审批流程。
- **⚙️ 配置 API** — 运行时配置读写，带 Schema 校验和热重载。

## 🏗️ 架构

```
┌──────────────────────────────────────────────────┐
│                   main.py                         │
│          端口探测 → uvicorn 启动                   │
└──────────────────┬───────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────┐
│            app/main.py                            │
│       FastAPI 应用工厂 + 生命周期管理                │
│                                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │ /health  │ │ /parse   │ │ /mineru  │          │
│  │  GET     │ │  POST    │ │  GET/POST│          │
│  └──────────┘ └────┬─────┘ └────┬─────┘          │
│                    │             │                │
│  ┌──────────┐ ┌────▼─────┐ ┌───▼──────┐          │
│  │ /config  │ │ /search  │ │ /graph   │          │
│  │  GET/POST│ │  POST    │ │  POST    │          │
│  └──────────┘ └──────────┘ └──────────┘          │
│                                                   │
│  ┌──────────┐ ┌──────────────────┐                │
│  │/experience│ │MineruApiManager  │                │
│  │  POST    │ │(子进程管理)       │                │
│  └──────────┘ └────────┬─────────┘                │
└─────────────────────────┼─────────────────────────┘
                          │ 子进程 (Job Object)
┌─────────────────────────▼─────────────────────────┐
│              MinerU OCR 引擎                       │
│          随机端口 · stdout→文件                     │
│          隐藏窗口 · 父进程退出即杀                   │
└───────────────────────────────────────────────────┘
```

**关键设计决策：**

| 决策 | 理由 |
|------|------|
| MinerU 作为子进程 | 隔离生命周期；崩溃不影响 API |
| 随机端口 (`port=None`) | 无端口冲突；自动避开常用开发端口 |
| stdout → 文件（永不使用管道） | 消除 `[Errno 22]` 管道关闭崩溃 |
| Job Object (Win) / `prctl` (Linux) | 父进程退出时保证子进程清理 |
| 所有 httpx 调用 `trust_env=False` | 防止 `HTTPS_PROXY` 劫持 localhost |

## 🚀 快速开始

```bash
# 1. 安装依赖
uv sync

# 2. 运行（开发模式 — 热重载）
APP_MODE=dev uv run python main.py
# → http://localhost:8765

# 3. 验证
curl http://localhost:8765/api/v1/health
```

```bash
# 生产模式（无热重载）
APP_MODE=prod uv run python main.py
# → http://localhost:8001

# 自定义端口
BACKEND_PORT=9000 APP_MODE=dev uv run python main.py
```

> **前置要求：** Python 3.12、`uv`。首次解析自动下载 MinerU 模型（约 2 GB）。国内使用 `HF_ENDPOINT=https://hf-mirror.com`（默认）加速下载。

## 📡 API 参考

### 健康检查

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/v1/health` | 后端健康 + MinerU 状态 + 版本信息 |

### 解析

| 方法 | 端点 | 说明 |
|------|------|------|
| `POST` | `/api/v1/parse/file/vt` | 异步解析单个文件 |
| `POST` | `/api/v1/parse/file/vt/legacy` | 旧版解析端点 |
| `POST` | `/api/v1/batch/parse/file/vt/stream` | 批量 SSE 流式解析 |
| `POST` | `/api/v1/batch/parse/file/vt` | 批量 JSON 响应解析 |

### MinerU

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/v1/mineru/status` | MinerU 引擎状态 |
| `POST` | `/api/v1/mineru/restart` | 强制重启 MinerU 子进程 |

### 搜索

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/v1/search/debug-paths` | 调试路径解析 |
| `POST` | `/api/v1/search/vector` | 语义向量搜索（BGE-M3） |
| `POST` | `/api/v1/search/batch-vector` | 批量向量搜索 |
| `POST` | `/api/v1/search/two-stage` | 两阶段：BM25 → 向量重排 |
| `POST` | `/api/v1/search/index-document` | 索引单个文档 |
| `POST` | `/api/v1/search/batch-index` | 批量索引文档 |
| `POST` | `/api/v1/search/reindex` | 重建向量索引 |
| `GET` | `/api/v1/search/stats` | 搜索索引统计 |
| `DELETE` | `/api/v1/search/kb/{kb_id}` | 删除 KB 搜索数据 |
| `DELETE` | `/api/v1/search/document` | 从索引中删除文档 |

### 图谱

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/v1/graph/health` | 图数据库健康 |
| `GET` | `/api/v1/graph/stats` | 图谱统计 |
| `GET` | `/api/v1/graph/search/documents` | 关键词搜索图谱 |
| `GET` | `/api/v1/graph/search/kbs` | 搜索图谱中的 KB |
| `GET` | `/api/v1/graph/search/tags` | 搜索图谱中的标签 |
| `GET` | `/api/v1/graph/document` | 文档中心图谱 |
| `GET` | `/api/v1/graph/document/related` | 相关文档 |
| `GET` | `/api/v1/graph/document/enhanced` | 增强文档图谱 |
| `GET` | `/api/v1/graph/documents-by-tag` | 按标签查文档 |
| `GET` | `/api/v1/graph/kb-overview` | KB 级图谱概览 |
| `GET` | `/api/v1/graph/neighbors` | 邻居节点浏览 |
| `GET` | `/api/v1/graph/cross-kb-documents` | 跨库桥接文档 |
| `GET` | `/api/v1/graph/document-paths` | 两文档间路径 |
| `GET` | `/api/v1/graph/central-documents` | 中心度排名文档 |
| `POST` | `/api/v1/graph/build-kb` | 构建 KB 图谱 |
| `POST` | `/api/v1/graph/build-all` | 构建所有 KB 图谱 |
| `POST` | `/api/v1/graph/agent-relation` | Agent 驱动关系 |
| `POST` | `/api/v1/graph/agent-relations/batch` | 批量 Agent 关系 |
| `DELETE` | `/api/v1/graph/document` | 从图谱删除文档 |
| `DELETE` | `/api/v1/graph/kb/{kb_id}` | 从图谱删除 KB |

### 经验

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/v1/experience/{kb_id}` | 列出经验 |
| `POST` | `/api/v1/experience/{kb_id}` | 创建经验 |
| `GET` | `/api/v1/experience/{kb_id}/dashboard` | 健康看板 |
| `POST` | `/api/v1/experience/{kb_id}/extract` | 从文档提取 |
| `POST` | `/api/v1/experience/{kb_id}/search` | 搜索经验 |
| `POST` | `/api/v1/experience/global-search` | 跨库搜索 |

### 配置

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/v1/config` | 读取当前运行时配置 |
| `PUT` | `/api/v1/config` | 更新配置 |
| `GET` | `/api/v1/config/schema` | 配置 JSON Schema |
| `POST` | `/api/v1/config/reload` | 热重载配置 |

## ⚙️ 配置

`backend/config.yml` — 后端专属配置：

```yaml
mineru:
  enabled: true             # 启用 MinerU OCR 引擎
  host: "127.0.0.1"        # MinerU 绑定地址
  model_source: "modelscope"  # 或 "huggingface"
```

端口和模式从**根目录 `config.yml`**（唯一真相源）读取。可通过环境变量覆盖：

| 变量 | 默认值（dev / prod） | 用途 |
|------|---------------------|------|
| `APP_MODE` | `dev` | 选择根 config.yml 的 dev 或 prod 段 |
| `BACKEND_PORT` | `8765` / `8001` | 覆盖后端监听端口 |
| `HF_ENDPOINT` | `https://hf-mirror.com` | HuggingFace 模型下载镜像 |
| `NEO4J_PASSWORD` | （来自 docker-compose） | Neo4j 认证 |

## 🧪 测试

```bash
# 快速单元测试（跳过 MinerU — 无需引擎）
uv run pytest
# → 约 50 个封闭测试，<10 秒

# 包含 MinerU 集成测试
uv run pytest --run-integration
# → 完整解析流程，需要运行中的 MinerU

# 单个测试
uv run pytest tests/test_unit.py -x -k "test_health_check"

# 覆盖率
uv run pytest --cov=app --cov-report=html
```

**测试结构：**
- `test_unit.py` — 封闭测试：健康检查、配置、Schema、路径解析。
- `test_parse_async.py` — 集成测试：完整解析流程（需要在线 MinerU）。
- `conftest.py` — 默认跳过集成测试（加 `--run-integration` 启用）。

## 📁 项目结构

```
backend/
├── main.py                    # 入口：端口探测 → uvicorn
├── app/
│   ├── main.py                # FastAPI 应用工厂 + 生命周期（启动 MinerU）
│   ├── config.py              # 单例配置读取（根目录 + 后端配置）
│   ├── api/routes/
│   │   ├── __init__.py        # 路由注册
│   │   ├── health.py          # GET /api/v1/health
│   │   ├── parse.py           # POST /api/v1/parse/*（异步 + 批量 SSE）
│   │   ├── mineru.py          # GET/POST /api/v1/mineru/*
│   │   ├── search.py          # POST /api/v1/search/*（关键词 + 向量 + 两阶段）
│   │   ├── graph.py           # POST /api/v1/graph/*（构建 + 搜索）
│   │   ├── experience.py      # POST /api/v1/experience/*（提取 + 看板）
│   │   ├── config.py          # GET/POST /api/v1/config
│   │   └── config_schema.py   # JSON Schema 配置校验
│   ├── models/
│   │   └── schemas.py         # Pydantic 请求/响应模型
│   ├── services/
│   │   └── mineru_service.py  # MineruParseService 封装
│   └── utils/
│       ├── paths.py           # PROJECT_ROOT、配置路径解析
│       └── mineru_manager.py  # MineruApiManager：子进程生命周期 + 任务轮询
├── tests/
│   ├── conftest.py            # Pytest fixtures + 集成测试跳过逻辑
│   ├── test_unit.py           # 封闭单元测试
│   └── test_parse_async.py    # 集成测试（需要运行中的 MinerU）
├── pyproject.toml             # uv 项目配置 + PyTorch CUDA 源
└── config.yml                 # 后端专属配置（MinerU 设置）
```

## 🌍 跨平台

三平台一等支持，平台特定的子进程生命周期：

| 平台 | MinerU 清理 | stdout 处理 | GPU 支持 |
|------|------------|------------|----------|
| **Windows** | Job Object (`KILL_ON_JOB_CLOSE`) | 文件（不用管道） | CUDA (cu130) |
| **Linux** | `prctl(PR_SET_PDEATHSIG)` | 文件（不用管道） | CUDA (cu130 x86_64) |
| **macOS** | 进程组 + atexit | 文件（不用管道） | MPS / CPU 回退 |

`pyproject.toml` 使用**基于 marker 的条件源**：Windows + Linux x86_64 从 PyTorch cu130 索引拉取 CUDA wheel；macOS 和 Linux aarch64 优雅回退到 PyPI (CPU/MPS)。`required-environments` 允许三平台，`uv sync` 处处可用。

## 🔧 技术栈

| 组件 | 技术 |
|------|------|
| 框架 | Python 3.12 · FastAPI · Uvicorn |
| PDF 解析 | MinerU OCR (≥3.4.2) |
| 向量数据库 | ChromaDB |
| 嵌入模型 | BGE-M3 (1024 维) · sentence-transformers |
| 关键词搜索 | jieba · BM25 |
| 知识图谱 | Neo4j (≥6.2.0) · transformers NER |
| 数据校验 | Pydantic · JSON Schema |
| 包管理器 | uv (hatchling 构建) |
| ML 运行时 | PyTorch 2.12.1 + CUDA 13.0 / MPS / CPU |

## 🤝 贡献

1. Fork → 功能分支 → 提交 → 推送 → PR
2. 提交前运行 `uv run pytest` — 所有单元测试必须通过
3. 如修改 MinerU 生命周期代码，请用 `--run-integration` 测试
4. 跨平台：在你使用的平台上测试即可；CI 覆盖其余两平台

## 📄 许可证

MIT · 隶属于 [RAG Knowledge Platform](https://github.com/kingdol666/rag-knowledge)
