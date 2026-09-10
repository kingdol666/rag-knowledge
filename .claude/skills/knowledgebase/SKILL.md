---
name: knowledgebase
description: >
  Knowledge base management — primary entry point and dispatcher. Routes user requests to the correct sub-skill based on scenario matching (ingest, search, manage, organize, verify, list, batch, experience, graph). NEVER handles KB operations directly. Triggered by: knowledge base, KB, document management, ingest, upload, parse, search, retrieval, view, organize, verify, experience, graph, batch, store, upload, parse, search, find, query, list, show, verify, audit, organize, experience, graph, batch, and any knowledge base operation phrase.
---

# Knowledge Base — Dispatcher

**Executor: dispatcher matches the scenario → delegates to the Archival sub-agent for execution**
- Once user input hits a KB keyword and triggers this skill, the dispatcher MUST delegate to the Archival agent
- The dispatcher's sole function: read input → match scenario → delegate to Archival via the `task` tool
- The dispatcher is strictly forbidden from executing any KB operation itself

> **⭐ KB architecture mental model**: This system's knowledge base is a 5-layer data model (disk .md ↔ .tree-fs.json ↔ .knowledge-base.yml ↔ ChromaDB vectors ↔ Neo4j graph), with 72 MCP tools classified by operation type. Before delegating, Archival **must first read** [kb-architecture.md](references/kb-architecture.md) to establish the correct mental model — understanding the 5-layer consistency rules, which operations require manual `kb_index_document` (only `kb_doc_save_parsed`), the pitfalls of hierarchical KBs, path format conventions, and the **post-fix invariants** (update_content/delete/move are all auto-indexed).

## Mission (Mandatory Rules)

Strict router — sole responsibility: **read input → match scenario → delegate to Archival**.

Executing any knowledge base operation itself is forbidden (add/delete/modify/query/index/graph/experience — all forbidden).
Bypassing trigger conditions, guessing scenarios, or skipping steps is forbidden.

---

## Mental Framework: Scenario Classification ⭐

```
The user says something
  └── Contains KB keywords?
       ├── Yes → match the signal keywords in the table below
       └── No → "I couldn't clearly understand your request. Please clarify whether you want to: ingest documents, search knowledge, manage the knowledge base, or organize the knowledge base?"

After a match:
  ├── Clear single scenario → route to the corresponding sub-skill
  ├── Init scenario → the main agent executes `Skill("knowledgebase-init")` directly, without going through Archival
  ├── Multiple mixed scenarios → route in Organize → Verify → Ingest → Manage → List/Search order
  └── Fuzzy fallback → see table below
```

---

## Sequential Workflow
**Step 1 — Detect KB keywords**: scan user input against the trigger keyword list in the frontmatter. Use kb_list(lightweight=true) to confirm the KB catalog is reachable. If nothing matches, output the fuzzy fallback message and wait for clarification.
**Step 2 — Longest-match scenario classification**: using the longest-keyword-first rule, map matched keywords to a single scenario (Ingest/Search/Manage/Organize/Verify/List/Batch/Experience/Graph/Init/Update).
**Step 3 — Single-scenario routing**: route to the corresponding skill://knowledgebase-<scenario> and read the sub-skill content for detailed steps. Init/Update scenarios are executed directly by the main agent, not delegated to Archival.
**Step 4 — Multi-scenario routing**: route in priority order Organize → Verify → Ingest → Manage → List/Search, delegating each scenario separately to Archival for execution.
**Step 5 — Archival delegation**: use the `task` tool to delegate execution to the Archival agent (see the delegation template below); Archival is responsible for autonomously confirming the scenario and strictly executing all steps of the sub-skill.
**Step 6 — Combined-task protocol**: with >=2 scenarios: confirm the routing order first → each subsequent delegation explicitly carries the previous step's key outputs (KB id/document paths/changed items) → report as soon as each step completes → isolate failures.
**Step 7 — Fuzzy fallback handling**: when classification is unclear, apply fuzzy fallback rules: look up/ask/search → Search, save/upload → Ingest, view/list → List, organize → Organize, verify/audit → Verify. If still uncertain, output a clarification question.

## Sequential Processing Steps

### Step 1: Detect KB Keywords
Scan user input for any trigger keyword from the frontmatter trigger list. If no keywords match, output the fuzzy fallback message and wait for clarification. Do not proceed to modification without explicit user intent.

### Step 2: Classify the Scenario
Map matched keywords to a single scenario using the classification table below. Each row maps a set of signal keywords to one scenario and its corresponding sub-skill.

**⭐ Longest-Match-First rule**: when multiple keywords match simultaneously, **the longest keyword wins**. For example, "check for updates" matches both "check" (Verify) and "check for updates" (Update); take the longer "check for updates" → Update. This rule resolves all prefix ambiguity.

