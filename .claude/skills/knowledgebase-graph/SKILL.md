---
name: knowledgebase-graph
description: >
  Knowledge graph build, query, and analysis for Neo4j-powered document relationship graph. Based on document metadata (tags, KB membership). Build per KB or globally, query (KB overview, document-centric, cross-KB discovery, keyword search, neighborhood exploration), cleanup (delete document/KB nodes). Triggered by: graph, knowledge graph, graph, knowledge graph, neo4j, entity relationships, entity, relationship, build graph, build the graph, cross-KB, cross knowledge base, document path, document path, central document, core document.
---

# Knowledge Graph — Build, Query, Analyze

## ⭐ Execution Model · Pre-Flight · Architecture (First Step of Any Job, Mandatory)

**Executor: Archival agent** — delegate via `task` (**delegation template + three-role execution model + combined-task boundaries**: must-read [execution-model.md](../knowledgebase/references/execution-model.md)). **Pre-Flight**: no work before it passes — one-probe double-check `kb_project_status` → branch handling → smoke test; full flow in [mcp-preflight-check.md](../knowledgebase/references/mcp-preflight-check.md). **Mental model**: before operating, must-read [kb-architecture.md](../knowledgebase/references/kb-architecture.md) (5-layer model + consistency invariants + 91-tool map); MCP-first principle (no terminal/HTTP bypass) in [skill-trigger-contract.md](../knowledgebase/references/skill-trigger-contract.md) Rule 5.

Graph nodes: `Document`, `KnowledgeBase`, `Tag`. Edges: `BELONGS_TO`, `HAS_SUBKB`, `HAS_TAG`, `RELATED_TO`.

---

## ⭐ Related Skills
- Document ingest & indexing → `skill://knowledgebase-ingest` (A6 vector+graph indexing)
- Batch graph rebuild → `skill://knowledgebase-batch` (B7 whole-library rebuild)
- Cross-library knowledge discovery → `skill://knowledgebase-search-enterprise`
- Architecture mental model → [kb-architecture.md](../knowledgebase/references/kb-architecture.md)

## Sequential Workflow
**Step 1 — Check Neo4j**: kb_graph_stats() confirm neo4j_available is true, otherwise kb_project_start(neo4j=true) to bring it up.
**Step 2 — Choose the query type**: select the operation type per the user request (overview/document query/cross-library discovery/keyword search/build/cleanup).
**Step 3 — KB overview query**: kb_graph_kb_overview(kb_id) → doc_count, sub-KBs, tag distribution, top central documents.
**Step 4 — Document-centric query**: kb_graph_document(doc_path) for all associations / kb_graph_document_related(doc_path) for related documents only.
**Step 5 — Cross-library bridge discovery**: kb_graph_cross_kb_documents(min_kbs=2) → bridge documents → kb_graph_central_documents(kb_id) → central documents.
**Step 6 — Document path query**: kb_graph_document_paths(doc_a, doc_b, max_depth=4) → shortest relationship path between two documents.
**Step 7 — Keyword search**: kb_graph_search(keyword, node_type="all") → substring matching of nodes by name/path.
**Step 8 — Build/rebuild**: kb_graph_build(kb_id, force=false) incremental / force=true full rebuild → kb_graph_stats() verify.
**Step 9 — Cleanup**: kb_graph_delete_document(doc_path) delete a document node / kb_graph_delete_kb(kb_id) delete the entire KB graph.

---

## Mental Framework: First Be Clear About What to Query ⭐

```
[User request] → [Query type] → [Pick tool] → [Build/Query/Clean]
```

| User says | Underlying need | Which flow to pick |
|--------|---------|---------|
| "What does this KB's graph look like" | Overview | KB Overview |
| "What is this document related to" | Document relations | Document-Centric |
| "Any cross-library bridge documents" | Cross-library discovery | Cross-KB Discovery |
| "Help me search graph nodes" | Keywords | Keyword Search |
| "Rebuild the graph" | Build | Build |
| "Deleted a document; the graph is dirty" | Cleanup | Cleanup |

---

## Query Decision Tree

