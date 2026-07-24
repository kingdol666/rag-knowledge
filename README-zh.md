<div align="center">

<img src="./docs/images/logo.svg" alt="RAG Knowledge Platform" width="128" height="128" />

# RAG Knowledge Platform

### 企业级文档智能与 Agentic 知识库平台

**从原始 PDF 到可验证、可被 Agent 查询的知识 —— 全程一条流水线，内容验证检索拒绝被向量相似度欺骗。**

<p>
<em>QDCVR 语义搜索 &middot; Neo4j 知识图谱 &middot; 经验全生命周期 (E0–E12)<br>
76 个 MCP 工具 &middot; 14 个 Agent 技能 &middot; MinerU OCR &middot; 跨平台</em>
</p>

<p>
<a href="#-快速开始"><img src="https://img.shields.io/badge/快速开始-3条命令-4338ca?style=for-the-badge&logo=rocket" /></a>
&nbsp;
<img src="https://img.shields.io/badge/平台-Win_%7C_Linux_%7C_macOS-334155?style=for-the-badge&logo=linux" />
&nbsp;
<img src="https://img.shields.io/badge/MCP工具-76个-8b5cf6?style=for-the-badge&logo=code" />
&nbsp;
<img src="https://img.shields.io/badge/技能-14个-f97316?style=for-the-badge&logo=openai" />
</p>

<p>
<a href="https://github.com/kingdol666/rag-knowledge/stargazers"><img src="https://img.shields.io/github/stars/kingdol666/rag-knowledge?style=flat-square&color=facc15" /></a>
&nbsp;
<a href="https://github.com/kingdol666/rag-knowledge/releases"><img src="https://img.shields.io/github/v/release/kingdol666/rag-knowledge?style=flat-square&color=8b5cf6&label=版本" /></a>
&nbsp;
<img src="https://img.shields.io/badge/Python-3.12-3776ab?style=flat-square&logo=python&logoColor=white" />
&nbsp;
<img src="https://img.shields.io/badge/license-MIT-22c55e?style=flat-square" />
&nbsp;
<img src="https://img.shields.io/badge/状态-生产就绪-0ea5e9?style=flat-square" />
</p>

<p>
<sub><a href="./README.md">English</a></sub> &nbsp;&middot;&nbsp; <sub><b>中文</b></sub>
</p>

---

<img src="./docs/images/rag-architecture.png" alt="RAG Knowledge Platform — 5层架构" width="900" />

</div>

<br>

## ✨ 为什么会有这个项目

> **现代 RAG 的核心问题：** 向量高相似 ≠ 内容相关。查询 *"PET 双向拉伸"* 时，向量检索会开心地返回 *"PP 薄膜"* 文献（余弦相似度 0.90）—— 二者都处在"聚合物薄膜"的语义空间里，嵌入模型被骗了。LLM 随后幻觉出一个自信但错误的答案。

本平台在**检索层**而非生成层解决这个问题。其核心方法 —— **QDCVR（查询驱动 · 内容验证检索）** —— 会读取候选文档正文，按独立的 **0–8 内容评分标准**打分，并执行一条不留情面的规则：

> ### 🎯 *“向量很快召回，内容才是真裁决。”*
> 即使向量相似度高达 **0.95**，只要内容评分 **≤ 4**，该文档就会被**丢弃**。

<div align="center">

| | 传统知识库工具 | **RAG Knowledge Platform** |
|:---:|:---|:---|
| 🔍 | 单一搜索策略（向量*或*关键词） | **多策略**：BM25 + 向量 + 标签语义 + 图谱扩展 |
| 🧠 | 盲信向量相似度 | **内容验证检索** —— 独立的 0–8 内容裁决 |
| 🤖 | AI 是后挂的，难集成 Agent | **Agent 原生**：76 个 MCP 工具，14 个技能，任意 MCP 客户端可用 |
| 💡 | 无结构化知识复用 | **经验库**：E0–E12 全生命周期，P0/P1/P2 可信度分级 |
| 🔧 | 多工具复杂安装，配置分散 | **一条命令** `ragctl setup`，单一 `config.yml` 真相源 |
| 🪟 | 满屏终端窗口 | **静默无头** —— dev 和 prod 均零终端窗口 |

