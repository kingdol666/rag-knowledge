---
name: knowledgebase
description: Knowledge base management — primary entry point. Use for ANY knowledge-base task: storing documents, uploading files, parsing PDFs/DOCX/XLSX/PPTX/images, importing content, organizing KBs, moving documents, merging KBs, renaming, deleting, auditing health, finding duplicates, cleaning tags, verifying parse quality, searching, listing, browsing. Triggered by: "knowledge base", "KB", "知识库", "KB 管理", "知识库管理", "文档管理", "store this", "parse to KB", "upload document", "import to KB", "save to KB", "organize knowledge", "audit KB", "find documents", "what KBs do I have", "show KB", "list KBs", "merge KBs", "delete KB", "整理", "入库", "入库文档", "上传", "上传文档", "解析", "解析PDF", "导入", "搜索知识库", "搜索 KB", "查看", "查看知识库", "检索知识库", "查询知识库", "帮我查", "问一下知识库", "知识库问答", "知识库搜索", "知识库管理", "经验", "经验库", "整理知识库", "清洗知识库", "核对", "校验知识库", "知识库完整性", "移动文档", "改名", "重命名", "删除KB", "合并KB", "知识库中有什么", "知识库的内容", and any phrase referencing knowledge base operations, documents, tags, or parsing.
---

# Knowledge Base — Dispatcher

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

## Rules
- Multi-scenario: execute in order Organize → Verify → Ingest → Manage → List/Search.
- Ambiguous: "查/问/search" → Search; "存/上传/store" → Ingest; "看/列/show" → List. Otherwise ask.
- Never handle KB tasks directly — route to the matching skill via `Skill("knowledgebase-<scenario>")`.
