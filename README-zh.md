<div align="center">
<img src="./docs/images/readme-hero.svg" alt="QDCVR — 可部署的知识库管理平台：基于内容的组织与内容核验的检索" width="100%" />

<br><br>

<a href="./README.md">English</a> &nbsp;·&nbsp; <b>简体中文</b>

<br><br>

<a href="#快速开始"><img src="https://img.shields.io/badge/快速开始-3_条命令-B24422?style=for-the-badge" alt="快速开始" /></a>
<a href="#mcp-工具"><img src="https://img.shields.io/badge/kb_*_MCP_工具-41_个-2E5D7F?style=for-the-badge" alt="41 个 kb_* MCP 工具" /></a>
<a href="#工作原理"><img src="https://img.shields.io/badge/检索协议-QDCVR_v2-B24422?style=for-the-badge" alt="QDCVR" /></a>
<a href="#publications"><img src="https://img.shields.io/badge/CIKM_%2726_Demo-论文-9E7A38?style=for-the-badge" alt="CIKM Demo 论文" /></a>

<br>

<img src="https://img.shields.io/badge/平台-Windows_·_Linux_·_macOS-334155?style=flat-square" alt="平台" />
<img src="https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.12" />
<img src="https://img.shields.io/badge/Node.js-≥18-339933?style=flat-square&logo=nodedotjs&logoColor=white" alt="Node 18+" />
<img src="https://img.shields.io/badge/许可证-MIT-3D6E3D?style=flat-square" alt="MIT" />
<a href="https://github.com/kingdol666/rag-knowledge/stargazers"><img src="https://img.shields.io/github/stars/kingdol666/rag-knowledge?style=flat-square&color=C49846" alt="Stars" /></a>
<a href="https://github.com/kingdol666/rag-knowledge/releases"><img src="https://img.shields.io/github/v/release/kingdol666/rag-knowledge?style=flat-square&color=9E7A38&label=release" alt="Release" /></a>

</div>

---

## 这是什么

一个自托管平台：把一个装满 PDF、Office 文档和扫描件的文件夹，变成 **AI Agent 真正可以信赖作答的知识库**——按文档*说了什么*来组织，而不是按它躺在哪个文件夹；并以四种方式对外提供能力：Web 界面、HTTP API、命令行，以及任何支持 MCP 的 Agent 都能驱动的 MCP 工具。

检索层是最有意思的部分。多数 RAG 栈按向量相似度排序然后祈祷。这一个运行一套查询协议——**QDCVR（Query-Driven Content-Verified Retrieval，查询驱动·内容核验检索）**——**真正阅读候选文档，并按一套可解释的 0–8 内容评分细则打分**，门控失败升级到图书管理员兜底，证据不足时返回明确的"未找到"报告而不是编造答案：

> **向量负责快，内容负责准。**
> 一份余弦相似度 **0.95** 的文档，若正文评分 **≤ 4**，会被**直接丢弃**——不是降权，是丢弃。

这就是我们 CIKM '26 Demo 论文所演示的系统：*QDCVR: A Deployable Knowledge-Base Management Platform with Content-Based Organization and Content-Verified Retrieval*（[论文 + 演示视频](#publications)）。

<br>

<div align="center">
<img src="./docs/images/readme-pipeline.svg" alt="入库管线：文件 → MinerU 解析 → 按内容路由的门类知识库 → 索引 → QDCVR 检索 → 核验后的回答" width="100%" />
</div>

---

## 目录

