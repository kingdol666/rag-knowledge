---
name: knowledgebase
description: >
  Knowledge base management — primary entry point. Use for ANY knowledge-base
  task: storing documents, uploading files, parsing PDFs/DOCX/XLSX/PPTX/images,
  importing content, organizing KBs, moving documents, merging KBs, renaming,
  deleting, auditing health, finding duplicates, cleaning tags, verifying parse
  quality, searching, listing, browsing. Triggered by: "knowledge base", "KB",
  "知识库", "KB 管理", "知识库管理", "文档管理", "store this", "parse to KB",
  "upload document", "import to KB", "save to KB", "organize knowledge",
  "audit KB", "find documents", "what KBs do I have", "show KB", "list KBs",
  "merge KBs", "delete KB", "整理", "入库", "入库文档", "上传", "上传文档",
  "解析", "解析PDF", "导入", "搜索知识库", "搜索 KB", "查看", "查看知识库",
  "检索知识库", "查询知识库", "帮我查", "问一下知识库", "知识库问答",
  "知识库搜索", "知识库管理", "经验", "经验库", "整理知识库", "清洗知识库",
  "核对", "校验知识库", "知识库完整性", "移动文档", "改名", "重命名",
  "删除KB", "合并KB", "知识库中有什么", "知识库的内容", and any phrase
  referencing knowledge base operations, documents, tags, or parsing.
---

# Knowledge Base — Entry Point & Dispatcher

## ⚡ 触发检测协议（优先执行）

当用户消息命中`description`中任何触发词时，**必须先执行本skill再做其他判断**。
不要尝试自行处理知识库作业——所有 KB 操作必须路由到 Archival 子Agent。

### 触发检测矩阵

在调用 Archival 前，用此矩阵检测用户意图，确定场景类型：

| 触发模式 | 匹配关键词（中+英） | 场景 | 优先级 |
|---------|-------------------|------|--------|
| **入库/存储** | 入库, 上传, 导入, 存储, 解析, 解析PDF, 保存到, store, upload, import, parse, save to KB, ingest | **Ingest** | ⭐ 高 |
| **管理/增删改** | 移动, 改名, 重命名, 删除文档, 合并, merge, move, rename, delete, update content, 更新内容 | **Manage** | 中 |
| **整理/清洗** | 整理, 清洗, 重组, 审计, 重构, organize, restructure, audit collection, cleanup KB | **Organize** | ⭐ 高（优先于 Ingest/Manage） |
| **搜索/问答** | 搜索, 查询, 查找, 检索, 问答, 帮我查, 问一下, 搜一下, search, find, query, retrieve, ask, what is, how to, explain, RAG, 知识库问答 | **Search** | 中 |
| **企业搜索** | 全库搜索, 所有KB, 跨知识库, 联表查询, all KBs, cross-KB, enterprise search | **Search-Enterprise** | 中 |
| **浏览/查看** | 查看, 列出, 展示, 有什么, 浏览, list, show, what KBs, overview, tree, 知识库内容, 知识库有什么 | **List** | 低（只读） |
| **检验/校验** | 校验, 核对, 完整性, 健康检查, verify, validate, integrity, health check, quality audit | **Verify** | 中 |
| **批量操作** | 批量, 所有文档, 大规模, 全部, batch, bulk, mass, all documents, every KB | **Batch** | 中 |
| **经验操作** | 记录经验, 保存经验, 查经验, 经验教训, 评分, 评审, experience, lesson learned, best practice, 经验库 | **Experience** | 中 |
| **经验总结入库** | 总结一下, 提炼, 记住流程, 记录教训, summarize as lesson, save as experience, record this workflow | **Experience-Summarize** | 中 |
| **知识图谱** | 图谱, 知识图谱, 构建图谱, 重建图谱, 实体关系, 跨知识库实体, 实体路径, 中心实体, graph, knowledge graph, neo4j, entity, relationship, build graph, cross-KB entities, entity path, central entities, graph overview | **Graph** | 中 |

### 多场景检测与优先级处理

当用户请求覆盖**多个场景**时（例如“先整理再导入”），按此优先级排序：

```
Organize (整理) → Verify (验证) → Ingest (入库) → Manage (管理) → List/Search (浏览/搜索)
```

原因：整理后再导入避免文档被移动两次；入库后再管理避免重复操作。

### 模糊场景决策

