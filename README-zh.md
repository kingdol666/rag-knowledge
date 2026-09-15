<div align="center">
<img src="./docs/images/readme-hero.svg" alt="RAG Knowledge Platform — 企业级文档智能与 Agentic 知识库" width="100%" />

<br><br>

<a href="./README.md">English</a> &nbsp;·&nbsp; <b>简体中文</b>

<br><br>

<a href="#-快速开始"><img src="https://img.shields.io/badge/快速开始-3_条命令-B24422?style=for-the-badge" alt="快速开始" /></a>
<a href="#-系统架构"><img src="https://img.shields.io/badge/技术栈-FastAPI_·_Nuxt_3_·_MCP-2E5D7F?style=for-the-badge" alt="技术栈" /></a>
<a href="#-94-个-mcp-工具"><img src="https://img.shields.io/badge/MCP_工具-94_个-9E7A38?style=for-the-badge" alt="94 个 MCP 工具" /></a>
<a href="#-工作原理"><img src="https://img.shields.io/badge/检索方法-QDCVR-B24422?style=for-the-badge" alt="QDCVR" /></a>

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

一个可自托管的知识库平台。它把一堆 PDF、Office 文档和扫描件，变成**一个 AI Agent 可以真正被信任去回答问题的知识库**，并通过四种方式暴露出来：Web 界面、HTTP API、命令行，以及 94 个 MCP 工具——任何支持 MCP 的 Agent 都能直接驱动它。

真正有意思的是检索层。大多数 RAG 方案按向量相似度排序，然后祈祷结果是对的。这个平台会**实际读取候选文档，用一套独立的 0–8 内容评分量表给它打分**，并把不及格的直接丢掉：

> **向量快，内容准。**
> 一个余弦相似度高达 **0.95**、但内容评分 **≤ 4** 的文档，会被**丢弃**——不是降权，是丢弃。

<br>

<div align="center">
<img src="./docs/images/readme-pipeline.svg" alt="入库流水线：文件 → MinerU OCR → 知识库 → 索引 → QDCVR 检索 → 已核验答案" width="100%" />
</div>

---

## 目录

