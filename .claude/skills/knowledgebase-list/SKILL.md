---
name: knowledgebase-list
description: >
  Knowledge base listing and discovery. L1→L3 read-only workflow: full inventory (KB names + descriptions + doc counts + tag vocabulary), KB drill-down (document metadata), folder tree browsing. Lightweight methods (kb_list→kb_get_documents with lightweight=true) for progressive disclosure. Never modifies anything. Triggered by: view, list, show, browse, what's there, list it out, inventory, list, show, overview, tree, browse, display, knowledge base content, what's in the knowledge base, view the knowledge base, which knowledge bases exist.
---

## ⭐ Related Skills
- Search & retrieval → `skill://knowledgebase-search`
- KB management → `skill://knowledgebase-manage`
- Organize & restructure → `skill://knowledgebase-organize`
- Verify → `skill://knowledgebase-verify`
- Architecture mental model → [kb-architecture.md](../knowledgebase/references/kb-architecture.md) of `skill://knowledgebase`

## Sequential Workflow
**Step 1 — Pre-Flight check**: run the mcp-preflight-check one-probe double-check to confirm MCP+backend+web health.
**Step 2 — Determine the viewing scope**: full inventory / specific KB drill-down / directory tree browsing / tag query.
**Step 3 — L1 full inventory**: kb_list() → get all KBs' name+description+doc_count → format the output.
**Step 4 — L2 KB drill-down**: kb_get_documents(kb_id) → get the specified KB's document metadata (name/description/tags/file size/parse date).
**Step 5 — L3 directory tree browsing**: fs_get_tree(include_files=true, max_depth=3) → browse the KB hierarchy + document file structure.
**Step 6 — Tag query**: kb_doc_get_by_tag(tag, kb_id) → find related documents across KBs by tag.
**Step 7 — Formatted output**: output per the user's request (table/list/tree/JSON), with doc count/tag coverage/index status statistics.
**Step 8 — Interactive deepening**: pick specific documents from the inventory → kb_doc_read() to view content → support next-step operations (search/manage/organize).

# Knowledge List — Collection Overview

## ⭐ Execution Model · Pre-Flight · Architecture (First Step of Any Job, Mandatory)

**Executor: Archival agent** — delegate via `task` (**delegation template + three-role execution model + combined-task boundaries**: must-read [execution-model.md](../knowledgebase/references/execution-model.md)). **Pre-Flight**: no work before it passes — one-probe double-check `kb_project_status` → branch handling → smoke test; full flow in [mcp-preflight-check.md](../knowledgebase/references/mcp-preflight-check.md). **Mental model**: before operating, must-read [kb-architecture.md](../knowledgebase/references/kb-architecture.md) (5-layer model + consistency invariants + 91-tool map); MCP-first principle (no terminal/HTTP bypass) in [skill-trigger-contract.md](../knowledgebase/references/skill-trigger-contract.md) Rule 5.

## Mental Framework: How Deep Does the User Want to Look? ⭐

User intent determines the display level. Probe the desired granularity with the first response.

```
"Show me what's in the knowledge base"
    │
    ├── "What KBs are there?" → L1 Full Inventory (KB-level overview)
    ├── "What documents are in the KB?" → L2 KB Drill-Down (document list)
    ├── "What does the directory tree look like?" → L3 Browse Tree (file tree)
    └── "Not sure, just browsing" → L1 → decide whether to enter L2 based on the user's reaction
```

### Reporting Depth Strategy
| User question | Display level | Information amount |
|---------|---------|--------|
| "What knowledge bases exist" | L1 | KB name + description + doc count |
| "What's in KB XX" | L2 | Document names + tags + vector index status |
| "Directory structure" | L3 | Full file tree |
| "Show me details of documents in KB XX" | L2 + `kb_doc_read` preview | Document content preview |

---

## L1 — Full Inventory

**Goal**: return a top-level overview of all KBs (names, descriptions, doc counts, tag vocabulary).

**Steps**:

1. `mcp__kb-mcp__kb_list()` — get all KBs: id, name, description, docCount
2. `mcp__kb-mcp__kb_tags_list()` — get the full tag vocabulary
3. `mcp__kb-mcp__fs_get_tree(max_depth=2)` — KB hierarchy structure

Lightweight method: `mcp__kb-mcp__kb_list(lightweight=true)` returns `[{kb_id, name, description, doc_count}]`.

Present as a table: KB Name | Description | Docs.

### Reporting Format
```
📚 Knowledge base overview (N total)
| KB | Description | Docs |
|----|------|--------|
| Embodied-AI | Embodied intelligence | 12 |
| ... | ... | ... |

📌 Tag vocabulary: [tag1, tag2, ...] (N total)
📁 Directory depth: 2 levels
```

## L2 — KB Drill-Down

**Goal**: enter a specific KB to view its document list and metadata.

**Steps**:

1. `mcp__kb-mcp__kb_get_documents(kb_id)` — document metadata: name, path, tags, size, vector_index, dates
2. Check each document's `vector_index` field
3. Provide `mcp__kb-mcp__kb_doc_read()` content previews on demand

