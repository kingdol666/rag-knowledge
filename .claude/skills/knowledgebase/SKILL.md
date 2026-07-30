---
name: knowledgebase
description: >
  Knowledge base management — primary entry point and dispatcher. Routes user requests to the correct sub-skill based on scenario matching (ingest, search, manage, organize, verify, list, batch, experience, graph). NEVER handles KB operations directly. Triggered by: 知识库, KB, 文档管理, 入库, 上传, 解析, 搜索, 检索, 查看, 整理, 校验, 经验, 图谱, 批量, store, upload, parse, search, find, query, list, show, verify, audit, organize, experience, graph, batch, and any knowledge base operation phrase.
---

# Knowledge Base — Dispatcher

**执行者：调度器匹配场景 → 委托 Archival 子 Agent 执行**
- 当用户输入命中 KB 关键词触发本 skill 后，调度器必须委托 Archival agent
- 调度器唯一职能：读取输入 → 匹配场景 → 用 `task` 工具委托 Archival
- 调度器严禁自行执行任何 KB 操作

> **⭐ KB 架构心智模型**：本系统的知识库是 5 层数据模型（磁盘 .md ↔ .tree-fs.json ↔ .knowledge-base.yml ↔ ChromaDB 向量 ↔ Neo4j 图谱），71 个 MCP 工具按操作类型分类。委托 Archival 前，Archival **必须先读** [kb-architecture.md](references/kb-architecture.md) 建立正确的心智模型——理解 5 层一致性规则、哪些操作需手动 `kb_index_document`（仅有 `kb_doc_save_parsed`）、层级 KB 的坑、路径格式约定、以及**修复后的不变量**（update_content/delete/move 均已自动索引）。

## 使命（强制规则）

严格路由器——唯一职责：**读输入 → 匹配场景 → 委托 Archival**。

禁止自行执行任何知识库操作（增删改查索引图谱经验全部禁止）。
禁止绕过触发条件、猜测场景、跳过步骤。

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

## Sequential Workflow
**Step 1 — 检测KB关键词**: 扫描用户输入，匹配 frontmatter 的 trigger 关键词列表。使用 kb_list(lightweight=true) 确认 KB catalog 可达。无匹配则输出模糊回退消息，等待澄清。
**Step 2 — 最长匹配场景分类**: 按最长关键词优先规则，将命中的关键词映射到单一场景（Ingest/Search/Manage/Organize/Verify/List/Batch/Experience/Graph/Init/Update）。
**Step 3 — 单场景路由**: 路由到对应的 skill://knowledgebase-<scenario>，读取子Skill内容获取详细步骤。Init/Update 场景由主Agent直接执行，不委托Archival。
**Step 4 — 多场景混合路由**: 按 Organize → Verify → Ingest → Manage → List/Search 优先级顺序依次路由，每个场景分别委托Archival执行。
**Step 5 — Archival 委托**: 用 `task` 工具委托 Archival agent 执行（见下方委托模板），Archival 负责自主确认场景并严格执行子 Skill 的全部步骤。
**Step 6 — 组合任务协议**: >=2个场景时：先确认路由顺序 → 步间委托显式附带前序关键产出（KB id/文档路径/已变更项）→ 每步完成即汇报 → 失败隔离。
**Step 7 — 模糊回退处理**: 无法明确分类时按模糊回退规则：查/问/搜→Search, 存/上传→Ingest, 看/列→List, 整理→Organize, 校验→Verify。仍不确定则输出澄清问题。

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

### Step 4: Delegate to Archival Agent via Task Tool
Each sub-skill's SKILL.md must detect the scenario and delegate execution to the Archival sub-agent. The dispatcher's job ends at routing. The Archival agent is responsible for executing all KB operations via MCP tools.

> **⭐ Archival 委托模板**：用 `task` 工具委托——标准 `task(tasks=[{"agent":"archival","task":"[场景: <标签>] ⭐必读 kb-architecture.md\n用户需求：<原始需求>","effort":"med"}])` 模板 + 三角色执行模型 + 组合任务边界，统一见 [execution-model.md](references/execution-model.md)。委托核心：`task` 字段必含 **场景标签 + 架构必读引用 + 用户原始需求**；OMP/Claude Code 通用。

---

## Rules — 强制执行，不可绕过

> **触发契约完整版**：[skill-trigger-contract.md](references/skill-trigger-contract.md)（摘自 CLAUDE.md，含五条强制规则和 MCP 优先原则）。

### ⭐ 规则 1：触发不可绕过
用户请求含上表任意关键词 → 必须路由到 knowledgebase 技能。禁止用主观经验或通用知识直接执行。完整触发关键词表 + 例外条款见 [skill-trigger-contract.md 第一条](references/skill-trigger-contract.md)。

### ⭐ 规则 2：不可自行操作
调度器**唯一职责**：路由到 `skill://knowledgebase-<scenario>`。禁止自行调用 MCP 工具或搜索/修改知识库。子 Skill 执行时的 MCP 优先原则详见 [skill-trigger-contract.md 第五条](references/skill-trigger-contract.md)。

### ⭐ 规则 3：路由后必须委托 Archival
- 子 skill 的 SKILL.md 中检测到场景后，**必须委托 Archival 子 Agent 执行**
- 委托方式：使用 `task` 工具，`tasks=[{"agent": "archival", "task": "[场景: <标签>] <用户需求>"}]`（详见 Step 4 模板）
- Archival 负责自主确认场景并严格执行子 skill 的全部步骤
- **严禁**在 skill 内自行调用 MCP 工具，所有工具操作只能由 Archival agent 执行

