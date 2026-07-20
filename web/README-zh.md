<h1 align="center">
  <img src="../docs/images/logo.svg" alt="RAG Knowledge Web" width="80" />
  <br/>
  RAG Knowledge Web
</h1>

<p align="center">
  <strong>Nuxt 3 前端 · Claude AI 聊天 · 知识库界面 · 图谱可视化</strong><br/>
  <em>RAG Knowledge Platform 的用户端 Web 应用</em>
</p>

<p align="center">
  <a href="#-快速开始"><img src="https://img.shields.io/badge/%E5%BF%AB%E9%80%9F%E5%BC%80%E5%A7%8B-2%20%E6%AD%A5-blue?style=for-the-badge" /></a>
  <a href="#-功能特性"><img src="https://img.shields.io/badge/%E9%A1%B5%E9%9D%A2-9%20%E9%A1%B5-9cf?style=for-the-badge" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" /></a>
  <a href="#-技术栈"><img src="https://img.shields.io/badge/platform-Win%20%7C%20Linux%20%7C%20macOS-lightgrey?style=for-the-badge" /></a>
  <a href="#-技术栈"><img src="https://img.shields.io/badge/Nuxt-3.x-00DC82?style=for-the-badge" /></a>
</p>

---

<p align="center">
  <sub><a href="./README.md">English</a> · <a href="./README-zh.md"><b>中文</b></a></sub>
</p>

---

## 📌 目录

