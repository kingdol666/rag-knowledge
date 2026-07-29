<div align="center">

<img src="./docs/images/logo.svg" alt="RAG Knowledge Platform" width="128" height="128" />

# RAG Knowledge Platform

### 企业级文档智能与 Agentic 知识库平台

**从原始 PDF 到可验证、可被 Agent 查询的知识 —— 全程一条流水线，内容验证检索拒绝被向量相似度欺骗。**

<p>
<em>QDCVR 语义搜索 · Neo4j 知识图谱 · 经验全生命周期 (E0–E12)<br>
71 个 MCP 工具 · 14 个 Agent 技能 · MinerU OCR · 跨平台</em>
</p>

<p>
<a href="#-快速开始"><img src="https://img.shields.io/badge/快速开始-3条命令-4338ca?style=for-the-badge&logo=rocket" /></a>
<a href="#-目录"><img src="https://img.shields.io/badge/平台-Win_%7C_Linux_%7C_macOS-334155?style=for-the-badge&logo=linux" /></a>
<a href="#%EF%B8%8F-71-个-mcp-工具"><img src="https://img.shields.io/badge/MCP工具-71个-8b5cf6?style=for-the-badge&logo=code" /></a>
<a href="#%EF%B8%8F-四种界面一个后端"><img src="https://img.shields.io/badge/技能-14个-f97316?style=for-the-badge&logo=openai" /></a>
</p>

<p>
<a href="https://github.com/kingdol666/rag-knowledge/stargazers"><img src="https://img.shields.io/github/stars/kingdol666/rag-knowledge?style=flat-square&color=facc15" /></a>
<a href="https://github.com/kingdol666/rag-knowledge/releases"><img src="https://img.shields.io/github/v/release/kingdol666/rag-knowledge?style=flat-square&color=8b5cf6&label=版本" /></a>
<img src="https://img.shields.io/github/commit-activity/m/kingdol666/rag-knowledge?style=flat-square&color=22c55e" />
<img src="https://img.shields.io/badge/Python-3.12-3776ab?style=flat-square&logo=python&logoColor=white" />
<img src="https://img.shields.io/badge/license-MIT-22c55e?style=flat-square" />
<img src="https://img.shields.io/badge/状态-生产就绪-0ea5e9?style=flat-square" />
</p>

<p>
<sub><a href="./README.md">English</a></sub> &nbsp;&middot;&nbsp; <sub><b>中文</b></sub>
</p>

---

<img src="./docs/images/rag-architecture.png" alt="RAG Knowledge Platform — 5层架构" width="900" />

</div>

---

## 📋 目录

<p align="center">
<a href="#-为什么会有这个项目">起源</a> ·
<a href="#-八大支柱">特性</a> ·
<a href="#-快速开始">快速开始</a> ·
<a href="#%EF%B8%8F-四种安装方式">安装</a> ·
<a href="#-前置要求">前置要求</a> ·
<a href="#%EF%B8%8F-四种界面一个后端">使用</a> ·
<a href="#-系统架构">架构</a> ·
<a href="#-配置">配置</a> ·
<a href="#%EF%B8%8F-71-个-mcp-工具">MCP 工具</a> ·
<a href="#-路线图">路线图</a> ·
<a href="#-贡献指南">贡献</a>
</p>

---

## ✨ 为什么会有这个项目

> **现代 RAG 的核心问题：** 向量高相似 ≠ 内容相关。查询 *"PET 双向拉伸"*，向量检索会开心地返回 *"PP 薄膜"* 文献（余弦相似度 0.90）—— 二者都处在"聚合物薄膜"的语义空间里，嵌入模型被骗了。LLM 随后幻觉出一个自信但错误的答案。

本平台在**检索层**而非生成层解决这个问题。其核心方法 —— **QDCVR（查询驱动 · 内容验证检索）** —— 会读取候选文档正文，按独立的 **0–8 内容评分标准**打分，并执行一条不留情面的规则：

> ### 🎯 *"向量很快召回，内容才是真裁决。"*
> 即使向量相似度高达 **0.95**，只要内容评分 **≤ 4**，该文档就会被**丢弃**。

<div align="center">

