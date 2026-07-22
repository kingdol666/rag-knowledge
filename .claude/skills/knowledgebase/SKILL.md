---
name: knowledgebase
description: Knowledge base management — primary entry point and dispatcher. Routes user requests to the correct sub-skill based on scenario matching (ingest, search, manage, organize, verify, list, batch, experience, graph). NEVER handles KB operations directly. Triggered by: 知识库, KB, 文档管理, 入库, 上传, 解析, 搜索, 检索, 查看, 整理, 校验, 经验, 图谱, 批量, store, upload, parse, search, find, query, list, show, verify, audit, organize, experience, graph, batch, and any knowledge base operation phrase.
---

# Knowledge Base — Dispatcher

**执行者：此技能由 Archival agent 执行**
- 当用户输入命中 KB 关键词触发本 skill 后，调度器必须委托 Archival agent
- 调度器唯一职能：读取输入 → 匹配场景 → 委托 Archival（`Agent(subagent_type="archival", ...)`）
- 调度器严禁自行执行任何 KB 操作

> **⭐ KB 架构心智模型**：本系统的知识库是 5 层数据模型（磁盘 .md ↔ .tree-fs.json ↔ .knowledge-base.yml ↔ ChromaDB 向量 ↔ Neo4j 图谱），76 个 MCP 工具按操作类型分类。委托 Archival 前，Archival **必须先读** [kb-architecture.md](references/kb-architecture.md) 建立正确的心智模型——理解哪些操作原子同步、哪些需手动重索引、层级 KB 的坑、路径格式约定。

## 使命（强制规则）

你是一个严格的路由器，你的唯一职责是：**读输入 → 匹配场景 → 委托 Archival**。

你**禁止**自行执行任何知识库操作（增删改查索引图谱经验全部禁止）。
你**禁止**绕过触发条件、猜测场景、跳过步骤。

---

## 思维框架：场景归类 ⭐

```
用户说了一句话
  └── 包含 KB 关键词？
       ├── 是 → 匹配下表的信号关键词
       └── 否 → "我没能清晰理解您的需求。请说明您是要：入库文档、搜索知识、管理知识库、还是整理知识库？"

匹配到后：
  ├── 明确单一场景 → 路由对应子 Skill
  ├── Init 场景 → 主 Agent 直接执行 `Skill("knowledgebase-init")`，不经过 Archival
  ├── 多场景混合 → 按 Organize → Verify → Ingest → Manage → List/Search 顺序路由
  └── 模糊回退 → 如下表
```

---

## Sequential Processing Steps

### Step 1: Detect KB Keywords
Scan user input for any trigger keyword from the frontmatter trigger list. If no keywords match, output the fuzzy fallback message and wait for clarification. Do not proceed to modification without explicit user intent.

### Step 2: Classify the Scenario
Map matched keywords to a single scenario using the classification table below. Each row maps a set of signal keywords to one scenario and its corresponding sub-skill.

**⭐ 最长匹配优先规则（Longest-Match-First）**：当多个关键词同时命中时，**最长的关键词优先**。例如"检查更新"同时命中"检查"(Verify) 和"检查更新"(Update)，取更长的"检查更新" → Update。此规则消解所有前缀歧义。

| Signal keywords | Scenario | Route to |
|---|---|---|
| 入库, 上传, 导入, 解析, 存储, 保存到, 放文档, 添加文档, store, upload, parse, ingest, save to KB, add doc, put document | **Ingest** | `Skill("knowledgebase-ingest")` |
| 移动, 改名, 删除, 合并, move, rename, delete, merge | **Manage** | `Skill("knowledgebase-manage")` |
| 整理, 清洗, 重组, 盘点, 大扫除, 全面梳理, 归并, 归类, organize, restructure, cleanup, reorganize | **Organize** | `Skill("knowledgebase-organize")` |
| 搜索, 查询, 检索, 哪里, 办法, 怎么解决, search, find, query, RAG, how to, explain, what is | **Search** | `Skill("knowledgebase-search")` |
| 全库搜索, 跨库, 跨知识库, cross-KB, enterprise | **Search-Enterprise** | `Skill("knowledgebase-search-enterprise")` |
| 查看, 列出, 浏览, 内容, list, show, overview, tree | **List** | `Skill("knowledgebase-list")` |
| 校验, 核对, 完整性, 检查, 检测, 检测问题, 审计知识库, audit, verify, validate, integrity, health check | **Verify** | `Skill("knowledgebase-verify")` |
| 批量, 全量, batch, bulk, mass | **Batch** | `Skill("knowledgebase-batch")` |
| 经验, 经验库, experience, lesson, best practice | **Experience** | `Skill("knowledgebase-experience")` |
| 记录经验, 总结经验, summarize as experience | **Experience-Summarize** | `Skill("knowledgebase-experience-summarize")` |
| 图谱, graph, neo4j, entity, build graph | **Graph** | `Skill("knowledgebase-graph")` |
| 初始化, 安装, 部署, 配置知识库, init, setup, install, deploy, bootstrap, getting started | **Init** | `Skill("knowledgebase-init")` (main agent — 不委托 Archival) |
| 更新知识库, 升级, 检查更新, 拉取最新, 新版本, update, upgrade, check for updates, ragctl update | **Update** | `Skill("knowledgebase-update")` (main agent — 不委托 Archival) |

