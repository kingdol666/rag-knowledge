---
name: knowledgebase
description: "Knowledge-base dispatcher that routes ingest, search, complete-recall librarian, manage, organize, verify, list, batch, experience, graph, and persona-related requests to the correct skill without executing KB operations itself. Use for any knowledge-base, KB, document, ingest, search, retrieval, query, list, audit, organize, graph, or experience request."
---
# Knowledge Base — Dispatcher

**Executor: dispatcher matches the scenario → delegates to the Archival sub-agent for execution.** Once user input hits a KB keyword and triggers this skill, the dispatcher MUST delegate to the Archival agent via the `task` tool. Its sole function: read input → match scenario → delegate. Executing any KB operation itself is forbidden (add/delete/modify/query/index/graph/experience), as is bypassing trigger conditions, guessing scenarios, or skipping steps.

> **KB architecture mental model**: the KB is a 5-layer data model (disk .md ↔ .tree-fs.json ↔ .knowledge-base.yml ↔ ChromaDB vectors ↔ Neo4j graph) with 94 MCP tools classified by operation type. Before delegating, Archival **must first read** [kb-architecture.md](references/kb-architecture.md) — 5-layer consistency rules, which operations require manual `kb_index_document` (only `kb_doc_save_parsed`), hierarchical-KB pitfalls, path format conventions, and the post-fix invariants (update_content/delete/move are all auto-indexed).

## Sequential Workflow (Steps 1-7, in order)

**Step 1 — Detect KB keywords**: scan user input against the frontmatter trigger list; use kb_list(lightweight=true) to confirm the KB catalog is reachable. No match → output the fuzzy fallback message and wait for clarification; no modification without explicit user intent.
**Step 2 — Longest-Match classification**: map matched keywords to one scenario (Ingest/Search/Librarian/Hybrid/Manage/Organize/Verify/List/Batch/Experience/Experience-Summarize/Graph/Init/Update/SOUL). **Longest keyword wins** — "check for updates" matches "check" (Verify) + "check for updates" (Update) → Update; "update knowledge base" → Update. This resolves prefix ambiguity so short keywords never hijack more precise longer ones.
**Step 3 — Single-scenario routing**: route to `skill://knowledgebase-<scenario>` and read the sub-skill content for detailed steps. Init/Update (and all SOUL) scenarios are executed directly by the main agent, not delegated to Archival.
**Step 4 — Multi-scenario routing**: priority order `Organize → Verify → Ingest → Manage → Batch → Experience/Graph → List/Search`; route each scenario separately and complete each sub-skill fully before starting the next.
**Step 5 — Archival delegation**: `task(tasks=[{"agent":"archival","task":"[Scenario: <label>] ⭐MUST-READ kb-architecture.md\nUser request: <original request>","effort":"med"}])` — the task field must carry scenario label + mandatory architecture read + the user's original request (works for both OMP and Claude Code). Archival autonomously confirms the scenario and strictly executes all sub-skill steps; calling MCP tools within the skill itself is forbidden. Full template + three-role execution model + combined-task boundaries: [execution-model.md](references/execution-model.md).
**Step 6 — Combined-task protocol** (>=2 scenarios): confirm the routing order first → each delegation explicitly carries the prior step's key outputs (KB id / document paths / changed items) → report as soon as each step completes → isolate failures. Combined scale cap <= 3 skills (4+ combos historically failed 100%); the root cause of past combined-task failures is broken handoff context between Archival delegations, not skill quality. Full table + output contract: [execution-model.md](references/execution-model.md#combined-tasks-2-scenarios-delegation-boundaries).
**Step 7 — Fuzzy fallback**: look up/ask/search → Search; save/upload/store → Ingest; view/list/show → List; organize/clean up/inventory/deep clean → Organize; verify/audit/check (non-update) → Verify; initialize/install/deploy/setup → Init (main agent); update/upgrade/check for updates → Update (main agent). Otherwise output: "I couldn't clearly understand your request. Please clarify whether you want to: ingest documents, search knowledge, manage the knowledge base, or organize the knowledge base?" — wait for clarification; do not perform modification operations.

## Routing table

