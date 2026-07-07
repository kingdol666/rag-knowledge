---
name: knowledgebase
description: Knowledge base management — primary entry point. Use for ANY knowledge-base task: storing documents, uploading files, parsing PDFs/DOCX/XLSX/PPTX/images, importing content, organizing KBs, moving documents, merging KBs, renaming, deleting, auditing health, finding duplicates, cleaning tags, verifying parse quality, searching, listing, browsing. Triggered by: "knowledge base", "KB", "知识库", "KB 管理", "知识库管理", "文档管理", "store this", "parse to KB", "upload document", "import to KB", "save to KB", "organize knowledge", "audit KB", "find documents", "what KBs do I have", "show KB", "list KBs", "merge KBs", "delete KB", "整理", "入库", "入库文档", "上传", "上传文档", "解析", "解析PDF", "导入", "搜索知识库", "搜索 KB", "查看", "查看知识库", "检索知识库", "查询知识库", "帮我查", "问一下知识库", "知识库问答", "知识库搜索", "知识库管理", "经验", "经验库", "整理知识库", "清洗知识库", "核对", "校验知识库", "知识库完整性", "移动文档", "改名", "重命名", "删除KB", "合并KB", "知识库中有什么", "知识库的内容", and any phrase referencing knowledge base operations, documents, tags, or parsing.
---

# Knowledge Base — Entry Point & Dispatcher

## Trigger Detection Matrix
| Pattern | Keywords (CN+EN) | Scenario | Priority |
|---|---|---|---|
| **Ingest** | 入库, 上传, 导入, 解析, store, upload, import, parse, ingest | **Ingest** | High |
| **Manage** | 移动, 改名, 删除, merge, move, rename, delete | **Manage** | Medium |
| **Organize** | 整理, 清洗, 重组, organize, restructure, audit, cleanup | **Organize** | High |
| **Search** | 搜索, 查询, 检索, search, find, query, retrieve, RAG | **Search** | Medium |
| **Enterprise Search** | 全库搜索, 跨库, all KBs, cross-KB, enterprise | **Search-Enterprise** | Medium |
| **List** | 查看, 列出, 浏览, list, show, overview, tree | **List** | Low (read-only) |
| **Verify** | 校验, 核对, 完整性, verify, validate, integrity, health | **Verify** | Medium |
| **Batch** | 批量, 所有文档, batch, bulk, mass, all documents | **Batch** | Medium |
| **Experience** | 经验, 经验库, experience, lesson, best practice | **Experience** | Medium |
| **Graph** | 图谱, graph, neo4j, entity, build graph | **Graph** | Medium |

Multi-scenario: order by Organize → Verify → Ingest → Manage → List/Search

### Fuzzy Fallback
No clear match? Contains 查/问/search → Search. Contains 存/上传/store → Ingest. Contains 看/列/show → List. Truly ambiguous → ask user.

## Dispatch Procedure
1. Read `.claude/agents/knowledge-admin.md`
2. Classify scenario via trigger matrix
3. `Agent(subagent_type="archival", prompt="[Detected scenario: X] ...")`
4. Relay response

## Routing Hard Rules
- **Never** handle KB tasks yourself — delegate to Archival
- **Never** hardcode scenario steps — only tag `[Detected scenario: X]`, let Archival judge
- If user says "只查不改" → tag `[Detected scenario: List]`

## Sub-Skill Routing (for Archival)
| Diagnosed | Invoke |
|---|---|
| Ingest | `Skill("knowledgebase-ingest")` |
| Manage | `Skill("knowledgebase-manage")` |
| Organize | `Skill("knowledgebase-organize")` |
| Search | `Skill("knowledgebase-search")` → auto-upgrades to enterprise if blind |
| Search-Enterprise | `Skill("knowledgebase-search-enterprise")` |
| Verify | `Skill("knowledgebase-verify")` |
| List | `Skill("knowledgebase-list")` |
| Batch | `Skill("knowledgebase-batch")` |
| Experience | `Skill("knowledgebase-experience")` |
| Graph | `Skill("knowledgebase-graph")` |
| Mixed | Organize→Verify→Ingest→Manage→List order |