</div>

---

## 🌟 八大支柱

<div align="center">
<img src="./docs/images/rag-pipeline.png" alt="QDCVR Agentic 优先企业检索流水线" width="900" />
</div>

| | 支柱 | 你将获得 |
|:---:|:---|:---|
| 📄 | **文档解析** | PDF / Word / Excel / PPT / 图片 → Markdown，基于 **MinerU OCR** 引擎 |
| 🧠 | **QDCVR 检索** | 查询驱动、内容验证的检索 —— 独立 0–8 内容评分 |
| 🔍 | **多策略搜索** | BM25 + 向量两阶段召回 · 跨库企业搜索 · `balance_kbs` 多样性防护 |
| 📊 | **知识图谱** | Neo4j 驱动 · 14 个图谱工具 · 实体/关系图 · 跨库文档桥接 |
| 💡 | **经验库** | E0–E12 全生命周期 · 结构化问题→方案→教训 · P0/P1/P2 可信度 · 衰减 |
| 🔌 | **76 个 MCP 工具** | 知识库 CRUD · 搜索 · 图谱 · 经验 · 解析 · 标签 · 向量索引 · 生命周期 · 全 MCP 原生 |
| 🎯 | **14 个 Agent 技能** | 自然语言命令 · 中英双语触发 · 自动分发到 Archival Agent |
| 🤫 | **静默无头** | 所有启动器均 **零终端窗口** · dev 和 prod 行为一致 |

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

完成。打开 **http://localhost:6789** 即可使用。

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
> **没有 Claude Code？没问题。** Web UI 完全独立运行。用任何 MCP 客户端即可访问 76 个工具，或直接在 `http://localhost:6789` 浏览和搜索。

### ✅ 验证一切正常

```bash
ragctl status                                   # 双模式：dev + prod 并排显示
curl http://localhost:8765/api/v1/health        # → {"status":"healthy"}
```

---

## 💻 四种安装方式

<table>
<tr>
<th width="25%">A. Claude Code 插件<br><sub><code>推荐</code></sub></th>
<th width="25%">B. OMP 全局安装</th>
<th width="25%">C. Skills 复制 + 向导</th>
<th width="25%">D. Git Clone（本地）</th>
</tr>
<tr>
<td valign="top">

使用 **Claude Code**，希望全局可用

```bash
claude plugin marketplace add kingdol666/rag-knowledge
claude plugin install rag-knowledge
```

然后你可以在 Claude Code || OMP 中简单地询问：`"初始化知识库系统"`。(/knowledgebase-init)

</td>
<td valign="top">

使用 **Oh My Pi** 作为编码 Agent

```bash
git clone https://github.com/kingdol666/rag-knowledge.git
cd rag-knowledge
node scripts/install_omp.cjs
```

</td>
<td valign="top">

不想装插件，但仍需引导式安装

```bash
git clone https://github.com/kingdol666/rag-knowledge.git ~/rag-knowledge
mkdir -p ~/.claude/skills
cp -r ~/rag-knowledge/.claude/skills/knowledgebase* ~/.claude/skills/
```

</td>
<td valign="top">

需要完全手动控制

```bash
git clone https://github.com/kingdol666/rag-knowledge.git
cd rag-knowledge
./ragctl setup && ./ragctl up
```

</td>
</tr>
</table>

<details>
<summary><b>📋 <code>ragctl setup</code> 具体做了什么？</b></summary>