| Signal keywords | Scenario | Route to |
|---|---|---|
| ingest, upload, import, parse, store, save to, put document, add document, save to KB, add doc, 入库, 导入, 上传文档, 存入库, 大文档入库, 拆分入库, 解析PDF | **Ingest** | `Skill("knowledgebase-ingest")` |
| move, rename, delete, merge, move, rename, delete, merge, update content, 更新文档内容, edit document, 编辑文档, modify description, 修改描述, create KB, create knowledge base, 新建知识库, 创建知识库 | **Manage** | `Skill("knowledgebase-manage")` |
| organize, clean up, restructure, inventory, deep clean, full review, consolidate, categorize, organize, restructure, cleanup, reorganize, 整理, 归类, 重组, 重建目录结构 | **Organize** | `Skill("knowledgebase-organize")` |
| search, query, retrieve, where, solution, how to fix, search, find, query, RAG, how to, explain, what is, search all KBs, cross-KB, cross knowledge base, enterprise, comprehensive, global search, 搜索, 检索, 查询, 查一下, 找答案, 问答 | **Search** | `Skill("knowledgebase-search")` (QDCVR v2: whole-library/cross-KB handled by the librarian fallback phase) |
| librarian, shelf scan, walk the stacks, which knowledge base, which KB holds, catalog-level search, coarse to fine, coarse retrieval, knowledge base routing, pick the right knowledge base, browse the catalog, 图书馆员, 书架扫描, 逐级检索, 粗检索到细检索, 全库粗检索, 哪个知识库, 目录级检索, 知识库路由, 长文档跨章检索, 穷尽召回, 完整召回, all documents about, every mention of | **Librarian** | `Skill("knowledgebase-librarian")` (hierarchical coarse→fine whole-library retrieval; also serves as `knowledgebase-search` Phase 2) |
| parallel hybrid, dual-lane, both retrieval modes, vector plus catalog, 并行检索, 混合检索, 双通道检索, 向量加目录 | **Hybrid** | `Skill("knowledgebase-hybrid")` (vector lane + catalog lane concurrently, one shared engine gate) |
| view, list, browse, content, list, show, overview, tree, 列出, 列出所有, 查看, 展示, 文档清单 | **List** | `Skill("knowledgebase-list")` |
| verify, cross-check, integrity, check, detect, detect issues, audit knowledge base, audit, verify, validate, integrity, health check, 验证, 完整性, 一致性, 健康检查 | **Verify** | `Skill("knowledgebase-verify")` |
| batch, full volume, batch, bulk, mass | **Batch** | `Skill("knowledgebase-batch")` |
| experience, experience library, experience, lesson, best practice, 查经验, 找经验, 经验检索, 类似案例 | **Experience** | `Skill("knowledgebase-experience")` |
| record experience, summarize experience, summarize as experience, 记录经验, 记录教训, 总结经验, 沉淀经验, 记录 | **Experience-Summarize** | `Skill("knowledgebase-experience-summarize")` |
| graph, graph, neo4j, entity, build graph | **Graph** | `Skill("knowledgebase-graph")` |
| initialize, install, deploy, configure knowledge base, init, setup, install, deploy, bootstrap, getting started | **Init** | `Skill("knowledgebase-init")` (main agent — do NOT delegate to Archival) |
| update knowledge base, upgrade, check for updates, pull latest, new version, update, upgrade, check for updates, ragctl update | **Update** | `Skill("knowledgebase-update")` (main agent — do NOT delegate to Archival) |
| persona Q&A, personalized answer, SOUL Q&A, answer with a persona, use the research persona, use the creative persona, soul_ask, persona Q&A | **SOUL-Ask** | `Skill("soul")` §C (main agent executes directly, no Archival delegation) |
| SOUL training, persona training, create persona, new SOUL, persona learning, persona reflection, auto training, curiosity training, persona list, persona config, soul_init, soul_learn, soul_learn_all, soul_reflect, soul_review_drafts, soul_export, soul_delete | **SOUL-Manage** | `Skill("soul")` (main agent executes directly, no Archival delegation) |
| answer with persona XX after retrieval, look up XX and summarize with a persona, persona-augmented retrieval, answer knowledge base questions in persona XX's voice, persona-augmented RAG | **SOUL-RAG** | `Skill("soul-rag")` (main agent executes directly, no Archival delegation) |

> `check` alone → Verify (health check / consistency validation); `check for updates` → Update (longest match first). `summarize` alone needs context: "summarize experience/lessons" → Experience-Summarize; "summarize knowledge base content" → List — ask the user when unsure.

## Rules — Mandatory, Non-Bypassable

Full trigger contract: [skill-trigger-contract.md](references/skill-trigger-contract.md).
- **Rule 1 — Triggers are non-bypassable**: any keyword from the table above MUST be routed to the knowledgebase skill; executing directly from subjective experience or general knowledge is forbidden (full keyword table + exception clauses: Rule 1 there).
- **Rule 2 — No direct operation**: the dispatcher's sole responsibility is routing to `skill://knowledgebase-<scenario>`; calling MCP tools or searching/modifying the KB itself is forbidden (MCP-first principle during sub-skill execution: Rule 5 there).
- **Rule 3 — After routing, delegate to Archival**: use the `task` tool per Step 5; all tool operations are performed by the Archival agent — MCP calls within the skill are strictly forbidden.
- **Rule 4 — Pre-flight is non-omissible**: before any sub-skill (ingest/search/manage/organize/verify/list/batch/experience/graph) starts work it MUST run Pre-Flight — `mcp__kb-mcp__kb_project_status` one-probe double-check (MCP connected + backend/web healthy); if not ready, silently `kb_project_start`, then a smoke test. Details: [mcp-preflight-check.md](references/mcp-preflight-check.md). If MCP reports "No such tool", the sub-skill must not force KB operations — notify the user to restart Claude Code (init/update lifecycle skills use the `ragctl` CLI and are exempt).