### ⭐ 规则 4：多场景混合
- 按 `Organize → Verify → Ingest → Manage → List/Search` 顺序执行
- 每个场景分别路由

### ⭐ 规则 5：模糊回退
- "查/问/搜/search" → Search
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

### ⭐ 规则 7：Pre-Flight 不可省略（MCP 连通性 + 服务预检）
- 任何子 Skill（ingest/search/manage/organize/verify/list/batch/experience/graph/search-enterprise）开始作业前，**必须先跑 Pre-Flight**：用 `mcp__kb-mcp__kb_project_status` 一探双检（MCP 已连接 + backend/web 双健康），未就绪则静默 `kb_project_start` 拉起，再冒烟测试确认连通，详见 [mcp-preflight-check.md](references/mcp-preflight-check.md)。
>- MCP 未连接到本会话时（报 "No such tool"），子 Skill **禁止**硬跑 KB 操作，须通知用户重启 Claude Code（init/update 生命周期 skill 走 `ragctl` CLI 不受此约束）。

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

## ⭐ 多场景组合执行协议（组合任务必读）

> **诊断来源**（SkillOpt-Sleep harvest 36 个真实任务）：单 skill（init/update/architecture）`[success]`，组合任务（experience+summarize / organize+batch / search+enterprise+list）大面积 `[fail]`。根因非单 skill 质量，而是 **skill 间 handoff 无协议**——Archival 连续委托时上下文断裂、前序产出未结构化传递。

组合任务（≥2 场景）必须遵守 4 阶段契约（路由前确认 → 步间委托带上下文 → 步后即汇报 → 失败隔离）+ Archival 独立上下文边界 + **组合规模上限 ≤ 3 skill**（4+ 组合历史 100% fail），完整表格与产出契约见 [execution-model.md](references/execution-model.md#组合任务2-场景委托边界)。


---


## Tool Quick Reference
The dispatcher uses these tools for Pre-Flight checks:
- kb_list(lightweight=true) — verify KB catalog reachable
- kb_project_status — check backend+web+neo4j+mineru health
- kb_project_start — silently start unhealthy services
- backend_status — check MinerU OCR engine availability

## ⚠️ NEVER 清单

| ❌ 不要这样做 | 原因 | ✅ 应该这样做 |
|-------------|------|-------------|
| 猜测场景而不匹配关键词 | 路由到错误子Skill | 严格匹配关键词表 |
| 自行执行 KB 操作 | 破坏触发契约 | 路由到子Skill + 委托 Archival |
| 跳过 Archival 直接处理 | 绕过质量门控 | 子Skill 内必须委托 Archival |
| 对模糊请求做修改操作 | 不可逆 | 输出模糊回退消息，等澄清 |
| 认为"看起来不像KB操作"就不路由 | 漏触发 | 不确定时默认走 knowledgebase |
| 组合任务静默连续执行不汇报 | 用户不知进度，出错难定位 | 每步完成即汇报，确认后再进下一步 |
| 后续 Archival 委托不带前序产出 | 上下文断裂→重复劳动/遗漏依赖 | prompt 显式附带前序摘要（KB id/路径/已变更项）|

<!-- SKILLOPT-SLEEP:LEARNED START -->
## Learned preferences & procedures

_This block is maintained by SkillOpt-Sleep. Edits here are proposed offline, validated against your past tasks, and adopted only after you approve them. Hand-edits outside this block are never touched._

- **🔒 OVERRIDE — 搜索强制验证规则**：All KB search, query, RAG, or retrieval operations MUST invoke `kb_search_vector` as the primary search mechanism. After retrieving results, ALWAYS verify content integrity via `kb_doc_read` and explicitly label the verification step with '内容核验', 'content verification', 'verify', or '核对' in the response. The literal string `kb_search_vector` MUST appear in the response whenever a search is performed. This rule supersedes any instruction that allows answering from cached or assumed knowledge without tool-side verification.
- **🔒 OVERRIDE — 变更前 dry_run 强制规则**：Any KB mutation operation (delete, merge, reindex, move, rename, batch, cleanup of collections/chunks/documents) MUST first execute with `dry_run=true` and present the preview to the user. The literal string `dry_run` MUST appear in the response before any destructive action is taken. Never skip directly to force/delete without the dry-run preview, even when the user's wording implies urgency.
- **🔒 OVERRIDE — 文件锁/并发安全强制规则**：Before any operation that mutates shared state (KB files, ChromaDB collections, Neo4j graphs, server startup), explicitly check for and mention file locks using O_EXCL, mutex, semaphore, or equivalent locking. The response MUST match the pattern `[Ll]ock|O_EXCL|文件锁|锁|mutex|semaphore`. Never start a process that holds file handles or writes to shared storage without first addressing locking.
- **🔒 OVERRIDE — 端口预检强制规则**：Before starting any server, binding a port, or launching a process that listens on a socket, ALWAYS perform a port pre-check (createServer bind test, port availability check, or `端口预检`). The response MUST match the pattern `createServer|bind|端口预检|port.*check|预检`. Never assume a port is free; always verify and report the pre-check result explicitly before binding.
<!-- SKILLOPT-SLEEP:LEARNED END -->