| | 传统知识库工具 | **RAG Knowledge Platform** |
|:---:|:---|:---|
| 🔍 | 单一搜索策略（向量*或*关键词） | **多策略**：BM25 + 向量 + 标签语义 + 图谱扩展 |
| 🧠 | 盲信向量相似度 | **内容验证检索** —— 独立的 0–8 内容裁决 |
| 🤖 | AI 是后挂的，难集成 Agent | **Agent 原生**：71 个 MCP 工具，14 个技能，任意 MCP 客户端 |
| 💡 | 无结构化知识复用 | **经验库**：E0–E12 全生命周期，P0/P1/P2 可信度分级 |
| 🔧 | 多工具复杂安装，配置分散 | **一条命令** `ragctl setup`，单一 `config.yml` 真相源 |
| 🪟 | 满屏终端窗口 | **静默无头** —— dev 和 prod 均零终端窗口 |

</div>

---

## 🌟 八大支柱

<div align="center">
<img src="./docs/images/rag-pipeline.png" alt="QDCVR Agentic 优先企业检索流水线" width="900" />
</div>

<div align="center">

| # | 支柱 | 你将获得 |
|:---:|:---|:---|
| 📄 | **文档解析** | PDF / Word / Excel / PPT / 图片 → Markdown，基于 **MinerU OCR** 引擎 |
| 🧠 | **QDCVR 检索** | 查询驱动、内容验证的检索 —— 独立 0–8 内容评分 |
| 🔍 | **多策略搜索** | BM25 + 向量两阶段召回 · 跨库企业搜索 · `balance_kbs` 多样性防护 |
| 📊 | **知识图谱** | Neo4j 驱动 · 11 个图谱工具 · 实体/关系图 · 跨库文档桥接 |
| 💡 | **经验库** | E0–E12 全生命周期 · 结构化问题→方案→教训 · P0/P1/P2 可信度 · 衰减 |
| 🔌 | **71 个 MCP 工具** | 知识库 CRUD · 搜索 · 图谱 · 经验 · 解析 · 标签 · 向量索引 · 生命周期 |
| 🎯 | **14 个 Agent 技能** | 自然语言命令 · 中英双语触发 · 自动分发到 Archival Agent |
| 🤫 | **静默无头** | 所有启动器均 **零终端窗口** · dev 和 prod 行为一致 |

</div>

---

## 🧠 QDCVR 检索方法

<div align="center">

### 查询驱动 · 内容验证检索

*你不会信任只看过封面的律师。你的 RAG 也不该信任一个余弦相似度分数。*

</div>

**QDCVR** 是一个 6 步检索流水线，设计目的就是抵御向量相似度的欺骗性评分：

```
用户查询
    │
    ▼
┌──────────────────────────────┐
│  ① 选择 KB                   │  智能分发到合适的知识库
│  (balance_kbs 多样性守卫)     │  防止大 KB 主导检索结果
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│  ② 多路径召回                 │  BM25 → 向量 → 标签语义 → 图谱
│  (4 条并行路径)               │  从每个角度查一遍
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│  ③ 内容验证                   │  ⭐ 核心创新
│  (0-8 评分标准)               │  读取文档正文，独立打分
│                               │  分数 < 6？→ 标签+描述扩展
│                               │  分数 < 4？→ 硬丢弃
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│  ④ 交叉验证                   │  去重，跨库合并，融合排序
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│  ⑤ 置信度评级                 │  P0（验证）/ P1（可能）/ P2（提示）
│  + 盲区声明                   │  诚实的"我不知道"——从不伪造答案
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│  ⑥ 合成答案 + 来源引用        │  每个结论都链接到源文档
└──────────────────────────────┘
```

<details>
<summary><b>🎯 0–8 内容评分标准（点击展开）</b></summary>

| 分数 | 含义 | 示例 |
|:----:|------|------|
| **0–2** | 离题/幻觉 | 向量相似度 0.95 但内容完全在说另一种材料 —— **丢弃** |
| **3–4** | 边缘提及 | 查询 "PET 拉伸"，命中在 20 页关于 PP 的文档中有一句提到 PET —— **丢弃** |
| **5–6** | 部分相关 | 涵盖了主题但缺少关键细节 —— 执行标签+描述 **扩展扫描** |
| **7–8** | 直接回答 | 精确匹配查询的领域、材料、上下文 —— 作为 **P0** 返回 |

> **规则**：向量负责建议候选，内容决定真实答案。0.95 的向量分数如果内容评分 ≤ 4，毫无意义。
</details>

<details>
<summary><b>🧪 实验结果对比</b></summary>

在 6 个领域的 20 个对抗性查询测试中：