| 步骤 | 操作 | 耗时 |
|------|------|------|
| 1 | 安装 `uv`（Python 包管理器），如缺失 | ~5 秒 |
| 2 | 确保 Python 3.12 可用（uv 管理） | ~10 秒 |
| 3 | 验证项目完整性（`backend/` + `web/`） | 即时 |
| 4 | 从 `.env.example` 创建 `.env` | 即时 |
| 5 | 安装后端依赖（FastAPI + torch + transformers + MinerU） | 5–15 分钟 |
| 6 | 安装 kb-mcp 依赖（MCP 服务端） | ~30 秒 |
| 7 | 安装前端依赖（Nuxt 3 + Ant Design Vue） | ~1 分钟 |
| 8 | 预下载 BGE-M3 嵌入模型（~2.2 GB） | 2–10 分钟 |
| 9 | 预下载 MinerU VLM 模型（OCR 引擎） | 3–10 分钟 |
| 10 | 全局注册 `ragctl` → `~/.local/bin` | 即时 |
| 11 | 最终环境检查 | ~2 秒 |

</details>

---

## ✅ 前置要求

只需以下工具在**开始前已安装** — `ragctl setup` 自动处理其余一切。

| 工具 | 版本 | 是否必需 | 说明 |
|------|------|:--------:|------|
| **Git** | 任意 | ✅ 必需 | 克隆仓库 |
| **Node.js** | ≥ 18（推荐 22） | ✅ 必需 | `ragctl` CLI + Nuxt 前端 |
| **uv** | ≥ 0.7 | ⚡ 自动安装 | Python 包管理器 — 缺失时 `ragctl setup` 自动安装 |
| **Python** | 3.12 | ⚡ via uv | uv 管理 Python 环境；无需手动安装 |
| **Docker** | 任意 | 📋 可选 | 仅 Neo4j 图谱需要。解析、搜索、经验功能不需要 |
| **Rust** | stable | 📋 可选 | 仅构建 Tauri 桌面应用需要 |

> **资源需求：** ~5 GB 磁盘 · 首次运行下载 BGE-M3（~2.2 GB）。默认源：**ModelScope**（国内快速）。海外用户在 `config.yml` 中设 `embedding.model_source: huggingface`。

---

## 🖥️ 使用方式 — 四种界面，一个后端

### 1. Claude Code — *自然语言*

安装完成后，直接用中英文描述你想做什么：

```text
"把 ./papers 里的 PDF 全部导入到一个新的 'ML-research' 知识库"
  → knowledgebase-ingest (A0→A9 质量门控)

"搜索：PET 双轴拉伸参数有哪些？"
  → QDCVR → 内容验证的答案 + 来源 + 置信度

"记录这个排查经验"
  → knowledgebase-experience-summarize → 结构化经验

"整理所有知识库 — 修复标签、描述、移动错位文档"
  → knowledgebase-organize (O0→O13)
```

> 如果服务未运行，**Archival Agent 会静默启动它们**（通过 `kb_project_start`）— 无终端，无手动步骤。

### 2. CLI — `ragctl`

```bash
ragctl up                     # 启动全部（静默，dev 模式）
ragctl up --appmode prod      # prod 端口（8001/3000）
ragctl status                 # 双模式：dev + prod 并排
ragctl logs web --tail        # 实时跟踪 Web 日志
ragctl restart backend -f     # 强制重启单个服务
ragctl backup                 # 跨平台备份（KB + ChromaDB + Neo4j）
ragctl down --appmode prod    # 仅停止 prod（Neo4j 保留）
```

<details>
<summary><b>📋 完整 CLI 参考</b></summary>

