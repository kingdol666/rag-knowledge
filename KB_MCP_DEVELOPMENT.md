# 知识库管理系统 — API 测试报告与 Agentic 知识管理开发规划

> 版本: 1.0  
> 日期: 2026-06-27  
> 适用项目: rag-knowledge (MinerU + FastAPI + Nuxt 3)  
> 文档性质: 端到端测试报告 + MCP 可行性分析 + 后续开发蓝图

---

## 一、端到端测试报告

### 1.1 测试环境

| 组件 | 地址 | 版本 |
|------|------|------|
| Nuxt 前端 (代理层) | http://localhost:3000 | Nuxt 3.21 |
| FastAPI 后端 | http://localhost:8765 | dev 模式 |
| MinerU OCR 引擎 | http://127.0.0.1:8764 | 3.4.0 (pipeline/CPU) |
| 知识库存储根 | `web/storage/tree-file-system/` | — |

测试通过 Web API (Nuxt 代理) 与 Server API (FastAPI) 两层,覆盖普通上传、解析落库、真实 PDF OCR 解析三类场景。

### 1.2 测试结果总览

**全量通过: 15 / 15**

```
======================================================================
  基础 API 测试: 12 通过 / 0 失败
  真实解析测试:  3 通过 / 0 失败
  合计:         15 通过 / 0 失败
======================================================================
```

### 1.3 详细测试项

#### 基础 API 测试 (无 MinerU 依赖)

| # | 测试项 | 结果 | 证据 |
|---|--------|:----:|------|
| 1 | server `/api/v1/health` | PASS | `{"status":"healthy"}` |
| 2 | web `/api/filesystem?action=count` | PASS | folders=11 files=25 |
| 3 | 创建知识库 (`isKnowledgeBase:true`) | PASS | id 生成 + `.knowledge-base.yml` 自动创建 |
| 4 | 普通文件上传 → 写入元数据 | PASS | api=True **json=True yml=True disk=True** |
| 5 | `save-parsed-files` 解析落库链路 | PASS | saved=1 **json=yml=disk=True** |
| 6-9 | server 4 个端点存在性 | PASS | health=200, parse 端点=422(缺参数,端点在) |
| 10-11 | web 解析路由存在性 | PASS | file-vt / batch-file-vt 均 200 |
| 12 | 测试库清理 | PASS | 无残留 |

#### 真实 PDF OCR 解析测试

| # | 测试项 | 结果 | 关键指标 |
|---|--------|:----:|----------|
| 13 | MinerU `/health` | PASS | healthy, v3.4.0 |
| 14 | 单文件解析 (OCR) → 落库 | PASS | parse=success, md_len=16652, **json=yml=disk=True**, 41s |
| 15 | 批量解析 (2 PDF 并行) → 落库 | PASS | successful=2, **a/b 均落库 (json=yml=disk=True)**, 79s |

### 1.4 结论

**三层写入闭环全部验证通过:**

```
普通上传 / 单文件解析 / 批量解析
        │
        ▼
  TreeFileSystemService.uploadFile(parentId)
        │
        ├── 写入磁盘: {知识库}/{文件名}.md
        ├── 写入 .tree-fs.json (全局索引)
        └── 写入 {知识库}/.knowledge-base.yml (库内索引)
```

无论通过哪个入口上传或解析,只要指定了 `parent_id` / `parentId` (知识库文件夹 id),文档都会被知识库管理系统正确识别——元数据(json+yml)与磁盘文件三者同步。

---

## 二、当前 API 能力清单

### 2.1 已验证可用的 API

#### Web API (Nuxt 代理层, 端口 3000/6789)