| Signal keywords | Scenario | Route to |
|---|---|---|
| ingest, upload, import, parse, store, save to, put document, add document, store, upload, parse, ingest, save to KB, add doc, put document | **Ingest** | `Skill("knowledgebase-ingest")` |
| move, rename, delete, merge, move, rename, delete, merge | **Manage** | `Skill("knowledgebase-manage")` |
| organize, clean up, restructure, inventory, deep clean, full review, consolidate, categorize, organize, restructure, cleanup, reorganize | **Organize** | `Skill("knowledgebase-organize")` |
| search, query, retrieve, where, solution, how to fix, search, find, query, RAG, how to, explain, what is | **Search** | `Skill("knowledgebase-search")` |
| search all KBs, cross-KB, cross knowledge base, cross-KB, enterprise | **Search-Enterprise** | `Skill("knowledgebase-search-enterprise")` |
| view, list, browse, content, list, show, overview, tree | **List** | `Skill("knowledgebase-list")` |
| verify, cross-check, integrity, check, detect, detect issues, audit knowledge base, audit, verify, validate, integrity, health check | **Verify** | `Skill("knowledgebase-verify")` |
| batch, full volume, batch, bulk, mass | **Batch** | `Skill("knowledgebase-batch")` |
| experience, experience library, experience, lesson, best practice | **Experience** | `Skill("knowledgebase-experience")` |
| record experience, summarize experience, summarize as experience | **Experience-Summarize** | `Skill("knowledgebase-experience-summarize")` |
| graph, graph, neo4j, entity, build graph | **Graph** | `Skill("knowledgebase-graph")` |
| initialize, install, deploy, configure knowledge base, init, setup, install, deploy, bootstrap, getting started | **Init** | `Skill("knowledgebase-init")` (main agent — do NOT delegate to Archival) |
| update knowledge base, upgrade, check for updates, pull latest, new version, update, upgrade, check for updates, ragctl update | **Update** | `Skill("knowledgebase-update")` (main agent — do NOT delegate to Archival) |
| persona Q&A, personalized answer, SOUL Q&A, answer with a persona, use the research persona, use the creative persona, persona-augmented retrieval, soul_ask, persona Q&A | **SOUL-Ask** | `Skill("soul")` §C (main agent executes directly, no Archival delegation) |
| SOUL training, persona training, create persona, new SOUL, persona learning, persona reflection, auto training, curiosity training, persona list, persona config, soul_init, soul_learn, soul_learn_all, soul_reflect, soul_review_drafts, soul_export, soul_delete | **SOUL-Manage** | `Skill("soul")` (main agent executes directly, no Archival delegation) |
| answer with persona XX after retrieval, look up XX and summarize with a persona, persona-augmented retrieval, answer knowledge base questions in persona XX's voice, persona-augmented RAG | **SOUL-RAG** | `Skill("soul-rag")` (main agent executes directly, no Archival delegation) |

> **Note**: `check` alone → Verify (health check / consistency validation). `check for updates` → Update (longest match first).
> `summarize` alone requires context: if the context is "summarize experience/lessons" → Experience-Summarize; if "summarize knowledge base content" → List. Ask the user when unsure.

### Step 3: Route to Sub-Skill
Based on classification outcome:
- **Single scenario** — Route to `skill://knowledgebase-<scenario>` (read the skill content for detailed steps).
- **Mixed scenarios** — Follow priority order: Organize → Verify → Ingest → Manage → List/Search. Complete each sub-skill fully before starting the next.
- **Ambiguous / fuzzy match** — Apply fuzzy fallback rules (see Rule 5).

### Step 4: Delegate to Archival Agent via Task Tool
Each sub-skill's SKILL.md must detect the scenario and delegate execution to the Archival sub-agent. The dispatcher's job ends at routing. The Archival agent is responsible for executing all KB operations via MCP tools.

> **⭐ Archival delegation template**: delegate with the `task` tool — the standard `task(tasks=[{"agent":"archival","task":"[Scenario: <label>] ⭐MUST-READ kb-architecture.md\nUser request: <original request>","effort":"med"}])` template + the three-role execution model + combined-task boundaries, unified in [execution-model.md](references/execution-model.md). Delegation core: the `task` field must contain **scenario label + mandatory architecture read reference + the user's original request**; works for both OMP and Claude Code.

---

## Rules — Mandatory, Non-Bypassable

> **Full trigger contract**: [skill-trigger-contract.md](references/skill-trigger-contract.md) (excerpted from CLAUDE.md, containing the five mandatory rules and the MCP-first principle).

### ⭐ Rule 1: Triggers Are Non-Bypassable
If the user request contains any keyword from the table above → it MUST be routed to the knowledgebase skill. Executing directly from subjective experience or general knowledge is forbidden. For the full trigger keyword table + exception clauses, see [skill-trigger-contract.md, Rule 1](references/skill-trigger-contract.md).

### ⭐ Rule 2: No Direct Operation
The dispatcher's **sole responsibility** is routing to `skill://knowledgebase-<scenario>`. Calling MCP tools or searching/modifying the knowledge base itself is forbidden. For the MCP-first principle during sub-skill execution, see [skill-trigger-contract.md, Rule 5](references/skill-trigger-contract.md).

