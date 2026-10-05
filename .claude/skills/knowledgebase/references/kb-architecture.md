# Knowledge Base Architecture — System Data Model & Operational Mental Model

> ⭐ **MUST-READ before any KB operation**. This document explains THIS system's knowledge base architecture (not generic KB concepts).
> The agent must understand this 5-layer data model to operate correctly — otherwise it will break consistency.

## 5-Layer Data Model

```
User documents (.md)
    │  kb_doc_create / kb_doc_save_parsed / kb_doc_update_content
    ▼
① Disk layer (storage/tree-file-system/<KB>/<doc>.md)
    │  Raw markdown files — the single source of truth for content
    │
    │  File-tree CRUD auto-sync
    ▼
② .tree-fs.json (global tree index: all folders + files + metadata)
    │  kb_list / kb_get_documents / fs_get_tree read here
    │
    │  Document CRUD within a KB auto-sync
    ▼
③ .knowledge-base.yml (per-KB document index: name/description/path/tags/vector_index)
    │  kb_search / kb_tags_list read here
    │
    │  kb_index_document / kb_batch_index write here
    ▼
④ ChromaDB (vector store: kb_<UUID> collection, document chunk vectors)
    │  kb_search_vector / kb_search_two_stage query here
    │
    │  kb_graph_build writes here
    ▼
⑤ Graph store (knowledge graph: Document/Tag/KB nodes + RELATED_TO/HAS_TAG edges — Neo4j or built-in graph store)
    │  kb_graph_* query here
```

> ⚠️ The graph supports **Neo4j** and the **built-in graph store** (automatic downgrade when Neo4j is absent). The `neo4j_available` flag in `kb_graph_stats`: true = Neo4j connected, false = built-in graph store. The kb_graph_* tools work normally in both modes.

## Consistency Invariants (atomicity guarantees)

**Every MCP CRUD call atomically updates ①②③** (the backend guarantees three-layer sync). Layers ④⑤ (vectors + graph) behave as follows:

| Operation | Auto-sync | Vector layer ④ | Graph layer ⑤ | Notes |
|------|---------|---------|---------|------|
| `kb_doc_create` | ①②③ | ✅ Automatic (fire-and-forget auto-index) | ✅ Automatic | Background auto-indexing after creation |
| `kb_doc_save_parsed` | ①②③ | ❌ Requires manual `kb_index_document` | ❌ Manual required | **Note: unlike create, does NOT auto-index** |
| `kb_doc_update_content` | ①③ | ✅ Automatic (auto-reindex, <1s) | ✅ Automatic | Vectors are recomputed automatically after content changes; new content is searchable immediately |
| `kb_doc_update_tags` | ③ | Does not affect ④ | ✅ Automatic (triggers graph reindex) | Tag changes sync to the graph |
| `kb_doc_move` | ①②③ | ✅ Automatic (re-indexed at destination) | Source side cleaned automatically | Destination is auto-indexed after the move |
| `kb_doc_delete` | ①②③ | ✅ Chunks cleaned automatically | ✅ Graph nodes cleaned automatically | Deletion is thorough (no vector residue left behind) |
| `kb_doc_batch_delete` | ①②③ | ✅ Automatic | ✅ Automatic | Same as single delete |

> ⚠️ **The only scenario that requires manual re-indexing**: `kb_doc_save_parsed` (after ingesting parsed output you must explicitly call `kb_index_document`).
> The old description "update_content/delete/move require manual re-indexing" is **outdated** — these operations now manage layers ④⑤ automatically.
>
> ⚠️ **Concurrent index safety**: auto-index and explicit `kb_index_document` are now serialized with a per-collection write lock; there is no race. If you still hit "index exists but search finds nothing", `kb_reindex(force=true)` fixes it.

## KB Hierarchy

```
Top-level KB (高分子双向拉伸文献库)
├── Sub-KB (03_PET_BOPET - 聚酯双向拉伸)    ← isKnowledgeBase=true
│   └── Document (PET-deformation-2022.md)
├── Sub-KB (04_PVA_BOPVA - 聚乙烯醇双向拉伸)
│   └── Document (...)
└── Direct documents (cross-domain-review.md)      ← the parent KB's own documents
```