| 端点 | 方法 | 用途 | 知识库写入 |
|------|------|------|:----------:|
| `/api/filesystem` | GET | 拉取树/子节点/计数 | — |
| `/api/filesystem/nodes` | POST | 创建文件夹/文件 (含 isKnowledgeBase) | 自动 |
| `/api/filesystem/nodes/{id}` | PATCH/DELETE | 更新/删除节点 | 同步 |
| `/api/filesystem/upload` | POST | 普通文件上传 | ✓ |
| `/api/parse/file-vt` | POST | 单文件解析 (支持 `parent_id`) | ✓ |
| `/api/parse/batch-file-vt` | POST | 批量解析 (支持 `parent_id`) | ✓ |
| `/api/parse/batch-file-vt-stream` | POST (SSE) | 流式批量解析 | ✓ |
| `/api/parse/save-parsed-files` | POST | 解析结果落库到指定知识库 | ✓ |
| `/api/preview/file` | GET | 文件预览/下载 | — |
| `/api/preview/markdown-preview` | GET | Markdown 渲染预览 | — |

#### Server API (FastAPI, 端口 8765)

| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/v1/health` | GET | 健康检查 |
| `/api/v1/parse/file/vt` | POST | v1 单文件解析 (MinerU async task) |
| `/api/v1/parse/file/vt/legacy` | POST | 同步解析 (向后兼容) |
| `/api/v1/batch/parse/file/vt` | POST | 批量解析 (JSON) |
| `/api/v1/batch/parse/file/vt/stream` | POST | 批量解析 (SSE) |
| `/api/deepagent/*` | * | DeepAgent 智能体执行 (摘要/分类等) |

### 2.2 数据存储结构

```
web/storage/tree-file-system/
├── .tree-fs.json                    # 全局索引 (所有文件夹+文件)
├── {知识库A}/
│   ├── .knowledge-base.yml          # 库内文档索引 (供 Agentic RAG 检索)
│   ├── doc1.md                      # 实际文档
│   ├── doc2.md
│   └── images/                      # 文档图片
└── {知识库B}/
    └── ...
```

`.knowledge-base.yml` 每条文档记录: `name / description / path / file_type / file_size / metadata`。
`.tree-fs.json` 含 folder+file 完整树,带 parentId 关系。

---

## 三、MCP 可行性分析

### 3.1 结论: 可行,且推荐

将上述 API 封装为 MCP (Model Context Protocol) 服务器是可行的,能让任何 Agent harness (Codex / Claude Desktop / Cursor / 自研 Agent) 通过统一协议驱动知识库的解析与上传。

### 3.2 为什么用 MCP,以及边界

| 方面 | 判断 |
|------|------|
| **是否要重写解析逻辑** | **否**。MCP 服务器是一层薄封装,内部调现有的 HTTP API,不重写 MinerU/服务端逻辑 |
| **写入侧(解析/上传)** | **走 HTTP API**。解析依赖 MinerU 子进程,分类依赖 DeepAgent,这些是有状态服务端资源,只能后端调度 |
| **读取侧(检索)** | **走文件直读**。`.tree-fs.json` 和 `.knowledge-base.yml` 是纯文本,MCP 进程直接读,零延迟、不抢后端资源 |
| **与现有系统的关系** | MCP 是"门面",不是替代。所有能力由现有 API 提供,MCP 只做协议翻译 |

**核心架构原则: 写入走 API,读取走直读。**

### 3.3 MCP 服务器应暴露的工具

#### 摄入组 (写入,内部调 HTTP API)

| 工具 | 参数 | 行为 |
|------|------|------|
| `list_knowledge_bases` | — | 列出所有库 id/name/description/文档数 |
| `create_knowledge_base` | name, description, parent_id? | 显式新建库 |
| `ingest_file` | file_path? / url? / raw_text?, filename?, target_kb_id?, use_ocr? | 摄入主入口: 获取→按需解析→(自动)分类→生成摘要→入库 |

#### 检索组 (读取,直接读文件)

| 工具 | 参数 | 行为 |
|------|------|------|
| `search_catalog` | query, top_k? | 跨库检索(搜库名/描述/文件名/摘要/关键词) |
| `get_kb_manifest` | kb_id | 取某库完整 `.knowledge-base.yml` |
| `read_document` | path, offset?, limit?, max_chars? | 分段读取 md 正文 |

### 3.4 实现路径

MCP 服务器可用 TypeScript (@modelcontextprotocol/sdk) 或 Python (mcp 官方 SDK) 实现,运行在本地 (stdio) 或远程 (SSE)。推荐 Python SDK,与后端同栈,复用 `requests` 调 HTTP API 即可。预估工作量: 摄入组 2 天,检索组 1 天,联调 1 天。

---

## 四、后续开发: 需要补全的 API 与功能

当前系统已具备完整的"上传+解析+存储+索引"闭环,但要支撑**智能化的知识管家 Agent 和检索 Agent**,还需补齐以下能力。按优先级排列。

### 4.1 P0 — 自动分类与摘要 (让摄入变 Agentic)

**现状缺口:** 当前 `parent_id` 需人工指定,文档 description 默认是 "Parsed from xxx.pdf"。

**需新增 API:**

| 端点 | 用途 |
|------|------|
| `POST /api/kb/auto-classify` | 输入 md 文本+现有库列表 → 返回最匹配库 id / 新分类建议。复用 DeepAgent,新增 `classifier` artifact |
| `POST /api/kb/auto-ingest` | 端到端自动摄入: 解析→分类→摘要→入库 (整合 auto-classify + content_briefer) |

**实现要点:**
- 复用现有 `content_briefer` artifact 生成摘要 (已验证可用)
- 新增 `classifier` artifact: 读 md 头部 2000 字 + 所有库的 name/description/RULE.md → LLM 输出匹配结果
- 同时生成 3-7 个关键词,写入 `.knowledge-base.yml` 的 metadata (检索质量的关键)

### 4.2 P0 — 检索 API (让知识库可被 Agent 查询)

**现状缺口:** 当前只有文件树浏览 API,没有面向检索的 API。`.tree-fs.json` 和 `.knowledge-base.yml` 已是检索用的索引,但缺查询入口。

**需新增 API:**

| 端点 | 用途 |
|------|------|
| `GET /api/kb/search?query=xxx&top_k=10` | 跨库关键词检索,返回候选文档 (库名/描述/路径/摘要) |
| `GET /api/kb/{kb_id}/documents` | 列出某库所有文档清单 (读 .knowledge-base.yml) |
| `GET /api/kb/document?path=xxx` | 读取单个文档正文 (支持分段) |
| `GET /api/kb/catalog` | 返回全局目录 (所有库+文档摘要,一次返回) |

**实现要点:**
- 第一版用纯文件读取 + 关键词/BM25 打分 (无需向量库)
- `.knowledge-base.yml` 的 description/keywords 就是检索字段
- 文档量过千后,可叠加 embedding (可选,P3)

### 4.3 P1 — 删除一致性修复

**现状缺陷:** 测试发现 DELETE 后 `.knowledge-base.yml` 偶发不同步 (磁盘+json 删了,yml 残留)。

**修复:**
- `TreeFileSystemService.deleteFile` 已调用 `removeFileFromYaml`,需排查单例 metadata 缓存竞态
- 或在 delete 路由强制 `reloadMetadata()` 后再删

### 4.4 P1 — 网页/URL 摄入通道

**现状缺口:** 只能传本地文件,不能直接摄入网页内容。

**需新增:**
- DeepAgent 已有 `web_search` 工具,可抓取 URL 内容
- 新增 `POST /api/kb/ingest-url` : 抓取→提炼为结构化 md→走 auto-ingest
- 这条路径**不经过 MinerU** (网页已是文本),直接提炼入库

### 4.5 P2 — RULE.md 作为分类规则

**现状:** 已支持每个知识库挂 RULE.md (create-rule 端点),但未被自动分类使用。

**增强:**
- auto-classify 时把候选库的 RULE.md 一并喂给 classifier
- RULE.md 描述"什么内容该进这个库",提升分类准确度

### 4.6 P3 — 向量检索 (规模化增强,非必须)

**适用场景:** 文档数过千,关键词检索召回不足时。

**方案:**
- `.knowledge-base.yml` 增加 `embedding` 字段 (或独立向量库如 Chroma/Qdrant)
- 检索 API 增加 `mode=vector` 选项
- 与关键词检索混合 (hybrid)

---

## 五、Agentic 知识管理系统的两层架构

基于上述能力,完整的 Agentic 知识系统由两层构成:

```
┌─────────────────────────────────────────────────────┐
│  Agent 层 (Codex / Claude / 自研)                     │
│  ┌────────────────┐    ┌────────────────┐           │
│  │ 知识管家 Agent  │    │ 知识检索 Agent  │           │
│  │ (摄入/分类/归档)│    │ (查询/取用/回答)│           │
│  └───────┬────────┘    └───────┬────────┘           │
│          │   MCP 协议           │                     │
└──────────┼──────────────────────┼─────────────────────┘
           │                      │
┌──────────▼──────────────────────▼─────────────────────┐
│  MCP 服务器 (薄封装)                                    │
│  摄入组工具 (调HTTP)        检索组工具 (读文件)          │
└──────────┬──────────────────────┬─────────────────────┘
           │                      │
┌──────────▼─────────┐  ┌─────────▼────────────────────┐
│  现有系统 (已就绪)   │  │  索引文件 (已就绪)            │
│  FastAPI + MinerU  │  │  .tree-fs.json              │
│  DeepAgent         │  │  .knowledge-base.yml        │
│  Web 代理层         │  │  {库}/*.md                  │
└────────────────────┘  └─────────────────────────────┘
```

**知识管家 Agent** 负责摄入侧: 收到文档/URL → 调 MCP 的 `ingest_file` → 自动分类 → 摘要 → 入库。
**知识检索 Agent** 负责消费侧: 收到问题 → 调 `search_catalog` 锁定候选 → `get_kb_manifest` 细筛 → `read_document` 读原文 → 回答 + 溯源。

检索 Agent 的核心纪律 (写进 Skill): 不只信目录描述,必须打开原文确认,不够就重查。这是"确保 RAG 是任务真正需要的"的工程来源。

---

## 六、开发路线图

| 阶段 | 内容 | 工作量 | 依赖 |
|------|------|:------:|------|
| **阶段1** | 检索 Skill + 检索 API (4.2) | 2-3 天 | 无 (现有索引即可) |
| **阶段2** | auto-ingest 端点 + classifier artifact (4.1) | 3-4 天 | DeepAgent 已就绪 |
| **阶段3** | MCP 服务器封装 (摄入组+检索组) | 3-4 天 | 阶段1+2 |
| **阶段4** | 两个 Agent Skill 编写 + 联调 | 2-3 天 | 阶段3 |
| **阶段5** | 删除一致性修复 (4.3) + URL 摄入 (4.4) | 2 天 | 可与上面并行 |

**建议起步顺序:** 先做阶段1 (检索 API + Skill),零风险高回报,立刻让现有知识库可被 Agentic 检索;再做阶段2/3 闭环摄入。

---

## 七、附录

### 7.1 测试用 Python 依赖
```
requests>=2.32
```

### 7.2 已验证的解析性能基线
- 单文件 (2.6MB / 19页): OCR 约 41 秒
- 批量 (2 文件并行): 约 79 秒
- MinerU CPU pipeline 模式,无 GPU

### 7.3 部署注意
后端 v1 返回的 `markdown_path` 是后端机器绝对路径,proxy 读正文回填需**前后端同机**。分离部署时需改为后端直接返回 markdown 正文,或新增按 task_id 取正文的接口。