---
name: knowledgebase-list
description: "Knowledge base listing and discovery. L1→L3 read-only workflow: full inventory (KB names + descriptions + doc counts + tag vocabulary), KB drill-down (document metadata), folder tree browsing. Lightweight methods (kb_list→kb_get_documents with lightweight=true) for progressive disclosure. Never modifies anything. Triggered by: view, list, show, browse, what's there, list it out, inventory, list, show, overview, tree, browse, display, knowledge base content, what's in the knowledge base, view the knowledge base, which knowledge bases exist."
---
# Knowledge List — Collection Overview

**Executor: Archival agent** — delegate via `task` (delegation template + three-role execution model + combined-task boundaries: must-read [execution-model.md](../knowledgebase/references/execution-model.md)). **Pre-Flight**: no work before it passes — one-probe double-check `kb_project_status` → branch handling → smoke test; full flow in [mcp-preflight-check.md](../knowledgebase/references/mcp-preflight-check.md). **Mental model**: before operating, must-read [kb-architecture.md](../knowledgebase/references/kb-architecture.md) (5-layer model + consistency invariants + 94-tool map); MCP-first principle (no terminal/HTTP bypass) in [skill-trigger-contract.md](../knowledgebase/references/skill-trigger-contract.md) Rule 5.

Related: search & retrieval → `skill://knowledgebase-search` · KB management → `skill://knowledgebase-manage` · organize & restructure → `skill://knowledgebase-organize` · verify → `skill://knowledgebase-verify`. Read-only skill — never modifies anything.

## Sequential Workflow

**Step 1 — Pre-Flight check**: one-probe double-check confirms MCP+backend+web health.
**Step 2 — Determine the viewing scope**: full inventory / KB drill-down / directory tree / tag query.
**Step 3 — L1 full inventory**: kb_list() → all KBs' name+description+doc_count → format the output.
**Step 4 — L2 KB drill-down**: kb_get_documents(kb_id) → document metadata (name/description/tags/file size/parse date).
**Step 5 — L3 directory tree browsing**: fs_get_tree(include_files=true, max_depth=3) → KB hierarchy + document file structure.
**Step 6 — Tag query**: kb_doc_get_by_tag(tag, kb_id) → related documents across KBs by tag.
**Step 7 — Formatted output**: table/list/tree/JSON per the request, with doc count/tag coverage/index status statistics.
**Step 8 — Interactive deepening**: pick documents → kb_doc_read() content preview → support next-step operations (search/manage/organize).

Depth is set by user intent — probe the granularity in the first response: "what KBs are there" → L1 (KB name + description + doc count) · "what's in KB XX" → L2 (doc names + tags + index status; plus a `kb_doc_read` preview when details are asked) · "directory structure" → L3 full tree · "not sure, just browsing" → L1, enter L2 based on the reaction.

## L1 — Full Inventory

1. `mcp__kb-mcp__kb_list()` — all KBs: id, name, description, docCount
2. `mcp__kb-mcp__kb_tags_list()` — full tag vocabulary (L1 must show it)
3. `mcp__kb-mcp__fs_get_tree(max_depth=2)` — KB hierarchy structure

Lightweight: `kb_list(lightweight=true)` returns `[{kb_id, name, description, doc_count}]`.

```
📚 Knowledge base overview (N total)
| KB | Description | Docs |
|----|------|--------|
| Embodied-AI | Embodied intelligence | 12 |

📌 Tag vocabulary: [tag1, tag2, ...] · 📁 Directory depth: 2 levels
```

## L2 — KB Drill-Down

1. `mcp__kb-mcp__kb_get_documents(kb_id)` — metadata: name, path, tags, size, vector_index, dates
2. Check each document's `vector_index` field (may be missing while vectors actually exist — see known issues; verify empirically with `kb_search_vector` before claiming "not indexed")
3. Provide `mcp__kb-mcp__kb_doc_read()` content previews on demand