- [🌟 功能特性](#-功能特性)
- [🏗️ 架构](#️-架构)
- [🚀 快速开始](#-快速开始)
- [📡 API 路由](#-api-路由)
- [📱 页面](#-页面)
- [⚙️ 配置](#️-配置)
- [📁 项目结构](#-项目结构)
- [🔧 技术栈](#-技术栈)
- [🤝 贡献](#-贡献)
- [📄 许可证](#-许可证)

## 🌟 功能特性

**🤖 Claude AI 聊天**
完整的 Claude Code SDK 集成，支持流式响应、权限审批界面、知识库增强模式（将检索上下文注入提示词）、消息队列并发控制、推理深度调节、多模态文件上传（图片 + 文档）以及会话历史管理。

**📁 可视化文件系统**
拖拽式文件浏览器，支持树状导航、多格式上传（PDF/Word/Excel/PPT/图片）、一键解析触发、文件预览（Markdown + 图片）以及文件夹增删改操作。

**🔍 知识库搜索**
QDCVR（查询驱动·内容验证检索）流水线界面 — 语义 + 关键词两阶段搜索，0–8 分内容评分，跨库企业搜索，标签过滤，带来源引用的结果排序。

**🕸️ 知识图谱**
基于 Neo4j 的交互式文档关系可视化 — KB 全局图谱、文档中心实体网络、跨库发现路径、中心度分析、标签文档聚类。

**💡 经验库**
结构化经验浏览，支持 P0/P1/P2 可信度分级、草稿审批流程、衰减追踪和看板分析。

**⚙️ 设置与配置**
运行时环境编辑器，支持热重载、后端 API 集成和带 Schema 校验的配置管理。

**🌐 双语**
完整的中英文国际化 — 每个标签、消息和 UI 元素都支持双语即时切换。

## 🏗️ 架构

```
┌─────────────────────────────────────────────────────┐
│                   浏览器                              │
│           Nuxt 3 SPA (Vue 3 + Ant Design Vue)        │
│           http://localhost:6789 (dev)                │
│           http://localhost:3000  (prod)              │
└─────────────────────┬───────────────────────────────┘
                      │ fetch() / SSE
┌─────────────────────▼───────────────────────────────┐
│              Nuxt 3 Server (代理层)                    │
│                                                      │
│  ┌────────────┐ ┌───────────┐ ┌────────────────┐    │
│  │ /api/claude│ │ /api/kb   │ │ /api/filesystem│    │
│  │  聊天      │ │  搜索     │ │  文件树 CRUD   │    │
│  │  会话      │ │  目录     │ │  上传          │    │
│  │  技能      │ │  标签     │ │  预览          │    │
│  │  工作区    │ │  文档     │ │                │    │
│  └────────────┘ └───────────┘ └────────────────┘    │
│                                                      │
│  ┌────────────┐ ┌───────────┐ ┌────────────────┐    │
│  │ /api/graph │ │ /api/parse│ │ /api/health    │    │
│  │  图谱搜索  │ │  PDF代理  │ │  系统状态      │    │
│  │  图谱概览  │ │           │ │                │    │
│  └────────────┘ └───────────┘ └────────────────┘    │
│                                                      │
│  ┌──────────────────────────────────────────────┐    │
│  │         server/services/ (业务逻辑)            │    │
│  │  TreeFileSystem · KnowledgeBaseYaml ·         │    │
│  │  KbSearch · PdfParse · TagManagement          │    │
│  └──────────────────────────────────────────────┘    │
└─────────────────────┬───────────────────────────────┘
                      │ 服务器间通信 (trust_env=False)
┌─────────────────────▼───────────────────────────────┐
│              FastAPI Backend (:8765 / :8001)          │
│              MinerU OCR · ChromaDB · Neo4j            │
└─────────────────────────────────────────────────────┘
```

**关键设计决策：**

| 决策 | 理由 |
|------|------|
| 服务器到服务器代理 | Nuxt server 路由转发至后端 — 零 CORS 问题。浏览器永远不直接访问 FastAPI。 |
| 解析数据流 | 浏览器 → Nuxt 代理 → 后端解析 → 返回 `markdown_path` → Nuxt 读取文件 → 回填内容 → 写入 KB 存储。 |
| KB 搜索仅读文件 | `kb-search-service.ts` 直接读取 `.tree-fs.json` + `.knowledge-base.yml` — 搜索零后端负载。 |
| 端口唯一真相源 | 所有端口、URL、路径从根 `config.yml` 通过 `utils/paths.mjs`（手动 YAML 解析器，零 npm 依赖）读取。 |

## 🚀 快速开始

```bash
# 1. 安装
npm install

# 2. 开发模式（热重载，端口 6789）
APP_MODE=dev npm run dev
# → http://localhost:6789

# 生产模式（端口 3000）
APP_MODE=prod npm run start
# → http://localhost:3000
```

```bash
# 生产构建
npm run build
npm run preview

# 类型检查
npx vue-tsc --noEmit --skipLibCheck
```

> **前置要求：** Node.js 18+、npm。解析、搜索、图谱功能需要后端运行。从 monorepo 根目录运行 `ragctl up` 启动，或 `cd backend && uv run python main.py`。

## 📡 API 路由

Nuxt server 作为浏览器与 FastAPI 后端之间的**代理层**。所有路由定义在 `server/api/` 下：

### Claude AI (`/api/claude`)

| 路由 | 方法 | 说明 |
|------|------|------|
| `/api/claude/chat` | `POST` | Claude Code SDK 流式聊天 |
| `/api/claude/sessions` | `GET` | 活动会话列表 |
| `/api/claude/history` | `GET` | 对话历史 |
| `/api/claude/skills` | `GET` | 可用技能列表 |
| `/api/claude/permission` | `POST` | 权限审批处理 |
| `/api/claude/upload` | `POST` | 多模态消息文件上传 |
| `/api/claude/workspaces` | `GET/POST` | 工作区上下文管理 |

### 知识库 (`/api/kb`)

| 路由 | 方法 | 说明 |
|------|------|------|
| `/api/kb/search` | `GET` | 跨 KB 搜索（关键词 + 向量） |
| `/api/kb/catalog` | `GET` | KB 目录（含文档数量） |
| `/api/kb/documents` | `GET` | 列出 KB 内文档 |
| `/api/kb/document` | `GET` | 获取文档详情及元数据 |
| `/api/kb/create` | `POST` | 创建知识库 |
| `/api/kb/update` | `PUT` | 更新 KB 元数据 |
| `/api/kb/delete` | `DELETE` | 删除知识库 |
| `/api/kb/tags` | `GET/POST` | 列出/更新文档标签 |

### 文件系统 (`/api/filesystem`)

| 路由 | 方法 | 说明 |
|------|------|------|
| `/api/filesystem/tree` | `GET` | 完整文件树及元数据 |
| `/api/filesystem/children` | `GET` | 文件夹子节点 |
| `/api/filesystem/upload` | `POST` | 上传并注册文件 |
| `/api/filesystem/preview` | `GET` | 文件内容预览 |

### 解析 (`/api/parse`)

| 路由 | 方法 | 说明 |
|------|------|------|
| `/api/parse/file-vt` | `POST` | 代理转发至后端解析端点 |

### 图谱 (`/api/graph`)

| 路由 | 方法 | 说明 |
|------|------|------|
| `/api/graph/search` | `GET` | 知识图谱搜索 |
| `/api/graph/kb-overview` | `GET` | KB 级图谱概览 |
| `/api/graph/document` | `GET` | 文档中心图谱 |
| `/api/graph/neighbors` | `GET` | 邻居节点浏览 |
| `/api/graph/build-kb` | `POST` | 触发 KB 图谱构建 |
| `/api/graph/build-all` | `POST` | 构建所有 KB 的图谱 |
| `/api/graph/stats` | `GET` | 图谱统计 |

### 健康 (`/api/health`)

| 路由 | 方法 | 说明 |
|------|------|------|
| `/api/health` | `GET` | 系统健康 + 服务状态 |

## 📱 页面

| 页面 | 路由 | 说明 |
|------|------|------|
| **首页** | `/` | 仪表盘概览，快捷操作入口 |
| **Claude 聊天** | `/claude-chat` | 完整 Claude Code SDK 聊天，支持流式、KB 增强、多模态 |
| **文件系统** | `/file-system` | 拖拽文件浏览器、上传、解析触发、预览 |
| **知识库** | `/knowledge-base` | KB 管理 — 创建、编辑、删除 KB + 文档列表 |
| **KB 搜索** | `/knowledge-search` | QDCVR 搜索界面，支持过滤、排序和来源显示 |
| **知识图谱** | `/knowledge-graph` | Neo4j 交互式图谱可视化 |
| **设置** | `/settings` | 环境配置编辑，支持热重载 |
| **关于** | `/about` | 项目信息和版本说明 |
| **关于项目** | `/about-project` | 技术架构和路线图 |

## ⚙️ 配置

所有端口和 URL 来自**根目录 `config.yml`** — 永不硬编码。`utils/paths.mjs` 提供零依赖手动 YAML 解析器。

| 变量 | 默认值（dev / prod） | 说明 |
|------|---------------------|------|
| `APP_MODE` | `dev` | 选择配置段（`dev` → 6789, `prod` → 3000） |
| `WEB_PORT` | 来自 config.yml | 覆盖前端监听端口 |
| `BACKEND_URL` | 来自 config.yml | 代理转发的后端 API 基 URL |

`server/` 目录代码运行在 Nuxt 服务端（Node.js），不在浏览器中执行。它充当 **BFF（Backend For Frontend）** — 代理请求、读取本地 KB 存储文件、编排业务逻辑。

## 📁 项目结构

```
web/
├── start.mjs                        # 启动脚本（读取 config.yml，解析端口）
├── nuxt.config.ts                   # Nuxt 配置 + 来自 config.yml 的 runtimeConfig
├── utils/
│   └── paths.mjs                    # 手动 YAML 配置读取器（零 npm 依赖）
├── pages/
│   ├── index.vue                    # 首页仪表盘
│   ├── claude-chat.vue              # Claude Code SDK 流式聊天
│   ├── file-system.vue              # 可视化文件树浏览器 + 上传
│   ├── knowledge-base.vue           # KB 管理 + 文档列表
│   ├── knowledge-search.vue         # QDCVR 搜索界面
│   ├── knowledge-graph.vue          # Neo4j 图谱可视化
│   └── settings.vue                 # 配置编辑器
├── composables/                     # Vue 组合式函数
│   ├── useTreeFileSystem.ts         # 文件树状态 + 操作
│   ├── usePDFParser.ts              # 解析触发 + 进度追踪
│   └── ...                          # 其他可复用 composables
├── components/                      # 共享 Vue 组件（模态框、查看器等）
├── server/
│   ├── api/                         # Nuxt 服务端 API 路由（代理层）
│   │   ├── claude/                  # 聊天、会话、技能、工作区
│   │   ├── kb/                      # 搜索、目录、文档、标签
│   │   ├── filesystem/              # 树、上传、预览
│   │   ├── parse/                   # PDF 解析代理
│   │   ├── graph/                   # Neo4j 图谱查询
│   │   ├── experience/              # 经验增删改查
│   │   ├── config/                  # 运行时配置
│   │   └── health/                  # 系统健康
│   ├── services/                    # 业务逻辑（服务端运行）
│   │   ├── tree-file-system-service.ts   # .tree-fs.json + 磁盘操作
│   │   ├── knowledge-base-yaml-service.ts # .knowledge-base.yml 管理
│   │   ├── kb-search-service.ts          # 跨 KB 关键词搜索
│   │   ├── pdf-parse-service.ts          # 后端代理 + Markdown 回填
│   │   └── tag-management-service.ts     # 标签注册表
│   └── utils/
│       ├── runtime-paths.ts          # 树存储路径解析
│       └── tree-service.ts           # 单例辅助函数
├── types/                           # TypeScript 接口定义
└── storage/
    └── tree-file-system/            # 默认 KB 文件存储（路径可配）
        ├── .tree-fs.json            # 全局文件树索引
        └── {kb-name}/               # 按 KB 存放的 Markdown 文档 + 图片
            └── .knowledge-base.yml  # 按 KB 的文档索引
```

## 🔧 技术栈

| 层级 | 技术 |
|------|------|
| 框架 | Nuxt 3 · Vue 3.5 · TypeScript |
| UI 库 | Ant Design Vue 4 · Ant Design Icons |
| AI 集成 | `@anthropic-ai/claude-agent-sdk`（流式聊天、多模态） |
| 状态管理 | Pinia + persistedstate 插件 |
| 国际化 | vue-i18n（中英双语） |
| Markdown | marked（渲染）· mammoth（Word 导入） |
| 图谱 | Neo4j JavaScript 驱动（通过服务端代理） |
| 构建 | Vite（Nuxt 内置）· cross-env |
| 测试 | Playwright（端到端） |

## 🤝 贡献

1. Fork → 功能分支 → 提交 → 推送 → PR
2. 提交前运行 `npx vue-tsc --noEmit --skipLibCheck` — 类型检查必须通过
3. UI 变更前请在 dev 和 prod 两种模式下测试
4. 新增 API 路由：遵循现有模式 — 路由文件 → service → 工具函数

## 📄 许可证

MIT · 隶属于 [RAG Knowledge Platform](https://github.com/kingdol666/rag-knowledge)
