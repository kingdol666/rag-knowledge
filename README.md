# RAG Knowledge Platform

> 文档智能解析 + 知识库管理 + 关键词检索的一体化平台

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

**MCP 服务层**（由 Claude Code 通过 stdio 自动连接）：

```
Claude Code / Agent
    │  MCP stdio (kb-mcp)
    ▼
kb-mcp MCP Server              ← ~40 个 MCP 工具：KB CRUD、解析、搜索、标签
    │  HTTP → Nuxt / FastAPI    +   直接读取文件索引
    ▼
Nuxt / FastAPI / 磁盘文件       ← 写入走 HTTP 接口，读取直接读索引文件
```

---

## 配置体系

**三层优先级，`.env` 是唯一入口：**

```
.env 文件（项目根目录）
    ↓ 无条件覆盖
os.environ（进程环境变量）
    ↓ 各模块按 APP_MODE 选择段
config.yml（dev / prod 段）
    ↓ 最后 fallback
代码内部默认值
```

### `.env` 可配置变量

| 变量 | 默认值(dev) | 默认值(prod) | 说明 |
|------|:----------:|:----------:|------|
| `APP_MODE` | `dev` | `prod` | 运行模式，决定使用 config.yml 的 dev/prod 段 |
| `BACKEND_PORT` | `8765` | `8001` | 后端 FastAPI 端口 |
| `BACKEND_HOST` | `0.0.0.0` | `0.0.0.0` | 后端监听地址 |
| `BACKEND_URL` | 自动拼接 | 自动拼接 | 完整后端 URL（设置后忽略 BACKEND_PORT） |
| `WEB_PORT` | `6789` | `3000` | 前端 Nuxt 端口 |
| `WEB_HOST` | `localhost` | `localhost` | 前端监听地址 |
| `WEB_URL` | 自动拼接 | 自动拼接 | 完整前端 URL（设置后忽略 WEB_PORT） |
| `NO_RELOAD` | `0` | — | 设为 `1` 时强制 prod 模式（禁止热重载） |
| `MINERU_HOST` | `127.0.0.1` | `127.0.0.1` | MinerU API 地址（仅 kb-mcp 健康检查用） |
| `MINERU_PORT` | `8764` | `8764` | MinerU API 端口 |
| `MINERU_URL` | 自动拼接 | 自动拼接 | 完整 MinerU URL |
| `TREE_STORAGE_PATH` | `../storage/tree-file-system` | 同左 | 知识库存储路径 |
| `MCP_HTTP_TIMEOUT` | `30` | `30` | MCP HTTP 请求超时（秒） |
| `MCP_PARSE_TIMEOUT` | `300` | `300` | PDF 解析超时（秒） |

### `config.yml` 共享配置

```yaml
server:
  cors_origins: ["*"]           # 跨域（允许所有来源）
  dev:
    backend_port: 8765
    frontend_port: 6789
    backend_url: "http://localhost:8765"
  prod:
    backend_port: 8001
    frontend_port: 3000
    backend_url: "http://localhost:8001"

mineru:
  enabled: true                 # 是否启用 MinerU OCR
  host: "127.0.0.1"
  model_source: modelscope      # huggingface | modelscope
  startup_timeout: 60           # 首次启动模型下载超时（秒）
```

> **使用方式：** 复制 `.env.example` 为 `.env`，按需修改即可。所有模块自动读取。

---

## MCP 自动启动机制

MCP 服务器（`kb-mcp`）启动时自动检查后端和前端是否可达，不可达时**根据模式决定启动行为**：

1. **健康探测** — HTTP GET 后端 `/api/v1/health` 和前端 `/api/kb/catalog`
2. **模式感知启动**：
   - `APP_MODE=dev`  → `CREATE_NEW_CONSOLE`（弹出控制台窗口，可看日志）
   - `APP_MODE=prod` → `DETACHED_PROCESS | CREATE_NO_WINDOW`（后台静默运行）
3. **等待就绪** — 最多等 30 秒，轮询直到就绪
4. **优雅降级** — 超时后打印警告，不阻塞 MCP 启动

### 使用方式

**方式一：Claude Code 自动启动（推荐）**

将 `.mcp.json` 放到仓库根目录（**无需设置 env**，所有变量从 `.env` 读取）：
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

**方式二：手动启动 MCP 服务**
```bash
# stdio 模式
uv run --directory kb-mcp python server.py

# SSE 模式（HTTP 传输）
uv run --directory kb-mcp python server.py --http
```

**方式三：独立启动前后端**
```bash
# 终端 1：后端
cd backend && uv run python main.py

# 终端 2：前端
cd web && node start.mjs
```

---

## 端口一览

