---
name: knowledgebase
description: Knowledge base management — primary entry point. Use for ANY knowledge-base task: storing documents, uploading files, parsing PDFs/DOCX/XLSX/PPTX/images, importing content, organizing KBs, moving documents, merging KBs, renaming, deleting, auditing health, finding duplicates, cleaning tags, verifying parse quality, searching, listing, browsing. Triggered by: "knowledge base", "KB", "知识库", "KB 管理", "知识库管理", "文档管理", "store this", "parse to KB", "upload document", "import to KB", "save to KB", "organize knowledge", "audit KB", "find documents", "what KBs do I have", "show KB", "list KBs", "merge KBs", "delete KB", "整理", "入库", "入库文档", "上传", "上传文档", "解析", "解析PDF", "导入", "搜索知识库", "搜索 KB", "查看", "查看知识库", "检索知识库", "查询知识库", "帮我查", "问一下知识库", "知识库问答", "知识库搜索", "知识库管理", "经验", "经验库", "整理知识库", "清洗知识库", "核对", "校验知识库", "知识库完整性", "移动文档", "改名", "重命名", "删除KB", "合并KB", "知识库中有什么", "知识库的内容", and any phrase referencing knowledge base operations, documents, tags, or parsing.
---

# Knowledge Base — Dispatcher

## 使命（强制规则）

你是一个严格的路由器，你的唯一职责是：**读输入 → 匹配场景 → 委托 Archival**。

你**禁止**自行执行任何知识库操作（增删改查索引图谱经验全部禁止）。
你**禁止**绕过触发条件、猜测场景、跳过步骤。

---

## Classify the scenario, then route to the matching sub-skill.

| Signal keywords | Scenario | Skill |
|---|---|---|
| 入库, 上传, 导入, 解析, store, upload, parse, ingest | **Ingest** | `Skill("knowledgebase-ingest")` |
| 移动, 改名, 删除, 合并, move, rename, delete, merge | **Manage** | `Skill("knowledgebase-manage")` |
| 整理, 清洗, 重组, 审计, organize, restructure, audit | **Organize** | `Skill("knowledgebase-organize")` |
| 搜索, 查询, 检索, search, find, query, RAG | **Search** | `Skill("knowledgebase-search")` |
| 全库搜索, 跨库, cross-KB, enterprise | **Search-Enterprise** | `Skill("knowledgebase-search-enterprise")` |
| 查看, 列出, 浏览, list, show, overview, tree | **List** | `Skill("knowledgebase-list")` |
| 校验, 核对, 完整性, verify, validate, integrity | **Verify** | `Skill("knowledgebase-verify")` |
| 批量, 全量, batch, bulk, mass | **Batch** | `Skill("knowledgebase-batch")` |
| 经验, 经验库, experience, lesson, best practice | **Experience** | `Skill("knowledgebase-experience")` |
| 记录经验, 总结, summarize as experience | **Experience-Summarize** | `Skill("knowledgebase-experience-summarize")` |
| 图谱, graph, neo4j, entity, build graph | **Graph** | `Skill("knowledgebase-graph")` |

## Rules — 强制执行，不可绕过

### ⭐ 规则 1：触发不可绕过
- **用户请求含上表任意关键词 → 必须路由到 knowledgebase 技能**
- 禁止用主观经验、通用知识或MCP工具直接执行
- 无法确定时默认路由，不做"我觉得不像KB操作"的判断

### ⭐ 规则 2：不可自行操作
- 调度器 **禁止** 自行调用任何 kb-mcp MCP 工具
- 调度器 **禁止** 自行搜索/读取/修改知识库
- **唯一允许的操作**：用 `Skill("knowledgebase-<scenario>")` 路由到子 skill

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