| 命令 | 说明 |
|------|------|
| `ragctl setup` · `init` | 一键完整部署 |
| `ragctl check` | 全面环境检查 + 修复建议 |
| `ragctl up` / `down` | 启动 / 停止所有服务（静默，无终端） |
| `ragctl start` / `stop` / `restart` [svc] | 单服务生命周期（`backend`\|`web`\|`neo4j`\|`all`） |
| `ragctl status [--appmode X]` | 双模式状态：端口 + HTTP 健康 + PID + MinerU |
| `ragctl logs [svc] [--tail] [--lines N]` | 查看 / 实时跟踪日志 |
| `ragctl deps` | 安装所有依赖（实时进度） |
| `ragctl model` | 预下载 BGE-M3 模型。`--source modelscope\|hf-mirror\|huggingface` |
| `ragctl backup` / `restore` | 跨平台备份与恢复（KB 文档 + ChromaDB + Neo4j） |
| `ragctl version` | 显示本地 VERSION + git SHA 对比 GitHub 远程 |
| `ragctl update` | 检查 GitHub 并拉取最新 |
| `ragctl install` | 全局注册 `ragctl` → `~/.local/bin` |
| `ragctl desktop` · `ui` | 启动 Tauri 桌面控制台 |
| `ragctl clean` | 清理 MinerU 产物 + 缓存（`--model` 需二次确认） |

**Flags：** `--appmode dev\|prod`（`--mode`, `-m`）、`--port-backend N`、`--port-web N`、`--no-neo4j` / `--no-backend` / `--no-web`、`--force`（`-f`）、`--tail`

</details>

### 3. MCP 客户端 — *任意 Agent*

```python
kb_project_start(backend=True, web=True, wait=True)   # 静默启动
kb_search_two_stage(query="强化学习", balance_kbs=True)
experience_search_global(query="ConnectError 排查")
kb_graph_cross_kb_documents(min_kbs=2)
```

### 4. Web UI

打开 **http://localhost:6789** — 浏览知识库、搜索文档、探索图谱、通过 Agent SDK 与 Claude 对话。

---

## 🔌 MCP 工具 — 76 个

全部通过 `mcp__kb-mcp__*` 从 Claude Code 或任意 MCP 客户端访问。

| 类别 | 数量 | 关键工具 |
|------|:----:|---------|
| **服务生命周期** | 6 | `kb_project_start`, `kb_project_status`, `kb_project_preflight`, `kb_project_version`, `kb_project_update`, `backend_status` |
| **知识库 CRUD** | 7 | `kb_list`, `kb_create`, `kb_update`, `kb_delete`, `kb_catalog`, `kb_doc_catalog`, `kb_get_documents` |
| **文档 CRUD** | 7 | `kb_doc_read`, `kb_doc_create`, `kb_doc_update_meta`, `kb_doc_update_content`, `kb_doc_delete`, `kb_doc_batch_delete`, `kb_doc_move` |
| **文件系统** | 4 | `fs_get_tree`, `fs_get_children`, `fs_get_count`, `fs_upload_file` |
| **解析** | 4 | `parse_doc`, `parse_doc_batch`, `parse_task_status`, `kb_doc_save_parsed` |
| **标签** | 4 | `kb_tags_list`, `kb_doc_update_tags`, `kb_doc_get_by_tag`, `kb_tags_cleanup` |
| **搜索** | 4 | `kb_search`, `kb_search_vector`, `kb_search_two_stage`, `kb_search_stats` |
| **向量/索引** | 4 | `kb_index_document`, `kb_batch_index`, `kb_reindex`, `kb_cleanup_orphan_collections` |
| **知识图谱** | 14 | `kb_graph_search` · `kb_graph_kb_overview` · `kb_graph_build` · `kb_graph_cross_kb_documents` · … |
| **经验** | 22 | `experience_create` · `experience_search_global` · `experience_search_smart` · `experience_dashboard` · `experience_extract` · … |

---

## 🎯 技能 — 14 个