**Key pitfalls** (⭐ verified in practice):
- ⭐ **`kb_doc_update_content` re-indexes automatically** (older versions required manual re-indexing; auto-reindex is now built in).
- ⭐ **`kb_doc_save_parsed` does not auto-index** (unlike create, you must explicitly call `kb_index_document`).
- ⭐ **`experience_search_smart` supports a kb_id parameter** to restrict the search to a single KB.
- ⭐ **`kb_search_two_stage`'s stage2_top_k is strictly honored**.
- ⭐ **Junk-tag content gate**: pure numbers / single characters / section headings are rejected (returns 400).
- **A parent KB's `kb_search_two_stage` returns sub-KB container entries (empty content)** → the correct approach: retrieve real content with **`kb_search_vector(kb_id=<parent KB>)`**. ⚠️ Current version: sub-KB document vectors are stored in the **sub-KB's own collection** (`kb_<sub-KB UUID>`), so searching the sub-KB UUID directly also returns results (the old description "sub-KB vectors live in the parent collection and searching the sub-KB UUID returns 0" is outdated); parent-KB search aggregates all descendant documents. `kb_graph_kb_overview(kb_id)` is only for viewing sub-KB structure/document counts and **must not** be used as a search entry point.
- `kb_get_documents(lightweight=true)` has no type field to distinguish documents vs sub-KB containers → use `file_type: knowledge-base` or `fs_get_tree(max_depth=2)` to tell them apart
- `kb_graph_kb_overview.related_kbs[].name` and `sub_kbs[].name` return UUIDs → use `kb_list(lightweight=true)` to resolve readable names

## Map of the 94 MCP Tools (by operation type)

| Category | Count | Representative tools | When to use |
|------|--------|---------|--------|
| **KB CRUD** | 5 | `kb_list` `kb_create` `kb_update` `kb_delete` `kb_get_documents` | Create/list/delete KBs |
| **Document read/write** | 8 | `kb_doc_read` `kb_doc_create` `kb_doc_save_parsed` `kb_doc_update_meta` `kb_doc_update_content` `kb_doc_delete` `kb_doc_batch_delete` `kb_doc_move` | Document CRUD (`save_parsed` stores parsed output) |
| **File system** | 3 | `fs_get_tree` `fs_get_children` `fs_upload_file` | Tree structure / raw files |
| **Parsing** | 3 | `parse_doc` `parse_doc_batch` `parse_task_status` | PDF→MD (non-blocking) |
| **Tags** | 4 | `kb_tags_list` `kb_doc_update_tags` `kb_doc_get_by_tag` `kb_tags_cleanup` | Tag management |
| **Search** | 4 | `kb_search` `kb_search_vector` `kb_search_two_stage` `kb_search_stats` | Keyword / vector / two-stage / stats |
| **Vector indexing** | 6 | `kb_index_document` `kb_batch_index` `kb_reindex` `kb_cleanup_orphan_collections` `kb_find_duplicates` `kb_task_status` | Index management + task polling |
| **Graph** | 11 | `kb_graph_search` `kb_graph_build` `kb_graph_kb_overview` `kb_graph_document` ... | Neo4j knowledge graph |
| **Experience** | 20 | `experience_search_smart` `experience_search_global` `experience_create` `experience_rerank` ... | Experience-KB full lifecycle (E0–E12) |
| **Meditation** | 6 | `experience_meditation_status` `experience_meditation_run` `experience_meditation_task_status` `experience_meditation_config_get/update` `experience_meditation_history` | Automatic experience synthesis (the experience subsystem's scheduler) |
| **Project** | 4 | `backend_status` `kb_project_status` `kb_project_start` `kb_project_update` | Service lifecycle |
| **🧠 SOUL persona** | **17** | `soul_init` `soul_learn` `soul_ask` `soul_qdcvr_ask` `soul_router` `soul_list` ... | Persona creation/training/Q&A/evaluation/export |
| **Health** | — | (merged into Project) | Pre-checks (`backend_status`) |

> 94 tools in total (77 KB core + 17 SOUL persona; per the measured `grep -c '@mcp.tool' kb-mcp/server.py`, calibrated 2026-09-09). `kb_doc_save_parsed` spans parsing + writing (parsed output is written to disk and ingested) and is classified under document writes to avoid double counting. The 6 Meditation tools (status/run/task_status/config_get/config_update/history) are the automatic synthesis subsystem of Experience. `kb_find_duplicates` is classified under vector indexing (vector-similarity-based duplicate detection). The SOUL persona system provides a complete distill (Butian) → train → Q&A → evaluate → export (LoRA) persona lifecycle.

> **Write-path principle**: write operations (create/update/delete/move) MUST go through MCP tools (HTTP → backend → atomic three-layer update). Read operations may read files directly, but MCP tools are recommended to guarantee consistency.

## Pre-Operation Check Contract

**Before any KB operation**, the agent must first confirm:
1. `mcp__kb-mcp__backend_status()` → backend healthy + MinerU available
2. If the operation spans multiple documents/KBs → first run `kb_list(lightweight=true)` to build a global picture
3. If it is a write operation → confirm the target KB exists (`kb_list` or `fs_get_tree`)

## Path Format Conventions

- `kb_get_documents` returns **backslash** paths on Windows (`KB\doc.md`)
- `kb_graph_*` uses **forward-slash** paths (`KB/doc.md`)
- `kb_doc_read` accepts both
- **Normalize to forward slashes when passing paths between tools** to avoid misses