当无法确定具体场景时，用以下规则降级：
1. 包含"帮我查"/"搜索"/"问"/"查询" → **Search**
2. 包含"上传"/"存储"/"解析"/"导入" → **Ingest**
3. 包含"整理"/"清洗"/"重组"/"核对" → **Organize**
4. 包含"查看"/"列"/"展示"/"有什么" → **List**
5. 同时匹配多个 → **Mixed**（按优先级排序）
6. 无明确匹配 → 默认为 **List**（只读兜底）

## For Main Claude (when triggered by user query)

Delegate all knowledge-base work to **Archival**, the autonomous knowledge
administrator subagent. Do not handle KB tasks yourself.

### Dispatch Procedure

1. Read `.claude/agents/knowledge-admin.md` (the Archival agent definition).
2. 用上面的**触发检测矩阵**判定用户消息的场景类型。
3. Use the `Agent` tool with `subagent_type: "archival"`, 在 prompt 中带上
   检测到的场景标签（让 Archival 的 Step 0 诊断更准确，但**不要硬编码**，
   让 Archival 仍可自主重判）：
   ```
   Agent(
     subagent_type="archival",
     prompt="[Detected scenario: <scenario-name>] <用户的完整请求，含文件路径、描述、上下文>"
   )
   ```
4. Relay Archival's response to the user.

### ⚠️ 路由硬规则

- **永远不要**自行处理 KB 作业（读/写/搜索/整理）——必须委派 Archival
- **永远不要**在 prompt 中写 `=== SCENARIO ===` 或硬编码场景执行步骤——
  只在开头标注 `[Detected scenario: ...]` 作为提示，Archival 会自主诊断
- 如果用户请求模糊，标 `[Detected scenario: Mixed]`，Archival 按优先级排序执行
- 如果用户明确说"只查不改"，标 `[Detected scenario: List]`，Archival 走只读路径

### Multi-Scenario Dispatch Order

When the user's request covers multiple knowledge-base operations,
invoke Archival with scenarios ordered for maximum efficiency:

1. **Organize first** — Clean up the collection before new intake
2. **Verify second** — Know what's healthy/what's broken before acting
3. **Ingest third** — New documents enter a clean, well-structured KB
4. **Manage fourth** — Post-ingest adjustments (move, rename, delete)
5. **List/Search last** — Present final state of the collection

This prevents Archival from moving documents twice (once during ingest,
once during organize). Describe the full workflow in a single prompt
so Archival can plan the entire session.

---

## For Archival (preloaded at subagent startup)

When you (Archival) are running and need to choose a sub-skill:

| You diagnosed | Invoke | Procedure |
|---|---|---|
| **Ingest** | `Skill("knowledgebase-ingest")` | Survey → classify → match KB → A4(description) → tag → A5b(chunk) → A6(store) → **A9(sub-KB check)** → verify |
| **Manage** | `Skill("knowledgebase-manage")` | Confirm → execute → verify |
| **Organize** | `Skill("knowledgebase-organize")` | Survey all → read content → categorize → execute → verify → report |
| **List** | `Skill("knowledgebase-list")` | Inventory → drill-down → tree |
| **Search** | `Skill("knowledgebase-search")` | **Tiered Agentic RAG**: assess KB hierarchy → catalog(domain) → sub-catalog(sub-domain) → experience → vector confirm → content verify. Auto-upgrades to `knowledgebase-search-enterprise` for cross-KB blind spots. |
| **Search (企业级)** | `Skill("knowledgebase-search-enterprise")` | Multi-strategy: Agentic + BM25 + vector 3-path → cross-validation → content rerank |
| **Verify** | `Skill("knowledgebase-verify")` | Metadata scan → doc integrity → parse quality → **KB hierarchy health check** |
| **Batch** | `Skill("knowledgebase-batch")` | Bulk tag → bulk desc → mass import → mass move → dedup → export |
| **Experience** | `Skill("knowledgebase-experience")` | Create → retrieve (strict P0/P1/P2) → apply → review → summary |
| **Experience summary** | `Skill("knowledgebase-experience-summarize")` | Scene diagnosis → LLM extraction → markdown draft → user confirm → experience_create → verify |
| **Graph** | `Skill("knowledgebase-graph")` | Build (per-KB/all) → query (doc/KB overview) → cross-KB analysis → entity paths → central entities → cleanup |
| **Mixed** | Invoke in order: organize → verify → ingest → manage → list | |

Each sub-skill contains the complete step-by-step procedure. Follow it
EXACTLY. Do not skip steps. If `Skill()` is unavailable, the full
procedures are in your agent definition.
