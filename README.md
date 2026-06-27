# RAG Knowledge Platform

> A RAG (Retrieval-Augmented Generation) knowledge management platform.
> PDF parsing via MinerU, LLM agents, modern web UI.

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://python.org)
[![Nuxt](https://img.shields.io/badge/Nuxt-3.x-00DC82)](https://nuxt.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An end-to-end document intelligence system: ingest PDFs, extract knowledge via OCR / VLM, build searchable knowledge bases, and interact with LLM agents for summarization and Q&A.

---

## Architecture

```
┌────────────────────────────────────────────────────────┐
│                    RAG Knowledge Platform               │
├──────────────┬────────────────────┬────────────────────┤
│   backend/   │     web/           │   frontend/        │
│  FastAPI +   │   Nuxt 3 +        │   Vue 3 + Vite     │
│  MinerU 3.x  │   Ant Design Vue  │   Ant Design Vue   │
│              │   (primary UI)    │   (legacy UI)       │
├──────────────┴────────────────────┴────────────────────┤
│              config.yml  ←  shared port & CORS config  │
└────────────────────────────────────────────────────────┘

 Browser ──► Nuxt server route ──► Python FastAPI backend
                   │                       │
              No browser CORS         MinerU API (subprocess)
              (server-to-server)      pipeline backend (CPU/GPU)
```

---

## Repository Layout

```
rag-knowledge/
├── config.yml          # ☝ 唯一端口 / CORS / URL 配置来源（dev + prod 双模式）
├── .env                # Environment variables (overrides)
├── .env.example        # Template .env file
├── start.bat           # Windows launcher
├── start.sh            # Linux / macOS launcher
├── README.md
├── backend/            # Git submodule → rag-knowledge-backend
├── web/                # Git submodule → rag-knowledge-frondend (Nuxt 3)
└── frontend/           # Git submodule → rag-knowledge-frontend (Vue + Vite)
```

---

## Quick Start

### Prerequisites

| Tool | Version | Check |
|------|---------|-------|
| [uv](https://docs.astral.sh/uv/) | latest | `uv --version` |
| [Node.js](https://nodejs.org) | ≥ 18 | `node --version` |
| Python | 3.11 or 3.12 | `python --version` |
| Git | ≥ 2.25 | `git --version` |

### 1. Clone (with submodules)

```bash
git clone --recurse-submodules https://github.com/kingdol666/rag-knowledge.git
cd rag-knowledge
```

> If you cloned without `--recurse-submodules`:
> ```bash
> git submodule update --init --recursive
> ```

### 2. Install dependencies

```bash
# Backend (Python) — requires uv: https://docs.astral.sh/uv/
cd backend
uv sync
cd ..

# Web frontend (Nuxt 3)
cd web
npm install
cd ..
```

### 3. 启动流程（共 3 个服务）

项目由三个服务组成，需要按顺序启动：

---

#### 服务 A：MinerU PDF 解析引擎（端口 8764）

MinerU 运行在隔离的虚拟环境中。首次需要安装依赖：

```bash
cd backend

# 创建并安装 MinerU 专用环境
cd sandbox/mineru_module
uv venv --python 3.12
uv pip install mineru[all]
cd ../..
```

启动 MinerU API（CPU 模式，无需 GPU）：

```bash
cd backend

# Windows:
set CUDA_VISIBLE_DEVICES=-1
set MINERU_DEFAULT_BACKEND=pipeline
set MINERU_MODEL_SOURCE=modelscope
sandbox/mineru_module/.venv/Scripts/mineru-api.exe --host 127.0.0.1 --port 8764

# Linux / macOS:
CUDA_VISIBLE_DEVICES=-1 MINERU_DEFAULT_BACKEND=pipeline \
  MINERU_MODEL_SOURCE=modelscope \
  sandbox/mineru_module/.venv/bin/mineru-api --host 127.0.0.1 --port 8764
```

验证：`curl http://127.0.0.1:8764/health`

---

#### 服务 B：Backend（FastAPI，端口 8765 / 8001）

```bash
# Dev 模式（端口 8765，自动重载，自动启动 MinerU）
cd backend
APP_MODE=dev uv run python main.py

# Prod 模式（端口 8001，无自动重载）
cd backend
APP_MODE=prod uv run python main.py

# 自定义端口（覆盖 config.yml）
BACKEND_PORT=9000 APP_MODE=dev uv run python main.py
```

**后端启动时自动执行：**
1. 读取 `config.yml`，检测 `mineru.enabled: true`
2. 自动拉起 `mineru-api` 子进程
3. 等待 `/health` 返回 200（超时 60 秒）
4. 预加载 DeepAgent 构件
5. 注册 FastAPI 路由 → 服务就绪

后端关闭时自动终止 MinerU 子进程。

验证：
```bash
curl http://localhost:8765/api/v1/health
# → {"status":"healthy"}
```

---

#### 服务 C：Web 前端（Nuxt 3，端口 6789 / 3000）

```bash
# Dev 模式
cd web
APP_MODE=dev npm run start
# → http://localhost:6789

# 或直接使用 Nuxt dev 命令
cd web
npm run dev
```

---

### 4. 快速启动（一键启动）

```bash
# Windows
start.bat

# Linux / macOS
./start.sh
```

---

### 5. 验证

```bash
# 健康检查
curl http://localhost:8765/api/v1/health    # dev
curl http://localhost:8001/api/v1/health    # prod

# 测试 PDF 解析 — 后端代理到 MinerU
curl -X POST -F "file=@your-document.pdf" http://localhost:8765/api/v1/parse/file/vt

# 直接测试 MinerU API
curl -X POST -F "files=@your-document.pdf" -F "return_md=true" \
  http://127.0.0.1:8764/file_parse
```

---

### 6. 服务端口一览

| 服务 | Dev 模式 | Prod 模式 | 说明 |
|------|----------|-----------|------|
| Web UI | `http://localhost:6789` | `http://localhost:3000` | Nuxt 3 前端 |
| API | `http://localhost:8765` | `http://localhost:8001` | FastAPI 后端 |
| API Docs | `http://localhost:8765/docs` | `http://localhost:8001/docs` | Swagger 文档 |
| MinerU | `http://127.0.0.1:8764` | `http://127.0.0.1:8764` | PDF 解析引擎 |

---

## 配置说明

### config.yml

`config.yml` 是**唯一的配置来源**：

```yaml
server:
  dev:                               # APP_MODE=dev 或未设置时使用
    host: "0.0.0.0"
    backend_port: 8765
    backend_url: "http://localhost:8765"
    cors_origins:
      - "http://localhost:6789"

  prod:                              # APP_MODE=prod 时使用
    host: "0.0.0.0"
    backend_port: 8001
    backend_url: "http://localhost:8001"
    cors_origins:
      - "http://localhost:3000"

# MinerU OCR / PDF 解析引擎配置
mineru:
  enabled: true
  host: "127.0.0.1"
  api_port: 8764
  start_on_boot: true
  startup_timeout: 60

# LLM 配置（用于 DeepAgent 智能体）
llm:
  type: custom
  model: glm-5
  base_url: https://open.bigmodel.cn/api/coding/paas/v4
  api_token: ${API_TOKEN}
  temperature: 0.7
  max_tokens: 40960

deepagent:
  defaults:
    input_text: "你好，你是谁"
    context: {}
    tools: []
    skills:
      - backend-maintainer
      - open-research
    model: glm-5
    temperature: 0.7
    max_tokens: 40960
    include_messages: true
```

端口解析优先级：
```
环境变量 APP_MODE → config.yml <mode> 段 → 代码默认值
```

---

## 开发指南

详细开发规范见 [backend/CLAUDE.md](backend/CLAUDE.md)。

核心原则：
- **模块分层**：routes / agent / models / utils 各司其职
- **配置驱动**：不硬编码端口、URL 等
- **隔离依赖**：MinerU 运行在独立虚拟环境中，不与主项目依赖冲突
- **自动生命周期**：后端启动时自动管理 MinerU 子进程

---

## 架构详解：请求流程

```
                         浏览器 (port 6789 / 3000)
                              │
                    ┌─────────┴──────────┐
                    │  Nuxt Server Route  │  (/api/parse/file-vt)
                    └─────────┬──────────┘
                              │  proxy: http://localhost:8765/api/v1/parse/file/vt
                    ┌─────────▼──────────┐
                    │  FastAPI Backend    │  (端口 8765)
                    └─────────┬──────────┘
                              │  proxy: http://127.0.0.1:8764/file_parse
                    ┌─────────▼──────────┐
                    │  MinerU API         │  (端口 8764, pipeline backend)
                    │  PDF → Markdown     │
                    └────────────────────┘
```

## Submodules

| Directory | Repository | Tech |
|-----------|-----------|------|
| `backend/` | [rag-knowledge-backend](https://github.com/kingdol666/rag-knowledge-backend) | Python · FastAPI · MinerU 3.x |
| `web/` | [rag-knowledge-frondend](https://github.com/kingdol666/rag-knowledge-frondend) | TypeScript · Nuxt 3 · Ant Design Vue |
| `frontend/` | [rag-knowledge-frontend](https://github.com/kingdol666/rag-knowledge-frontend) | Vue 3 · Vite · Ant Design Vue (legacy) |

---

## Platform Compatibility

| Platform | Backend | Frontend | Notes |
|----------|---------|----------|-------|
| **Windows 10/11** | ✓ | ✓ | Use Git Bash or PowerShell. `start.bat` included. |
| **Linux** | ✓ | ✓ | All features. `./start.sh`. GPU: CUDA ≥ 11.8. |
| **macOS** | ✓ | ✓ | CPU always OK. Apple Silicon GPU: vlm.backend: mlx-engine. |

---

## License

MIT
