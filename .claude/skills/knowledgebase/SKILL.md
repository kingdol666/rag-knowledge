---
name: knowledgebase
description: Knowledge base management — primary entry point and dispatcher. Routes user requests to the correct sub-skill based on scenario matching (ingest, search, manage, organize, verify, list, batch, experience, graph). NEVER handles KB operations directly. Triggered by: 知识库, KB, 文档管理, 入库, 上传, 解析, 搜索, 检索, 查看, 整理, 校验, 经验, 图谱, 批量, store, upload, parse, search, find, query, list, show, verify, audit, organize, experience, graph, batch, and any knowledge base operation phrase.
---

# Knowledge Base — Dispatcher

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
  ├── 多场景混合 → 按 Organize → Verify → Ingest → Manage → List/Search 顺序路由
  └── 模糊回退 → 如下表
```

---

## Sequential Processing Steps

### Step 1: Detect KB Keywords
Scan user input for any trigger keyword from the frontmatter trigger list. If no keywords match, output the fuzzy fallback message and wait for clarification. Do not proceed to modification without explicit user intent.

### Step 2: Classify the Scenario
Map matched keywords to a single scenario using the classification table below. Each row maps a set of signal keywords to one scenario and its corresponding sub-skill.

| Signal keywords | Scenario | Route to |
|---|---|---|
| 入库, 上传, 导入, 解析, store, upload, parse, ingest | **Ingest** | `Skill("knowledgebase-ingest")` |
| 移动, 改名, 删除, 合并, move, rename, delete, merge | **Manage** | `Skill("knowledgebase-manage")` |
| 整理, 清洗, 重组, 审计, organize, restructure, audit | **Organize** | `Skill("knowledgebase-organize")` |
| 搜索, 查询, 检索, search, find, query, RAG | **Search** | `Skill("knowledgebase-search")` |
| 全库搜索, 跨库, cross-KB, enterprise | **Search-Enterprise** | `Skill("knowledgebase-search-enterprise")` |
| 查看, 列出, 浏览, list, show, overview, tree | **List** | `Skill("knowledgebase-list")` |
| 校验, 核对, 完整性, 检查, 检测, verify, validate, integrity | **Verify** | `Skill("knowledgebase-verify")` |
| 批量, 全量, batch, bulk, mass | **Batch** | `Skill("knowledgebase-batch")` |
| 经验, 经验库, experience, lesson, best practice | **Experience** | `Skill("knowledgebase-experience")` |
| 记录经验, 总结, summarize as experience | **Experience-Summarize** | `Skill("knowledgebase-experience-summarize")` |
| 图谱, graph, neo4j, entity, build graph | **Graph** | `Skill("knowledgebase-graph")` |

### Step 3: Route to Sub-Skill
Based on classification outcome:
- **Single scenario** — Route directly via `Skill("knowledgebase-<scenario>")`.
- **Mixed scenarios** — Follow priority order: Organize → Verify → Ingest → Manage → List/Search. Complete each sub-skill fully before starting the next.
- **Ambiguous / fuzzy match** — Apply fuzzy fallback rules (see Rule 5).

### Step 4: Sub-Skill Delegates to Archival Agent
Each sub-skill's SKILL.md must detect the scenario and delegate execution to the Archival sub-agent. The dispatcher's job ends at routing. The Archival agent is responsible for executing all KB operations via MCP tools.

---

## Rules — 强制执行，不可绕过

### ⭐ 规则 1：触发不可绕过
- **用户请求含上表任意关键词 → 必须路由到 knowledgebase 技能**
- 禁止用主观经验、通用知识或MCP工具直接执行
- 无法确定时默认路由，不做"我觉得不像KB操作"的判断

### ⭐ 规则 2：不可自行操作
- 调度器 **禁止** 自行调用任何 kb-mcp MCP 工具
- 调度器 **禁止** 自行搜索/读取/修改知识库
- **唯一允许的操作**：用 `Skill("knowledgebase-<scenario>")` 路由到子 skill
- ⭐ 并且子 Skill 执行时必须通过 MCP 工具（禁止终端/API 绕行，详见子 Skill 的 MCP 优先原则）

### ⭐ 规则 3：路由后必须委托 Archival
- 子 skill 的 SKILL.md 中检测到场景后，**必须委托 Archival 子 Agent 执行**
- `Agent(subagent_type="archival", prompt="[Detected scenario: <场景标签>]<用户原始需求>")`
- Archival 负责自主确认场景并严格执行子 skill 的全部步骤
- **严禁**在 skill 内自行调用 MCP 工具，所有工具操作只能由 Archival agent 执行

### ⭐ 规则 4：多场景混合
- 按 `Organize → Verify → Ingest → Manage → List/Search` 顺序执行
- 每个场景分别路由

### ⭐ 规则 5：模糊回退
- "查/问/search" → Search
- "存/上传/store" → Ingest
- "看/列/show" → List
- 否则输出："我没能清晰理解您的需求。请说明您是要：入库文档、搜索知识、管理知识库、还是整理知识库？"——等待澄清，不做修改操作

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