```
What does the user want to query?
    │
    ├── "Overview of this KB"
    │   → kb_graph_kb_overview(kb_id)
    │      (doc_count, sub-KBs, tag distribution, top central docs)
    │
    ├── "What is this document linked to"
    │   → All info: kb_graph_document(doc_path, limit=50)
    │   → Related docs only: kb_graph_document_related(doc_path, limit=20)
    │
    ├── "Cross-KB bridge documents"
    │   → kb_graph_cross_kb_documents(min_kbs=2, limit=50)
    │
    ├── "Central/core documents"
    │   → kb_graph_central_documents(kb_id, top_n=20)
    │
    ├── "Path between two documents"
    │   → kb_graph_document_paths(doc_a, doc_b, max_depth=4)
    │
    ├── "Find documents by tag"
    │   ⚠️ `kb_graph_documents_by_tag` has been removed (returns empty for tags); use `kb_doc_get_by_tag` instead (the graph models tags via doc-doc `RELATED_TO{shared_tag}` edges; no direct tag→doc edges are built)
    │   → **Recommended: `kb_doc_get_by_tag(tag)`** (goes through the YAML registry; reliable; works across skills)
    │
    ├── "Keyword search"
    │   → kb_graph_search(keyword, node_type="all", limit=20)   # ⚠️ the parameter is keyword (not query)
    │     (node_type: all/document/kb/tag — all merges the three result types)
    │
    ├── "Graph health/statistics"
    │   → kb_graph_stats()  # check neo4j_available field — whether Neo4j is available
    │   → kb_graph_stats() — node/edge counts
    │
    ├── "Rebuild the graph"
    │   → kb_graph_build(kb_id="", force=true)
    │     (empty kb_id=whole library; specific kb_id=single KB)
    │
    └── "Clean the graph/delete nodes"
        → kb_graph_delete_document(doc_path) — single document
        → kb_graph_delete_kb(kb_id) — entire KB
```

---

## Build

```
kb_graph_build(kb_id="", force=false)    # empty kb_id=whole library; specific kb_id=single KB (incremental)
```
- `force=false`: skips already-indexed documents (fast)
- `force=true`: full rebuild (use after schema changes/cleanup)

### Post-Build Verification
After the first build or a force rebuild, always verify:
```
kb_graph_stats()       # compare whether node/edge counts are reasonable
kb_graph_kb_overview(kb_id)  # whether doc_count matches the actual document count
```
If `total_relations` is 0 but doc_count is normal → the graph data was actually written; stats has a bug (use `kb_graph_document()` spot checks to confirm).

---

## Global Stats
```
kb_graph_stats()      # node/edge counts, relationship distribution
kb_graph_stats()  # check neo4j_available field     # Neo4j availability check
```

## KB Overview
`kb_graph_kb_overview(kb_id)` — doc count, sub-KBs, tag distribution, related KBs, top central docs.

> **Known display limitation**: `related_kbs[].name` and `sub_kbs[].name` return **UUIDs** instead of readable names. Use `kb_list(lightweight=true)` to look up the UUID→name mapping.

## Document-Centric Query
| Task | Tool |
|---|---|
| Full graph of a doc | `kb_graph_document(doc_path, limit=50)` |
| Related docs only | `kb_graph_document_related(doc_path, limit=20)` |
| Docs by tag | ⚠️ `kb_doc_get_by_tag(tag)` (recommended; goes through YAML); `kb_graph_documents_by_tag` has been removed (always returns empty for tags); use `kb_doc_get_by_tag` |
| Neighborhood exploration | Use `kb_graph_document(doc_path)` — returns related documents including neighbors |

> **Path format**: `kb_graph_*` tools use **forward slash** paths (e.g. `Energy-Batteries/lithium-ion-design.md`). `kb_get_documents` returns **backslash** paths on Windows (e.g. `Energy-Batteries\lithium-ion-design.md`). Normalize to forward slashes when passing parameters across tools.

## Cross-KB Discovery
```
kb_graph_cross_kb_documents(min_kbs=2, limit=50)   # bridge docs
kb_graph_central_documents(kb_id, top_n=20)          # most connected docs
kb_graph_document_paths(doc_a, doc_b, max_depth=4)   # path between two docs
```