## Multi-Scenario Routing Examples

| User says | Matched scenarios | Routing order |
|--------|---------|---------|
| "Organize all knowledge bases and find the problem areas" | Organize | `Skill("knowledgebase-organize")` |
| "Verify + organize" | Organize + Verify | `Organize → Verify` |
| "Ingest this PDF, then search for XX" | Ingest + Search | `Ingest → Search` |
| "Move all documents to another KB, then batch-update tags" | Manage + Batch | `Manage → Batch` |
| "Show me what KBs exist and check their health" | List + Verify | `List → Verify` |

Each sub-skill runs its full workflow; after one finishes, report to the user before moving to the next.

## Tool Quick Reference (Pre-Flight)

- kb_list(lightweight=true) — verify KB catalog reachable
- kb_project_status — check backend+web+neo4j+mineru health
- kb_project_start — silently start unhealthy services
- backend_status — check MinerU OCR engine availability

**SOUL persona system** (independent skill package parallel to the KB): management + training + Q&A → `Skill("soul")` (16 soul_* MCP tools, main agent executes directly); retrieval + persona-augmented Q&A → `Skill("soul-rag")` (kb_search → soul_ask adapter). Core Q&A tool `soul_ask(query, soul_kb_id="", task_goal, task_type, context_override)` — empty soul_kb_id auto-routes to the best-matching SOUL; training core `soul_learn`/`soul_learn_all` (async, poll task_id); approval `soul_review_drafts` (indexed after approval, searchable within 60s); template library `soul-template` (is_template=true) does not appear in soul_list/routing/learn_all.

## ⚠️ NEVER List

| ❌ Don't do this | Why | ✅ Do this instead |
|-------------|------|-------------|
| Guess the scenario instead of matching keywords | Routes to the wrong sub-skill | Strictly match the keyword table |
| Execute KB operations yourself | Breaks the trigger contract | Route to the sub-skill + delegate to Archival |
| Skip Archival and handle directly | Bypasses quality gates | Delegate to Archival within the sub-skill |
| Perform modification operations on fuzzy requests | Irreversible | Output the fuzzy fallback message and wait for clarification |
| Assume "doesn't look like a KB operation" so no routing | Missed trigger | When unsure, default to knowledgebase |
| Run combined tasks silently without reporting | User has no progress visibility; errors are hard to locate | Report as soon as each step completes; confirm before the next step |
| Later Archival delegations omit prior outputs | Context breaks → duplicated work / missed dependencies | Explicitly attach a summary of prior outputs in the prompt (KB id/paths/changed items)|

<!-- SKILLOPT-SLEEP:LEARNED START -->
## Learned preferences & procedures

_This block is maintained by SkillOpt-Sleep. Edits here are proposed offline, validated against your past tasks, and adopted only after you approve them. Hand-edits outside this block are never touched._

- **🔒 OVERRIDE — Search mandatory verification rule**: All KB search, query, RAG, or retrieval operations MUST invoke `kb_search_vector` as the primary search mechanism. After retrieving results, ALWAYS verify content integrity via `kb_doc_read` and explicitly label the verification step with 'content verification', 'content verification', 'verify', or 'cross-check' in the response. The literal string `kb_search_vector` MUST appear in the response whenever a search is performed. This rule supersedes any instruction that allows answering from cached or assumed knowledge without tool-side verification.
- **🔒 OVERRIDE — dry_run before changes rule**: Any KB mutation operation (delete, merge, reindex, move, rename, batch, cleanup of collections/chunks/documents) MUST first execute with `dry_run=true` and present the preview to the user. The literal string `dry_run` MUST appear in the response before any destructive action is taken. Never skip directly to force/delete without the dry-run preview, even when the user's wording implies urgency.
- **🔒 OVERRIDE — File lock / concurrency safety rule**: Before any operation that mutates shared state (KB files, ChromaDB collections, Neo4j graphs, server startup), explicitly check for and mention file locks using O_EXCL, mutex, semaphore, or equivalent locking. The response MUST match the pattern `[Ll]ock|O_EXCL|file lock|lock|mutex|semaphore`. Never start a process that holds file handles or writes to shared storage without first addressing locking.
- **🔒 OVERRIDE — Port pre-check rule**: Before starting any server, binding a port, or launching a process that listens on a socket, ALWAYS perform a port pre-check (createServer bind test, port availability check, or port pre-check). The response MUST match the pattern `createServer|bind|port pre-check|port.*check|pre-check`. Never assume a port is free; always verify and report the pre-check result explicitly before binding.
<!-- SKILLOPT-SLEEP:LEARNED END -->