| 技能 | 流程 | 用途 |
|------|------|------|
| **knowledgebase** | 路由器 | 分发用户意图到正确的子技能 |
| **knowledgebase-init** | Phase 0→11 | 引导式全新安装向导（主 Agent） |
| **knowledgebase-update** | Phase 0→5 | 版本检查 + 安全 GitHub 拉取（主 Agent） |
| **knowledgebase-ingest** | A0→A9 | 文档入库 + 质量门控 |
| **knowledgebase-search** | Step 0–6 | QDCVR 检索 + 内容验证 |
| **knowledgebase-search-enterprise** | Phase 0–5 | 多策略跨库搜索 |
| **knowledgebase-manage** | M1→M6 | 文档与知识库管理 |
| **knowledgebase-organize** | O0→O13 | 全库整理重组 |
| **knowledgebase-verify** | V1→V9 | 完整性与质量校验 |
| **knowledgebase-list** | L1→L3 | 只读浏览 |
| **knowledgebase-graph** | — | Neo4j 图谱构建、查询、分析 |
| **knowledgebase-experience** | E0→E12 | 经验生命周期管理 |
| **knowledgebase-experience-summarize** | S1→S5 | 提炼并保存结构化经验 |
| **knowledgebase-batch** | B1→B7 | 高吞吐量批量操作 |

> 所有技能均**自包含** — 无外部 CLAUDE.md 依赖。12 个委派给 Archival Agent；`init` 和 `update` 在主 Agent 上运行。

---

## 🧠 QDCVR 检索方法

旗舰贡献。一条七阶段流水线，让检索变得可信：

```
查询 → Step 0: 意图识别 + 改写 → Step 1: 智能选库
      → Step 2: 两阶段召回 (BM25 → 向量, balance_kbs)
      → Step 2.5: 去重 + 硬阈值
      → Step 3: 内容验证 (0–8 打分) ⭐
      → Step 5: 置信度分级 (P0 / P1 / P2)
      → Step 6: 回答 + 盲点声明
```

**内容验证评分标准**从三个维度给每个候选打分：

| 维度 | 分值 | 判据 |
|------|:----:|------|
| 主题相关 | 0–3 | 3 = 正文直接围绕查询主体 |
| 场景/问题匹配 | 0–3 | 3 = 直接解决查询的问题 |
| 答案证据 | 0–2 | 2 = 含可直接引用的数据/步骤/结论 |

> **决策规则：** `≥ 6 分 → 采纳 (P0)` · `= 5 分 → 补充 (P1)` · `≤ 4 分 → 丢弃` — **与向量相似度无关。**

<details>
<summary><b>📖 经验可信度模型 (P0/P1/P2)</b></summary>

结构化运维知识（问题→方案→教训）通过 13 阶段全生命周期（**E0–E12**）管理，含可信度分级和时效衰减：

| 层级 | 条件 | 呈现方式 |
|------|------|---------|
| **P0 强** | 向量≥0.65 ∧ 内容≥6 ∧ 评分≥4 ∧ 审核数≥1 | 直接引用作答 |
| **P1 已确认** | 向量≥0.45 ∧ 内容≥4 | 引用并标注 |
| **P2 补充** | 向量≥0.35 ∧ 内容≥3 | 默认隐藏，按需展开 |
| **丢弃** | 内容验证失败 或 向量 < 0.35 | 永不呈现 |

**衰减规则：** 陈旧未验证（>30天, 应用0次）→ 降级；有争议（评分<2, 审核≥3）→ 强制封顶 P2；未审核（0审核 ∧ 应用0次）→ 封顶 P1。

</details>

---

## 🏗️ 架构

```
浏览器 / Claude Code / MCP 客户端
        │
        ▼
┌──────────────────┐
│  Nuxt 3 Web UI   │  端口 6789 (dev) / 3000 (prod)
│  (代理层)         │
└────────┬─────────┘
         │  服务间通信
         ▼
┌──────────────────┐
│  FastAPI 后端     │  端口 8765 (dev) / 8001 (prod)
│  + MinerU OCR     │  临时端口
└────────┬─────────┘
         │  文件读取
         ▼
┌─────────────────────────────────────┐
│  $TREE_STORAGE_PATH/                │
│  ├── .tree-fs.json                  │
│  │── {KB}/.knowledge-base.yml       │
│  │── {KB}/doc.md                    │
│  │                                  │
│  + ChromaDB (BGE-M3, 1024维)       │
│  + Neo4j (bolt://127.0.0.1:7687)   │
└─────────────────────────────────────┘
```