| | |
|---|---|
| [**界面截图**](#界面截图) | 浅色与深色主题下的真实界面 |
| [**工作原理**](#工作原理) | 检索流水线与 0–8 评分量表 |
| [**系统架构**](#系统架构) | 服务、端口、存储引擎 |
| [**快速开始**](#快速开始) | 克隆 → 安装 → 启动 |
| [**四种使用方式**](#四种使用方式) | Web 界面 · HTTP · CLI · MCP |
| [**94 个 MCP 工具**](#94-个-mcp-工具) | 按类别完整清单 |
| [**外部 HTTP API**](#外部-http-api) | 不依赖 Agent，任何系统都能调用 |
| [**验证数据**](#验证数据) | 哪些数字被实测过，怎么测的 |
| [**适用范围与非目标**](#适用范围与非目标) | 这个项目**不做**什么 |

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

**QDCVR 检索** —— 三种策略、范围控制，以及一条真实反映语料内容的标签栏。

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

**Agent 对话** —— 在应用内直接驱动编程 Agent 操作知识库。

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
<img src="./docs/screenshots/app/dark-desktop-home.jpg" alt="深色模式首页" width="100%" />
</div>

<details>
<summary><b>更多深色主题界面</b></summary>

<br>

<div align="center">
<img src="./docs/screenshots/app/dark-desktop-knowledge-search.jpg" alt="深色检索" width="49%" />
<img src="./docs/screenshots/app/dark-desktop-knowledge-graph.jpg" alt="深色图谱" width="49%" />
<br><br>
<img src="./docs/screenshots/app/dark-desktop-knowledge-base.jpg" alt="深色知识库" width="49%" />
<img src="./docs/screenshots/app/dark-desktop-soul.jpg" alt="深色 SOUL 工作室" width="49%" />
</div>

</details>

### 移动端

布局基于容器查询（container query）系统，响应的是**自身内容区的宽度**，而不只是视口宽度。侧边栏变为抽屉，表格变为卡片，触摸目标扩展至 44 px 下限。

<div align="center">
<img src="./docs/screenshots/app/mobile-home.jpg" alt="移动端首页" width="24%" />
<img src="./docs/screenshots/app/mobile-knowledge-base.jpg" alt="移动端知识库" width="24%" />
<img src="./docs/screenshots/app/mobile-knowledge-search.jpg" alt="移动端检索" width="24%" />
<img src="./docs/screenshots/app/mobile-knowledge-graph.jpg" alt="移动端图谱" width="24%" />
<br>
<img src="./docs/screenshots/app/mobile-soul.jpg" alt="移动端 SOUL 工作室" width="24%" />
<img src="./docs/screenshots/app/mobile-tokens.jpg" alt="移动端 API Token" width="24%" />
<img src="./docs/screenshots/app/dark-mobile-home.jpg" alt="移动端深色首页" width="24%" />
<img src="./docs/screenshots/app/dark-mobile-knowledge-base.jpg" alt="移动端深色知识库" width="24%" />
</div>

---

## 工作原理

`QDCVR` —— **Query-Driven, Content-Verified Retrieval**（查询驱动 · 内容验证检索）。共七个阶段，严格按序执行：

```
用户查询
  │
  ├─ 0 · 意图识别                 运维类 / 事实类 / 探索类
  │
  ├─ 1 · 知识库选择               对目录做 Agentic 扫描
  │                                balance_kbs 护栏防止单一大库垄断结果
  │
  ├─ 2 · 多阶段召回               BM25 ──▶ 向量 ──▶ 标签语义 ──▶ 图谱
  │                                每一阶段都是「召回」阶段，不是排序阶段
  │
  ├─ 3 · ⭐ 内容验证              读取候选文档，按 0–8 打分
  │                                得分 < 6 → 触发标签+描述扩展轮
  │                                得分 ≤ 4 → 硬性丢弃
  │
  ├─ 4 · 交叉验证                 去重、跨库合并、排序融合
  │
  ├─ 5 · 可信度分级               P0 已验证 · P1 较可信 · P2 仅线索
  │                                盲区会被明确声明，绝不掩盖
  │
  └─ 6 · 答案与引用               每一条论断都链接到来源文档
```

<details>
<summary><b>0–8 内容评分量表</b></summary>

<br>

| 分数 | 含义 | 处理方式 |
|:---:|---|---|
| **0–2** | 跑题，或文档讲的完全是另一回事 | **丢弃** |
| **3–4** | 擦边——在无关文档里只有一句话相关 | **丢弃** |
| **5–6** | 部分相关——话题对，但缺少追问的具体细节 | 保留，触发一轮**扩展** |
| **7–8** | 直接回答该问题 | 保留，有资格进入 P0 |

这套量表的关键在于：它是在**召回之后**、且**通过阅读内容**来执行的。因此高余弦相似度不能为文档换来任何豁免。这正是分级有意义的原因——一个 P0 结果，同时通过了相似度筛选和内容判断两道关。

</details>

### 跨库盲区缓解

当一次常规两阶段检索返回的候选中，来自**少于两个**不同知识库时，系统会自动以三路并行召回重试，并交叉验证结果：

| 路径 | 策略 | 能捞回什么 |
|:---:|---|---|
| **A** | 对目录做 Agentic 知识库扫描 | 词表不一致导致词法索引漏掉的查询 |
| **B** | 两阶段 BM25 → 向量 | 标准的高精度路径 |
| **C** | 纯跨库向量检索 | 完全没有词法重叠的语义匹配 |

三路结果会被合并、去重，过短的假阳性片段会被降级（不足 50 字符的片段最高只能到 P2）。这直接针对一个典型失效模式：BM25 第一阶段召回悄悄把候选集收窄到只剩一个知识库。

---

## 系统架构

<div align="center">
<img src="./docs/images/readme-architecture.svg" alt="系统架构：客户端、MCP 工具层、服务层、存储层" width="100%" />
</div>

三个服务加一层工具层，端口与路径全部来自同一个 `config.yml`：

| 端口 | 服务 | 职责 |
|---:|---|---|
| `6789` | Nuxt 3 | 界面 + 服务端代理。浏览器从不直接调用后端（不暴露 CORS 面）。 |
| `8770` | FastAPI | 解析调度、向量、图谱、经验、SOUL。端口被占用时拒绝启动。 |
| *动态* | MinerU OCR | 自动挑一个空闲端口。作为受管子进程运行，随父进程退出。 |
| `7687` | Neo4j | 文档图谱、跨库桥接。 |
| — | ChromaDB | 分块向量，每个知识库一个 collection。 |

**读写分离是刻意设计的：** 写操作走 HTTP API，保证原子性与可审计；读操作直接读磁盘上的 `.tree-fs.json` 与 `.knowledge-base.yml`，因此检索对后端零负载。

> **说明：** 两份 README 记录的都是默认的 `8770`/`6789` 组合。如果你同时跑了多个实例，可能会看到第二个后端监听在别的端口（例如 `8771`）——请以 `config.yml` 和设置页顶部横幅显示的运行值为准。

---

## 快速开始

```bash
# 1 · 克隆仓库
git clone https://github.com/kingdol666/rag-knowledge.git
cd rag-knowledge

# 2 · 安装全部依赖与模型（可重复执行）
./ragctl setup          # Windows: ragctl setup

# 3 · 一键启动 —— 静默，无终端窗口弹出
./ragctl up             # Windows: ragctl up

# 检查状态
./ragctl status
```

然后打开 **http://localhost:6789**。

`ragctl` 是所有操作的统一入口——服务、模型、配置、健康检查、知识库、人格与 Agent Harness。

<details>
<summary><b><code>ragctl</code> 全部命令</b></summary>

<br>

| 分组 | 命令 |
|---|---|
| **生命周期** | `setup` `up` `down` `start` `stop` `restart` `status` `logs` |
| **资源管理** | `install` `model` `mineru-model` `clean` `backup` `restore` |
| **界面** | `desktop`（别名 `ui`） |
| **知识** | `meditation` `soul`（别名 `persona`） `harness` |
| **日常维护** | `check` `deps` `version` `update` |

`soul` 子命令：`distill` `list` `status` `init` `learn` `learn-all` `train-rl` `evaluate` `review-cognition` `harness` `ask` `router` `review` `reflect` `export` `train` `checkpoint`。

</details>

### 环境要求

| | 要求 | 原因 |
|---|---|---|
| **Python** | 3.12（`>=3.12,<3.13`） | MinerU 与后端锁定在此区间 |
| **Node.js** | ≥ 18 | Nuxt 3 |
| **uv** | 较新版本即可 | Python 环境管理 |
| **磁盘** | 数 GB | MinerU 模型加你的语料 |
| **可选** | `7687` 上的 Neo4j | 缺失时图谱功能会优雅降级 |

---

## 四种使用方式

### 1 · Web 界面

共十个页面：仪表盘、文件系统、知识库管理、QDCVR 检索、图谱浏览器、SOUL 人格工作室、Agent 对话、系统设置、API Token、登录。支持浅色/深色，从桌面到手机全尺寸适配。

### 2 · HTTP API

完全不需要 Agent 或 MCP。见[外部 HTTP API](#外部-http-api)。

### 3 · 命令行

```bash
./ragctl status                 # 服务健康状态
./ragctl logs backend -f        # 实时跟踪日志
./ragctl soul list              # 人格列表
./ragctl harness                # Agent Harness 可用性
./ragctl backup                 # 备份存储
```

### 4 · MCP —— 任意 Agent

MCP 服务器由你的客户端通过仓库根目录的 `.mcp.json` 以 stdio 方式拉起。Claude Code、Cursor 或任何支持 MCP 的客户端都可以，平台本身无需重启。

```jsonc
// .mcp.json（仓库中已包含）
{
  "mcpServers": {
    "kb-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "kb-mcp", "python", "server.py"]
    }
  }
}
```

然后直接用自然语言提问即可——*「关于 PET 薄膜双向拉伸我们有哪些资料？」*——Agent 会经由 knowledgebase 技能路由，并强制走完所有质量门控。

---

## 94 个 MCP 工具

所有工具都在 `kb-mcp/server.py` 中通过 FastMCP 注册。下表的分区是完备且互斥的。

| 类别 | 数量 | 覆盖内容 |
|---|:---:|---|
| **SOUL 人格** | 20 | init · list · status · learn · learn-all · train-rl · evaluate · calibrate · 认知草稿 · review · reflect · checkpoint · rollback · ask · qdcvr-ask · router · export（LoRA） |
| **经验库** | 26 | 完整 E0–E12 生命周期 · 全局检索 · 智能检索 · 重排 · 提取 · 草稿（列表/读取/审批/驳回）· 陈旧检查 · 同步 · 看板 · 衰减 · 冥想（运行/状态/历史/配置） |
| **知识图谱** | 11 | 图谱检索 · 统计 · 单文档关系 · 关联文档 · 库概览 · 构建 · 跨库文档 · 路径 · 中心文档 · 删除文档/库 |
| **文档 CRUD** | 9 | 读取 · 新建 · 改元数据 · 改内容 · 删除 · 批量删除 · 移动 · 保存解析结果 |
| **向量 / 索引** | 6 | 单文档索引 · 批量索引 · 重建索引 · 清理孤儿 · 查重 · 任务状态 |
| **知识库 CRUD** | 4 | 列表 · 新建 · 更新 · 删除 |
| **检索** | 4 | 检索（仅元数据）· 向量 · 两阶段（主入口）· 统计 |
| **标签** | 4 | 列表 · 更新 · 按标签取文档 · 清理 |
| **项目生命周期** | 4 | 状态 · 启动 · 更新 · 后端状态 |
| **文件系统** | 3 | 取目录树 · 取子节点 · 上传文件 |
| **解析** | 3 | 解析单文档 · 批量解析 · 解析任务状态 |
| | **94** | |

有两条设计规则值得了解：

- **解析工具全部非阻塞。** 它们立即返回 `task_id`，用 `parse_task_status` 轮询即可。解析永远不会阻塞 Agent 的一轮对话。
- **长任务同样返回 task id。** `kb_reindex`、`kb_graph_build`、`experience_meditation_run` 都返回任务 id，而不是把连接挂住。

<details>
<summary><b>Agent 技能（20 个）</b></summary>

<br>

`knowledgebase` 调度器把中英文自然语言请求路由到对应子技能，并委托给 Archival 子 Agent 执行，以确保质量门控不会被跳过：

`knowledgebase` · `knowledgebase-init` · `knowledgebase-update` · `knowledgebase-ingest` · `knowledgebase-search` · `knowledgebase-manage` · `knowledgebase-experience` · `knowledgebase-graph` · `knowledgebase-verify` · `butian` · `soul` · `soul-rag`，其余位于 `.claude/skills/`。

</details>

---

## 外部 HTTP API

认证**默认开启**（`server.auth.enabled: true`）。除 `/api/v1/health` 与 `/api/v1/auth/*` 外，所有接口都需要 Bearer Token。交互式文档在后端的 **`/docs`**；生成的 OpenAPI 会为非公开接口标注 `bearerAuth`。

```bash
# 0 · 获取令牌（全新安装需先注册）
TOKEN=$(curl -s -X POST http://localhost:6789/api/auth/login \
  -H 'content-type: application/json' \
  -d '{"username":"you","password":"your-password"}' | jq -r .token)

# 1 · 创建知识库
curl -s -X POST http://localhost:6789/api/kb/create \
  -H "Authorization: Bearer $TOKEN" -H 'content-type: application/json' \
  -d '{"name":"engineering-notes","description":"内部工程笔记"}'

# 2 · 写入文档（kbId 与 kb_id 均可，snake_case 别名会自动归一化）
curl -s -X POST http://localhost:6789/api/kb/documents/create \
  -H "Authorization: Bearer $TOKEN" -H 'content-type: application/json' \
  -d '{"kbId":"<kbId>","name":"pump-failure.md","content":"# 泵故障\n\n轴承温度超过 90°C..."}'

# 3 · 检索（两阶段：BM25 粗排 → 向量精排）
curl -s -X POST http://localhost:6789/api/v1/search/two-stage \
  -H "Authorization: Bearer $TOKEN" -H 'content-type: application/json' \
  -d '{"query":"轴承温度上限","limit":5}'

# 健康检查无需令牌
curl -s http://localhost:8770/api/v1/health
```

默认限流为 **600 次请求 / 60 秒**。

<details>
<summary><b>接口分布</b></summary>

<br>

| 领域 | 基础路径 |
|---|---|
| 认证 | `/api/v1/auth/{register,login,verify}` · `/api/auth/*`（Web 代理） |
| 知识库 | `/api/kb/{create,catalog,documents}` |
| 检索 | `/api/v1/search/{two-stage,vector}` |
| 经验 | `/api/v1/experience/*` |
| SOUL | `/api/v1/soul/*` |
| 图谱 | `/api/v1/graph/*` |
| 解析 | `/api/v1/parse/*` |
| MinerU | `/api/v1/mineru/{status,restart}` |
| 健康 | `/api/v1/health`（公开） |

以线上 OpenAPI 文档为准——它列出 114 条路径 / 121 个操作，并显式标注了其中 5 个公开接口。

</details>

---

## 配置

只有一个文件。仓库根目录的 `config.yml` 是端口与主机的唯一事实来源，后端、Web 代理与 MCP 服务器读取的都是它。

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

优先级为：`BACKEND_PORT` 环境变量 → `config.yml` → 代码默认值。`APP_MODE=dev|prod` 决定读取哪一段。代码库中没有任何地方硬编码端口或路径。

> 在 `APP_MODE=dev` 下修改 `config.yml` 会触发热重载。长时间会话建议使用 `APP_MODE=prod`，避免日志/数据库写入引发的重载风暴。

---

## 存储模型

```
web/storage/tree-file-system/
├── .tree-fs.json                 # L1 · 权威全局目录树索引
└── {知识库名称}/
    ├── .knowledge-base.yml       # L2 · 单库文档索引（名称、标签、元数据）
    ├── {文档}.md                 # L3 · 解析/上传后的 Markdown
    └── images/                   #      解析过程中抽取的图片
```

| 层 | 存储 | 内容 |
|:---:|---|---|
| **L1** | `.tree-fs.json` | 全部文件夹与文件及其元数据 |
| **L2** | `.knowledge-base.yml` | 单库检索索引——检索直接读它 |
| **L3** | 磁盘上的 `.md` | 内容本身 |
| **L4** | ChromaDB | 分块向量，每库一个 collection |
| **L5** | Neo4j | 文档、标签、知识库节点及其类型化关系 |

> L5 只会为你**显式构建过图谱**的知识库填充。全新安装时图谱是空的，图谱页显示零节点是正常的——尤其是标签节点，只有在带标签文档上执行过图谱构建后才会出现。

---

## 验证数据

以下数字均可由仓库内已提交的产物复现，脚本与出处都在本仓库中。

**入库完整性。** 两套语料、五个层级端到端校验；在已提交的运行记录中，入库模块报告的完整性为 `1.000`（`benchmark-suite/results/module_a_ingestion_r1.json`、`module_a_std2_r1.json`）。

**检索 —— 自建语料。** 数据来自 `benchmark-suite/results/module_b_retrieval_r2.json`（20 条查询，已完整提交）：

| 策略 | Hit@1 | Recall@5 | P@5 | 延迟 |
|---|:---:|:---:|:---:|:---:|
| 分阶段 BM25 → 向量 + 内容裁定 | 0.800 | **0.908** | **0.210** | 1.33 s |
| 纯稠密向量 | **0.900** | 0.917 | 0.200 | **0.081 s** |

**检索 —— SciFact。** 数据来自 `module_b_std2_r2.json`：稠密向量在 Hit@3（0.900 vs 0.833）、Recall@5（0.900 vs 0.833）与 nDCG@10（0.834 vs 0.809）上领先；BM25 的 MRR 最高（0.839）。

**这些数字说明了什么。** 内容裁定**不是白捡的收益**。它提升了 P@5 与 Recall@5——也就是找回了更多相关内容——代价是约 **13 倍延迟**，因为它要读文档而不是算向量。在两套语料上它都**没有**提升 Hit@1。任何「它全面优于纯向量检索」的说法都不被已提交的证据支持，本 README 也不作此声称。

**Agent 接口。** 针对线上平台的外部 API 端到端检查 **73/73 全部通过**（涵盖知识库管理、内容检索、经验生命周期、人格训练）。

> **关于已撤下的结果。** 本 README 的早期版本引用过一组更大的基准数据（`P@5 0.590 → 0.630`、`FPR 12 % → 3.0 %`、`84 ms → 38 ms`）。这些数字来自 `benchmark-web/backend/results/`，而该目录在本仓库中**找不到任何生成脚本**——它们无法复现，且与上文可追溯的运行结果相矛盾。因此它们被**删除**而不是被重述。如果你需要这些数字，请在上游提交可复现脚本之前，将其视为不可用。

<sub>计数最后核验于 **2026-09-15** 的线上实例：12 个知识库 · 209 份文档 · 94 个 MCP 工具 · 20 个技能 · 233 个后端测试 · 124 条 Web 路由 · 114 条 API 路径。</sub>

---

## 适用范围与非目标

明确说明这个项目**不是**什么：

- **不是托管服务。** 它按设计自托管，没有多租户隔离方案。
- **不是微调平台。** SOUL 的 LoRA 导出是一条**导出**路径，不要指望它能与专用训练器竞争。
- **不是在每个维度上都优于纯向量检索。** 见上面的诚实说明——它是在召回类指标上以延迟换精度。
- **在 Windows 上不是完全不挑环境的。** Python 3.12 的版本锁定是真实约束，目前不支持 3.13。
- **开箱不是图谱完备的。** L5 需要按知识库显式执行图谱构建才会填充。

---

## 参与贡献

欢迎提交 Issue 与 Pull Request。开 PR 之前请先跑：

```bash
cd backend && uv run pytest          # 后端单元测试（集成测试需加 --run-integration）
cd web && npx nuxt build             # 类型检查 + 构建
node scripts/validate_skills.cjs     # 跨技能一致性检查（8 项）
```

约定：端口与路径一律来自 `config.yml`；Python 必须写类型标注并使用 `logging`，禁止 `print`；`httpx` 调用必须传 `trust_env=False`，避免 localhost 请求被代理劫持；解析工具绝不阻塞。

---

## 许可证

MIT —— 见 [LICENSE](./LICENSE)。

<div align="center">
<br>
<sub>本项目是面向「内容验证检索」的研究平台。<br>
截图均为运行中应用的真实捕获；基准数字要么可追溯到已提交产物，要么不予列出。</sub>
</div>