| 服务 | Dev | Prod | 说明 |
|------|:---:|:----:|------|
| Web UI | 6789 | 3000 | Nuxt 3 前端 |
| API | 8765 | 8001 | FastAPI 后端 |
| API Docs | 8765/docs | 8001/docs | Swagger 文档 |
| MinerU | 自动分配 | 自动分配 | PDF 解析引擎（后端自动管理，不固定端口） |

> 所有端口均可通过 `.env` 自定义：修改 `BACKEND_PORT` / `WEB_PORT` 即可。

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
cd backend && uv sync && cd ..

# MinerU 隔离环境（首次需要）
cd backend/sandbox/mineru_module
uv venv --python 3.12
uv pip install mineru[all]
cd ../..

# 前端
cd web && npm install && cd ..
```

### 3. 配置环境

```bash
cp .env.example .env    # 按需修改端口 / 模式
```

### 4. 一键启动

```bash
# Windows
start.bat

# Linux / macOS
./start.sh
```

<details>
<summary>手动启动（三个终端）</summary>

**终端 A — 后端 (端口 8765)**

```bash
cd backend
uv run python main.py
```

**终端 B — 前端 (端口 6789)**

```bash
cd web
node start.mjs
```

</details>

### 5. 验证

```bash
# 后端健康检查
curl http://localhost:8765/api/v1/health

# 前端健康检查
curl http://localhost:6789/api/kb/catalog
```

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
1. 回填 Markdown 正文（后端 API 直接返回内容）
2. 写入指定知识库的 `.tree-fs.json` + `.knowledge-base.yml`
3. 磁盘保存 `{知识库}/{文件名}.md`

---

## 仓库结构

```
rag-knowledge/
├── .env.example            # 环境变量模板（所有可配置变量一览）
├── .mcp.json               # Claude Code MCP 连接配置
├── config.yml              # 前后端共用端口/服务配置
├── config.yml.example      # 完整配置模板（含 mineru 详细配置）
├── start.bat               # Windows 一键启动
├── start.sh                # Linux/macOS 一键启动
├── backend/                # [子模块] FastAPI + MinerU 后端
│   ├── main.py             # 入口，端口探测 + uvicorn 启动
│   ├── app/
│   │   ├── config.py       # 配置管理器（读取 config.yml + 环境变量）
│   │   ├── api/routes/     # health / parse / mineru 路由
│   │   ├── services/       # MinerU 解析服务
│   │   └── utils/          # 路径解析工具
│   └── sandbox/mineru_module/  # MinerU 隔离环境
├── web/                    # [子模块] Nuxt 3 前端
│   ├── start.mjs           # 启动入口（读取 config.yml + .env）
│   ├── server/             # Nuxt 服务端路由（代理后端 API）
│   └── storage/tree-file-system/  # 知识库存储目录
├── kb-mcp/                 # [本地] MCP 服务器
│   ├── server.py           # ~40 个 MCP 工具
│   ├── config.py           # URL 读取（env > config.yml）
│   ├── kb_client/          # HTTP 客户端（零硬编码）
│   └── task_registry.py    # 异步解析任务管理
├── scripts/                # 测试与验证脚本
│   ├── verify-env.py               # 环境变量连通性测试
│   ├── test-all-env-scenarios.py   # 多场景端口测试
│   ├── test-mcp-startup-mode.py    # MCP 模式感知启动测试
│   ├── test-config-and-mcp-e2e.py  # 配置 + MCP 端到端测试
│   ├── test-everything-e2e.py      # 完整回归测试
│   └── quick-config-check.py       # 无状态快速检查
└── frontend/               # [子模块] Vue 3 旧版前端 (legacy)
```

---

## 知识库存储结构

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

## 测试

执行完整回归测试：

```bash
# 全部配置检测 + MCP dev/prod 模式端到端
python scripts/test-everything-e2e.py

# 仅配置接线检测（无需启动服务）
python scripts/quick-config-check.py

# 三场景端口测试（MCP 配置 + Backend 配置 + 启动验证）
python scripts/test-all-env-scenarios.py
```

---

## 开发规范

- **配置驱动**：不硬编码端口/URL，统一从 `config.yml` + `.env` 读取
- **ENV > config.yml**：所有模块优先读取环境变量，再 fallback 配置文件
- **类型完整**：Python 函数参数和返回值必须有类型注解
- **Windows 优先**：`pyproject.toml` 有 `required-environments = ["win32"]`

---

## 已知问题

1. **MinerU 端口自动分配** — 避免硬编码 8764，`MineruApiManager(port=None)` 自动选取空闲端口
2. **MinerU stdout → 文件** — 日志写入 `backend/logs/mineru-api.log`，不通过 pipe（避免 [Errno 22]）
3. **HTTPS_PROXY 劫持 localhost** — httpx 调用使用 `trust_env=False`，避免 localhost 被代理到 7890
4. **kb-mcp API 一致性** — `name`/`path` 不同步、`file_size` 缓存陈旧等问题

---

## License

MIT