| 方法 | P@5 | FPR | 延迟 |
|------|:---:|:---:|:----:|
| 纯向量（盲信） | 0.590 | 12.0% | 84 ms |
| QDCVR 领域检索（验证后） | **0.630** | **3.0%** | **38 ms** |
| 跨域对抗查询 | — | **0.00%** | — |

跨域假阳性率：**0%**（纯向量 50–77%）。

完整基准测试： [`docs/paper/benchmark/SYSTEM-BENCHMARK-PLAN.md`](./docs/paper/benchmark/SYSTEM-BENCHMARK-PLAN.md)
</details>

---

## 🚀 快速开始

> **三条命令，从零到完整可用的平台。**

```bash
# 1 — 克隆仓库
git clone https://github.com/kingdol666/rag-knowledge.git
cd rag-knowledge

# 2 — 一键安装（自动安装所有依赖 + 模型）
./ragctl setup

# 3 — 启动所有服务（静默，零终端窗口）
./ragctl up
```

<div align="center">
<br>
<a href="https://github.com/kingdol666/rag-knowledge/stargazers"><img src="https://img.shields.io/badge/给我们点星-facc15?style=for-the-badge&logo=github&logoColor=black" /></a>
<a href="https://github.com/kingdol666/rag-knowledge/issues"><img src="https://img.shields.io/badge/报告问题-ef4444?style=for-the-badge&logo=github&logoColor=white" /></a>
<br>
</div>

<details>
<summary><b>🔧 Windows 用户 — 使用相同命令（原生）</b></summary>

```powershell
.\ragctl.bat setup
.\ragctl.bat up

# 或 ragctl 全局注册后：
ragctl setup
ragctl up
```
</details>

> [!TIP]
> **没有 Claude Code？没问题。** Web UI 完全独立运行。用任何 MCP 客户端即可访问 71 个工具，或直接在 `http://localhost:6789` 浏览和搜索。

### ✅ 验证一切正常

```bash
ragctl status                                   # 双模式：dev + prod 并排显示
curl http://localhost:8765/api/v1/health        # → {"status":"healthy"}
```

### 🔍 界面对照

| 界面 | 地址 | 用途 |
|------|:----:|------|
| 🌐 **Web UI** | `http://localhost:6789` | 浏览 KB、搜索、图谱可视化 |
| 📚 **API 文档** | `http://localhost:8765/docs` | Swagger UI，69 个端点 |
| 🖥️ **CLI** | `ragctl status` | 服务健康检查 |
| 🤖 **Agent** | Claude Code 会话 | 说"列出所有知识库" |

---

## 🗺️ 四种安装方式

<table>
<tr>
<th width="25%">A. Claude Code 插件<br><sub>推荐</sub></th>
<th width="25%">B. OMP 全局安装</th>
<th width="25%">C. Skills 复制 + 向导</th>
<th width="25%">D. Git Clone（本地）</th>
</tr>
<tr>
<td valign="top">

使用 **Claude Code**，全局注册。

```bash
/plugin marketplace add kingdol666/rag-knowledge
/plugin install rag-knowledge@rag-knowledge
/reload-plugins
```

然后告诉 Agent：

> **"初始化知识库"**

</td>
<td valign="top">

使用 **Oh My Pi** 作为 Agent。

```bash
git clone https://github.com/kingdol666/rag-knowledge.git
cd rag-knowledge
node scripts/install_omp.cjs
```

然后告诉 Agent：

> **"初始化知识库系统"** → `/knowledgebase-init`

</td>
<td valign="top">

仅复制技能，不装插件。

```bash
git clone https://github.com/kingdol666/rag-knowledge.git ~/rag-knowledge
mkdir -p ~/.claude/skills
cp -r ~/rag-knowledge/.claude/skills/knowledgebase* ~/.claude/skills/
```

然后告诉 Agent：

> **"初始化知识库"**

</td>
<td valign="top">

完全手动控制。

```bash
git clone https://github.com/kingdol666/rag-knowledge.git
cd rag-knowledge
./ragctl setup && ./ragctl up
```

打开 **http://localhost:6789**。

</td>
</tr>
</table>

---

## 📦 前置要求

| 工具 | 版本 | 是否必需 | 说明 |
|------|------|:--------:|------|
| **Git** | 任意 | ✅ | 克隆仓库 |
| **Node.js** | ≥ 18 | ✅ | `ragctl` CLI + Nuxt 前端 |
| **uv** | ≥ 0.7 | ⚡ 自动安装 | Python 包管理器 |
| **Python** | 3.12 | ⚡ via uv | uv 自动管理，无需手动安装 |
| **Docker** | 任意 | 📋 可选 | 仅 Neo4j 图谱需要 |
| **Rust** | stable | 📋 可选 | 仅 Tauri 桌面应用需要 |