| | |
|---|---|
| [**界面截图**](#界面截图) | 浅色/深色、桌面/移动端的真实界面 |
| [**工作原理**](#工作原理) | QDCVR v2 协议与 0–8 评分细则 |
| [**Agent 对话，任意 Harness**](#agent-对话任意-harness) | 14 个 Harness、按 Harness 选模型、统一 HITL |
| [**系统架构**](#系统架构) | 服务、端口、存储引擎 |
| [**快速开始**](#快速开始) | 克隆 → 安装 → 启动 |
| [**四种使用方式**](#四种使用方式) | Web · HTTP · CLI · MCP |
| [**MCP 工具**](#mcp-工具) | 94 个工具中的 41 个 `kb_*` 领域工具，按类分组 |
| [**外部 HTTP API**](#外部-http-api) | 不需要 Agent 也能调用 |
| [**基准测评**](#基准测评) | 可复现流水线与全部数字 |
| [**适用范围与非目标**](#适用范围与非目标) | 本系统*不*做什么 |

---

## 界面截图

以下全部是运行中应用的真实截图，存放在 [`docs/screenshots/app/`](./docs/screenshots/app/)，并附带一份[清单文件](./docs/screenshots/app/MANIFEST.json)，记录每张图的原始尺寸与编码参数。没有效果图。

### 知识库管理

增删改查、跨库移动、标签管理、内容就地编辑。

<div align="center">
<img src="./docs/screenshots/app/desktop-knowledge-base.jpg" alt="知识库管理" width="100%" />
</div>

<details>
<summary><b>更多界面 —— 点击展开</b></summary>

<br>

**QDCVR 检索** —— 向量优先检索、范围控制，以及一条真实反映语料内容的标签栏。

<div align="center">
<img src="./docs/screenshots/app/desktop-knowledge-search.jpg" alt="QDCVR 检索界面" width="100%" />
</div>

**知识图谱** —— 基于 Neo4j 的文档关系、跨库桥接与路径发现。

<div align="center">
<img src="./docs/screenshots/app/desktop-knowledge-graph.jpg" alt="知识图谱浏览器" width="100%" />
</div>

**SOUL 人格工作室** —— 蒸馏人格、训练人格，并用该人格检索知识库。

<div align="center">
<img src="./docs/screenshots/app/desktop-soul.jpg" alt="SOUL 人格工作室" width="100%" />
</div>

**文件系统** —— 由 `.tree-fs.json` 支撑的权威目录树。

<div align="center">
<img src="./docs/screenshots/app/desktop-file-system.jpg" alt="文件系统目录树" width="100%" />
</div>

**Agent 对话** —— 在应用内驱动 14 种 Agent Harness 操作知识库，支持按 Harness 选择模型与统一的人工审批（HITL）。

<div align="center">
<img src="./docs/screenshots/app/desktop-claude-chat.jpg" alt="Agent 对话" width="100%" />
</div>

**系统设置与 API Token** —— 实时端口/绑定信息横幅、带过期时间的范围化令牌。

<div align="center">
<img src="./docs/screenshots/app/desktop-settings.jpg" alt="系统设置" width="49%" />
<img src="./docs/screenshots/app/desktop-tokens.jpg" alt="API Token 管理" width="49%" />
</div>

</details>

### 深色主题

每个界面都有真正的深色主题——不是把浅色反相了事。

<div align="center">
<img src="./docs/screenshots/app/dark-desktop-home.jpg" alt="深色首页" width="100%" />
</div>

<details>
<summary><b>更多深色界面</b></summary>

<br>

<div align="center">
<img src="./docs/screenshots/app/dark-desktop-knowledge-search.jpg" alt="深色检索" width="49%" />
<img src="./docs/screenshots/app/dark-desktop-knowledge-graph.jpg" alt="深色图谱" width="49%" />
<br><br>
<img src="./docs/screenshots/app/dark-desktop-knowledge-base.jpg" alt="深色知识库" width="49%" />
<img src="./docs/screenshots/app/dark-desktop-soul.jpg" alt="深色 SOUL" width="49%" />
</div>

</details>

### 移动端

布局基于容器查询：响应的是自身内容区域的宽度，而不仅是视口。侧栏变抽屉、表格变卡片、触控目标提升到 44 px 下限。

<div align="center">
<img src="./docs/screenshots/app/mobile-home.jpg" alt="移动端首页" width="24%" />
<img src="./docs/screenshots/app/mobile-knowledge-base.jpg" alt="移动端知识库" width="24%" />
<img src="./docs/screenshots/app/mobile-knowledge-search.jpg" alt="移动端检索" width="24%" />
<img src="./docs/screenshots/app/mobile-knowledge-graph.jpg" alt="移动端图谱" width="24%" />
<br>
<img src="./docs/screenshots/app/mobile-soul.jpg" alt="移动端 SOUL" width="24%" />
<img src="./docs/screenshots/app/mobile-tokens.jpg" alt="移动端 Token" width="24%" />
<img src="./docs/screenshots/app/dark-mobile-home.jpg" alt="深色移动端首页" width="24%" />
<img src="./docs/screenshots/app/dark-mobile-knowledge-base.jpg" alt="深色移动端知识库" width="24%" />
</div>

---

## 工作原理

`QDCVR`——**查询驱动·内容核验检索**。每次查询按顺序走一遍协议：

```
查询
  │
  ├─ 0 · 查询改写               模糊提问 → 适合检索的查询
  │
  ├─ 1 · 向量优先召回           在路由到的门类库上执行 kb_search_vector；
  │                             balance_kbs 防止一个大库垄断候选池
  │
  ├─ 2 · ⭐ 内容门控（0–8）     Agent 真正阅读候选正文并打分：
  │                             主题 0–3 · 场景 0–3 · 证据 0–2
  │                             得分 ≥ 6 → 快速通过，直接作答
  │                             得分 = 5 → 留作后备，升级处理
  │                             得分 ≤ 4 → 丢弃
  │
  ├─ 3 · 图书管理员兜底         门控失败？在路由库内定向再检索 + 深度
  │                             续读——基准中唯一一次门控失败
  │                             就是在这里被挽救的
  │
  ├─ 4 · 未找到契约             全部失败？给出明确的"未找到"报告
  │                             ——绝不编造
  │
  └─ 5 · 回答 + 引用            五段式格式：检索路径 · 回答 · 来源 ·
                                置信度 · 声明的盲区
```

<details>
<summary><b>0–8 内容评分细则</b></summary>

<br>

| 得分 | 含义 | 处理 |
|:---:|---|---|
| **0–2** | 离题，或文档讲的完全是另一回事 | **丢弃** |
| **3–4** | 沾边——不相关文档里埋了一句相关的话 | **丢弃** |
| **5** | 主题对口，但所问的具体内容不在已读窗口内 | 留作**后备** → **图书管理员升级**（定向再检索 + 续读） |
| **6–7** | 主题对口，能部分深度地回答问题 | 保留，快速通过 |
| **8** | 从读到的正文直接回答问题 | 保留，快速通过 |

这套细则的关键在于：它在召回**之后**、通过**阅读内容**来打分，所以高的余弦分买不到任何好处。而且门控失败时，协议不会默默返回"最不坏的那个"——它会再去找，找不到就明说。

</details>

---

## Agent 对话，任意 Harness

内置对话页通过同一层适配器对接 **14 种 Agent Harness**——Claude Code、OMP、Codex CLI、Gemini CLI、Copilot CLI、Cursor CLI、DeepSeek Harness、Hermes Agent、OpenCode、Crush、Goose、Qwen Code、pi，外加一个用于 CI 的进程内 mock：

- **按 Harness 选择模型**——每种 Harness 暴露自己真实的模型目录（`omp models --json`、`opencode models`、ACP `configOptions`……）；下拉选择，或输入该 Harness 接受的任意模型名。
- **按 Harness 的思考强度**——只提供各 Harness 原生支持的档位（`--thinking`、`model_reasoning_effort`、`--effort`、ACP `reasoning_effort`），绝不虚构。
- **按 Harness 的作业权限**——沿用各 Harness 自己的语义：Claude 的 permissionMode、Codex 的沙箱档位、ACP 的 `request_permission` 等。
- **统一人工在环（HITL）**——所有审批请求（Claude 的 `canUseTool`、ACP 的 `session/request_permission`）都汇聚为同一个聊天内审批弹窗；允许、拒绝，或在 Harness 给出的选项中选择。流会阻塞直到你做出决定。
- **可用性是探测出来的，不是猜的**——平台在启动时和按需探测每个 Harness（可执行文件、版本、凭据）；不可用的在界面中置灰并给出原因，每个 Harness 都有一键诊断和可选的真实往返自测。

---

## 系统架构

<div align="center">
<img src="./docs/images/readme-architecture.svg" alt="架构：客户端、MCP 工具层、服务、存储" width="100%" />
</div>

三个服务加一层工具，全部从同一份 `config.yml` 读取端口与路径：

| 端口 | 服务 | 职责 |
|---:|---|---|
| `6789` | Nuxt 3 | UI + 服务端代理。浏览器不直接调用后端（无 CORS 暴露面）。 |
| `8770` | FastAPI | 解析调度、向量、图谱、经验、SOUL。端口被占用时拒绝启动。 |
| *临时* | MinerU 解析 | 双模式：配置了远程 mineru-api 时优先远程（启动探测），否则本地引擎在空闲端口上以受管子进程方式自启动。 |
| `7687` | Neo4j | 文档图谱、跨库桥接。 |
| — | ChromaDB | 分块向量，每个知识库一个集合。 |

**读写不对称是刻意设计：**写入走 HTTP API，保证原子与可审计；读取直接走磁盘上的 `.tree-fs.json` 与 `.knowledge-base.yml`，检索对后端零负载。

> **说明：**两份 README 记录的是默认 `8770`/`6789` 组合。如果你在跑多个实例，可能看到第二个后端占用其他端口（例如 `8771`）——请检查 `config.yml`、`.env`（`BACKEND_PORT`）以及设置页横幅，横幅显示的是运行值。

---

## 快速开始

```bash
# 1 · 克隆
git clone https://github.com/kingdol666/rag-knowledge.git
cd rag-knowledge

# 2 · 安装全部依赖 + 模型（幂等）
./ragctl setup          # Windows: ragctl setup

# 3 · 一键启动——静默，无终端窗口
./ragctl up             # Windows: ragctl up

# 检查
./ragctl status
```

然后打开 **http://localhost:6789**。

`ragctl` 是所有操作的唯一入口——服务、模型、配置、健康检查、知识库、人格与 Harness。

<details>
<summary><b>全部 <code>ragctl</code> 命令</b></summary>

<br>

| 分组 | 命令 |
|---|---|
| **生命周期** | `setup` `up` `down` `start` `stop` `restart` `status` `logs` |
| **资产** | `install` `model` `mineru-model` `clean` `backup` `restore` |
| **界面** | `desktop`（别名 `ui`） |
| **知识** | `meditation` `soul`（别名 `persona`） `harness` |
| **维护** | `check` `deps` `version` `update` |

`soul` 子命令：`distill` `list` `status` `init` `learn` `learn-all` `train-rl` `evaluate` `review-cognition` `harness` `ask` `router` `review` `reflect` `export` `train` `checkpoint`。

</details>

### 环境要求

| | 要求 | 原因 |
|---|---|---|
| **Python** | 3.12（`>=3.12,<3.13`） | MinerU 与后端锁定在此范围 |
| **Node.js** | ≥ 18 | Nuxt 3 |
| **uv** | 任意较新版本 | Python 环境管理 |
| **磁盘** | 数 GB | MinerU 模型与你的语料 |
| **可选** | Neo4j `7687` | 图谱功能在缺失时优雅降级 |

---

## 四种使用方式

### 1 · Web 界面

十一个页面：仪表盘、文件系统、知识库管理、QDCVR 检索、图谱浏览器、SOUL 人格工作室、Agent 对话、Harness 总览、系统设置、API Token、登录。浅色深色俱全，桌面到手机自适应。

### 2 · HTTP API

以下都不需要 Agent 或 MCP。见[外部 HTTP API](#外部-http-api)。

### 3 · 命令行

```bash
./ragctl status                 # 服务健康
```

### 4 · MCP —— 任意 Agent

MCP 服务器由你的客户端通过仓库根目录的 `.mcp.json` 以 stdio 启动。Claude Code、Cursor 或任何支持 MCP 的客户端都可以；无需重启平台。

```jsonc
// .mcp.json（仓库已内置）
{
  "mcpServers": {
    "kb-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "kb-mcp", "python", "server.py"]
    }
  }
}
```

然后直接对话——*"PET 薄膜双轴拉伸方面我们有什么资料？"*——Agent 会经由 knowledgebase 技能路由，质量门控不可绕过。

---

## MCP 工具

全部工具在 `kb-mcp/server.py` 中以 FastMCP 注册：**总计 94 个，其中 41 个是 `kb_*` 知识库工具**——也就是 CIKM Demo 论文所演示的领域面。下面的分组是穷尽且互斥的。

**`kb_*` 知识库工具 —— 41 个**（论文 Demo 驱动的部分）：

| 分组 | 数量 | 覆盖 |
|---|:---:|---|
| **知识图谱** | 11 | graph-search · stats · 单文档关系 · related · 库概览 · build · 跨库文档 · paths · 中心文档 · 删除文档/库 |
| **文档 CRUD** | 9 | read · create · update-meta · update-content · delete · batch-delete · move · save-parsed · get-documents |
| **向量 / 索引** | 6 | index-document · batch-index · reindex · cleanup-orphans · find-duplicates · task-status |
| **知识库 CRUD** | 4 | list · create · update · delete |
| **检索** | 4 | search（元数据）· vector · two-stage · stats |
| **标签** | 4 | list · update · get-by-tag · cleanup |
| | **41** | |

**平台工具 —— 53 个**（平台其余能力）：

| 分组 | 数量 | 覆盖 |
|---|:---:|---|
| **经验** | 26 | E0–E12 完整生命周期 · search-global · search-smart · rerank · extract · drafts（列表/读取/批准/驳回）· stale-check · sync · dashboard · decay · meditation（run/status/history/config） |
| **SOUL 人格** | 20 | init · list · status · learn · learn-all · train-rl · evaluate · calibrate · cognition drafts · review · reflect · checkpoint · rollback · ask · qdcvr-ask · router · export (LoRA) |
| **项目生命周期** | 4 | status · start · update · backend-status |
| **文件系统** | 3 | get-tree · get-children · upload-file |
| | **53** | |

两条值得知道的设计规则：

- **解析工具不阻塞。**它们立即返回 `task_id`；用 `parse_task_status` 轮询。解析永远不会卡住 Agent 的一轮对话。
- **长任务同样返回任务号。**`kb_reindex`、`kb_graph_build` 与 `experience_meditation_run` 都返回任务号，而不是挂住连接。

<details>
<summary><b>Agent 技能</b></summary>

<br>

`knowledgebase` 分发技能把自然语言请求（中英文皆可）路由到对应子技能（ingest、search、manage、organize、update、verify、graph、experience……），并委派给 Archival 子 Agent 执行，保证质量门控不可绕过。QDCVR v2 检索技能与基准测评中 Track A 执行的是同一套协议。

</details>

---

## 外部 HTTP API

鉴权**默认开启**（`server.auth.enabled: true`）。除 `/api/v1/health` 与 `/api/v1/auth/*` 外，所有端点都需要 Bearer Token。交互式文档见后端 **`/docs`**；生成的 OpenAPI 对非公开操作标注了 `bearerAuth`。

```bash
# 0 · 获取 token（全新安装请先注册）
TOKEN=$(curl -s -X POST http://localhost:6789/api/auth/login \
  -H 'content-type: application/json' \
  -d '{"username":"you","password":"your-password"}' | jq -r .token)

# 1 · 建一个知识库
curl -s -X POST http://localhost:6789/api/kb/create \
  -H "Authorization: Bearer $TOKEN" -H 'content-type: application/json' \
  -d '{"name":"engineering-notes","description":"内部工程笔记"}'

# 2 · 写入文档（kbId 与 kb_id 都接受；snake_case 别名自动归一）
curl -s -X POST http://localhost:6789/api/kb/documents/create \
  -H "Authorization: Bearer $TOKEN" -H 'content-type: application/json' \
  -d '{"kbId":"<kbId>","name":"pump-failure.md","content":"# 泵故障\n\n轴承温度超过 90°C……"}'

# 3 · 向量检索（QDCVR Phase 1 的召回工具）
curl -s -X POST http://localhost:6789/api/v1/search/vector \
  -H "Authorization: Bearer $TOKEN" -H 'content-type: application/json' \
  -d '{"query":"轴承温度上限","limit":5}'

# 健康检查无需 token
curl -s http://localhost:8770/api/v1/health
```

限流默认 **600 次 / 60 秒**。

<details>
<summary><b>端点地图</b></summary>

<br>

| 领域 | 基础路径 |
|---|---|
| 鉴权 | `/api/v1/auth/{register,login,verify}` · `/api/auth/*`（Web 代理） |
| 知识库 | `/api/kb/{create,catalog,documents}` |
| 检索 | `/api/v1/search/{two-stage,vector}` |
| Harness | `/api/v1/meditation/harnesses`（含按引擎的 models / diagnostics / diagnose） |
| 经验 | `/api/v1/experience/*` |
| SOUL | `/api/v1/soul/*` |
| 图谱 | `/api/v1/graph/*` |
| 解析 | `/api/v1/parse/*` |
| MinerU | `/api/v1/mineru/{status,probe}` |
| 健康 | `/api/v1/health`（公开） |

以在线 OpenAPI 文档为准。

</details>

---

## 配置

一个文件。仓库根目录的 `config.yml` 是端口与路径的唯一事实源，后端、Web 代理与 MCP 服务器都读它。

```yaml
server:
  dev:
    backend_port: 8770
    frontend_port: 6789
    backend_url: "http://localhost:8770"
  prod:
    backend_port: 8001
    frontend_port: 3000
    backend_url: "http://localhost:8001"
```

优先级：`BACKEND_PORT` 环境变量 → `config.yml` → 代码默认。`APP_MODE=dev|prod` 选择对应段。代码里没有任何硬编码的端口或路径。

> 在 `APP_MODE=dev` 下修改 `config.yml` 会触发热重载。长会话建议 `APP_MODE=prod`，避免日志/数据库写入引发重载风暴。

---

## 存储模型

```
web/storage/tree-file-system/
├── .tree-fs.json                 # L1 · 全局权威目录索引
└── {知识库}/
    ├── .knowledge-base.yml       # L2 · 每库文档索引（名称、标签、元数据）
    ├── {文档}.md                 # L3 · 解析/上传的 markdown 正文
    └── images/                   #      解析时抽取的图片
```

| 层 | 存储 | 内容 |
|:---:|---|---|
| **L1** | `.tree-fs.json` | 全部文件夹与文件及元数据 |
| **L2** | `.knowledge-base.yml` | 每库检索索引——检索直接读取 |
| **L3** | 磁盘 `.md` | 正文本身 |
| **L4** | ChromaDB | 分块向量，每库一个集合 |
| **L5** | Neo4j | 文档、标签、知识库节点及类型化关系 |

> 只有对某个知识库执行过图谱构建，L5 才会有数据。全新安装时图谱为空，图谱页面显示零节点是正常现象——标签节点尤其要等对打标文档跑过图谱构建才会出现。

---

## 基准测评

所有测评从**一条可复现流水线**出发：[`benchmark-suite/PIPELINE.md`](./benchmark-suite/PIPELINE.md) —— 下载 50 篇真实 arXiv 论文（26 个领域）→ 经生产链 MinerU 解析 → 按内容路由进 5 个门类库（该步是 Agent 判断件，依据逐篇导出的摘要）→ 每个 part 打内容标签 → 建三个复刻分块库（固定 800 字 / 结构化 / 段落）→ 重启 → 跑 10 题脚本化回归 → 同样 10 题在三条轨道上作答（QDCVR v2 skill 流程 vs 裸 Agent vs dense 基线）→ 生成报告。**一条红线：严禁编造——判断工件必须能追溯至导出的证据。**

**本轮提交的数字**（均可追溯至 `benchmark-suite/results/`）：

| 阶段 | 结果 |
|---|---|
| 解析（MinerU 生产链） | 50/50 篇 · 380 万字符 |
| 内容路由 + 验证 | 50/50 进入 5 个门类库（165 个入库文档） |
| 内容标签 | 165/165 part 打标，0 失败 |
| 复刻库 | 2 366 / 1 385 / 10 219 chunks |
| 脚本化 10 题回归（向量优先） | **9/10 = 90%** —— 唯一未过是长文分块窗口未含核验词组（`doc_hit=true`），跨运行一致 |
| **实答三轨**，同样 10 题 | **A · QDCVR v2：10/10 命中所问**（门控 6–8/8，一次图书管理员挽救，top-1 金标召回 10/10，向量召回均 ≈1.6 s + 读取 0.8 s）· **B · 裸 Agent：金标 10/10**，溯源止步文件名，均时 78.8 s · **C · dense 基线：内容匹配**，2/10 弃答，无来源路径，均时 12.2 s |
| 诚实失败探针 | 3 个语料外问题 → 全部给出明确"未找到"报告，零编造 |

CIKM Demo 论文的配图（`paper_demo/figures/`）即由这些工件生成。

> **关于已撤下的数字。**本 README 早期版本引用过标准语料的 IR 式指标（`Hit@k`、`nDCG@10` 等），更早还引用过 `benchmark-web/backend/results/` 下一个仓库内**没有生成脚本**的较大基准。IR 语料在 2026-09 的基准重构中退役（标准语料衡量的是排序，不是知识库管理）；被替代的脚本与语料归档于 `.bench_backup_20260917/`。凡不能由仓库内脚本重新生成的数字，一律视为不可用。

<sub>数字最后核对于 **2026-09-19** 的运行实例：8 个知识库 · 门类库 165 个入库文档 · 94 个 MCP 工具（41 个 `kb_*`）· 286 项后端测试通过。</sub>

---

## Publications

- **设计版 README 展示页** —— 本 README 的艺术化单页呈现：[`docs/readme-showcase/index.html`](./docs/readme-showcase/index.html)（截图：[`README-showcase.png`](./docs/readme-showcase/README-showcase.png)）。
- **QDCVR: A Deployable Knowledge-Base Management Platform with Content-Based Organization and Content-Verified Retrieval** —— CIKM '26 Demo 投稿。正文：[`paper_demo/tex/`](./paper_demo/tex/)，配图：[`paper_demo/figures/`](./paper_demo/figures/)，演示视频：[paper_demo/video/qdcvr-demo.mp4](./paper_demo/video/qdcvr-demo.mp4)。

---

## 适用范围与非目标

明确说明这**不是**什么：

- **不是托管服务。**设计即自托管；这里没有多租户隔离的故事。
- **不是微调平台。**SOUL 的 LoRA 导出是一条*导出*路径，不是能与专职训练竞争的训练管线。
- **不是向量检索的替代品。**当答案就在一个 Agent 能整个读完的小语料里时，裸 Agent 不需要索引就能作答；本平台的价值在大规模管理——按内容的组织、逐 part 标签、图谱、完整性，以及溯源到文档 part 与章节的回答。
- **在 Windows 上没有 Python 3.12 不是开箱即用。**依赖锁定是真实的；3.13 暂不支持。
- **不是开箱即满的图谱。**L5 由显式的按库图谱构建填充。

---

## 参与贡献

欢迎 Issue 与 PR。提交 PR 前：

```bash
cd backend && uv run pytest          # 后端单元测试（集成测试需 --run-integration）
cd web && npx nuxt build             # 类型检查 + 构建
node scripts/validate_skills.cjs     # 跨技能一致性（8 项检查）
```

约定：端口与路径一律来自 `config.yml`；Python 使用类型标注与 `logging`，不用 `print`；`httpx` 调用传 `trust_env=False`，防止本机代理劫持；解析工具永不阻塞。

---

## 许可证

MIT —— 见 [LICENSE](./LICENSE)。

<div align="center">
<br>
<sub>一个研究内容核验检索的科研平台。<br>
界面截图均为运行中应用的真实截图；基准数字均可追溯至已提交的工件，否则不予声明。</sub>
</div>