> **原则：** 写入 → HTTP API（后端/Web 代理）。读取 → 直接文件访问（`.tree-fs.json` + `.knowledge-base.yml`）。

### 五层数据模型

| 层级 | 内容 | 格式 |
|------|------|------|
| L1 原始 | 原始文档 | PDF / DOCX / XLSX / PNG |
| L2 解析 | Markdown + 图片 | `.md` |
| L3 向量 | 分块嵌入 | ChromaDB collections |
| L4 图谱 | 实体/关系节点 | Neo4j |
| L5 经验 | 结构化教训 | YAML + Markdown |

---

## ⚙️ 配置

**`config.yml`**（项目根目录）是**端口配置的唯一真相源**。**`.env`** 覆盖，由 `ragctl setup` 创建。

| 变量 | 默认值 (dev / prod) | 用途 |
|------|---------------------|------|
| `APP_MODE` | `dev` | 选择 config.yml 配置段 |
| `BACKEND_PORT` | `8765` / `8001` | FastAPI 端口 |
| `WEB_PORT` | `6789` / `3000` | Nuxt Web 端口 |
| `BACKEND_URL` | 自动推导 | 完整后端 URL |
| `HF_ENDPOINT` | `https://hf-mirror.com` | 模型下载镜像 |
| `TREE_STORAGE_PATH` | `./storage/tree-file-system` | KB 数据存储路径 |
| `NEO4J_PASSWORD` | （来自 docker-compose） | 图数据库密码 |

运行时切换模式，无需修改 `.env`：

```bash
ragctl up --appmode prod       # 后端 → 8001, 前端 → 3000
ragctl status                  # 同时显示 dev + prod
ragctl down --appmode prod     # 仅停止 prod（Neo4j 保留）
```

### API 速率限制

内置滑动窗口速率限制器（在 `config.yml` 中配置）：

```yaml
server:
  rate_limit:
    enabled: true
    window_sec: 60
    max_requests: 120      # 普通接口
    heavy_max: 20          # 解析/MinerU 接口
```

---

## 🤫 静默运行

所有启动器在 dev 和 prod 中均以**零终端窗口**启动服务。输出流到**三个同步界面** — 全部读取相同的日志文件：

| 界面 | 命令 |
|------|------|
| 📄 磁盘文件 | `backend/logs/desktop-stdout.log` · `web/logs/desktop-stdout.log` · `backend/logs/mineru-api.log` |
| 🖥️ Tauri 桌面控制台 | 实时日志流（跟踪相同文件） |
| ⌨️ `ragctl logs` | CLI 查看器 + 实时跟踪 |

```bash
ragctl logs backend            # 最近 80 行
ragctl logs web --tail         # 实时跟踪（Ctrl+C 退出）
ragctl logs mineru --lines 200 # 200 行 OCR 输出
```

---

## 🛠️ 故障排查

| 症状 | 可能原因 | 修复 |
|------|---------|------|
| MCP 连接失败 | `uv` 不在 PATH（新终端） | `ragctl setup` 安装 uv；重开终端 |
| 后端无法启动 | 依赖未安装 | `ragctl setup`（或 `cd backend && uv sync`） |
| Web 无法启动 | 缺少 `node_modules` | `ragctl setup`（或 `cd web && npm install`） |
| `backend/` 或 `web/` 为空 | 仓库未完整克隆 | `ragctl setup` |
| 图谱查询失败（搜索正常） | Neo4j 未运行 | `ragctl start neo4j`（需要 Docker） |
| BGE 模型下载慢/失败 | 到 HuggingFace 网络问题 | 设 `HF_ENDPOINT=https://huggingface.co` |
| 端口被占用 | 上一个服务仍在运行 | `ragctl down` 然后 `ragctl up` |
| 技能未出现在 `/skills` | 不在项目目录（方式 C） | `cd rag-knowledge` 并重启 Claude Code |
| `ragctl` 全局找不到 | `ragctl install` 被跳过 | 在项目根目录运行 `ragctl install` |

<details>
<summary><b>❓ 常见问题</b></summary>