Lightweight: `kb_get_documents(lightweight=true, kb_id)` returns `[{doc_path, name, description}]`.

## L3 — Browse Tree

1. `mcp__kb-mcp__fs_get_tree(include_files=True, max_depth=0)` — 0 = unlimited (whole-library trees are slow on large libraries — L1 first, full tree only on demand)
2. `mcp__kb-mcp__fs_get_tree()["_stats"]` — folder/file/total statistics

## Known Issues

- **Hierarchical KB search returns empty content** — a parent KB's `kb_search_two_stage` returns sub-KB container entries with empty content. Use `kb_search_vector(kb_id=<parent KB>)` for real content (sub-KB documents' vector chunks live under the parent's collection; searching the sub-KB UUID returns 0). `kb_graph_kb_overview(kb_id)` is for viewing sub-KB structure only, not a search entry point.
- **`vector_index` metadata may be missing** — the vectors exist in ChromaDB but were not written to YAML. Fix with `kb_reindex(kb_id, force=true)` (a write op; the List flow never runs it automatically).
- **Graph sub-KB nodes show UUIDs only** — `kb_graph_kb_overview`'s sub-KB name is a UUID; look up readable names via `kb_list(lightweight=true)`.
- **`kb_graph_build` may return `total_relations` 0** — a stats counting bug; the graph data was actually written to Neo4j. Spot check with `kb_graph_document(doc_path)` — do not assume the build failed.
- **Tag registry accumulates orphan tags** — `kb_tags_list()` may return historical tags with 0 document references; detect with `kb_tags_cleanup(dry_run=true)`. Harmless to search — document-level tags are filtered automatically.
- **`kb_search_vector` path auto-normalization** — the MCP layer converts backslashes to forward slashes and dedups by (doc_path, chunk_index); `kb_search_two_stage` results still require manual Agent dedup.
- **kb-mcp MCP startup check** — before any KB operation, first call `backend_status` to verify MCP connectivity. When MCP is unavailable: ① Bash-check services ② check `.mcp.json` / `.omp/mcp.json` ③ manually start kb-mcp ④ backend healthy but MCP unavailable → notify the user to restart the session ⑤ HTTP API only as a fallback after the user confirms.

## Storage Model

```
$TREE_STORAGE_PATH/
├── .tree-fs.json                    # global tree structure index
├── {knowledge-base-name}/
│   ├── .knowledge-base.yml          # KB document index (name, description, path, tags)
│   └── doc1.md                      # Markdown document
```

Read `TREE_STORAGE_PATH` from config.yml (default `./storage/tree-file-system`). Writes → HTTP API (backend/web proxy); reads → direct file access. `fs_upload_file` three-write atomic consistency: disk file + .tree-fs.json + .knowledge-base.yml update in sync; any layer's failure rolls back the whole operation.

## ⚠️ NEVER List

| ❌ Don't do this | Why | ✅ Do this instead |
|-------------|------|-------------|
| Non-read-only operations (modify/delete/move) | List is pure viewing — breaks the user's "just looking" expectation | Read-only; route other operations to Manage/Ingest |
| `fs_get_tree(max_depth=0)` on the whole library up front | Large libraries (>500 files) serialize 524KB JSON and slow the context | L1 first with `max_depth=2`; only L3 full tree on demand |
| Not showing the tag vocabulary | The user can't tell which domains the knowledge base covers | L1 must show `kb_tags_list()` |
| Trust `doc_count` as the exact document count | Includes sub-KB container entries — actual document count is lower | Filter by `file_type` or use `fs_get_tree` to distinguish |
| Report "not indexed" just because `vector_index` is missing | YAML metadata may be missing — the vectors are actually in ChromaDB | Verify empirically with `kb_search_vector(query, kb_id)` |
| Show sub-KBs as UUIDs | `kb_graph_kb_overview` returns UUIDs — meaningless to the user | Look up readable names via `kb_list(lightweight=true)` |