Lightweight method: `mcp__kb-mcp__kb_get_documents(lightweight=true, kb_id)` returns `[{doc_path, name, description}]`.

**Note**: the `vector_index` field may be missing (see known issues below). To confirm vector index status, verify with `mcp__kb-mcp__kb_search_vector()`.

## L3 — Browse Tree

**Goal**: display the file system's complete tree structure.

**Steps**:

1. `mcp__kb-mcp__fs_get_tree(include_files=True, max_depth=0)` — 0 = unlimited
2. `mcp__kb-mcp__fs_get_tree()["_stats"]` — folder/file/total statistics

Lightweight method: KB level via `mcp__kb-mcp__kb_list(lightweight=true)`; document level via `mcp__kb-mcp__kb_get_documents(lightweight=true, kb_id)`.

---

## Known Issues

- **Hierarchical KB search returns empty content** — a parent KB's `kb_search_two_stage` returns sub-KB container entries with empty content. **Correct approach**: use `kb_search_vector(kb_id=<parent KB>)` to retrieve real content (sub-KB documents' vector chunks live under the parent KB's collection; searching the sub-KB UUID returns 0). `kb_graph_kb_overview(kb_id)` is only for viewing sub-KB structure, not a search entry point.
- **Vector index metadata may be missing** — some documents' `vector_index` field was not written to YAML after indexing (the vectors actually exist in ChromaDB). Fix with `kb_reindex(kb_id, force=true)` (a write operation; the List flow does not run it automatically).
- **Graph sub-KB nodes show UUIDs only** — `kb_graph_kb_overview`'s sub-KB name field is a UUID, not a readable name. Look up readable names via `kb_list(lightweight=true)`.
- **`kb_graph_build`'s returned `total_relations` may be 0** — this is a stats counting bug; the graph data was actually written to Neo4j. **Do not** assume the build failed because of a 0 return. Spot check with `kb_graph_document(doc_path)`.
- **Tag registry accumulates orphan tags** — the tag list returned by `kb_tags_list()` may contain historical tags with 0 document references. Detect with `kb_tags_cleanup(dry_run=true)`. Does not affect search — document-level tags are filtered automatically.
- **`kb_search_vector` path auto-normalization** — the MCP layer automatically converts backslash paths to forward slashes and dedups by (doc_path, chunk_index). `kb_search_two_stage` results still require manual Agent dedup.
- **⭐ kb-mcp MCP startup check** — before any KB operation, first call `backend_status` to verify MCP connectivity. When MCP is unavailable: ① Bash-check services ② check `.mcp.json` / `.omp/mcp.json` ③ manually start kb-mcp ④ backend healthy but MCP unavailable → notify the user to restart the session ⑤ only use the HTTP API as fallback after the user confirms.

## Storage Model

```
$TREE_STORAGE_PATH/
├── .tree-fs.json                    # global tree structure index
├── {knowledge-base-name}/
│   ├── .knowledge-base.yml          # KB document index (name, description, path, tags)
│   └── doc1.md                      # Markdown document
```
- **Storage path**: read `TREE_STORAGE_PATH` from config.yml (default `./storage/tree-file-system`)
- **Writes** → HTTP API (backend/web proxy)
- **Reads** → direct file access (`.tree-fs.json` + `.knowledge-base.yml`)
- **Three-write atomic consistency**: `fs_upload_file` → updates ①the disk file ②`.tree-fs.json` ③`.knowledge-base.yml` simultaneously. Any layer's failure rolls back the whole operation.

---

## References

- [Knowledge Base Skill Trigger Contract](../knowledgebase/references/skill-trigger-contract.md) — full text in the knowledgebase common references: skill trigger chain, Archival delegation, MCP-first principle

> The reference files above live in the `knowledgebase/references/` directory and remain independently accessible after the plugin is installed globally.

---

## ⚠️ NEVER List

| ❌ Don't do this | Why | ✅ Do this instead |
|-------------|------|-------------|
| Non-read-only operations (modify/delete/move) | List is pure viewing — breaks the user's "just looking" expectation | Read-only; route other operations to Manage/Ingest |
| `fs_get_tree(max_depth=0)` on the whole library | Large libraries (>500 files) serialize 524KB JSON and slow the context | L1 first with `max_depth=2`; only L3 full tree on demand |
| Not showing the tag vocabulary | The user can't tell which domains the knowledge base covers | L1 must show `kb_tags_list()` |
| Trust `doc_count` as the exact document count | Includes sub-KB container entries — actual document count is lower | Filter by `file_type` or use `fs_get_tree` to distinguish |
| Report "not indexed" just because `vector_index` is missing | YAML metadata may be missing — the vectors are actually in ChromaDB | Verify empirically with `kb_search_vector(query, kb_id)` |
| Show sub-KBs as UUIDs | `kb_graph_kb_overview` returns UUIDs — meaningless to the user | Look up readable names via `kb_list(lightweight=true)` |