<details>
<summary><b>真的不开终端窗口吗？</b></summary>

是的。已验证：Windows 上 `windowsHide` + 直接二进制启动（无 `cmd.exe` 包装）；POSIX 上 `start_new_session`。
</details>

<details>
<summary><b>dev 和 prod 有什么区别？</b></summary>

端口和配置。dev：后端 `8765` / 前端 `6789`。prod：后端 `8001` / 前端 `3000`。用 `--appmode prod` 切换。两者完全静默。
</details>

<details>
<summary><b>数据存在哪里？</b></summary>

全部本地 — `$TREE_STORAGE_PATH`（KB 文件）+ Neo4j（图谱）+ ChromaDB（向量）。无云端，无遥测。
</details>

<details>
<summary><b>需要 Docker 吗？</b></summary>

仅 Neo4j 知识图谱需要。解析、搜索、经验功能全部不需要。
</details>

<details>
<summary><b>不用 Claude Code 能用吗？</b></summary>

可以。Web UI（`http://localhost:6789`）功能完整，任何 MCP 客户端都能调用 76 个工具。
</details>

</details>

---

## 📁 项目结构

```
rag-knowledge/
├── backend/              ← FastAPI + MinerU OCR 引擎
├── web/                  ← Nuxt 3 + Ant Design Vue（含 Claude Chat）
├── kb-mcp/               ← MCP 服务端 — 76 个工具
├── command/              ← ragctl CLI (Node.js, js-yaml)
├── src-tauri/            ← Tauri v2 桌面应用 (Rust)
├── .claude/              ← Claude Code 技能 (14) + Archival Agent
├── .omp/                 ← OMP 原生 Agent、命令、MCP 配置
├── .claude-plugin/       ← 插件 + 市场清单
├── scripts/              ← GPU 检测、技能验证、OMP 安装器
├── docs/                 ← 架构、论文框架、测试方案
├── .mcp.json             ← kb-mcp MCP 自动连接 (Claude Code 本地项目)
├── config.yml            ← 中央配置（唯一真相源）
├── docker-compose.yml    ← Neo4j 容器
├── .env.example          ← 环境变量模板
├── VERSION               ← 语义版本号
├── ragctl / ragctl.bat   ← CLI 入口 (Linux·macOS / Windows)
├── start.bat / start.sh  ← 静默启动器（委托给 ragctl up）
└── README.md
```

---

## 🔧 技术栈

<table>
<tr>
<td width="50%" valign="top">

| 组件 | 技术 |
|------|------|
| **后端** | Python 3.12 · FastAPI · MinerU OCR · ChromaDB |
| **前端** | TypeScript · Nuxt 3 · Ant Design Vue |
| **Claude Chat** | Vue 3 · Claude Agent SDK · SQLite |
| **MCP 服务** | Python · FastMCP · httpx |

</td>
<td width="50%" valign="top">

| 组件 | 技术 |
|------|------|
| **CLI** | Node.js · js-yaml |
| **桌面** | Rust · Tauri v2 |
| **图谱** | Neo4j 5.20 (Docker) |
| **嵌入** | BGE-M3 (1024维) · sentence-transformers |

</td>
</tr>
</table>

---

## 📄 许可证

MIT © [kingdol](https://github.com/kingdol666)

---

<div align="center">

<sub>使用</sub>
<a href="https://fastapi.tiangolo.com/">FastAPI</a>
<sub>·</sub>
<a href="https://nuxt.com/">Nuxt 3</a>
<sub>·</sub>
<a href="https://neo4j.com/">Neo4j</a>
<sub>·</sub>
<a href="https://www.chromadb.com/">ChromaDB</a>
<sub>·</sub>
<a href="https://modelcontextprotocol.io/">MCP</a>
<sub>·</sub>
<a href="https://mineru.net/">MinerU</a>
<sub> 构建</sub>

<br><br>

<sub>⭐ 如果这个项目对你有帮助，请给个 Star！</sub>

</div>