### ⭐ Rule 3: After Routing, Must Delegate to Archival
- Once a sub-skill's SKILL.md detects the scenario, it **MUST delegate to the Archival sub-agent** for execution
- Delegation method: use the `task` tool, `tasks=[{"agent": "archival", "task": "[Scenario: <label>] <user request>"}]` (see the Step 4 template for details)
- Archival is responsible for autonomously confirming the scenario and strictly executing all steps of the sub-skill
- **Strictly forbidden** to call MCP tools within the skill itself; all tool operations must be performed by the Archival agent

### ⭐ Rule 4: Multiple Mixed Scenarios
- Execute in `Organize → Verify → Ingest → Manage → List/Search` order
- Route each scenario separately

### ⭐ Rule 5: Fuzzy Fallback
- "look up/ask/search" → Search
- "save/upload/store" → Ingest
- "view/list/show" → List
- "organize/clean up/inventory/deep clean/organize" → Organize
- "verify/audit/check (non-update)/verify" → Verify
- "initialize/install/deploy/setup" → Init (main agent, no Archival delegation)
- "update/upgrade/check for updates/update" → Update (main agent, no Archival delegation)
- Otherwise output: "I couldn't clearly understand your request. Please clarify whether you want to: ingest documents, search knowledge, manage the knowledge base, or organize the knowledge base?" — wait for clarification; do not perform modification operations

### ⭐ Rule 6: Longest Match First (Resolves Prefix Ambiguity)
- When input matches multiple keywords simultaneously, **the scenario of the longest keyword takes priority**
- Typical case: `check for updates` matches both "check" (Verify) + "check for updates" (Update) → take the longer → **Update**
- Typical case: `update knowledge base` matches both "update" (Update) + "knowledge base" (generic) → take the longer → **Update**
- This rule prevents short prefix keywords from hijacking more precise longer keywords

### ⭐ Rule 7: Pre-Flight Is Non-Omissible (MCP connectivity + service pre-check)
- Before any sub-skill (ingest/search/manage/organize/verify/list/batch/experience/graph/search-enterprise) starts work, it **MUST first run Pre-Flight**: use `mcp__kb-mcp__kb_project_status` for the one-probe double-check (MCP connected + backend/web both healthy); if not ready, silently `kb_project_start` to bring services up, then run a smoke test to confirm connectivity. See [mcp-preflight-check.md](references/mcp-preflight-check.md) for details.
>- If MCP is not connected to this session (reports "No such tool"), the sub-skill **must not** force KB operations; notify the user to restart Claude Code (init/update lifecycle skills use the `ragctl` CLI and are not subject to this constraint).

---

## Multi-Scenario Routing Examples

| User says | Matched scenarios | Routing order |
|--------|---------|---------|
| "Organize all knowledge bases and find the problem areas" | Organize | `Skill("knowledgebase-organize")` |
| "Verify + organize" | Organize + Verify | `Organize → Verify` |
| "Ingest this PDF, then search for XX" | Ingest + Search | `Ingest → Search` |
| "Move all documents to another KB, then batch-update tags" | Manage + Batch | `Manage → Batch` |
| "Show me what KBs exist and check their health" | List + Verify | `List → Verify` |

> For multi-scenario tasks, each sub-skill runs its full workflow. After one finishes, report the result to the user before moving to the next.

## ⭐ Multi-Scenario Combined Execution Protocol (MUST-READ for combined tasks)

> **Diagnosis source** (SkillOpt-Sleep harvest of 36 real tasks): single skills (init/update/architecture) were `[success]`, while combined tasks (experience+summarize / organize+batch / search+enterprise+list) largely `[fail]`. The root cause is not individual skill quality but the **lack of a handoff protocol between skills** — during consecutive Archival delegations, context breaks and prior outputs are not passed in a structured way.

Combined tasks (>=2 scenarios) must follow the 4-phase contract (confirm before routing → delegations carry context → report after each step → isolate failures) + the Archival independent-context boundary + **combined scale cap <= 3 skills** (4+ combos historically failed 100%). For the full table and output contract, see [execution-model.md](references/execution-model.md#combined-tasks-2-scenarios-delegation-boundaries).


---


## Tool Quick Reference
The dispatcher uses these tools for Pre-Flight checks:
- kb_list(lightweight=true) — verify KB catalog reachable
- kb_project_status — check backend+web+neo4j+mineru health
- kb_project_start — silently start unhealthy services
- backend_status — check MinerU OCR engine availability

**SOUL persona system** (persona management/training/evaluation/Q&A — an independent skill package, parallel to the knowledge base):
- Persona management + training + Q&A → `Skill("soul")` (16 soul_* MCP tools; main agent executes directly)
- Retrieval + persona-augmented Q&A → `Skill("soul-rag")` (kb_search → soul_ask combined adapter)
- Template library `soul-template` (is_template=true; does not appear in soul_list/routing/learn_all);
  core persona Q&A tool `soul_ask(query, soul_kb_id="", task_goal, task_type, context_override)`
  — when soul_kb_id is empty, auto-routes to the best-matching SOUL; training core `soul_learn`/`soul_learn_all`
  (async, poll task_id); approval `soul_review_drafts` (indexed after approval, searchable within 60s)

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
