# RAG Knowledge Platform

> 文档智能解析 + 知识库管理 + 智能检索的一体化平台

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://python.org)
[![Nuxt](https://img.shields.io/badge/Nuxt-3.x-00DC82)](https://nuxt.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

把 PDF 文档解析为标准 Markdown，自动归档到树形知识库，并通过关键词检索跨库查询文档。

---

## 它能做什么

- **PDF 解析为 Markdown** — 基于 MinerU 3.x 的 OCR/VLM 引擎，保留结构、提取图片，单文件或批量解析
- **知识库管理** — 树形文件夹结构，支持创建知识库、上传文件、自动维护索引（`.tree-fs.json` + `.knowledge-base.yml`）
- **知识检索** — 跨知识库关键词搜索，按相关度排序，支持分段预览文档正文
- **智能摘要** — 为解析后的文档自动生成内容摘要（通过 LLM 集成）

---

## 架构

```
浏览器 (6789 / 3000)
    │
    ▼
Nuxt 3 前端 (代理层)          ← 文件管理、解析触发、知识检索页面
    │  server-to-server
    ▼
FastAPI 后端 (8765 / 8001)    ← 解析调度、MinerU 子进程管理
    │  subprocess (Job Object)
    ▼
MinerU OCR 引擎 (临时端口)     ← PDF → Markdown 转换
```

还有一个 **MCP 服务层**（由 Claude Code 通过 stdio 自动连接）：

```
Claude Code / Agent
    │  MCP stdio (kb-mcp)
    ▼
kb-mcp MCP Server              ← ~40 个 MCP 工具：KB CRUD、解析、搜索、标签
    │  HTTP → Nuxt / FastAPI    +   直接读取文件索引
    ▼
Nuxt / FastAPI / 磁盘文件       ← 写入走 HTTP 接口，读取直接读索引文件
```

三个服务 + MCP 层都通过 `config.yml` 统一配置端口和 CORS，互不硬编码。

---

## MCP 自动启动机制

MCP 服务器（`kb-mcp`）启动时自动检查后端和前端是否可达，不可达时**静默在后台启动**（无控制台窗口）：

1. **健康探测** — 同时 HTTP GET 后端 `/api/v1/health` 和前端 `/api/kb/catalog`
2. **静默启动** — 未运行的服务以 `DETACHED_PROCESS | CREATE_NO_WINDOW` 模式拉起
3. **等待就绪** — 最多等 30 秒，轮询直到就绪
4. **优雅降级** — 超时后打印警告，不阻塞 MCP 启动

### 优先级链（ENV > config.yml）

| 环境变量 | 作用 | 示例 |
|----------|------|------|
| `APP_MODE` | 选择 `dev`/`prod` 配置段 | `dev` |
| `BACKEND_URL` | **完整后端 URL**（最高优先级，统一驱动前后端连接） | `http://localhost:9000` |
| `BACKEND_PORT` | 后端端口（env 驱动时使用） | `9000` |
| `WEB_URL` | **完整前端 URL**（最高优先级） | `http://localhost:4000` |
| `WEB_PORT` / `FRONTEND_PORT` | 前端端口 | `4000` |
| `TREE_STORAGE_PATH` | 知识库存储路径（相对 `web/` 根目录） | `./storage/tree-file-system` |

```
.mcp.json env   (最高 — 已存在于 process.env，不被 .env 覆盖)
    │  未设置则 fallback
    ▼
.env 文件        (中等 — 被 _load_dotenv() 加载，不覆盖已存在的键)
    │  未设置则 fallback
    ▼
config.yml      (最低 — 各模块约定的默认端口和 URL)
```

### 使用方式

**方式一：Claude Code 自动启动（推荐）**

将 `.mcp.json` 放到仓库根目录：
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
Claude Code 连接时自动检查后端/前端，未运行则静默启动后台进程。

**方式二：手动启动 MCP 服务**
```bash
# stdio 模式（供 Agent harness 使用）
uv run --directory kb-mcp python server.py

# SSE 模式（HTTP 传输）
uv run --directory kb-mcp python server.py --http
```

**方式三：独立启动前后端**
```bash
# 终端 1：后端
cd backend && APP_MODE=dev uv run python main.py

# 终端 2：前端
cd web && APP_MODE=dev npm run start
```

### 在 `.env` 中自定义端口

```bash
# .env 文件 — 设置后会覆盖 config.yml 的端口
BACKEND_PORT=9000
WEB_PORT=4000
```

此时 MCP 自动启动时：
- 健康探测 → 探测 `127.0.0.1:9000`（后端）和 `127.0.0.1:4000`（前端）
- 自动启动 → 后端在 9000 端口启动，前端在 4000 端口启动（均无窗口）
- 前端 API 连接 → `BACKEND_URL` 统一驱动前端 Nuxt 的 `pdfParserApiUrl`
- MCP 工具路由 → `kb_client` 的 `BACKEND_URL` 和 `WEB_URL` 自动对应

---

## 快速开始

### 环境要求

| 工具 | 版本 | 用途 |
|------|------|------|
| [uv](https://docs.astral.sh/uv/) | latest | Python 包管理 |
| [Node.js](https://nodejs.org) | >= 18 | 前端运行 |
| Python | 3.11 或 3.12 | 后端运行 |
| Git | >= 2.25 | 版本控制 |

### 1. 克隆（含子模块）

```bash
git clone --recurse-submodules https://github.com/kingdol666/rag-knowledge.git
cd rag-knowledge

# 如果克隆时没带子模块：
git submodule update --init --recursive
```

### 2. 安装依赖

```bash
# 后端
cd backend
uv sync
cd ..

# MinerU 隔离环境（首次需要）
cd backend/sandbox/mineru_module
uv venv --python 3.12
uv pip install mineru[all]
cd ../../..

# 前端
cd web
npm install
cd ..
```

### 3. 一键启动

```bash
# Windows
start.bat

# Linux / macOS
./start.sh
```

脚本会按顺序启动三个服务：MinerU → 后端 → 前端。

<details>
<summary>手动启动（三个终端）</summary>

**终端 A — MinerU**

MinerU 由后端**自动管理**，无需手动启动。后端启动时自动拉起 `mineru-api` 子进程（分配临时端口，无控制台窗口）。如果仍要手动启动：
```bash
cd backend
CUDA_VISIBLE_DEVICES=-1 MINERU_DEFAULT_BACKEND=pipeline \
  MINERU_MODEL_SOURCE=modelscope \
  sandbox/mineru_module/.venv/bin/mineru-api --host 127.0.0.1 --port 8764
```

**终端 B — 后端 (端口 8765)**

```bash
cd backend
APP_MODE=dev uv run python main.py
```

**终端 C — 前端 (端口 6789)**

```bash
cd web
APP_MODE=dev npm run start
```

</details>

### 4. 验证

```bash
# 健康检查
curl http://localhost:8765/api/v1/health     # 后端

# 打开前端
# 浏览器访问 http://localhost:6789
```

---

## 端口一览

| 服务 | Dev | Prod | 说明 |
|------|:---:|:----:|------|
| Web UI | 6789 | 3000 | Nuxt 3 前端 |
| API | 8765 | 8001 | FastAPI 后端 |
| API Docs | 8765/docs | 8001/docs | Swagger 文档 |
| MinerU | 自动分配 | 自动分配 | PDF 解析引擎（后端自动管理，不固定端口） |

---

## 功能导览

### 文件管理页面 (`/file-system`)

- 树形知识库浏览，支持创建文件夹/知识库
- 上传文件（任意类型）到指定知识库
- PDF 解析：单文件或批量上传，OCR 解析后自动归档
- 内置预览：Markdown、PDF、图片、视频、音频、Office 文档

### 知识检索页面 (`/knowledge-search`)

- **浏览知识库**：以卡片网格展示所有知识库，点击查看库内文档清单
- **关键词搜索**：跨所有知识库检索文档，按相关度排序
- **文档预览**：点击任意文档，右侧抽屉分段加载 Markdown 正文

### 解析 API

前端通过 `/api/parse/*` 代理到后端 v1 接口，解析完成后自动：
1. 回填 Markdown 正文（后端 API 直接返回内容，无需读取磁盘文件）
2. 写入指定知识库的 `.tree-fs.json` + `.knowledge-base.yml`
3. 磁盘保存 `{知识库}/{文件名}.md`

---

## 配置

`config.yml` 是唯一的端口配置来源：

```yaml
server:
  dev:
    backend_port: 8765
    frontend_port: 6789
    backend_url: "http://localhost:8765"
    cors_origins:
      - "http://localhost:6789"
  prod:
    backend_port: 8001
    frontend_port: 3000
    backend_url: "http://localhost:8001"
    cors_origins:
      - "http://localhost:3000"
```

优先级：`APP_MODE` 环境变量 → `config.yml` 对应段 → 代码默认值。

---

## 仓库结构

```
rag-knowledge/
├── config.yml              # 前后端共用配置
├── start.bat               # Windows 一键启动
├── start.sh                # Linux/macOS 一键启动
├── backend/                # 子模块: FastAPI + MinerU 后端
├── web/                    # 子模块: Nuxt 3 前端
└── frontend/               # 子模块: Vue 3 旧版前端 (legacy)
```

| 目录 | 仓库 | 技术栈 |
|------|------|--------|
| `backend/` | [rag-knowledge-backend](https://github.com/kingdol666/rag-knowledge-backend) | Python · FastAPI · MinerU 3.x |
| `web/` | [rag-knowledge-frondend](https://github.com/kingdol666/rag-knowledge-frondend) | TypeScript · Nuxt 3 · Ant Design Vue |
| `frontend/` | [rag-knowledge-frontend](https://github.com/kingdol666/rag-knowledge-frontend) | Vue 3 · Vite (legacy) |

---

## 知识库数据结构

```
web/storage/tree-file-system/
├── .tree-fs.json                    # 全局索引（所有文件夹+文件）
├── {知识库A}/
│   ├── .knowledge-base.yml          # 库内文档索引（供检索用）
│   ├── doc1.md                      # 实际文档
│   └── images/                      # 文档提取的图片
└── {知识库B}/
    └── ...
```

- `.tree-fs.json` — 全局树结构，记录每个文件夹和文件的元数据
- `.knowledge-base.yml` — 每个知识库根目录的文档清单，包含 name/description/path/metadata

---

## 平台兼容性

| 平台 | 后端 | 前端 | 备注 |
|------|:----:|:----:|------|
| Windows 10/11 | OK | OK | 使用 PowerShell 或 Git Bash |
| Linux | OK | OK | GPU 需 CUDA >= 11.8 |
| macOS | OK | OK | Apple Silicon GPU: `vlm.backend: mlx-engine` |

---

## License

MIT