> **磁盘：** 约 5 GB · 首次运行下载 BGE-M3（~2.2 GB）。默认 ModelScope（国内高速），海外用户在 `config.yml` 中设 `embedding.model_source: huggingface`。

---

## 🖥️ 四种界面，一个后端

### 1. 🤖 Claude Code — *自然语言*

```text
"列出所有知识库"                              → kb_list
"把 ./papers 里的 PDF 全部导入到 ML-research 知识库" → knowledgebase-ingest
"搜索：PET 双轴拉伸参数有哪些？"                 → QDCVR → 验证答案 + 来源
"整理所有知识库 — 修复标签、描述、移动错位文档"      → knowledgebase-organize
"记录这个排查经验"                              → knowledgebase-experience-summarize
```

### 2. ⌨️ CLI — *`ragctl`*

```bash
ragctl up                          # 启动全部（静默）
ragctl up --appmode prod           # 生产端口（8001/3000）
ragctl status                      # 双模式状态
ragctl logs web --tail             # 实时跟踪 Web 日志
ragctl restart backend -f          # 强制重启
ragctl backup                      # 跨平台备份
ragctl down                        # 停止所有服务
```

### 3. 🔌 MCP 客户端 — *任意 Agent*

```python
kb_project_start(backend=True, web=True, wait=True)
kb_search_two_stage(query="强化学习", balance_kbs=True)
experience_search_global(query="ConnectError 排查")
kb_graph_cross_kb_documents(min_kbs=2)
```

### 4. 🌐 Web UI — *浏览器访问*

打开 **http://localhost:6789**：

| 页面 | 路由 | 功能 |
|------|:----:|------|
| 🏠 **首页** | `/` | 仪表盘（28 KBs, 168 文档） |
| 📁 **文件系统** | `/file-system` | 树形浏览、上传、解析、预览 |
| 🗄️ **知识库** | `/knowledge-base` | 知识库 CRUD，文档管理 |
| 🔎 **知识搜索** | `/knowledge-search` | QDCVR 搜索，策略选择 |
| 🌐 **图谱探索** | `/knowledge-graph` | D3.js 力导向图可视化 |
| 🤖 **Claude 对话** | `/claude-chat` | Agent SDK 流式交互 |
| ⚙️ **系统设置** | `/settings` | 配置编辑器，热重载 |
| ❓ **关于** | `/about` / `/about-project` | 发布说明 + 路线图 |

---

## 🏗️ 系统架构

```
浏览器 / Claude Code / MCP 客户端
        │
        ▼
┌──────────────────────────────┐
│  Nuxt 3 Web UI （代理层）     │  6789 (dev) / 3000 (prod)
└──────────────┬───────────────┘
               │ 服务间通信 (trust_env=False)
               ▼
┌──────────────────────────────┐
│  FastAPI 后端 + MinerU OCR   │  8765 (dev) / 8001 (prod)
└──────────────┬───────────────┘
               │ 文件 I/O
               ▼
┌──────────────────────────────────────────────┐
│  存储层                                        │
│  ├── .tree-fs.json  （全局文件树索引）           │
│  ├── {KB}/.knowledge-base.yml（文档索引）       │
│  ├── {KB}/*.md     （文档内容）                 │
│  ├── ChromaDB      （BGE-M3 1024维向量）        │
│  └── Neo4j         （bolt://127.0.0.1:7687）    │
└──────────────────────────────────────────────┘
```

### 五层存储模型

| 层 | 内容 | 技术 |
|:---:|------|------|
| **L1** | 原始 Markdown 文档 | `storage/tree-file-system/{KB}/{doc}.md` |
| **L2** | 文件树索引 | `.tree-fs.json` |
| **L3** | 文档注册表 | `.knowledge-base.yml` |
| **L4** | 向量嵌入（1024 维） | ChromaDB + BGE-M3 |
| **L5** | 知识图谱 | Neo4j（文档/标签/KB 节点 + 关系） |

> **原则：** 写入 → HTTP API（保证 5 层一致）。读取 → 直接文件读取（零后端负载）。

---

## ⚙️ 配置

`config.yml`（项目根目录）是唯一的真相源。`.env` 可覆盖，由 `ragctl setup` 自动创建。