## Keyword Search
```
kb_graph_search(keyword, node_type="all", limit=20)   # ⚠️ the parameter is keyword (not query)
# node_type: "all" (default; merges document+kb+tag results) / "document" / "kb" / "tag"
# Returns: {documents:[...], kbs:[...], tags:[...], counts:{documents, kbs, tags}}
```
- ⚠️ **The parameter name is `keyword`**, not `query` (wrong parameter returns Invalid args + a schema hint).
- `node_type="document"` effectively matches by name/path substring.
- ⚠️ **`node_type="tag"` currently returns empty for all tags** (the graph models tags via doc-doc `RELATED_TO{shared_tag}` edges; no direct tag→doc edges are built). To find documents by tag, use `kb_doc_get_by_tag(tag)` (goes through the YAML registry; reliable).
- `node_type="all"` returns all three node types in one call (documents/kbs/tags arrays).

## Cleanup
```
kb_graph_delete_document(doc_path)   # remove single doc node + edges
kb_graph_delete_kb(kb_id)            # remove entire KB from graph
```
Use after deleting documents or KBs to keep graph clean.

## After Document Move
1. `kb_graph_delete_document(doc_path=old_path)` — remove stale node
2. `kb_graph_build(kb_id=target, force=false)` — incremental add to new KB

---

## ⚠️ NEVER List

| ❌ Don't do this | Why | ✅ Do this instead |
|-------------|------|-------------|
| Query without building the graph first | Empty results mislead | First `kb_graph_stats()  # check neo4j_available field` to confirm availability, then query |
| Treat `force=false` as a full rebuild | Incremental only; new schema doesn't fix old data | After schema changes you must use `force=true` |
| Delete documents without deleting graph nodes | Orphan nodes pollute results | After deleting documents you must run `kb_graph_delete_document()` |
| Misread `total_relations=0` | Stats bug; data actually exists | Spot check with `kb_graph_document()` to verify |
| Frequently run `kb_graph_build()` (empty kb_id=whole library) | Heavy; consumes Neo4j resources | Use whole-library only after bulk cleanups; daily use `kb_graph_build(kb_id=...)` per KB |

**⭐ MANDATORY — READ [graph-tools.md](references/graph-tools.md) before any graph build/query operation** — full 14-tool parameter reference with known gotchas per tool.

<!-- SKILLOPT-SLEEP:LEARNED START -->
## Learned preferences & procedures

_This block is maintained by SkillOpt-Sleep. Edits here are proposed offline, validated against your past tasks, and adopted only after you approve them. Hand-edits outside this block are never touched._

- OVERRIDE: Whenever explaining or diagnosing that kb_graph_build returned total_relations=0 but documents were actually indexed (the known stats bug), the response MUST include the EXACT phrase "kb_graph_build returning total_relations=0 is a stats bug, not a build failure; use kb_graph_document to verify the graph data." verbatim. This is NOT optional commentary — it is a required output string that MUST appear whenever this specific scenario is discussed. Supersedes any shorter or paraphrased explanation of the same bug.
- OVERRIDE — verbatim tool plan: whenever a request asks to BUILD a knowledge graph and then QUERY it (e.g., build the graph + graph overview + core document relations), the response MUST contain the exact strings 'kb_graph_build', 'kb_graph_kb_overview', and at least one of 'kb_graph_document' / 'kb_graph_document_related' / 'relation' in the announced plan. Tool names verbatim — paraphrases like 'build the graph', 'view the overview', or 'core document relationships' do NOT satisfy this. Supersedes any instruction to describe steps generically.
- OVERRIDE — plan before pre-flight: the FIRST sentence of any graph-task response must state the concrete planned tool sequence using verbatim MCP tool names (e.g., kb_graph_build then kb_graph_kb_overview then kb_graph_document). Do NOT open with a pre-flight/connectivity sentence alone (e.g., 'First, let me verify MCP connectivity'); pre-flight checks (kb_graph_stats, kb_project_start) still run but are described AFTER the tool-named plan.
- RULE — tool names as identifiers: every step planned or reported for graph work must cite its exact MCP tool name verbatim (kb_graph_stats, kb_graph_build, kb_graph_kb_overview, kb_graph_document, kb_graph_document_related, kb_graph_search, …), never only a generic description of the action; tool names listed in this skill's Sequential Workflow / decision tree must be written exactly as they appear there.
<!-- SKILLOPT-SLEEP:LEARNED END -->