> **注意**：`检查` 单独出现 → Verify（健康检查/一致性校验）。`检查更新` → Update（最长匹配优先）。
> `总结` 单独出现需结合上下文判断：若语境是"总结经验/教训"→ Experience-Summarize；若语境是"总结知识库内容"→ List。无法确定时询问用户。

### Step 3: Route to Sub-Skill
Based on classification outcome:
- **Single scenario** — Route to `skill://knowledgebase-<scenario>` (read the skill content for detailed steps).
- **Mixed scenarios** — Follow priority order: Organize → Verify → Ingest → Manage → List/Search. Complete each sub-skill fully before starting the next.
- **Ambiguous / fuzzy match** — Apply fuzzy fallback rules (see Rule 5).

### Step 4: Sub-Skill Delegates to Archival Agent
Each sub-skill's SKILL.md must detect the scenario and delegate execution to the Archival sub-agent. The dispatcher's job ends at routing. The Archival agent is responsible for executing all KB operations via MCP tools.

> **⭐ Archival 委托 prompt 模板**（必须包含架构引用）：
> Delegate to the Archival agent with:
> ```
> task(agent: "archival", prompt="[Detected scenario: <场景标签>]
>
> ⭐ 操作前必读 skill://knowledgebase/references/kb-architecture.md 建立 5 层数据模型心智模型。
>
> 用户需求：<原始需求>")
> ```
> (Claude Code equivalent: `Agent(subagent_type="archival", prompt=...)`)

---

## Rules — 强制执行，不可绕过

> **触发契约完整版**：[skill-trigger-contract.md](references/skill-trigger-contract.md)（摘自 CLAUDE.md，含五条强制规则和 MCP 优先原则）。

### ⭐ 规则 1：触发不可绕过
- **用户请求含上表任意关键词 → 必须路由到 knowledgebase 技能**
- 禁止用主观经验、通用知识或MCP工具直接执行
- 无法确定时默认路由，不做"我觉得不像KB操作"的判断

### ⭐ 规则 2：不可自行操作
- 调度器 **禁止** 自行调用任何 kb-mcp MCP 工具
- 调度器 **禁止** 自行搜索/读取/修改知识库
- **唯一允许的操作**：路由到 `skill://knowledgebase-<scenario>` 获取详细流程
- ⭐ 并且子 Skill 执行时必须通过 MCP 工具（禁止终端/API 绕行，详见子 Skill 的 MCP 优先原则）

### ⭐ 规则 3：路由后必须委托 Archival
- 子 skill 的 SKILL.md 中检测到场景后，**必须委托 Archival 子 Agent 执行**
- 委托方式：`task(agent: "archival", prompt="[Detected scenario: <场景标签>]<用户原始需求>")`
- Archival 负责自主确认场景并严格执行子 skill 的全部步骤
- **严禁**在 skill 内自行调用 MCP 工具，所有工具操作只能由 Archival agent 执行

### ⭐ 规则 4：多场景混合
- 按 `Organize → Verify → Ingest → Manage → List/Search` 顺序执行
- 每个场景分别路由

### ⭐ 规则 5：模糊回退
- "查/问/search" → Search
- "存/上传/store" → Ingest
- "看/列/show" → List
- "整理/清洗/盘点/大扫除/organize" → Organize
- "校验/审计/检查（非更新）/verify" → Verify
- "初始化/安装/部署/setup" → Init (main agent, 不委托 Archival)
- "更新/升级/检查更新/update" → Update (main agent, 不委托 Archival)
- 否则输出："我没能清晰理解您的需求。请说明您是要：入库文档、搜索知识、管理知识库、还是整理知识库？"——等待澄清，不做修改操作

### ⭐ 规则 6：最长匹配优先（消解前缀歧义）
- 当输入同时命中多个关键词时，**字符数最长的关键词所属场景优先**
- 典型案例：`检查更新` 同时命中"检查"(Verify) + "检查更新"(Update) → 取更长 → **Update**
- 典型案例：`更新知识库` 同时命中"更新"(Update) + "知识库"(通用) → 取更长 → **Update**
- 此规则防止短前缀关键词劫持更精确的长关键词

---

## 多场景路由示例

| 用户说 | 命中场景 | 路由顺序 |
|--------|---------|---------|
| "整理所有知识库，找到有问题的地方" | Organize | `Skill("knowledgebase-organize")` |
| "校验+整理" | Organize + Verify | `Organize → Verify` |
| "入库这篇PDF，然后搜一下XX" | Ingest + Search | `Ingest → Search` |
| "把所有文档移库，再批量改标签" | Manage + Batch | `Manage → Batch` |
| "看看有什么KB，检查一下健康度" | List + Verify | `List → Verify` |

> 多场景时每个子 Skill 走完整流程。前一个完成后通知用户结果，再进下一个。

---

## ⚠️ NEVER 清单

| ❌ 不要这样做 | 原因 | ✅ 应该这样做 |
|-------------|------|-------------|
| 猜测场景而不匹配关键词 | 路由到错误子Skill | 严格匹配关键词表 |
| 自行执行 KB 操作 | 破坏触发契约 | 路由到子Skill + 委托 Archival |
| 跳过 Archival 直接处理 | 绕过质量门控 | 子Skill 内必须委托 Archival |
| 对模糊请求做修改操作 | 不可逆 | 输出模糊回退消息，等澄清 |
| 认为"看起来不像KB操作"就不路由 | 漏触发 | 不确定时默认走 knowledgebase |