| 变量 | 默认值（dev / prod） | 用途 |
|------|---------------------|------|
| `APP_MODE` | `dev` | 选择配置段 |
| `BACKEND_PORT` | `8765` / `8001` | FastAPI 端口 |
| `WEB_PORT` | `6789` / `3000` | Nuxt 端口 |
| `BACKEND_URL` | `http://localhost:8765` | 后端完整 URL |
| `TREE_STORAGE_PATH` | `./storage/tree-file-system` | KB 数据根路径 |
| `NEO4J_PASSWORD` | (docker-compose) | 图谱数据库认证 |

```bash
ragctl up --appmode prod        # 切换到生产端口
ragctl status                   # dev + prod 并排显示
ragctl down --appmode prod      # 仅停止 prod，保留 Neo4j
```

---

## ⚡ 71 个 MCP 工具

所有工具均可通过 `mcp__kb-mcp__*` 从任何 MCP 兼容 Agent 访问。

<div align="center">

| 类别 | 数量 | 类别 | 数量 |
|:-----|:----:|:-----|:----:|
| **知识库 CRUD** | 5 | **文档 CRUD** | 9 |
| **搜索** | 4 | **文件系统** | 3 |
| **向量索引** | 3 | **解析**（非阻塞） | 3 |
| **知识图谱** | 11 | **经验生命周期** | 20 |
| **标签** | 4 | **服务生命周期** | 4 |
| **清理** | 1 | **后端状态** | 1 |

</div>

---

## 🗺️ 路线图

- [x] **v1.0** — 核心 QDCVR 检索，知识库 CRUD，Web UI，MCP 工具
- [x] **v2.0** — 知识图谱，经验生命周期，双语 i18n
- [x] **v2.1** — 冥想（自动经验），MinerU OCR，多格式解析
- [x] **v2.2** — Tauri 桌面应用，CIKM 基准测试（18 实验）
- [x] **v2.3** — 五层一致性，静默无头，删除时自动清理图谱
- [ ] **v2.4** — 多模态（图片搜索），REST API 密钥认证
- [ ] **v2.5** — WebSocket 实时协作，团队工作区
- [ ] **v3.0** — 分布式索引（Ray），10 万+ 文档规模

---

## 🤝 贡献指南

欢迎提交贡献！

1. 🍴 **Fork** 本仓库
2. 🌿 创建**功能分支**（`git checkout -b feature/amazing`）
3. 💻 **编码**，遵循现有风格
4. ✅ **测试**（`pytest backend/tests/`）
5. 📝 **提交**，写清晰的消息
6. 🚀 **推送**并发起 **Pull Request**

**准则：**
- 保持**原子化** —— 一个 PR 一个功能/修复
- **先测试**再提交（前端：`npx vue-tsc --noEmit`，后端：`pytest`）
- **文档化**新功能
- **没有 AI 废代码** —— 每行代码都应有其目的

---

## 🌐 社区与支持

<div align="center">

| 资源 | 链接 |
|:-----|:-----|
| 🐛 **报告 Bug** | [GitHub Issues](https://github.com/kingdol666/rag-knowledge/issues) |
| ⭐ **给我们点星** | [GitHub](https://github.com/kingdol666/rag-knowledge) |
| :gb: **英文文档** | [README.md](./README.md) |
| 💬 **讨论** | [GitHub Discussions](https://github.com/kingdol666/rag-knowledge/discussions) |
| 📦 **版本发布** | [GitHub Releases](https://github.com/kingdol666/rag-knowledge/releases) |

</div>

---

## 📄 许可证

MIT © [kingdol](https://github.com/kingdol666)

---

<div align="center">

<sub>基于</sub>
<a href="https://fastapi.tiangolo.com/">FastAPI</a> ·
<a href="https://nuxt.com/">Nuxt 3</a> ·
<a href="https://neo4j.com/">Neo4j</a> ·
<a href="https://www.chromadb.com/">ChromaDB</a> ·
<a href="https://modelcontextprotocol.io/">MCP</a> ·
<a href="https://mineru.net/">MinerU</a>

<br>

**⭐ 在 GitHub 上给我们点星 —— 每一颗星都让项目变得更好！** ⭐

<a href="https://github.com/kingdol666/rag-knowledge/stargazers">
<picture>
<source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=kingdol666/rag-knowledge&type=Date&theme=dark" />
<source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=kingdol666/rag-knowledge&type=Date" />
<img alt="Star History Chart" src="https://api.star-history.com/svg?repos=kingdol666/rag-knowledge&type=Date" width="600" />
</picture>
</a>

</div>
